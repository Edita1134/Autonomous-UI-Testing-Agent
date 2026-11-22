"""Plain data types shared across the agent. No behaviour beyond small helpers."""

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"  # The Acceptance Criterion is met (backed by evidence).
    FAIL = "FAIL"  # The application does not meet the criterion.
    BLOCKED = "BLOCKED"  # The agent could not reach a trustworthy conclusion.


@dataclass(frozen=True)
class AcceptanceCriterion:
    id: str
    text: str


@dataclass(frozen=True)
class Ticket:
    number: int | None
    title: str
    body: str
    target_url: str
    criteria: list[AcceptanceCriterion]


@dataclass(frozen=True)
class Scenario:
    """A criterion plus the natural-language steps generated to check it."""

    criterion: AcceptanceCriterion
    steps: list[str]


@dataclass
class ActionRecord:
    """One tool call the executor made, and what happened."""

    tool: str
    args: dict
    thought: str
    outcome: str
    ok: bool

    def describe(self) -> str:
        args = ", ".join(f"{key}={value!r}" for key, value in self.args.items())
        status = "OK" if self.ok else "FAILED"
        return f"{self.tool}({args}) -> {status}: {self.outcome}"


@dataclass
class StepResult:
    instruction: str
    completed: bool
    summary: str
    actions: list[ActionRecord] = field(default_factory=list)
    healed: bool = False  # True if the step only succeeded on the self-healing retry.


@dataclass
class CriterionResult:
    criterion: AcceptanceCriterion
    verdict: Verdict
    reason: str
    evidence: str
    steps: list[StepResult]
    screenshot: str = ""
