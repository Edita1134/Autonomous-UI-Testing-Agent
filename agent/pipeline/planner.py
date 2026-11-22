"""Planner: turns acceptance criteria into natural-language test steps."""

import logging

from agent.llm import prompts
from agent.llm.client import LLMClient
from agent.models import Scenario, Ticket

log = logging.getLogger("agent.planner")


class Planner:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def plan(self, ticket: Ticket) -> list[Scenario]:
        """One Scenario per acceptance criterion, in the ticket's order."""
        raw = self._llm.chat_json(prompts.planner_messages(ticket))
        steps_by_id = {
            item.get("criterion_id"): [str(step) for step in item.get("steps", []) if str(step).strip()]
            for item in raw.get("scenarios", [])
            if isinstance(item, dict)
        }
        scenarios = []
        for criterion in ticket.criteria:
            steps = steps_by_id.get(criterion.id)
            if not steps:  # Guardrail: never silently drop an AC.
                log.warning("Planner returned no steps for %s; falling back to the AC text.", criterion.id)
                steps = [criterion.text]
            scenarios.append(Scenario(criterion=criterion, steps=steps))
            log.info("PLAN %s: %s", criterion.id, " | ".join(steps))
        return scenarios
