"""Home: mandate, how to use the app, real data coverage and roadmap (Amber design)."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from core.config import DATA_START, PORTFOLIO_START
from services import (
    DataUnavailableError,
    benchmark_status,
    coverage_by_zone,
    load_data_window,
    load_series_names,
    load_universe,
    universe_totals,
)
from web_util import (
    APP_NAME,
    CHART_BLUE,
    COMING_LATER,
    FOOTER_GREY,
    PAGES,
    PEACH,
    badge,
    chart_colors,
    feature_card,
    fmt_date,
    fmt_int,
    fmt_pct,
    section_header,
    style_figure,
)

BANNER_PATH = Path(__file__).parent / "assets" / "leman_banner.png"
HERO_HEIGHT = "400px"   # fixed-height hero, as in the reference design
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

st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
st.markdown(
    badge("Live · Universe screening", live=True) + badge("In development · ERC & backtesting", live=False),
    unsafe_allow_html=True,
)
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Mandate (welcome block)
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="amber-top">The mandate</div>
    <div class="amber-lead">We act as consultants to a <b>multi-asset pension fund</b>. The target portfolio
    spreads <b>risk</b>, not capital, equally across its building blocks: an ERC portfolio gives every asset
    the same contribution to total portfolio volatility. Asset classes are global equities (six investor
    zones), US corporate &amp; government bonds and commodities.</div>
    <div class="amber-lead">Within equities, the investor first chooses <b>regions</b>, <b>industries</b>
    and an <b>ESG ambition</b>. This app currently delivers that first step: an interactive, transparent
    screening of the stock universe.</div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# How to use this app
# --------------------------------------------------------------------------- #
section_header("How to use this app")
s1, s2, s3 = st.columns(3, gap="medium")
with s1:
    feature_card("1. Investor Preferences", "Choose regions, industries and ESG ambition.")
with s2:
    feature_card("2. Universe Explorer", "Inspect the screened stocks, ESG scores and volatility.")
with s3:
    feature_card("3. Methodology", "Data sources, screening rules and current limitations.")

st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
_, cta_col, _ = st.columns([1, 2, 1])
with cta_col, st.container(key="cta"):
    st.markdown("### Ready to define your investment universe?")
    st.markdown("Set your preferences in a few clicks and see the screened universe immediately.")
    st.page_link(PAGES["preferences"], label="Start with Investor Preferences", icon=":material/arrow_forward:")

# --------------------------------------------------------------------------- #
# Real data coverage
# --------------------------------------------------------------------------- #
section_header("Data coverage")

try:
    universe = load_universe()
except DataUnavailableError as exc:
    st.error(str(exc))
    st.stop()

totals = universe_totals(universe)
window = load_data_window()
bonds = load_series_names("bonds")
commodities = load_series_names("commodities")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity universe", fmt_int(totals["stocks"]), help="Index constituents across the six investor zones.")
c2.metric(
    "Eligible at portfolio start",
    fmt_int(totals["eligible_at_start"]),
    help=f"Stocks with a sufficiently complete 1-year history on {PORTFOLIO_START}.",
)
c3.metric(
    "ESG score coverage",
    fmt_pct(totals["esg_coverage"]),
    help=f"{fmt_int(totals['with_esg'])} of {fmt_int(totals['stocks'])} stocks have an ESG score.",
)
c4.metric(
    "Bond & commodity indices",
    fmt_int(len(bonds) + len(commodities)),
    help=f"{len(bonds)} bond and {len(commodities)} commodity indices in the processed data.",
)
if window is not None:
    st.caption(
        f"Processed daily series from {fmt_date(window[0])} to {fmt_date(window[1])} "
        f"(latest available observation; historical data, not live quotes). "
        f"Estimation starts {DATA_START}, portfolio starts {PORTFOLIO_START}."
    )

st.write("")
cov = coverage_by_zone(universe)
chart_col, table_col = st.columns([5, 7], gap="large")
with chart_col:
    st.markdown("<p class='feature-title'>Stocks per investor zone</p>", unsafe_allow_html=True)
    zones_rev = cov.index[::-1]  # first zone on top
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
    st.markdown("<p class='feature-title'>Coverage by zone</p>", unsafe_allow_html=True)
    st.dataframe(
        cov.reset_index()[["zone", "source_index", "stocks", "eligible_at_start", "esg_coverage", "median_esg"]],
        hide_index=True,
        width="stretch",
        column_config={
            "zone": "Investor zone",
            "source_index": "Source index",
            "stocks": st.column_config.NumberColumn("Stocks", format="%d", width="small"),
            "eligible_at_start": st.column_config.NumberColumn("Eligible", format="%d", width="small",
                                                               help=f"Eligible on {PORTFOLIO_START}"),
            "esg_coverage": st.column_config.ProgressColumn(
                "ESG coverage", format="percent", min_value=0.0, max_value=1.0,
                help="Share of the zone's stocks with an ESG score",
            ),
            "median_esg": st.column_config.NumberColumn("Median ESG", format="%.1f", width="small",
                                                        help="Median ESG score (0-100), missing scores ignored"),
        },
    )

st.write("")
b_col, s_col = st.columns(2, gap="large")
with b_col:
    st.markdown("<p class='feature-title'>Benchmarks</p>", unsafe_allow_html=True)
    bench = benchmark_status(load_series_names("benchmarks"))
    st.dataframe(bench, hide_index=True, width="stretch",
                 column_config={"benchmark": "Benchmark", "used_for": "Used for", "status": "Status"})
with s_col:
    st.markdown("<p class='feature-title'>Non-equity sleeves</p>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            f"- **Bonds:** {', '.join(bonds) if bonds else 'not available'}\n"
            f"- **Commodities:** {', '.join(commodities) if commodities else 'not available'}"
        )
        st.caption("Volatility convention: annualized 1-year (252 business days) rolling standard deviation "
                   "of daily simple returns.")

# --------------------------------------------------------------------------- #
# Roadmap
# --------------------------------------------------------------------------- #
section_header("Roadmap")
r1, r2 = st.columns(2, gap="medium")
with r1:
    feature_card(badge("Live", True),
                 "Cleaned processed data · ESG best-in-class screening · Universe exploration")
with r2:
    feature_card(badge("In development", False), " · ".join(COMING_LATER))
st.write("")
st.caption(
    "No portfolio weights, risk contributions or performance figures are shown until the "
    "optimization and backtesting modules are delivered. Educational research, not investment advice."
)
st.markdown(f'<span style="color:{FOOTER_GREY};font-size:.8rem">Source data: Datastream (daily, USD).</span>',
            unsafe_allow_html=True)
