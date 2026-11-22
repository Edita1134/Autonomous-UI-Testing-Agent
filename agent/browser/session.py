"""Playwright wrapper exposing a few *semantic* browser actions to the LLM.

The agent never sees CSS or XPath. It describes elements by ARIA role and
accessible name (e.g. role="button", name="Add to cart"), which is how a
human would describe them and survives markup changes.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, sync_playwright

from agent.config import Settings

VIEWPORT = {"width": 1280, "height": 800}
SETTLE_MS = 300
NAVIGATION_TIMEOUT_MS = 30_000  # Page loads are slower than clicks, so they get their own limit.
# Containers searched when the model scopes an element with `within_text`.
_CONTAINER_SELECTOR = "div, li, tr, section, article, form"
# Actions the LLM is allowed to trigger (anything else is rejected).
ALLOWED_ACTIONS = {"navigate", "click", "fill", "press_key"}


class ToolError(Exception):
    """An action failed; the message is shown to the LLM so it can adapt."""


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    title: str
    tree: str  # ARIA snapshot: the page as roles + accessible names.

    def render(self) -> str:
        return f"URL: {self.url}\nTitle: {self.title}\n{self.tree}"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha1(self.render().encode()).hexdigest()[:12]


def _scope_note(within_text: str) -> str:
    return f" within '{within_text}'" if within_text else ""


class BrowserSession:
    """Context manager owning one Chromium page (with video recording)."""

    def __init__(self, settings: Settings, video_dir: Path):
        self._settings = settings
        self._video_dir = video_dir

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=self._settings.headless)
            self._context = self._browser.new_context(
                viewport=VIEWPORT, record_video_dir=str(self._video_dir), record_video_size=VIEWPORT
            )
            self._page: Page = self._context.new_page()
            self._page.set_default_timeout(self._settings.action_timeout_ms)
        except Exception:
            self._playwright.stop()  # Do not leave the Playwright driver running if the launch failed.
            raise
        return self

    def __exit__(self, *_exc) -> None:
        self._context.close()  # Closing the context finalises the video file.
        self._browser.close()
        self._playwright.stop()

    # ---- Observation -------------------------------------------------------------

    def snapshot(self) -> PageSnapshot:
        """The page as the LLM sees it: URL, title and the ARIA tree (truncated)."""
        tree = self._page.locator("body").aria_snapshot()
        limit = self._settings.max_snapshot_chars
        if len(tree) > limit:
            tree = tree[:limit] + "\n... [snapshot truncated]"
        return PageSnapshot(url=self._page.url, title=self._page.title(), tree=tree)

    def screenshot(self, path: Path) -> None:
        self._page.screenshot(path=str(path))

    # ---- Actions (names must match tool_schemas.py) -------------------------------

    def execute(self, action: str, args: dict) -> str:
        """Run an allowed action by name; returns a short outcome string."""
        if action not in ALLOWED_ACTIONS:
            raise ToolError(f"Unknown action '{action}'. Allowed: {sorted(ALLOWED_ACTIONS)}")
        try:
            return getattr(self, action)(**args)
        except TypeError as exc:
            raise ToolError(f"Bad arguments for {action}: {exc}") from exc

    def navigate(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            raise ToolError("url must start with http:// or https://")
        return self._act(
            f"Navigated to {url}",
            lambda: self._page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS),
        )

    def click(self, role: str, name: str, within_text: str = "") -> str:
        target = self._resolve(role, name, within_text)
        return self._act(f"Clicked {role} '{name}'" + _scope_note(within_text), target.click)

    def fill(self, role: str, name: str, value: str, within_text: str = "") -> str:
        target = self._resolve(role, name, within_text)
        return self._act(f"Typed into {role} '{name}'" + _scope_note(within_text), lambda: target.fill(value))

    def press_key(self, key: str) -> str:
        return self._act(f"Pressed {key}", lambda: self._page.keyboard.press(key))

    # ---- Internals ---------------------------------------------------------------

    def _resolve(self, role: str, name: str, within_text: str) -> Locator:
        """Find exactly one element by role + accessible name, or explain why not.

        There is deliberately no index (`nth`) option: models tend to pass nth=0 by default, which
        silently picks an arbitrary element. Ambiguity must be resolved semantically, with nearby text.
        """
        if within_text:
            container = (
                self._page.locator(_CONTAINER_SELECTOR)
                .filter(has_text=within_text)
                .filter(has=self._by_role(self._page, role, name))
                .last  # Last match in document order = the innermost container.
            )
            matches = self._by_role(container, role, name)
        else:
            matches = self._by_role(self._page, role, name)

        count = matches.count()
        description = f"{role} '{name}'" + _scope_note(within_text)
        if count == 0:
            raise ToolError(f"No {description} found on the page. Check the current page snapshot.")
        if count > 1:
            raise ToolError(
                f"{count} elements match {description}. Set `within_text` to nearby text that "
                f"identifies the right one (e.g. the product or row name)."
            )
        return matches

    @staticmethod
    def _by_role(scope: Page | Locator, role: str, name: str) -> Locator:
        if role == "text":  # Escape hatch for non-interactive text.
            return scope.get_by_text(name)
        return scope.get_by_role(role, name=name)

    def _act(self, description: str, action) -> str:
        try:
            action()
            self._page.wait_for_timeout(SETTLE_MS)
        except PlaywrightError as exc:
            first_line = str(exc).strip().splitlines()[0]
            raise ToolError(f"{description} failed: {first_line}") from exc
        return description
