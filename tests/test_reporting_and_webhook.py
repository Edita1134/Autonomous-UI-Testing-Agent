"""Unit tests for the report verdict roll-up, run-folder naming and webhook signatures."""

import hashlib
import hmac
from datetime import timedelta

from agent.models import AcceptanceCriterion, CriterionResult, Ticket, Verdict
from agent.reporting.evidence import EvidenceStore
from agent.reporting.reporter import RunReport
from agent.triggers.webhook import signature_is_valid


def _report(*verdicts: Verdict) -> RunReport:
    criterion = AcceptanceCriterion(id="AC1", text="Something works")
    ticket = Ticket(number=1, title="T", body="", target_url="https://example.com", criteria=[criterion])
    results = [CriterionResult(criterion, verdict, "reason", "quote", []) for verdict in verdicts]
    return RunReport(ticket=ticket, results=results, model="m", duration=timedelta(seconds=1), video_files=[])


def test_overall_is_fail_if_any_criterion_fails():
    assert _report(Verdict.PASS, Verdict.FAIL, Verdict.BLOCKED).overall is Verdict.FAIL


def test_overall_is_blocked_if_nothing_failed_but_something_is_inconclusive():
    assert _report(Verdict.PASS, Verdict.BLOCKED).overall is Verdict.BLOCKED


def test_overall_is_pass_only_when_every_criterion_passes():
    assert _report(Verdict.PASS, Verdict.PASS).overall is Verdict.PASS


def test_two_runs_in_the_same_second_get_different_folders(tmp_path):
    first = EvidenceStore(tmp_path)
    second = EvidenceStore(tmp_path)
    assert first.root != second.root
    assert second.root.exists()


def test_webhook_signature_accepts_only_the_right_secret():
    body = b'{"action": "labeled"}'
    good = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert signature_is_valid("secret", body, good)
    assert not signature_is_valid("other", body, good)
    assert not signature_is_valid("secret", body, "")
