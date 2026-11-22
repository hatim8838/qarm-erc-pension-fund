"""Home: who we are, the approach, the track record, how to use the app and the data behind it."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from core.config import PORTFOLIO_START
from services import (
    DataUnavailableError,
    coverage_by_zone,
    load_data_window,
    load_series_names,
    load_universe,
    universe_totals,
)
from web_util import (
    APP_NAME,
    CHART_BLUE,
    FOOTER_GREY,
    PAGES,
    PEACH,
    chart_colors,
    feature_card,
    fmt_date,
    fmt_int,
    fmt_pct,
    section_header,
    style_figure,
)

BANNER_PATH = Path(__file__).parent / "assets" / "leman_banner.png"
HERO_HEIGHT = "400px"   # fixed-height hero
BANNER_FOCUS_Y = "18%"  # vertical framing: 0% = top of the image, 100% = bottom


@st.cache_data(show_spinner=False)
def _banner_data_uri() -> str:
    """Banner as a light JPEG data URI (the PNG is 2 MB)."""
    from PIL import Image

    img = Image.open(BANNER_PATH).convert("RGB")
    img.thumbnail((1800, 1800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- #
# Hero
# --------------------------------------------------------------------------- #
try:
    st.markdown(
        f'<div role="img" aria-label="{APP_NAME}: Grow your wealth. Balance your risk." '
        f'style="width:100%; height:{HERO_HEIGHT}; border-radius:15px; '
        f"background:url({_banner_data_uri()}) center {BANNER_FOCUS_Y} / cover no-repeat;\"></div>",
        unsafe_allow_html=True,
    )
except Exception:  # Pillow or the image missing: fall back to the plain image
    st.image(str(BANNER_PATH), width="stretch")

st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Mandate
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="amber-top">A pension portfolio where no single risk dominates</div>
    <div class="amber-lead">We manage a <b>multi-asset portfolio for a pension fund</b>: global equities,
    US bonds and commodities. Instead of splitting the money equally, we split the <b>risk</b> equally:
    every building block contributes the same share of the portfolio's volatility. This is the
    <b>Equal Risk Contribution (ERC)</b> approach.</div>
    <div class="amber-lead">You choose where to invest and how demanding the ESG screen should be;
    we build the portfolio, show you where its risk comes from and how the same rules behaved in the past.</div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Approach
# --------------------------------------------------------------------------- #
section_header("Our approach")
a1, a2, a3 = st.columns(3, gap="medium")
with a1:
    feature_card(
        "Equal risk, not equal capital",
        "Calmer assets receive more capital, volatile ones less, so that each region, bonds and "
        "commodities carry the same share of risk.",
    )
with a2:
    feature_card(
        "ESG best in class",
        "Each stock is compared with peers of the same region and industry. Only the best rated are kept, "
        "at the level of ambition you choose.",
    )
with a3:
    feature_card(
        "Robust by design",
        "No return forecasts: the allocation relies only on risk and correlations, which are far more "
        "stable to estimate.",
    )

# --------------------------------------------------------------------------- #
# How to use this app
# --------------------------------------------------------------------------- #
section_header("How it works")
s1, s2, s3, s4 = st.columns(4, gap="medium")
with s1:
    feature_card("1. Your preferences", "Choose regions, industries, ESG ambition and asset classes.")
with s2:
    feature_card("2. Your universe", "Explore the stocks that passed your screen.")
with s3:
    feature_card("3. Your portfolio", "See the allocation, where the risk comes from and the historical simulation.")
with s4:
    feature_card("4. Our methodology", "The method in plain language, the data and its limits.")

st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
_, cta_col, _ = st.columns([1, 2, 1])
with cta_col, st.container(key="cta"):
    st.markdown("### Ready to build your portfolio?")
    st.markdown("Set your preferences in a few clicks; the risk-balanced portfolio follows.")
    st.page_link(PAGES["preferences"], label="Start with your preferences", icon=":material/arrow_forward:")

# --------------------------------------------------------------------------- #
# Data behind the portfolio
# --------------------------------------------------------------------------- #
section_header("The data behind it")

try:
    universe = load_universe()
except DataUnavailableError as exc:
    st.error(str(exc))
    st.stop()

totals = universe_totals(universe)
window = load_data_window()
bonds = load_series_names("bonds")
commodities = load_series_names("commodities")
cov = coverage_by_zone(universe)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stocks in the universe", fmt_int(totals["stocks"]),
          help=f"Index constituents across the {len(cov)} equity regions.")
c2.metric("Equity regions", fmt_int(len(cov)), help="US, Eurozone, Pacific and EM EMEA.")
c3.metric("ESG score coverage", fmt_pct(totals["esg_coverage"]),
          help=f"{fmt_int(totals['with_esg'])} of {fmt_int(totals['stocks'])} stocks have an ESG score.")
c4.metric("Bond & commodity indices", fmt_int(len(bonds) + len(commodities)),
          help=f"Bonds: {', '.join(bonds) or '—'}. Commodities: {', '.join(commodities) or '—'}.")

st.write("")
chart_col, table_col = st.columns([5, 7], gap="large")
with chart_col:
    st.markdown("<p class='feature-title'>Stocks per region</p>", unsafe_allow_html=True)
    zones_rev = cov.index[::-1]  # first region on top
    fig = go.Figure()
    fig.add_bar(name="All constituents", y=zones_rev, x=cov.loc[zones_rev, "stocks"],
                orientation="h", marker_color=PEACH)
    fig.add_bar(name=f"Eligible on {PORTFOLIO_START}", y=zones_rev, x=cov.loc[zones_rev, "eligible_at_start"],
                orientation="h", marker_color=CHART_BLUE)
    fig.update_layout(barmode="overlay", xaxis_title="Number of stocks")
    fig = style_figure(fig, height=320)
    fig.update_layout(margin=dict(t=30))
    fig.update_xaxes(showgrid=True, gridcolor=chart_colors()["grid"])
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig)
with table_col:
    st.markdown("<p class='feature-title'>Coverage by region</p>", unsafe_allow_html=True)
    st.dataframe(
        cov.reset_index()[["zone", "source_index", "stocks", "eligible_at_start", "esg_coverage", "median_esg"]],
        hide_index=True,
        width="stretch",
        column_config={
            "zone": "Region",
            "source_index": "Source index",
            "stocks": st.column_config.NumberColumn("Stocks", format="%d", width="small"),
            "eligible_at_start": st.column_config.NumberColumn("Eligible", format="%d", width="small",
                                                               help=f"Full one-year history on {PORTFOLIO_START}"),
            "esg_coverage": st.column_config.ProgressColumn(
                "ESG coverage", format="percent", min_value=0.0, max_value=1.0,
                help="Share of the region's stocks with an ESG score",
            ),
            "median_esg": st.column_config.NumberColumn("Median ESG", format="%.1f", width="small",
                                                        help="Median ESG score (0-100)"),
        },
    )

window_txt = f"{fmt_date(window[0])} to {fmt_date(window[1])}" if window is not None else "the full history"
st.markdown(
    f'<span style="color:{FOOTER_GREY};font-size:.85rem">Source: Datastream, daily total returns in USD, '
    f"{window_txt}. Historical data, not live quotes.</span>",
    unsafe_allow_html=True,
)
