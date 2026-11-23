"""Universe Explorer (Amber design): results of the investor screening."""

import streamlit as st
import plotly.express as px

from web_util import CHART_BLUE, PAGES, RESULT_KEY, SLEEVE_COLORS, page_header, section_header, style_figure

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

table = filtered[
    ["name", "zone", "country", "industry",
     "sector", "isin"]
].rename(columns={
    "name": "Company",
    "zone": "Region",
    "country": "Country",
    "industry": "Industry",
    "sector": "Sector",
    "isin": "ISIN"
})

table = table.sort_values(["Region", "Company"])

st.dataframe(table, hide_index=True, width="stretch")

cap_col, dl_col = st.columns([3, 1], vertical_alignment="center")
cap_col.caption(f"{len(table)} companies displayed.")
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
