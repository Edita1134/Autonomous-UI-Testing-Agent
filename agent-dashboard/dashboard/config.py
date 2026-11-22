"""Dashboard settings. The only link to the agent project is the folder it lives in (AGENT_DIR)."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    agent_dir: Path  # Folder containing the agent project (has agent/, issues/, evidence/).
    agent_python: str  # Python interpreter that has the agent's dependencies installed.
    host: str = "127.0.0.1"
    port: int = 8765

    @property
    def evidence_dir(self) -> Path:
        return self.agent_dir / "evidence"

    @property
    def issues_dir(self) -> Path:
        return self.agent_dir / "issues"

    def agent_problem(self) -> str:
        """Empty string if the agent project looks usable, otherwise what is wrong."""
        if not (self.agent_dir / "agent" / "main.py").exists():
            return f"AGENT_DIR does not contain the agent project: {self.agent_dir} (set AGENT_DIR in .env)"
        return ""

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        # Default: this project sits inside the agent project's folder.
        agent_dir = Path(os.getenv("AGENT_DIR") or PROJECT_ROOT.parent).resolve()
        return cls(
            agent_dir=agent_dir,
            agent_python=os.getenv("AGENT_PYTHON") or _find_python(agent_dir),
            port=int(os.getenv("PORT", "8765")),
        )


def _find_python(agent_dir: Path) -> str:
    """Prefer a usable agent virtualenv; fall back to the interpreter running the dashboard."""
    for relative in (".venv/Scripts/python.exe", ".venv/bin/python"):
        candidate = agent_dir / relative
        pyvenv_cfg = agent_dir / ".venv" / "pyvenv.cfg"
        if candidate.exists() and pyvenv_cfg.exists():
            cfg = pyvenv_cfg.read_text(encoding="utf-8", errors="replace")
            executable_line = next(
                (line for line in cfg.splitlines() if line.lower().startswith("executable = ")),
                "",
            )
            recorded = executable_line.partition("=")[2].strip()
            if not recorded or Path(recorded).exists():
                return str(candidate)
    return sys.executable
