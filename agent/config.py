"""Runtime settings, loaded once from environment variables (and an optional .env file)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # So .env and evidence/ do not depend on the working directory.
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_TARGET_URL = "https://www.saucedemo.com"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    model: str = DEFAULT_MODEL
    default_target_url: str = DEFAULT_TARGET_URL
    headless: bool = True
    evidence_dir: Path = PROJECT_ROOT / "evidence"

    # Agent guardrails (see docs/TEST_PLAN.md, "Preventing infinite loops").
    max_actions_per_step: int = 8
    max_snapshot_chars: int = 6000
    action_timeout_ms: int = 5000
    self_heal: bool = True

    # GitHub integration (all optional).
    github_token: str = ""
    github_repo: str = ""
    webhook_secret: str = ""
    trigger_label: str = "RFQA"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            raise ConfigError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        return cls(
            gemini_api_key=api_key,
            model=_normalise_model(os.getenv("GEMINI_MODEL", DEFAULT_MODEL)),
            default_target_url=os.getenv("DEFAULT_TARGET_URL", DEFAULT_TARGET_URL),
            headless=os.getenv("HEADED", "false").lower() != "true",
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_repo=os.getenv("GITHUB_REPO", ""),
            webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            trigger_label=os.getenv("TRIGGER_LABEL", "RFQA"),
        )


def _normalise_model(name: str) -> str:
    """Tolerate a missing prefix: '3.5-flash-lite' means 'gemini-3.5-flash-lite'. Blank means the default."""
    name = name.strip().removeprefix("models/") or DEFAULT_MODEL
    return f"gemini-{name}" if name[0].isdigit() else name
