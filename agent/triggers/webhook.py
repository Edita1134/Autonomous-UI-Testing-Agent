"""GitHub webhook receiver: labelling an issue 'RFQA' starts the agent.

Run:  uvicorn agent.triggers.webhook:app --port 8000
Then expose it (e.g. `ngrok http 8000`) and add a webhook in the repo settings:
  payload URL  <public-url>/webhook, content type application/json,
  secret       the value of GITHUB_WEBHOOK_SECRET, event: "Issues".

Why a label? "Moving a card to RFQA" is simulated by adding the RFQA label,
which works for any repo (Projects v2 events are only available to org webhooks).
"""

import hashlib
import hmac
import json
import logging
import threading
from functools import lru_cache

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from agent.config import Settings
from agent.pipeline.runner import run_ticket
from agent.tickets.github import GitHubClient

log = logging.getLogger("agent.webhook")
app = FastAPI(title="RFQA webhook")


@lru_cache
def get_settings() -> Settings:
    """Read the environment once, on first use (importing this module must not need an API key)."""
    return Settings.from_env()


# The agent drives one real browser and writes one evidence folder, so runs queue up instead of overlapping.
_run_lock = threading.Lock()


def signature_is_valid(secret: str, body: bytes, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")


def run_issue(number: int) -> None:
    """Background job: fetch the issue, run the agent, post the report back."""
    with _run_lock:
        try:
            settings = get_settings()
            github = GitHubClient(settings)
            report, markdown = run_ticket(github.fetch_ticket(number), settings)
            github.post_result(number, markdown, report.overall)
        except Exception:  # A background task has no caller to report to, so log it.
            log.exception("Run for issue #%s failed", number)


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks) -> dict:
    settings = get_settings()
    body = await request.body()
    if not settings.webhook_secret:
        raise HTTPException(500, "GITHUB_WEBHOOK_SECRET is not configured")
    if not signature_is_valid(settings.webhook_secret, body, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(401, "Invalid signature")

    payload = json.loads(body)
    is_trigger = (
        request.headers.get("X-GitHub-Event") == "issues"
        and payload.get("action") == "labeled"
        and payload.get("label", {}).get("name") == settings.trigger_label
    )
    if not is_trigger:
        return {"status": "ignored"}

    number = payload["issue"]["number"]
    log.info("RFQA label added to issue #%s; starting agent", number)
    background.add_task(run_issue, number)
    return {"status": "started", "issue": number}
