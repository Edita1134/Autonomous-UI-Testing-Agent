"""Executor: the observe -> think -> act loop that performs each test step.

Guardrails against runaway behaviour (all enforced in code):
  * a hard cap on actions per step
  * a LoopGuard that warns, then aborts, when the agent repeats itself
  * malformed/unknown tool calls are recorded as failed actions, not crashes
  * one self-healing retry per step before giving up
"""

import json
import logging

from agent.llm import prompts
from agent.browser.session import BrowserSession, ToolError
from agent.config import Settings
from agent.reporting.evidence import EvidenceStore
from agent.llm.client import LLMClient, MalformedToolCallError, ToolCall
from agent.pipeline.loop_guard import LoopGuard
from agent.models import ActionRecord, Scenario, StepResult
from agent.llm.tool_schemas import FINISH_STEP, TOOL_SCHEMAS

log = logging.getLogger("agent.executor")


class Executor:
    def __init__(self, llm: LLMClient, browser: BrowserSession, evidence: EvidenceStore, settings: Settings):
        self._llm = llm
        self._browser = browser
        self._evidence = evidence
        self._settings = settings

    def run_scenario(self, scenario: Scenario) -> list[StepResult]:
        """Run a scenario's steps in order; stop at the first step that cannot be completed."""
        results = []
        total = len(scenario.steps)
        for index, instruction in enumerate(scenario.steps, 1):
            label = f"{scenario.criterion.id}.{index}"
            log.info("[%s] STEP %d/%d: %s", scenario.criterion.id, index, total, instruction)
            result = self._run_step_with_healing(label, instruction)
            results.append(result)
            if not result.completed:
                log.info("[%s] Step blocked, skipping remaining steps: %s", label, result.summary)
                break
        return results

    def _run_step_with_healing(self, label: str, instruction: str) -> StepResult:
        result = self._attempt_step(label, instruction)
        if result.completed or not self._settings.self_heal:
            return result
        log.info("[%s] SELF-HEAL: retrying once after failure: %s", label, result.summary)
        # The retry starts fresh, so tell it what the failed attempt already did (it may have succeeded).
        already_done = "\n".join(f"- {action.describe()}" for action in result.actions) or "- (no actions)"
        failure = f"{result.summary}\nActions already taken in that attempt (their effects are on the page now):\n{already_done}"
        retry = self._attempt_step(label, instruction, prior_failure=failure)
        retry.healed = retry.completed
        return retry

    def _attempt_step(self, label: str, instruction: str, prior_failure: str = "") -> StepResult:
        actions: list[ActionRecord] = []
        guard = LoopGuard()
        warned = False

        for _ in range(self._settings.max_actions_per_step):
            snapshot = self._browser.snapshot()
            log.info("[%s] OBSERVE: %s | %s", label, snapshot.url, snapshot.title)
            messages = prompts.executor_messages(instruction, snapshot.render(), actions, prior_failure, warned)

            try:
                reply = self._llm.chat(messages, tools=TOOL_SCHEMAS)
            except MalformedToolCallError as exc:
                actions.append(ActionRecord("invalid_call", {}, "", f"Model sent a malformed tool call: {exc}", False))
                continue
            if not reply.tool_calls:
                actions.append(ActionRecord("no_call", {}, "", "Model returned no tool call.", False))
                continue

            call = reply.tool_calls[0]  # One action per turn keeps the loop easy to follow and debug.
            thought = str(call.arguments.get("thought", ""))
            log.info("[%s] THOUGHT: %s", label, thought)

            if call.name == FINISH_STEP:
                return self._finish(label, instruction, call, actions)

            record = self._perform(call, thought)
            actions.append(record)
            log.info("[%s] ACTION: %s", label, record.describe())
            self._browser.screenshot(self._evidence.screenshot_path(f"{label}_{call.name}"))

            after = self._browser.snapshot()
            signature = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
            if guard.record(signature, after.fingerprint):
                if warned:
                    return StepResult(instruction, False, "Aborted: agent was repeating the same action without progress.", actions)
                log.info("[%s] LOOP DETECTED: warning the agent", label)
                warned = True

        return StepResult(
            instruction, False, f"Aborted: exceeded {self._settings.max_actions_per_step} actions for this step.", actions
        )

    def _perform(self, call: ToolCall, thought: str) -> ActionRecord:
        args = {key: value for key, value in call.arguments.items() if key != "thought"}
        try:
            outcome = self._browser.execute(call.name, args)
            return ActionRecord(call.name, args, thought, outcome, ok=True)
        except ToolError as exc:
            return ActionRecord(call.name, args, thought, str(exc), ok=False)

    def _finish(self, label: str, instruction: str, call: ToolCall, actions: list[ActionRecord]) -> StepResult:
        completed = call.arguments.get("status") == "done"
        summary = str(call.arguments.get("summary", "")).strip() or "(no summary given)"
        log.info("[%s] FINISH: %s - %s", label, "done" if completed else "blocked", summary)
        return StepResult(instruction, completed, summary, actions)
