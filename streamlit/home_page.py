"""Home: mandate, how to use the app, real data coverage and roadmap."""

from __future__ import annotations

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
    COMING_LATER,
    NAVY,
    PAGES,
    SLATE,
    badge,
    fmt_date,
    fmt_int,
    fmt_pct,
    page_header,
    style_figure,
)

page_header(
    APP_NAME,
    "Multi-asset portfolio construction for a pension fund with Equal Risk Contributions (ERC) "
    "and ESG-based risk budgeting.",
    eyebrow="HEC Lausanne · Quantitative Asset & Risk Management II",
)

st.markdown(
    badge("Live · Universe screening", live=True) + badge("In development · ERC & backtesting", live=False),
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Mandate + how to use
# --------------------------------------------------------------------------- #
left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader("The mandate")
    st.markdown(
        "We act as consultants to a **multi-asset pension fund**. The target portfolio spreads "
        "**risk**, not capital, equally across its building blocks: an ERC portfolio gives every "
        "asset the same contribution to total portfolio volatility. Asset classes are global "
        "equities (six investor zones), US corporate & government bonds and commodities.\n\n"
        "Within equities, the investor first chooses **regions**, **industries** and an **ESG "
        "ambition**. This app currently delivers that first step: an interactive, transparent "
        "screening of the stock universe."
    )
with right:
    with st.container(border=True):
        st.markdown("**How to use this app**")
        st.markdown(
            "1. **Investor Preferences**: choose regions, industries and ESG ambition.\n"
            "2. **Universe Explorer**: inspect the screened stocks, ESG scores and volatility.\n"
            "3. **Methodology**: data sources, screening rules and current limitations."
        )
        st.page_link(PAGES["preferences"], label="Start with Investor Preferences", icon=":material/arrow_forward:")

# --------------------------------------------------------------------------- #
# Real data coverage
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Data coverage")

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

cov = coverage_by_zone(universe)
chart_col, table_col = st.columns([5, 7], gap="medium")
with chart_col:
    st.markdown("**Stocks per investor zone**")
    zones_rev = cov.index[::-1]  # first zone on top
    fig = go.Figure()
    fig.add_bar(name="All constituents", y=zones_rev, x=cov.loc[zones_rev, "stocks"],
                orientation="h", marker_color="#C9D3E0")
    fig.add_bar(name=f"Eligible on {PORTFOLIO_START}", y=zones_rev, x=cov.loc[zones_rev, "eligible_at_start"],
                orientation="h", marker_color=NAVY)
    fig.update_layout(barmode="overlay", xaxis_title="Number of stocks")
    fig = style_figure(fig, height=300)
    fig.update_layout(margin=dict(t=30))
    fig.update_xaxes(showgrid=True, gridcolor="#E3E8EF")
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch")
with table_col:
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

b_col, s_col = st.columns(2, gap="large")
with b_col:
    st.markdown("**Benchmarks**")
    bench = benchmark_status(load_series_names("benchmarks"))
    st.dataframe(bench, hide_index=True, width="stretch",
                 column_config={"benchmark": "Benchmark", "used_for": "Used for", "status": "Status"})
with s_col:
    st.markdown("**Non-equity sleeves**")
    st.markdown(
        f"- Bonds: {', '.join(bonds) if bonds else 'not available'}\n"
        f"- Commodities: {', '.join(commodities) if commodities else 'not available'}"
    )
    st.caption("Volatility convention: annualized 1-year (252 business days) rolling standard deviation "
               "of daily simple returns.")

# --------------------------------------------------------------------------- #
# Roadmap
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Roadmap")
st.markdown(
    badge("Live", True) + " Cleaned processed data · ESG best-in-class screening · Universe exploration",
    unsafe_allow_html=True,
)
st.markdown(
    badge("In development", False) + " " + " · ".join(COMING_LATER),
    unsafe_allow_html=True,
)
st.caption(
    "No portfolio weights, risk contributions or performance figures are shown until the "
    "optimization and backtesting modules are delivered. Educational research, not investment advice."
)
st.markdown(f'<span style="color:{SLATE};font-size:.8rem">Source data: Datastream (daily, USD).</span>',
            unsafe_allow_html=True)
