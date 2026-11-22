"""Verifier: an independent LLM call that judges one acceptance criterion.

Anti-hallucination guardrail: a PASS or FAIL is only accepted if the quoted
evidence really appears in what the agent observed. Otherwise it is downgraded
to BLOCKED instead of trusting a made-up justification.
"""

import logging
import re

from agent.llm import prompts
from agent.llm.client import LLMClient
from agent.models import Scenario, StepResult, Verdict

log = logging.getLogger("agent.verifier")


def is_grounded(quote: str, observed_text: str) -> bool:
    """True if `quote` appears (ignoring case/whitespace) in the observed text."""
    quote = _normalise(quote)
    return bool(quote) and quote in _normalise(observed_text)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class Verifier:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def verify(
        self, scenario: Scenario, steps: list[StepResult], snapshot_text: str
    ) -> tuple[Verdict, str, str]:
        """Returns (verdict, reason, evidence)."""
        try:
            raw = self._llm.chat_json(prompts.verifier_messages(scenario, steps, snapshot_text))
            verdict = Verdict(str(raw.get("verdict", "")).upper())
        except ValueError as exc:  # Invalid JSON or an unknown verdict value.
            return Verdict.BLOCKED, f"Verifier returned an unusable answer: {exc}", ""

        reason = str(raw.get("reason", "")).strip()
        evidence = str(raw.get("evidence", "")).strip()

        if verdict is not Verdict.BLOCKED:
            observed = snapshot_text + "\n" + _steps_as_text(steps)
            if not is_grounded(evidence, observed):
                log.warning("Rejected %s for %s: evidence %r not found in observations", verdict.value, scenario.criterion.id, evidence)
                return Verdict.BLOCKED, f"Verifier said {verdict.value} but its evidence was not found on the page. Original reason: {reason}", evidence
        return verdict, reason, evidence


def _steps_as_text(steps: list[StepResult]) -> str:
    """Tool-generated outcomes only. The executor's own summaries are LLM prose, so not trusted as proof."""
    return "\n".join(action.outcome for step in steps for action in step.actions)
