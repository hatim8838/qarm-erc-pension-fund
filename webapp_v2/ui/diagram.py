"""Animated step diagram: each pipeline step rises in turn with its lecture badge and formula."""

from __future__ import annotations

import streamlit as st

from ui.blocks import badge


def pipeline(steps: list[tuple[str, str, str]]) -> None:
    """One card per step (badge, title, st.latex formula), joined by animated arrows."""
    for i, (lecture, title, formula) in enumerate(steps):
        if i:
            st.html(f'<div class="flow-arrow" style="--i:{i}"></div>')
        with st.container(key=f"flow_step_{i}"):
            st.html(f'<div class="flow-title">{badge(lecture)} <strong>{title}</strong></div>')
            st.latex(formula)
