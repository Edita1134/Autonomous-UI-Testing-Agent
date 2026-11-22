"""Read a GitHub issue so the UI can show it before running it.

The repo name and token are the agent project's own settings (GITHUB_REPO, GITHUB_TOKEN in its .env), so
nothing secret is stored in the dashboard and both projects always point at the same repository.
"""

import os

import requests
from dotenv import dotenv_values

from dashboard.config import Settings

API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 15


class GitHubError(Exception):
    """A problem to show the user. `status` is the HTTP status the dashboard API should answer with."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def fetch_issue_markdown(settings: Settings, number: int) -> str:
    """The issue as '# Title' + body, the same shape as the sample tickets."""
    repo, token = _github_settings(settings)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(f"{API_ROOT}/repos/{repo}/issues/{number}", headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise GitHubError(f"Could not reach GitHub: {exc}", 502) from exc

    if response.status_code == 404:
        raise GitHubError(f"Issue #{number} not found in {repo} (private repo? check GITHUB_TOKEN).", 404)
    if response.status_code in (401, 403):
        raise GitHubError("GitHub refused the request. Check GITHUB_TOKEN and its Issues permission.", 502)
    if not response.ok:
        raise GitHubError(f"GitHub answered {response.status_code}.", 502)

    issue = response.json()
    if "pull_request" in issue:
        raise GitHubError(f"#{number} is a pull request, not an issue.", 400)
    return f"# {issue['title']}\n\n{issue.get('body') or ''}"


def _github_settings(settings: Settings) -> tuple[str, str]:
    """(repo, token) from the agent project's .env, falling back to this process's environment."""
    file_values = dotenv_values(settings.agent_dir / ".env")
    repo = file_values.get("GITHUB_REPO") or os.getenv("GITHUB_REPO") or ""
    token = file_values.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
    if not repo:
        raise GitHubError("GITHUB_REPO is not set in the agent project's .env (expected 'owner/repo').")
    return repo, token
