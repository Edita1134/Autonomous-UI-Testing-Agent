"""FastAPI backend: start agent runs, poll live progress, browse past evidence."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dashboard.agent_runner import AgentRunner
from dashboard.config import Settings
from dashboard.github import GitHubError, fetch_issue_markdown

settings = Settings.from_env()
runner = AgentRunner(settings)
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="UI Test Agent Dashboard")


class StartRequest(BaseModel):
    markdown: str
    headed: bool = False
    issue: int | None = None  # Run this GitHub issue (the agent fetches it) instead of the pasted text.
    post: bool = False  # Comment the result back on that issue.


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/issues")
def list_issues() -> list[dict]:
    """Sample tickets from the agent project's issues/ folder."""
    return [
        {"name": path.stem, "markdown": path.read_text(encoding="utf-8")}
        for path in sorted(settings.issues_dir.glob("*.md"))
    ]


@app.get("/api/github/issues/{number}")
def github_issue(number: int) -> dict:
    """Fetch a GitHub issue (repo and token come from the agent project's .env)."""
    try:
        return {"number": number, "markdown": fetch_issue_markdown(settings, number)}
    except GitHubError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


@app.post("/api/runs")
def start_run(request: StartRequest) -> dict:
    try:
        criteria = runner.start(request.markdown, request.headed, request.issue, request.post)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"run_id": "", "criteria": criteria}


@app.post("/api/stop")
def stop_run() -> dict:
    runner.stop()
    return {"stopped": True}


@app.get("/api/progress")
def progress(since: int = 0) -> dict:
    """Live state: new log lines since `since`, status, and screenshots taken so far."""
    state = runner.progress(since)
    state["screenshots"] = _screenshots(state["run_id"]) if state["run_id"] else []
    return state


@app.get("/api/runs")
def past_runs() -> list[dict]:
    runs = []
    for report_file in sorted(settings.evidence_dir.glob("run-*/report.json"), reverse=True):
        try:
            data = json.loads(report_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # One damaged report must not hide every other run.
        runs.append(
            {
                "run_id": report_file.parent.name,
                "title": data.get("title", ""),
                "overall": data["overall"],
                "duration_seconds": data.get("duration_seconds", 0),
            }
        )
    return runs


@app.get("/api/runs/{run_id}")
def run_details(run_id: str) -> dict:
    report_file = _run_dir(run_id) / "report.json"
    if not report_file.exists():
        raise HTTPException(404, "Report not found for this run")
    data = json.loads(report_file.read_text(encoding="utf-8"))
    data["run_id"] = run_id
    data["screenshots"] = _screenshots(run_id)
    return data


def _run_dir(run_id: str) -> Path:
    if not run_id.startswith("run-") or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(400, "Invalid run id")
    return settings.evidence_dir / run_id


def _screenshots(run_id: str) -> list[str]:
    folder = _run_dir(run_id) / "screenshots"
    return [f"/evidence/{run_id}/screenshots/{path.name}" for path in sorted(folder.glob("*.png"))]


# The React build (frontend/ -> dashboard/static/) puts its JS and CSS in static/assets.
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")
# check_dir=False: the evidence folder may not exist until the agent's first run.
app.mount("/evidence", StaticFiles(directory=settings.evidence_dir, check_dir=False), name="evidence")
