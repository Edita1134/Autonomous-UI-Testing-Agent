"""Orchestrates one full run: plan -> execute -> verify -> report."""

import logging
from datetime import datetime

from agent.browser.session import BrowserSession
from agent.config import Settings
from agent.reporting.evidence import EvidenceStore
from agent.pipeline.executor import Executor
from agent.llm.client import LLMClient
from agent.models import CriterionResult, Ticket
from agent.pipeline.planner import Planner
from agent.reporting.reporter import RunReport, write_report
from agent.pipeline.verifier import Verifier

log = logging.getLogger("agent.runner")


def run_ticket(
    ticket: Ticket, settings: Settings, evidence: EvidenceStore | None = None
) -> tuple[RunReport, str]:
    """Test every acceptance criterion of `ticket`. Returns the report and its markdown.

    Pass your own `evidence` store if you need to know the run folder before the run ends (the UI does).
    """
    started = datetime.now()
    evidence = evidence or EvidenceStore(settings.evidence_dir)
    evidence.start_logging()
    try:
        return _run(ticket, settings, evidence, started)
    finally:
        evidence.stop_logging()


def _run(ticket: Ticket, settings: Settings, evidence: EvidenceStore, started: datetime) -> tuple[RunReport, str]:
    log.info("Run %s: %s (%d acceptance criteria)", evidence.run_id, ticket.title, len(ticket.criteria))

    llm = LLMClient(settings)
    scenarios = Planner(llm).plan(ticket)
    verifier = Verifier(llm)
    results: list[CriterionResult] = []

    with BrowserSession(settings, evidence.video_dir) as browser:
        browser.navigate(ticket.target_url)
        executor = Executor(llm, browser, evidence, settings)
        for scenario in scenarios:
            steps = executor.run_scenario(scenario)

            final_snapshot = browser.snapshot()
            screenshot = evidence.screenshot_path(f"{scenario.criterion.id}_final")
            browser.screenshot(screenshot)

            verdict, reason, quote = verifier.verify(scenario, steps, final_snapshot.render())
            log.info("RESULT %s: %s - %s", scenario.criterion.id, verdict.value, reason)
            results.append(
                CriterionResult(
                    scenario.criterion, verdict, reason, quote, steps, screenshot=evidence.relative(screenshot)
                )
            )

    report = RunReport(
        ticket=ticket,
        results=results,
        model=settings.model,
        duration=datetime.now() - started,
        video_files=[evidence.relative(path) for path in evidence.video_files()],
    )
    markdown = write_report(report, evidence)
    log.info("OVERALL: %s (report: %s)", report.overall.value, evidence.root / "report.md")
    return report, markdown
