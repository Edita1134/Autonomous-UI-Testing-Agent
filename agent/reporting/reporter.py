"""Builds the final pass/fail report (markdown + JSON) from a finished run."""

import json
from dataclasses import asdict, dataclass
from datetime import timedelta

from agent.reporting.evidence import EvidenceStore
from agent.models import CriterionResult, Ticket, Verdict


@dataclass
class RunReport:
    ticket: Ticket
    results: list[CriterionResult]
    model: str
    duration: timedelta
    video_files: list[str]

    @property
    def overall(self) -> Verdict:
        verdicts = {result.verdict for result in self.results}
        if Verdict.FAIL in verdicts:
            return Verdict.FAIL
        if Verdict.BLOCKED in verdicts:
            return Verdict.BLOCKED
        return Verdict.PASS


def render_markdown(report: RunReport) -> str:
    lines = [
        f"# QA Report: {report.ticket.title}",
        "",
        f"**Overall result: {report.overall.value}**  ",
        f"Target: {report.ticket.target_url}  ",
        f"Model: `{report.model}`  Duration: {int(report.duration.total_seconds())}s",
        "",
        "| AC | Result | Reason |",
        "|----|--------|--------|",
    ]
    lines += [
        f"| {r.criterion.id}: {r.criterion.text} | {r.verdict.value} | {_one_line(r.reason)} |" for r in report.results
    ]
    for result in report.results:
        lines += ["", f"## {result.criterion.id}: {result.verdict.value}", f"*{result.criterion.text}*", ""]
        lines.append(f"- **Reason:** {result.reason}")
        lines.append(f"- **Evidence quoted from page:** `{result.evidence or 'n/a'}`")
        if result.screenshot:
            lines.append(f"- **Final screenshot:** [{result.screenshot}]({result.screenshot})")
        lines.append("- **Steps:**")
        for step in result.steps:
            status = "done" if step.completed else "BLOCKED"
            healed = " (self-healed)" if step.healed else ""
            lines.append(f"  - [{status}{healed}] {step.instruction} - {step.summary}")
    if report.video_files:
        lines += ["", "## Video", *[f"- [{path}]({path})" for path in report.video_files]]
    return "\n".join(lines) + "\n"


def write_report(report: RunReport, evidence: EvidenceStore) -> str:
    """Write report.md and report.json into the run folder; returns the markdown."""
    markdown = render_markdown(report)
    (evidence.root / "report.md").write_text(markdown, encoding="utf-8")
    payload = {
        "title": report.ticket.title,
        "target_url": report.ticket.target_url,
        "overall": report.overall.value,
        "model": report.model,
        "video_files": report.video_files,
        "duration_seconds": int(report.duration.total_seconds()),
        "results": [asdict(result) for result in report.results],
    }
    (evidence.root / "report.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return markdown


def _one_line(text: str) -> str:
    return text.replace("\n", " ").replace("|", "/")
