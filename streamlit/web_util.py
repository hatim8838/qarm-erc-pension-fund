"""Shared layout, theme and formatting helpers for the Streamlit pages."""

from __future__ import annotations

import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

APP_NAME = "Léman Wealth Management"

# Page files (relative to the entry point) - one place for st.Page / st.page_link.
PAGES = {
    "home": "home_page.py",
    "preferences": "investor_preferences.py",
    "explorer": "universe_explorer.py",
    "methodology": "methodology.py",
}

# Session-state keys shared across pages.
PREFS_KEY = "investor_prefs"        # last answers of the questionnaire (survive page switches)
RESULT_KEY = "screening_result"     # last applied screening (dict from services.run_screening)

# Modules planned by the quant team; shown as text only, never as working pages.
COMING_LATER = ["ERC Optimization", "ESG Risk Budgeting", "Backtesting", "Performance Analytics"]

# Restrained palette (navy / slate, green reserved for ESG).
NAVY = "#1B365D"
SLATE = "#5B6B7F"
ESG_GREEN = "#2E7D5B"
LIGHT_GRID = "#E3E8EF"
ZONE_COLORS = {
    "US": "#1B365D",
    "Europe": "#3E6FA8",
    "Asia": "#7A9CC6",
    "Oceania": "#2E7D5B",
    "Middle East & Africa": "#C08A3E",
    "Emerging Europe": "#8C5A7A",
}

_CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1250px;}
.qarm-eyebrow {color: #5B6B7F; font-size: 0.8rem; letter-spacing: .08em;
               text-transform: uppercase; margin-bottom: .1rem;}
.qarm-badge {display: inline-block; padding: .15rem .55rem; border-radius: 999px;
             font-size: .75rem; font-weight: 600; margin-right: .3rem;}
.qarm-live {background: #E5F2EC; color: #2E7D5B;}
.qarm-dev {background: #EEF1F5; color: #5B6B7F;}
</style>
"""


def apply_theme() -> None:
    """Inject the small CSS layer (call once per run, from the entry point)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Consistent page title block."""
    if eyebrow:
        st.markdown(f'<div class="qarm-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def badge(text: str, live: bool) -> str:
    """HTML status pill: green for live features, grey for in-development ones."""
    cls = "qarm-live" if live else "qarm-dev"
    return f'<span class="qarm-badge {cls}">{text}</span>'


def style_figure(fig: go.Figure, height: int = 340) -> go.Figure:
    """Common Plotly styling (fonts, margins, grid, legend)."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#1A1F2B"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor=LIGHT_GRID)
    fig.update_yaxes(gridcolor=LIGHT_GRID, zeroline=False)
    return fig


# --------------------------------------------------------------------------- #
# Formatting (missing values stay visibly missing)
# --------------------------------------------------------------------------- #
MISSING = "—"


def _is_missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def fmt_int(x) -> str:
    return MISSING if _is_missing(x) else f"{int(x):,}"


def fmt_pct(x, digits: int = 1) -> str:
    """0.214 -> '21.4%'."""
    return MISSING if _is_missing(x) else f"{100 * float(x):.{digits}f}%"


def fmt_score(x, digits: int = 1) -> str:
    """ESG score on its native 0-100 scale."""
    return MISSING if _is_missing(x) else f"{float(x):.{digits}f}"


def fmt_date(ts) -> str:
    return MISSING if ts is None else ts.strftime("%d %b %Y")