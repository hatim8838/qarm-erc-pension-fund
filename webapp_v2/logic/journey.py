"""Client-journey rules: which steps apply and whether a step has a valid choice."""

from __future__ import annotations

import config as cfg
from logic import profile, universe
from logic.portfolio import Choices, client_sleeves

STEPS = ("regions", "classes", "sectors", "esg", "profile", "portfolio")
STOCK_STEPS = {"sectors", "esg"}  # only meaningful when equities are held


def active_steps(classes) -> list[str]:
    """Steps shown to the client: sectors and ESG are skipped without equities."""
    if cfg.EQUITIES in classes:
        return list(STEPS)
    return [s for s in STEPS if s not in STOCK_STEPS]


def to_choices(state: dict) -> Choices:
    """Choices from the session values (risk level only once the questionnaire is complete)."""
    answers = state["answers"]
    lvl = profile.level(profile.score(answers)) if profile.is_complete(answers) else None
    return Choices(tuple(state["regions"]), tuple(state["classes"]), tuple(state["sectors"]), state["esg"], lvl)


def problem(step: str, state: dict) -> str | None:
    """Key of the content.PROBLEMS message that blocks "Next", or None when the step is valid."""
    choices = to_choices(state)
    if step == "regions" and not choices.regions:
        return "no_region"
    if step == "classes" and len(client_sleeves(choices)) < 2:
        return "two_sleeves"
    if step == "sectors" and not choices.sectors:
        return "no_sector"
    if step in STOCK_STEPS and universe.thin_regions(choices.regions, choices.sectors, choices.esg):
        return "thin_sleeve"
    if step == "profile" and not profile.is_complete(state["answers"]):
        return "questionnaire"
    return None
