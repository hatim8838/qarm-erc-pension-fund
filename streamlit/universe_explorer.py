"""Universe Explorer: results of the investor screening (implemented in the next step)."""

from __future__ import annotations

import streamlit as st

from web_util import PAGES, page_header

page_header(
    "Universe Explorer",
    "Explore the ESG-screened stock universe. This is a screened universe, not an optimized portfolio.",
    eyebrow="Step 2 · Investor",
)
st.info("Results will appear here once Investor Preferences are applied (next development step).",
        icon=":material/construction:")
st.page_link(PAGES["preferences"], label="Go to Investor Preferences", icon=":material/arrow_back:")
