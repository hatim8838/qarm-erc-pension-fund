"""Client journey step 3f: the portfolio, an "Adjust my choices" panel and five analysis tabs."""

import streamlit as st

import config as cfg
import content
import services
from logic import data, journey, profile, report
from pages import portfolio_tabs
from ui import blocks

T = content.TEXT


def _copy(key: str) -> None:
    """Copy an adjust-panel widget into the journey choice ``key``."""
    st.session_state[key] = st.session_state[f"adj_{key}"]


def _copy_level() -> None:
    """Change the risk level by rewriting the answers to the middle of that score band."""
    st.session_state["answers"] = profile.answers_for_level(st.session_state["adj_level"])


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
        b.selectbox(content.JOURNEY["esg"][0], cfg.ESG_MODES, index=cfg.ESG_MODES.index(values["esg"]),
                    format_func=content.ESG_LABELS.get, key="adj_esg", on_change=_copy, args=("esg",))
        level = journey.to_choices(values).level
        a.select_slider(T["level"], list(cfg.TARGET_VOLS), value=level, key="adj_level",
                        format_func=lambda k: f"{k} · {content.LEVEL_NAMES[k]} · σ* {blocks.pct(cfg.TARGET_VOLS[k])}",
                        on_change=_copy_level)
        b.slider(T["cost"], 0, cfg.MAX_COST_BPS, value=values["cost"], key="adj_cost", on_change=_copy, args=("cost",))


def first_problem(values: dict) -> str | None:
    """The first step whose choice is no longer valid after an adjustment."""
    for step in journey.active_steps(values["classes"]):
        if journey.problem(step, values):
            return step
    return None


def headline(result: dict, choices) -> None:
    """α, risk-free share, σ*, holdings, and a warning when σ* cannot be reached without leverage."""
    d = report.last_decision(result)
    blocks.figures([
        (blocks.count_up(100 * d["alpha"], 1, "%"), T["alpha"]),
        (blocks.count_up(100 * (1 - d["alpha"]), 1, "%"), T["rf_share"]),
        (blocks.count_up(report.holdings_count(result)), T["holdings"]),
    ])
    if d["sigma_hat"] < choices.target():
        st.warning(T["unreachable"].format(target=blocks.pct(choices.target()), sigma=blocks.pct(d["sigma_hat"])),
                   icon=":material/info:")


def render(values: dict) -> None:
    """3f: build the client's portfolio and show it."""
    choices = journey.to_choices(values)
    lvl = choices.level
    blocks.section(content.JOURNEY["portfolio"][0], content.JOURNEY["portfolio"][1].format(
        level=content.LEVEL_NAMES[lvl], target=blocks.pct(choices.target()), n=len(journey.client_sleeves(choices))))
    adjust_panel(values)
    broken = first_problem(values)
    if broken:
        st.error(content.PROBLEMS[journey.problem(broken, values)].format(regions="", n=cfg.MIN_STOCKS_PER_SLEEVE))
        return
    result, note = services.build_with_loader(choices)
    st.caption(note)
    headline(result, choices)
    portfolio_tabs.render(result, choices, values)
