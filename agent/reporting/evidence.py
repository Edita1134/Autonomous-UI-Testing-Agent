"""Where a run's artifacts go: logs, screenshots, video and the final report.

Layout: evidence/<run_id>/{agent.log, screenshots/, video/, report.md, report.json}
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(message)s"


class EvidenceStore:
    def __init__(self, base_dir: Path):
        self.run_id = _unique_run_id(base_dir)
        self.root = base_dir / self.run_id
        self.screenshots_dir = self.root / "screenshots"
        self.video_dir = self.root / "video"
        for directory in (self.screenshots_dir, self.video_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self._shot_count = 0
        self._handlers: list[logging.Handler] = []

    def screenshot_path(self, label: str) -> Path:
        """Next sequential screenshot path, e.g. screenshots/003_AC1.2_click.png"""
        self._shot_count += 1
        return self.screenshots_dir / f"{self._shot_count:03d}_{label}.png"

    def relative(self, path: Path) -> str:
        """Path relative to the run folder, with forward slashes (for markdown links)."""
        return path.relative_to(self.root).as_posix()

    def video_files(self) -> list[Path]:
        return sorted(self.video_dir.glob("*.webm"))

    def start_logging(self) -> None:
        """Send the 'agent' logger to the console and to agent.log (other handlers, e.g. the UI's, are kept)."""
        logger = logging.getLogger("agent")
        logger.setLevel(logging.INFO)
        self._handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(self.root / "agent.log", "w", "utf-8")]
        for handler in self._handlers:
            handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
            logger.addHandler(handler)

    def stop_logging(self) -> None:
        """Detach and close the handlers added by start_logging."""
        logger = logging.getLogger("agent")
        for handler in self._handlers:
            logger.removeHandler(handler)
            handler.close()
        self._handlers = []


def _unique_run_id(base_dir: Path) -> str:
    """run-YYYYMMDD-HHMMSS, with a numeric suffix if two runs start within the same second."""
    stem = datetime.now().strftime("run-%Y%m%d-%H%M%S")
    run_id, attempt = stem, 1
    while (base_dir / run_id).exists():
        attempt += 1
        run_id = f"{stem}-{attempt}"
    return run_id
