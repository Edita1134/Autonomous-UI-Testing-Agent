import pytest

from agent.tickets.parser import parse_ticket

DEFAULT_URL = "https://default.example"

BODY = """\
Some intro text.
Target URL: https://www.saucedemo.com

## Acceptance Criteria
- AC1: User can log in
- [ ] **AC2**: Cart badge shows 1
3. Plain numbered item

## Notes
- This bullet is not an AC
"""


def test_extracts_criteria_only_from_the_ac_section():
    ticket = parse_ticket(7, "Title", BODY, DEFAULT_URL)
    assert [c.text for c in ticket.criteria] == ["User can log in", "Cart badge shows 1", "Plain numbered item"]


def test_keeps_explicit_ids_and_numbers_the_rest():
    ticket = parse_ticket(7, "Title", BODY, DEFAULT_URL)
    assert [c.id for c in ticket.criteria] == ["AC1", "AC2", "AC3"]


def test_reads_target_url_or_falls_back_to_default():
    assert parse_ticket(1, "T", BODY, DEFAULT_URL).target_url == "https://www.saucedemo.com"
    no_url = "## Acceptance Criteria\n- one thing"
    assert parse_ticket(1, "T", no_url, DEFAULT_URL).target_url == DEFAULT_URL


def test_missing_acceptance_criteria_is_an_error():
    with pytest.raises(ValueError, match="acceptance criteria"):
        parse_ticket(1, "T", "Just a description", DEFAULT_URL)
