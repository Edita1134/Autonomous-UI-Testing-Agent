"""Detects an agent repeating itself without making progress."""

from collections import deque


class LoopGuard:
    """Flags when the same (action, resulting page) occurs `limit` times in a row."""

    def __init__(self, limit: int = 3):
        self._recent: deque[str] = deque(maxlen=limit)

    def record(self, action_signature: str, page_fingerprint: str) -> bool:
        """Record one turn; returns True if the agent appears stuck."""
        self._recent.append(f"{action_signature}@{page_fingerprint}")
        return len(self._recent) == self._recent.maxlen and len(set(self._recent)) == 1
