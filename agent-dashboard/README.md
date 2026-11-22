# Agent Dashboard

A web dashboard for the **Autonomous UI Test Agent** project. Pick or edit a ticket, press **Run agent**, and
watch the agent's observations, thoughts and actions live, next to per-criterion PASS / FAIL cards and
screenshots. Past runs can be reopened (log replay, report, video).

This is a **separate project**. It never imports agent code. It starts the agent's command line
(`python -m agent.main --issue-file ...`) and reads the files the agent writes (`evidence/run-*/`).

## Quick start

1. Open this folder in its own VS Code window (File > Open Folder).
2. Install and launch:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m dashboard
```

A new browser window opens at http://127.0.0.1:8765.

## Pointing it at the agent project

By default it assumes this folder sits **inside** the agent project folder. If you move it elsewhere,
copy `.env.example` to `.env` and set:

```
AGENT_DIR=C:\path\to\agent\project
```

`AGENT_DIR` must contain `agent/`, `issues/` and `evidence/`. The agent is run with the Python from
`AGENT_DIR\.venv` when it exists (or set `AGENT_PYTHON`), and it reads its own `GEMINI_API_KEY` from its own `.env`.
Nothing secret is stored in this project.

## Choosing the website to test

The **Website to test** field above the ticket text sets the ticket's `Target URL:` line (typing there edits the
ticket text, and editing the text updates the field). Leave it empty to use the agent's default site
(`DEFAULT_TARGET_URL`). The acceptance criteria must describe the site you enter. For a GitHub issue the URL comes
from the issue itself, so the field is read-only there.

## Running a GitHub issue

Type an issue number in the ticket panel and press **Load**. The ticket text appears and the button becomes
**Run issue #N**. Tick **Post the result** to comment the report on the issue and add a `qa-*` label.

`GITHUB_REPO` (`owner/repo`) and `GITHUB_TOKEN` are read from the **agent project's** `.env`, so nothing secret
is stored here. The token needs read and write access to Issues. The agent fetches the issue itself when it runs,
so editing the loaded text detaches it from GitHub and runs your text instead.

## How it works

| File | Role |
|------|------|
| `dashboard/app.py` | FastAPI endpoints: start a run, poll progress, list past runs, serve evidence files |
| `dashboard/agent_runner.py` | Runs the agent subprocess; tails `agent.log` for live events; reads `report.json` for the verdict |
| `dashboard/config.py` | Settings (`AGENT_DIR`, `AGENT_PYTHON`, `PORT`) |
| `frontend/` | The React + TypeScript UI source (Vite). `npm run build` outputs into `dashboard/static/` |
| `dashboard/static/` | The built UI served by the Python server (committed, so Node is not needed to just run it) |

Only one run at a time is allowed, because the agent drives a single real browser.

## Working on the UI (React)

The UI is a Vite + React + TypeScript app in `frontend/`.

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 with hot reload; proxies /api to the Python server
npm run build      # type-checks, then writes the production build to ../dashboard/static
```

For `npm run dev`, keep `python -m dashboard` running in another terminal (it serves the API on port 8765).

| Frontend file | Role |
|---------------|------|
| `src/parseLog.ts` | Turns raw agent log lines into steps, entries and verdicts (the only place that knows the log format) |
| `src/hooks/useRun.ts` | Starts/stops runs, polls progress, opens past runs |
| `src/components/` | `ActivityFeed` (step cards), `CriteriaPanel`, `Screenshots`, `TicketPanel`, `RunHistory`, `Header` |
