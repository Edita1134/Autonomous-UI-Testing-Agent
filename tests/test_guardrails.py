"""Unit tests for the code-level guardrails (no network, no browser, no LLM)."""

from agent.pipeline.loop_guard import LoopGuard
from agent.models import AcceptanceCriterion, Scenario, StepResult, Verdict
from agent.pipeline.verifier import Verifier, is_grounded


class FakeLLM:
    def __init__(self, answer: dict):
        self._answer = answer

    def chat_json(self, _messages):
        return self._answer


SCENARIO = Scenario(AcceptanceCriterion("AC1", "badge shows 1"), ["click add"])
SNAPSHOT = 'URL: x\nTitle: Shop\n- link "1"\n- button "Remove"'


def test_loop_guard_triggers_only_after_identical_repeats():
    guard = LoopGuard(limit=3)
    assert not guard.record("click:a", "p1")
    assert not guard.record("click:a", "p1")
    assert guard.record("click:a", "p1")


def test_loop_guard_resets_when_page_changes():
    guard = LoopGuard(limit=3)
    guard.record("click:a", "p1")
    guard.record("click:a", "p1")
    assert not guard.record("click:a", "p2")


def test_is_grounded_ignores_case_and_whitespace():
    assert is_grounded('BUTTON   "remove"', SNAPSHOT)
    assert not is_grounded("Thank you for your order", SNAPSHOT)
    assert not is_grounded("", SNAPSHOT)


def test_verifier_accepts_pass_with_real_evidence():
    llm = FakeLLM({"verdict": "PASS", "evidence": 'link "1"', "reason": "badge is 1"})
    verdict, _, _ = Verifier(llm).verify(SCENARIO, [], SNAPSHOT)
    assert verdict is Verdict.PASS


def test_verifier_downgrades_pass_with_invented_evidence():
    llm = FakeLLM({"verdict": "PASS", "evidence": "Thank you for your order!", "reason": "done"})
    verdict, reason, _ = Verifier(llm).verify(SCENARIO, [], SNAPSHOT)
    assert verdict is Verdict.BLOCKED
    assert "not found on the page" in reason


def test_verifier_survives_unknown_verdict():
    llm = FakeLLM({"verdict": "MAYBE", "evidence": "", "reason": ""})
    verdict, _, _ = Verifier(llm).verify(SCENARIO, [StepResult("s", True, "ok")], SNAPSHOT)
    assert verdict is Verdict.BLOCKED
