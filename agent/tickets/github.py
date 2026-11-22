"""Minimal GitHub REST client: read an issue, post the result back."""

import requests

from agent.config import Settings
from agent.models import Ticket, Verdict
from agent.tickets.parser import parse_ticket

API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 15
MAX_COMMENT_CHARS = 60_000  # GitHub rejects comments over 65,536 characters.

_RESULT_LABELS = {
    Verdict.PASS: "qa-passed",
    Verdict.FAIL: "qa-failed",
    Verdict.BLOCKED: "qa-blocked",
}


class GitHubClient:
    def __init__(self, settings: Settings):
        if not settings.github_repo:
            raise ValueError("GITHUB_REPO is not set (expected 'owner/repo').")
        self._repo = settings.github_repo
        self._default_url = settings.default_target_url
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/vnd.github+json"
        if settings.github_token:
            self._session.headers["Authorization"] = f"Bearer {settings.github_token}"

    def fetch_ticket(self, number: int) -> Ticket:
        issue = self._request("GET", f"/issues/{number}").json()
        if "pull_request" in issue:
            raise ValueError(f"#{number} is a pull request, not an issue.")
        return parse_ticket(number, issue["title"], issue.get("body") or "", self._default_url)

    def post_result(self, number: int, report_markdown: str, overall: Verdict) -> None:
        """Comment the report on the issue and make the qa-* label match the latest result."""
        body = _truncate(report_markdown)
        self._request("POST", f"/issues/{number}/comments", json={"body": body})
        for outdated in set(_RESULT_LABELS.values()) - {_RESULT_LABELS[overall]}:
            self._remove_label(number, outdated)  # A re-run must not leave "qa-failed" next to "qa-passed".
        self._request("POST", f"/issues/{number}/labels", json={"labels": [_RESULT_LABELS[overall]]})

    def _remove_label(self, number: int, label: str) -> None:
        try:
            self._request("DELETE", f"/issues/{number}/labels/{label}")
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 404:  # 404 = the label was not on the issue.
                raise

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        response = self._session.request(
            method, f"{API_ROOT}/repos/{self._repo}{path}", timeout=TIMEOUT_SECONDS, **kwargs
        )
        response.raise_for_status()
        return response


def _truncate(markdown: str) -> str:
    if len(markdown) <= MAX_COMMENT_CHARS:
        return markdown
    return markdown[:MAX_COMMENT_CHARS] + "\n\n... (report truncated; see the run's evidence folder)"
