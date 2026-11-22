"""Command-line entry point.

Examples:
    python -m agent.main --issue-file issues/checkout-flow.md
    python -m agent.main --issue 1 --post          # read from GitHub, comment the result back
"""

import argparse
import sys
import traceback
from dataclasses import replace
from pathlib import Path

import requests

from agent.config import ConfigError, Settings
from agent.llm.client import QuotaExhaustedError
from agent.tickets.github import GitHubClient
from agent.models import Ticket, Verdict
from agent.pipeline.runner import run_ticket
from agent.tickets.parser import parse_ticket

EXIT_CODES = {Verdict.PASS: 0, Verdict.FAIL: 1, Verdict.BLOCKED: 2}


def load_ticket_from_file(path: Path, default_url: str) -> Ticket:
    """A local markdown file: first line '# Title', the rest is the issue body."""
    first_line, _, body = path.read_text(encoding="utf-8").partition("\n")
    return parse_ticket(None, first_line.lstrip("# ").strip(), body, default_url)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autonomous UI test agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--issue", type=int, help="GitHub issue number (needs GITHUB_REPO in .env)")
    source.add_argument("--issue-file", type=Path, help="Local markdown file instead of a GitHub issue")
    parser.add_argument("--post", action="store_true", help="Comment the report on the GitHub issue")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        settings = Settings.from_env()
        if args.headed:
            settings = replace(settings, headless=False)

        if args.issue_file:
            ticket = load_ticket_from_file(args.issue_file, settings.default_target_url)
        else:
            ticket = GitHubClient(settings).fetch_ticket(args.issue)

        report, markdown = run_ticket(ticket, settings)
        if args.post and args.issue:
            _post_result(settings, args.issue, markdown, report.overall)
        print(f"\nOverall: {report.overall.value}")
        return EXIT_CODES[report.overall]
    except (ConfigError, ValueError, QuotaExhaustedError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except requests.RequestException as exc:  # Fetching the issue failed: nothing was tested.
        print(f"Error: GitHub request failed: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:  # A crash must not look like a test verdict (exit code 1 means FAIL).
        traceback.print_exc()
        print(f"Error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


def _post_result(settings: Settings, issue: int, markdown: str, overall: Verdict) -> None:
    """Comment the report on the issue. A posting failure must not hide the test verdict."""
    try:
        GitHubClient(settings).post_result(issue, markdown, overall)
        print(f"Posted result to GitHub issue #{issue}.")
    except requests.RequestException as exc:
        print(f"Warning: could not post result to GitHub issue #{issue}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
