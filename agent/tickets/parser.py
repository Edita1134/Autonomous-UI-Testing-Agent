"""Turn a GitHub issue (title + markdown body) into a structured Ticket."""

import re

from agent.models import AcceptanceCriterion, Ticket

_HEADING_RE = re.compile(r"^#{1,6}\s*(.+?)\s*$")
_AC_HEADING_RE = re.compile(r"acceptance criteria", re.IGNORECASE)
# Matches "- item", "- [ ] item", "1. item", optionally prefixed with "AC1:" / "**AC1**:".
_ITEM_RE = re.compile(
    r"^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)]\s*)"
    r"(?:\*{0,2}(?P<id>AC\d+)\*{0,2}\s*[:.\-]\s*)?"
    r"(?P<text>\S.*)$"
)
_TARGET_URL_RE = re.compile(r"target url:\s*<?(https?://[^\s>]+)>?", re.IGNORECASE)


def parse_ticket(number: int | None, title: str, body: str, default_url: str) -> Ticket:
    """Build a Ticket; raises ValueError if the issue has no acceptance criteria."""
    criteria = _parse_criteria(body)
    if not criteria:
        raise ValueError("No acceptance criteria found. Add an '## Acceptance Criteria' list to the issue.")
    url_match = _TARGET_URL_RE.search(body)
    target_url = url_match.group(1).rstrip(".,)") if url_match else default_url
    return Ticket(number=number, title=title, body=body, target_url=target_url, criteria=criteria)


def _parse_criteria(body: str) -> list[AcceptanceCriterion]:
    criteria: list[AcceptanceCriterion] = []
    in_section = False
    for line in body.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            in_section = bool(_AC_HEADING_RE.search(heading.group(1)))
            continue
        item = _ITEM_RE.match(line) if in_section else None
        if item:
            text = item.group("text").replace("**", "").strip()
            criteria.append(AcceptanceCriterion(id=item.group("id") or f"AC{len(criteria) + 1}", text=text))
    return criteria
