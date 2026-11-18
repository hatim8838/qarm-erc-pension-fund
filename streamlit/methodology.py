"""Methodology & transparency (content added in a later step)."""

from __future__ import annotations

import streamlit as st

from web_util import page_header

page_header(
    "Methodology",
    "Data sources, screening rules, volatility convention and current limitations.",
    eyebrow="Transparency",
)
st.info("Methodology content is added in a later development step.", icon=":material/construction:")
