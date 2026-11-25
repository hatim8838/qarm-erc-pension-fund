"""Client journey: a stepper over 3a-3f; choices live in st.session_state."""

from __future__ import annotations

from copy import deepcopy

import streamlit as st

import config as cfg
import content
from logic import data, journey, portfolio, universe
from pages import journey_portfolio, journey_steps
from ui import blocks

# Choices are stored under plain keys (not widget keys) so they survive when a step's
# widgets are not drawn; widgets copy their value here in on_change callbacks.
DEFAULTS = {"step": "regions", "regions": [], "classes": [], "sectors": data.sectors(),
            "esg": portfolio.NO_SCREEN, "level": cfg.DEFAULT_LEVEL}
SHOWN = "_stepper_shown"  # (step, steps) drawn by the last full run of the page
RENDER = {"regions": journey_steps.regions, "classes": journey_steps.classes, "sectors": journey_steps.sectors,
          "esg": journey_steps.esg, "profile": journey_steps.profile_step, "portfolio": journey_portfolio.render}


def state() -> dict:
    """The journey values of the session, created on the first visit."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, deepcopy(value))
    return {key: st.session_state[key] for key in DEFAULTS}


def stepper(current: str, steps: list[str]) -> None:
    """Progress bar of the active steps (done / current / to do)."""
    cells = []
    for i, step in enumerate(steps):
        css = "now" if step == current else "done" if i < steps.index(current) else ""
        number = content.JOURNEY[step][0].split(" · ")[0]
        cells.append(f'<div class="{css}"><b>{number}</b>{content.STEP_NAMES[step]}</div>')
    st.html(f'<nav class="stepper">{"".join(cells)}</nav>')


def move(delta: int) -> None:
    """Go to the previous or next active step."""
    steps = journey.active_steps(st.session_state["classes"])
    st.session_state["step"] = steps[steps.index(st.session_state["step"]) + delta]


def blocking_message(step: str, values: dict) -> str | None:
    """Text of the problem that blocks "Next", if any."""
    key = journey.problem(step, values)
    if key is None:
        return None
    thin = universe.thin_regions(values["regions"], tuple(values["sectors"]), values["esg"])
    return content.PROBLEMS[key].format(regions=", ".join(thin), n=cfg.MIN_STOCKS_PER_SLEEVE)


def nav_buttons(step: str, steps: list[str], values: dict) -> None:
    """Back / Next; Next is disabled, with the reason, until the step is valid."""
    message = blocking_message(step, values)
    if message:
        st.warning(message, icon=":material/block:")
    back, _, forward = st.columns([1, 4, 1])
    back.button(content.NAV_BUTTONS["back"], key="back", on_click=move, args=(-1,), disabled=step == steps[0],
                width="stretch")
    if step != steps[-1]:
        forward.button(content.NAV_BUTTONS["next"], key="next", type="primary", on_click=move, args=(1,),
                       disabled=message is not None, width="stretch")


def current() -> tuple[dict, list[str], str]:
    """Journey values, active steps and the step to show."""
    values = state()
    steps = journey.active_steps(values["classes"])
    return values, steps, values["step"] if values["step"] in steps else steps[0]


@st.fragment
def step_body() -> None:
    """The current step and its Back / Next buttons: a widget here reruns only this block. When the step
    or the list of steps changes (Back, Next, equities on or off), the whole page reruns for the stepper."""
    values, steps, step = current()
    if (step, steps) != st.session_state.get(SHOWN):
        st.rerun()
    RENDER[step](values)
    nav_buttons(step, steps, state())


_, steps_shown, step_shown = current()
st.session_state[SHOWN] = (step_shown, steps_shown)
blocks.hero("journey")
stepper(step_shown, steps_shown)
step_body()
