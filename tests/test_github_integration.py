"""GitHub ticket integration tests with a fake HTTP session."""

import requests

from agent.config import Settings
from agent.models import Verdict
from agent.tickets.github import GitHubClient, _truncate


class FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append((method, url, timeout, kwargs))
        if method == "GET":
            return FakeResponse({
                "title": "Login checkout",
                "body": "Target URL: https://shop.example\n\n## Acceptance Criteria\n- AC1: User can log in",
            })
        if method == "DELETE":
            return FakeResponse(status_code=404)
        return FakeResponse({"ok": True})


def settings(tmp_path):
    return Settings(
        gemini_api_key="test",
        github_repo="owner/repo",
        github_token="secret-token",
        default_target_url="https://default.example",
        evidence_dir=tmp_path,
    )


def test_fetches_and_parses_github_issue(monkeypatch, tmp_path):
    session = FakeSession()
    monkeypatch.setattr(requests, "Session", lambda: session)

    ticket = GitHubClient(settings(tmp_path)).fetch_ticket(42)

    assert ticket.number == 42
    assert ticket.title == "Login checkout"
    assert ticket.target_url == "https://shop.example"
    assert [criterion.id for criterion in ticket.criteria] == ["AC1"]
    assert session.headers["Authorization"] == "Bearer secret-token"
    assert session.calls[0][0:3] == (
        "GET",
        "https://api.github.com/repos/owner/repo/issues/42",
        15,
    )


def test_rejects_pull_request(monkeypatch, tmp_path):
    class PullRequestSession(FakeSession):
        def request(self, method, url, timeout=None, **kwargs):
            self.calls.append((method, url, timeout, kwargs))
            return FakeResponse({"title": "PR", "body": "body", "pull_request": {}})

    session = PullRequestSession()
    monkeypatch.setattr(requests, "Session", lambda: session)

    try:
        GitHubClient(settings(tmp_path)).fetch_ticket(9)
        assert False, "Expected a pull request to be rejected"
    except ValueError as exc:
        assert "pull request" in str(exc)


def test_post_result_comments_and_updates_verdict_label(monkeypatch, tmp_path):
    session = FakeSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    client = GitHubClient(settings(tmp_path))

    client.post_result(42, "## QA Report", Verdict.PASS)

    methods = [call[0] for call in session.calls]
    assert methods[:2] == ["POST", "DELETE"] or methods[0] == "POST"
    comment_calls = [call for call in session.calls if call[0] == "POST" and call[1].endswith("/comments")]
    label_calls = [call for call in session.calls if call[0] == "POST" and call[1].endswith("/labels")]
    assert comment_calls[0][3]["json"] == {"body": "## QA Report"}
    assert label_calls[0][3]["json"] == {"labels": ["qa-passed"]}


def test_missing_github_repo_is_rejected(tmp_path):
    config = Settings(gemini_api_key="test", github_repo="", evidence_dir=tmp_path)

    try:
        GitHubClient(config)
        assert False, "Expected a missing repository error"
    except ValueError as exc:
        assert "GITHUB_REPO" in str(exc)


def test_large_report_is_truncated():
    report = "x" * 60_001

    truncated = _truncate(report)

    assert "report truncated" in truncated
    assert len(truncated) <= 60_000 + len("\n\n... (report truncated; see the run's evidence folder)")
