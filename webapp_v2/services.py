"""Cached entry points between the pages and logic/ (the only module that uses st.cache_*).

Big read-only objects are shared with st.cache_resource (no copy per call); the risk level α is never in a
cache key: the α mix is applied after the cached ERC part.
"""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

import content
from logic import portfolio, report, store
from logic.portfolio import Choices
from ui import blocks


@st.cache_resource(show_spinner=False, max_entries=32)
def erc_part(regions: tuple, classes: tuple, sectors: tuple, esg: str) -> dict:
    """α-free part of a client portfolio, shared read-only by every session, with its compute time."""
    start = time.perf_counter()
    part = portfolio.erc_part(regions, classes, sectors, esg)
    return {"part": part, "seconds": time.perf_counter() - start}


def build_timed(choices: Choices) -> tuple[dict, float, bool]:
    """Result, compute time of its ERC part, and whether that part came from the cache."""
    start = time.perf_counter()
    cached = erc_part(choices.regions, choices.classes, choices.sectors, choices.esg)
    hit = time.perf_counter() - start < 0.5 * cached["seconds"]
    return portfolio.mix(cached["part"], choices), cached["seconds"], hit


def build_with_loader(choices: Choices) -> tuple[dict, str]:
    """Build with an animated loading state; returns the result and a "recomputed in" note."""
    placeholder = st.empty()
    placeholder.html(blocks.loader(content.TEXT["loading"]))
    result, seconds, cached = build_timed(choices)
    placeholder.empty()
    return result, content.TEXT["cached" if cached else "computed"].format(s=seconds)


@st.cache_resource(show_spinner=False)
def _stored_lab() -> tuple[pd.DataFrame, pd.Series] | None:
    return store.load_strategy()


@st.cache_data(show_spinner=False)
def _live_lab(_result: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Computed once per process (the baseline never changes); the result is not hashed."""
    return report.strategy_lab(_result)


def strategy_lab() -> tuple[pd.DataFrame, pd.Series]:
    """"Our strategy" numbers: precomputed when available, else computed live with the loader."""
    stored = _stored_lab()
    if stored is not None:
        return stored
    result, _ = build_with_loader(portfolio.baseline())
    return _live_lab(result)
