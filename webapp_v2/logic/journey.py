"""Client-journey rules: which steps apply and whether a step has a valid choice."""

from __future__ import annotations

import config as cfg
from logic import universe
from logic.portfolio import Choices, client_sleeves

STEPS = ("regions", "classes", "sectors", "esg", "profile", "portfolio")
STOCK_STEPS = {"sectors", "esg"}  # only meaningful when equities are held


def active_steps(classes) -> list[str]:
    """Steps shown to the client: always all six, so the path is visible from the start (without equities,
    the sectors and ESG steps only say that they do not apply)."""
    return list(STEPS)


def to_choices(state: dict) -> Choices:
    """Choices from the session values."""
    return Choices(tuple(state["regions"]), tuple(state["classes"]), tuple(state["sectors"]), state["esg"],
                   state["level"])


def problem(step: str, state: dict) -> str | None:
    """Key of the content.PROBLEMS message that blocks "Next", or None when the step is valid."""
    choices = to_choices(state)
    if step == "regions" and not choices.regions:
        return "no_region"
    if step == "classes" and len(client_sleeves(choices)) < 2:
        return "two_sleeves"
    if step == "sectors" and cfg.EQUITIES in choices.classes and not choices.sectors:
        return "no_sector"
    if step in STOCK_STEPS and cfg.EQUITIES not in choices.classes:  # nothing to choose without equities
        return None
    if step in STOCK_STEPS and universe.thin_regions(choices.regions, choices.sectors, choices.esg):
        return "thin_sleeve"
    return None
