"""Cached entry points between the pages and logic/ (the only module that uses st.cache_*)."""

from __future__ import annotations

import time

import streamlit as st

import content
from logic import portfolio
from logic.portfolio import Choices
from ui import blocks


@st.cache_data(show_spinner=False, max_entries=32)
def build(choices: Choices) -> dict:
    """The client's backtest for one full set of choices, with the time it took to compute."""
    start = time.perf_counter()
    result = portfolio.build(choices)
    result["seconds"] = time.perf_counter() - start
    return result


def build_timed(choices: Choices) -> tuple[dict, float, bool]:
    """Result, compute time, and whether it came from the cache (a hit returns almost instantly)."""
    start = time.perf_counter()
    result = build(choices)
    return result, result["seconds"], time.perf_counter() - start < 0.5 * result["seconds"]


def build_with_loader(choices: Choices) -> tuple[dict, str]:
    """Build with an animated loading state; returns the result and a "recomputed in" note."""
    placeholder = st.empty()
    placeholder.html(blocks.loader(content.TEXT["loading"]))
    result, seconds, cached = build_timed(choices)
    placeholder.empty()
    return result, content.TEXT["cached" if cached else "computed"].format(s=seconds)
