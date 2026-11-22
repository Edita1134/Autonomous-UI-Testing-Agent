"""Runs the agent as a subprocess and reads its evidence folder to report live progress.

The dashboard never imports agent code: the agent's CLI and its files on disk are the whole interface
(`python -m agent.main --issue-file ...`, then evidence/run-*/agent.log and report.json).
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dashboard.config import Settings

_LOG_LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d) \| (.*)$")
# Agent exit codes (see the agent's README): 0 pass, 1 fail, 2 blocked, 3 input/config error.
_EXIT_VERDICTS = {0: "PASS", 1: "FAIL", 2: "BLOCKED"}
_AC_HEADING_RE = re.compile(r"^#{1,6}\s*acceptance criteria", re.IGNORECASE)
_ITEM_RE = re.compile(r"^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)]\s*)(?:\*{0,2}(AC\d+)\*{0,2}\s*[:.\-]\s*)?(\S.*)$")


def preview_criteria(markdown: str) -> list[dict]:
    """Quick look at the ticket's ACs to draw the cards. The agent does the real parsing."""
    criteria, in_section = [], False
    for line in markdown.splitlines():
        if line.lstrip().startswith("#"):
            in_section = bool(_AC_HEADING_RE.match(line.strip()))
        elif in_section and (item := _ITEM_RE.match(line)):
            criteria.append({"id": item.group(1) or f"AC{len(criteria) + 1}", "text": item.group(2).replace("**", "")})
    return criteria


class AgentRunner:
    """One agent process at a time (it drives a single real browser)."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._work_dir = Path(tempfile.mkdtemp(prefix="agent-dashboard-"))
        self._process: subprocess.Popen | None = None
        self._started_at = 0.0
        self._stopped = False
        self._output_file = self._work_dir / "agent-output.txt"

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, markdown: str, headed: bool, issue: int | None = None, post: bool = False) -> list[dict]:
        """Launch the agent on this ticket. Returns the criteria preview. Raises ValueError/RuntimeError.

        With `issue`, the agent fetches that GitHub issue itself (`markdown` is only used for the preview)
        and, with `post`, comments the result back on it.
        """
        if problem := self._settings.agent_problem():
            raise ValueError(problem)
        if self.is_running:
            raise RuntimeError("A run is already in progress.")
        criteria = preview_criteria(markdown)
        if not criteria:
            raise ValueError("No acceptance criteria found. Add an '## Acceptance Criteria' list to the ticket.")

        command = [self._settings.agent_python, "-m", "agent.main"]
        if issue is not None:
            command += ["--issue", str(issue)]
            if post:
                command.append("--post")
        else:
            ticket_file = self._work_dir / "ticket.md"
            ticket_file.write_text(markdown, encoding="utf-8")
            command += ["--issue-file", str(ticket_file)]
        if headed:
            command.append("--headed")

        self._started_at = time.time()
        self._stopped = False
        with self._output_file.open("w", encoding="utf-8") as output:
            self._process = subprocess.Popen(
                command,
                cwd=self._settings.agent_dir,
                stdout=output,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        return criteria

    def stop(self) -> None:
        """Kill the agent and the browser it launched."""
        if not self.is_running or self._process is None:
            return
        self._stopped = True
        if sys.platform == "win32":  # /T also kills child processes (Chromium).
            subprocess.run(["taskkill", "/PID", str(self._process.pid), "/T", "/F"], capture_output=True)
        else:
            self._process.terminate()

    def progress(self, since: int) -> dict:
        run_dir = self._current_run_dir()
        events = _read_log_events(run_dir / "agent.log") if run_dir else []
        status, overall, error = self._status(run_dir)
        return {
            "run_id": run_dir.name if run_dir else "",
            "status": status,
            "overall": overall,
            "error": error,
            "github_note": self._github_note() if status == "done" else "",
            "events": events[since:],
            "next": len(events),
        }

    # ---- Internals -----------------------------------------------------------------

    def _current_run_dir(self) -> Path | None:
        """The newest run folder created since this run started."""
        if not self._process or not self._settings.evidence_dir.exists():
            return None
        fresh = [
            path
            for path in self._settings.evidence_dir.glob("run-*")
            if path.is_dir() and path.stat().st_mtime >= self._started_at - 1
        ]
        return max(fresh, key=lambda path: path.stat().st_mtime, default=None)

    def _status(self, run_dir: Path | None) -> tuple[str, str, str]:
        """Returns (status, overall verdict, error message)."""
        if self._process is None:
            return "idle", "", ""
        code = self._process.poll()
        if code is None:
            return "running", "", ""
        if self._stopped:
            return "error", "", "Run stopped by user."
        report = run_dir / "report.json" if run_dir else None
        if code in _EXIT_VERDICTS and report and report.exists():
            return "done", json.loads(report.read_text(encoding="utf-8"))["overall"], ""
        return "error", "", self._error_text(code)  # A crash, or a run that ended without writing its report.

    def _github_note(self) -> str:
        """What happened when posting the result to GitHub (the agent prints one line about it), if anything."""
        for line in self._output_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(("Posted result to GitHub", "Warning: could not post")):
                return line
        return ""

    def _error_text(self, code: int) -> str:
        lines = self._output_file.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        message = next((line for line in reversed(lines) if line.startswith("Error:")), "")
        return f"Agent exited with code {code}.\n" + (message[:600] or "\n".join(lines[-6:]))


def _read_log_events(log_file: Path) -> list[dict]:
    """Parse agent.log into events; a line without a timestamp continues the previous message."""
    if not log_file.exists():
        return []
    events: list[dict] = []
    for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _LOG_LINE_RE.match(line)
        if match:
            events.append({"time": match.group(1), "text": match.group(2)})
        elif events and line.strip():
            events[-1]["text"] += "\n" + line
    return events

