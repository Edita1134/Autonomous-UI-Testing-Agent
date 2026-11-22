"""Pipeline tests with a scripted fake LLM and a fake browser: no API key, network or Chromium needed.

They exercise the real Executor, Verifier and guardrails end to end, so a broken guardrail fails here
instead of during a slow, paid live run.
"""

from dataclasses import dataclass

import pytest

from agent.browser.session import PageSnapshot, ToolError
from agent.config import Settings
from agent.llm.client import LLMReply, MalformedToolCallError, ToolCall
from agent.models import AcceptanceCriterion, Scenario, Verdict
from agent.pipeline.executor import Executor
from agent.pipeline.verifier import Verifier
from agent.reporting.evidence import EvidenceStore


def click(name: str = "Login") -> ToolCall:
    return ToolCall("click", {"thought": "go", "role": "button", "name": name})


def finish(status: str = "done", summary: str = "ok") -> ToolCall:
    return ToolCall("finish_step", {"thought": "done", "status": status, "summary": summary})


class FakeLLM:
    """Plays back scripted turns: a ToolCall, a list of them, or an exception to raise."""

    def __init__(self, tool_turns=(), json_turns=()):
        self._tool_turns = list(tool_turns)
        self._json_turns = list(json_turns)
        self.tool_calls_made = 0

    def chat(self, messages, tools=None):
        self.tool_calls_made += 1
        turn = self._tool_turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return LLMReply(content="", tool_calls=turn if isinstance(turn, list) else [turn])

    def chat_json(self, messages):
        return self._json_turns.pop(0)


@dataclass
class FakeBrowser:
    """A page whose text changes after each successful action; clicks can be scripted to fail."""

    fail_clicks: int = 0
    page_text: str = "heading Products"

    def __post_init__(self):
        self.executed = []

    def snapshot(self) -> PageSnapshot:
        return PageSnapshot(url="https://shop.test", title="Shop", tree=f"{self.page_text} #{len(self.executed)}")

    def screenshot(self, path) -> None:
        pass

    def execute(self, action: str, args: dict) -> str:
        if self.fail_clicks > 0:
            self.fail_clicks -= 1
            raise ToolError("No button found")
        self.executed.append((action, args))
        return f"Did {action}"


@pytest.fixture
def settings(tmp_path):
    return Settings(gemini_api_key="test", evidence_dir=tmp_path, max_actions_per_step=3)


def make_executor(settings, llm, browser, tmp_path) -> Executor:
    return Executor(llm, browser, EvidenceStore(tmp_path), settings)


def test_step_completes_when_the_model_acts_then_finishes(settings, tmp_path):
    llm = FakeLLM([click(), finish()])
    result = make_executor(settings, llm, FakeBrowser(), tmp_path)._attempt_step("AC1.1", "Click Login")

    assert result.completed
    assert [action.tool for action in result.actions] == ["click"]


def test_step_is_aborted_after_the_action_cap(settings, tmp_path):
    # Different arguments each time, so the loop guard stays quiet and only the cap can stop it.
    llm = FakeLLM([click(f"Button {i}") for i in range(10)])
    result = make_executor(settings, llm, FakeBrowser(), tmp_path)._attempt_step("AC1.1", "Click something")

    assert not result.completed
    assert "exceeded 3 actions" in result.summary
    assert llm.tool_calls_made == 3


def test_loop_guard_warns_then_aborts_a_repeating_agent(tmp_path):
    settings = Settings(gemini_api_key="test", evidence_dir=tmp_path, max_actions_per_step=20)
    browser = FakeBrowser()
    browser.snapshot = lambda: PageSnapshot("https://shop.test", "Shop", "never changes")  # No progress at all.
    llm = FakeLLM([click() for _ in range(20)])
    result = make_executor(settings, llm, browser, tmp_path)._attempt_step("AC1.1", "Click Login")

    assert not result.completed
    assert "repeating the same action" in result.summary
    assert llm.tool_calls_made < 20


def test_malformed_tool_call_is_recorded_and_the_run_continues(settings, tmp_path):
    llm = FakeLLM([MalformedToolCallError("bad json"), finish()])
    result = make_executor(settings, llm, FakeBrowser(), tmp_path)._attempt_step("AC1.1", "Look at the page")

    assert result.completed
    assert result.actions[0].tool == "invalid_call" and not result.actions[0].ok


def test_failed_action_is_reported_to_the_model_not_raised(settings, tmp_path):
    llm = FakeLLM([click(), click("Sign in"), finish()])
    browser = FakeBrowser(fail_clicks=1)
    result = make_executor(settings, llm, browser, tmp_path)._attempt_step("AC1.1", "Click Login")

    assert result.completed
    assert [action.ok for action in result.actions] == [False, True]


def test_self_healing_retries_a_blocked_step_once(settings, tmp_path):
    llm = FakeLLM([finish("blocked", "could not find it"), finish("done", "found it on retry")])
    result = make_executor(settings, llm, FakeBrowser(), tmp_path)._run_step_with_healing("AC1.1", "Look at the page")

    assert result.completed and result.healed


def test_self_healing_gives_up_after_one_retry(settings, tmp_path):
    llm = FakeLLM([finish("blocked", "nope"), finish("blocked", "still nope")])
    result = make_executor(settings, llm, FakeBrowser(), tmp_path)._run_step_with_healing("AC1.1", "Look at the page")

    assert not result.completed and not result.healed
    assert llm.tool_calls_made == 2


def test_scenario_stops_at_the_first_blocked_step(tmp_path):
    settings = Settings(gemini_api_key="test", evidence_dir=tmp_path, self_heal=False)
    scenario = Scenario(AcceptanceCriterion("AC1", "x"), ["step one", "step two", "step three"])
    llm = FakeLLM([finish("done"), finish("blocked", "stuck")])
    results = make_executor(settings, llm, FakeBrowser(), tmp_path).run_scenario(scenario)

    assert [result.completed for result in results] == [True, False]  # Step three never ran.


def test_verifier_downgrades_a_verdict_whose_evidence_is_not_on_the_page():
    scenario = Scenario(AcceptanceCriterion("AC1", "Products page is shown"), ["Look at the page"])
    invented = {"verdict": "PASS", "reason": "Looks right", "evidence": "Welcome back, Ada"}
    verdict, reason, _ = Verifier(FakeLLM(json_turns=[invented])).verify(scenario, [], "heading Products")

    assert verdict is Verdict.BLOCKED
    assert "evidence was not found" in reason


def test_verifier_accepts_a_verdict_whose_evidence_is_on_the_page():
    scenario = Scenario(AcceptanceCriterion("AC1", "Products page is shown"), ["Look at the page"])
    grounded = {"verdict": "PASS", "reason": "Header visible", "evidence": "heading Products"}
    verdict, _, _ = Verifier(FakeLLM(json_turns=[grounded])).verify(scenario, [], "URL: x\nheading Products")

    assert verdict is Verdict.PASS
