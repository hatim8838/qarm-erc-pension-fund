"""Client journey step 3f: the portfolio, an "Adjust my choices" panel and three analysis tabs."""

from __future__ import annotations

import streamlit as st

import config as cfg
import content
import services
from logic import data, journey, report, universe
from pages import portfolio_tabs
from pages.journey_steps import esg_label, level_label
from ui import blocks

T = content.TEXT


def _copy(key: str) -> None:
    """Copy an adjust-panel widget into the journey choice ``key``."""
    st.session_state[key] = st.session_state[f"adj_{key}"]


def adjust_panel(values: dict) -> None:
    """Every choice in one place; each change recomputes the portfolio (cached by the full set of choices)."""
    with st.expander(T["adjust"], icon=":material/tune:"):
        a, b = st.columns(2)
        a.multiselect(content.JOURNEY["regions"][0], data.regions(), default=values["regions"], key="adj_regions",
                      on_change=_copy, args=("regions",))
        b.multiselect(content.JOURNEY["classes"][0], data.asset_classes(), default=values["classes"],
                      key="adj_classes", on_change=_copy, args=("classes",))
        a.multiselect(content.JOURNEY["sectors"][0], data.sectors(), default=values["sectors"], key="adj_sectors",
                      on_change=_copy, args=("sectors",))
        b.select_slider(T["esg_level"], list(cfg.ESG_LEVELS), value=values["esg"], format_func=esg_label,
                        key="adj_esg", on_change=_copy, args=("esg",), help=content.ESG_HELP)
        a.select_slider(T["level_slider"], list(cfg.ALPHAS), value=values["level"], format_func=level_label,
                        key="adj_level", on_change=_copy, args=("level",))


def first_problem(values: dict) -> str | None:
    """The first step whose choice is no longer valid after an adjustment."""
    for step in journey.active_steps(values["classes"]):
        if journey.problem(step, values):
            return step
    return None


def headline(result: dict) -> None:
    """α in the ERC portfolio, 1 − α in the risk-free asset, and the number of holdings."""
    alpha = result["alpha"]
    blocks.figures([
        (blocks.count_up(100 * alpha, 0, "%"), T["alpha"]),
        (blocks.count_up(100 * (1 - alpha), 0, "%"), T["rf_share"]),
        (blocks.count_up(report.holdings_count(result)), T["holdings"]),
    ])


def render(values: dict) -> None:
    """3f: build the client's portfolio and show it."""
    choices = journey.to_choices(values)
    blocks.section(content.JOURNEY["portfolio"][0], content.JOURNEY["portfolio"][1].format(
        level=content.LEVEL_NAMES[choices.level], alpha=blocks.pct(choices.alpha(), 0), esg=esg_label(choices.esg),
        n=len(journey.client_sleeves(choices))))
    adjust_panel(values)
    broken = first_problem(values)
    if broken:
        thin = ", ".join(universe.thin_regions(choices.regions, choices.sectors, choices.esg))
        st.error(content.PROBLEMS[journey.problem(broken, values)].format(regions=thin, n=cfg.MIN_STOCKS_PER_SLEEVE))
        return
    result, note = services.build_with_loader(choices)
    st.caption(note)
    headline(result)
    portfolio_tabs.render(result, choices, values)
