"""Universe Explorer (Amber design): results of the investor screening."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from core.config import EQUITY_ASSET_CLASS, ICB_INDUSTRIES, PORTFOLIO_START, ZONES
from core.importation_data import read_processed
from web_util import (
    CHART_BLUE, PAGES, RESULT_KEY, SLEEVE_COLORS, page_header, section_header, style_figure, theme_mode,
)

# Listing country (ISIN prefix) -> full name, for the companies table.
COUNTRY_NAMES = {
    "AE": "United Arab Emirates", "AT": "Austria", "AU": "Australia", "BE": "Belgium", "BM": "Bermuda",
    "CH": "Switzerland", "CZ": "Czech Republic", "DE": "Germany", "EG": "Egypt", "ES": "Spain",
    "FI": "Finland", "FR": "France", "GB": "United Kingdom", "GR": "Greece", "HK": "Hong Kong",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "JE": "Jersey", "JP": "Japan", "KW": "Kuwait",
    "KY": "Cayman Islands", "LU": "Luxembourg", "NL": "Netherlands", "NZ": "New Zealand", "PL": "Poland",
    "PT": "Portugal", "QA": "Qatar", "SA": "Saudi Arabia", "SG": "Singapore", "TR": "Turkey",
    "US": "United States", "ZA": "South Africa",
}


@st.cache_data(show_spinner="Loading volatilities…")
def latest_volatility(stocks: tuple[tuple[str, str], ...]) -> tuple[pd.Series, pd.Timestamp | None]:
    """1-year annualised volatility of each stock on the latest data date (index ``"<zone>|<name>"``).

    Only the value on the latest date is used: a stock that stopped trading earlier (delisted,
    merged...) gets NaN instead of an old, stale volatility from the year it last traded.
    """
    vols = []
    for zone in ZONES:
        names = [n for z, n in stocks if z == zone]
        if names:
            vol = read_processed("volatility", EQUITY_ASSET_CLASS[zone], columns=names)
            vol.columns = [f"{zone}|{n}" for n in vol.columns]
            vols.append(vol)
    if not vols:
        return pd.Series(dtype=float), None
    vol = pd.concat(vols, axis=1).dropna(how="all")
    last_date = vol.index[-1]
    return vol.loc[last_date].astype(float), last_date

page_header(
    "Universe Explorer",
    "Explore your personalized investment universe.",
    eyebrow="Léman Wealth Management · Step 2"
)

result = st.session_state.get(RESULT_KEY)

if result is None:
    _, cta_col, _ = st.columns([1, 2, 1])
    with cta_col, st.container(key="cta"):
        st.markdown("### No screened universe yet")
        st.markdown("Please apply your investor preferences first.")
        st.page_link(PAGES["preferences"], label="Investor Preferences", icon=":material/arrow_forward:")
    st.stop()

selected = result["selected"].copy()
funnel = result["funnel"]
params = result["params"]

# Key indicators
c1, c2, c3, c4 = st.columns(4)

c1.metric("Stocks in scope", funnel["in_scope"])
c2.metric("Eligible stocks", funnel["eligible_in_scope"])
c3.metric("Selected stocks", len(selected))
c4.metric("Regions", len(params.regions))

st.caption(
    "Screened investment universe — portfolio weights "
    "have not yet been calculated."
)

if selected.empty:
    st.warning("No stocks match your selection.")
    st.stop()

# Geographical and industry breakdown
section_header("Investment universe breakdown")

left, right = st.columns(2, gap="large")

with left:
    st.markdown("<p class='feature-title'>Geographical breakdown</p>", unsafe_allow_html=True)

    regions = selected["zone"].value_counts().reset_index()
    regions.columns = ["Region", "Stocks"]

    fig = px.bar(
        regions,
        x="Region",
        y="Stocks",
        text="Stocks",
        color="Region",
        color_discrete_map=SLEEVE_COLORS,  # same colour per region as on the ERC Portfolio page
    )

    fig = style_figure(fig)
    fig.update_traces(textposition="outside", texttemplate="<b>%{text}</b>", textfont_size=11, cliponaxis=False)
    fig.update_layout(
        height=420,
        showlegend=False,
        margin=dict(l=10, r=20, t=30, b=30),
        xaxis_title=None,
        yaxis_title="Number of stocks"
    )

    st.plotly_chart(fig)

with right:
    st.markdown("<p class='feature-title'>Industry breakdown</p>", unsafe_allow_html=True)

    sectors = selected["industry"].fillna(
        "Unclassified"
    ).value_counts().reset_index()

    sectors.columns = ["Industry", "Stocks"]
    sectors = sectors.sort_values("Stocks")

    fig = px.bar(
        sectors,
        x="Stocks",
        y="Industry",
        orientation="h",
        text="Stocks",
        color_discrete_sequence=[CHART_BLUE]
    )

    fig = style_figure(fig)
    fig.update_traces(
        textposition="outside",
        texttemplate="<b>%{text}</b>",  # bold count next to each bar
        textfont_size=11,
        cliponaxis=False
    )
    fig.update_layout(
        height=420,
        showlegend=False,
        margin=dict(l=10, r=35, t=30, b=30),
        xaxis_title="Number of stocks",
        yaxis_title=None
    )

    st.plotly_chart(fig)

st.caption(
    "Breakdowns are based on stock counts, "
    "not portfolio weights."
)

# Interactive stock table
section_header("Selected companies")

with st.container(key="card_filters"):
    f1, f2 = st.columns([2, 3], gap="medium")
    search = f1.text_input("Search for a company", placeholder="e.g. Nestlé")
    regions_filter = f2.multiselect(
        "Filter by region",
        options=sorted(selected["zone"].unique()),
        default=sorted(selected["zone"].unique())
    )

filtered = selected[selected["zone"].isin(regions_filter)]

if search:
    filtered = filtered[
        filtered["name"].str.contains(
            search, case=False, regex=False, na=False
        )
    ]

# Professional ordering: regions in the app order, then ICB industry order, then company name.
order = pd.DataFrame(
    {
        "z": filtered["zone"].map({z: i for i, z in enumerate(ZONES)}),
        "i": filtered["industry"].map({ind: i for i, ind in enumerate(ICB_INDUSTRIES)}).fillna(len(ICB_INDUSTRIES)),
        "n": filtered["name"].str.upper(),
    },
    index=filtered.index,
)
filtered = filtered.loc[order.sort_values(["z", "i", "n"], kind="mergesort").index]

vol, vol_date = latest_volatility(tuple((str(z), str(n)) for z, n in zip(selected["zone"], selected["name"])))

table = pd.DataFrame(
    {
        "Company": filtered["name"],
        "ISIN": filtered["isin"],
        "Country": filtered["country"].map(COUNTRY_NAMES).fillna(filtered["country"]),
        "Region": filtered["zone"],
        "Industry": filtered["industry"],
        "Sector": filtered["sector"],
        "1Y volatility": 100 * vol.reindex(filtered.index).to_numpy(),
    }
)
# Show the history check only when it tells something (i.e. not every company has it).
show_history = "eligible_at_start" in filtered.columns and not filtered["eligible_at_start"].all()
if show_history:
    table[f"Full history in {PORTFOLIO_START[:4]}"] = filtered["eligible_at_start"].astype(bool).to_numpy()

vol_note = f" as of {vol_date:%d %b %Y}" if vol_date is not None else ""

# Volatility bar: full at the 95th percentile (rounded up to 10%), so one extreme stock
# does not squash all the other bars.
vol_values = table["1Y volatility"].dropna()
vol_cap = float(max(10, 10 * np.ceil(vol_values.quantile(0.95) / 10))) if not vol_values.empty else 100.0

# Region in its sleeve colour (same colours as the charts), one shade per theme so it stays readable.
REGION_TEXT = {
    "Light": {"US": "#1976D2", "Eurozone": "#B7791F", "Pacific": "#CC6600", "EM EMEA": "#1A2A6C"},
    "Dark": {"US": "#64B5F6", "Eurozone": "#F9C74F", "Pacific": "#FF9933", "EM EMEA": "#9FA8DA"},
}[theme_mode()]
styled = table.style.map(
    lambda r: f"color: {REGION_TEXT.get(r, 'inherit')}; font-weight: 600;", subset=["Region"]
).map(lambda _: "font-weight: 600;", subset=["Company"])

st.dataframe(
    styled,
    hide_index=True,
    width="stretch",
    row_height=38,
    height=min(40 + 38 * len(table), 498),  # about 12 rows visible, scroll for the rest
    column_config={
        "Company": st.column_config.TextColumn("Company", width="large", pinned=True),
        "ISIN": st.column_config.TextColumn(
            "ISIN", width="medium", help="International Securities Identification Number (unique security code)."
        ),
        "Country": st.column_config.TextColumn("Country", help="Country of listing, from the ISIN prefix."),
        "Region": st.column_config.TextColumn("Region", width="small", help="Equity sleeve of the portfolio."),
        "Industry": st.column_config.TextColumn("Industry", help="ICB industry (11 industries)."),
        "Sector": st.column_config.TextColumn("Sector", width="large", help="ICB sector, a finer split of the industry."),
        "1Y volatility": st.column_config.ProgressColumn(
            "1Y volatility",
            format="%.1f%%",
            min_value=0.0,
            max_value=vol_cap,
            width="medium",
            help=f"Annualised volatility of daily returns over the last 252 business days{vol_note}. "
            f"The bar is full at {vol_cap:.0f}%. Empty = no trading in the last year (e.g. delisted). "
            "ERC gives less capital to more volatile stocks.",
        ),
        f"Full history in {PORTFOLIO_START[:4]}": st.column_config.CheckboxColumn(
            f"Full history in {PORTFOLIO_START[:4]}",
            width="small",
            help=f"Complete 1-year return history on {PORTFOLIO_START}, the first rebalancing date.",
        ),
    },
)

cap_col, dl_col = st.columns([3, 1], vertical_alignment="center")
cap_col.caption(
    f"Showing **{len(table):,}** of **{len(selected):,}** selected companies · sorted by region, industry and name"
    f"{' · volatility' + vol_note if vol_date is not None else ''}."
)
dl_col.download_button(
    "Download selected companies",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="leman_investment_universe.csv",
    mime="text/csv",
    icon=":material/download:",
    width="stretch",
)

st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
_, cta_col, _ = st.columns([1, 2, 1])
with cta_col, st.container(key="cta"):
    st.markdown("### Want a different universe?")
    st.markdown("Change regions or industries and screen again.")
    st.page_link(
        PAGES["preferences"],
        label="Modify investor preferences",
        icon=":material/tune:",
    )
