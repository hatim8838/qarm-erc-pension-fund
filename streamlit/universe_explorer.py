"""Universe Explorer: results of the investor screening (implemented in the next step)."""

import streamlit as st
import pandas as pd
import plotly.express as px

from web_util import PAGES, RESULT_KEY, page_header, style_figure

page_header(
    "Universe Explorer",
    "Explore your personalized ESG-screened investment universe.",
    eyebrow="Léman Wealth Management · Step 2"
)

result = st.session_state.get(RESULT_KEY)

if result is None:
    st.info("Please apply your investor preferences first.")
    st.page_link(PAGES["preferences"], label="Investor Preferences")
    st.stop()

selected = result["selected"].copy()
funnel = result["funnel"]
params = result["params"]

# Key indicators
c1, c2, c3, c4 = st.columns(4)

c1.metric("Stocks in scope", funnel["in_scope"])
c2.metric("Eligible stocks", funnel["eligible_in_scope"])
c3.metric("Selected stocks", len(selected))
c4.metric("ESG ambition", params.esg_label)

st.caption(
    "Screened investment universe — portfolio weights "
    "have not yet been calculated."
)

if selected.empty:
    st.warning("No stocks match your selection.")
    st.stop()

st.divider()


# Geographical and industry breakdown
st.subheader("Investment universe breakdown")

left, right = st.columns(2, gap="large")

with left:
    st.markdown("**Geographical breakdown**")

    regions = selected["zone"].value_counts().reset_index()
    regions.columns = ["Region", "Stocks"]

    fig = px.bar(
        regions,
        x="Region",
        y="Stocks",
        text="Stocks",
        color_discrete_sequence=["#1B365D"]
    )

    fig = style_figure(fig)
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=420,
        showlegend=False,
        margin=dict(l=10, r=20, t=30, b=30),
        xaxis_title=None,
        yaxis_title="Number of stocks"
    )

    st.plotly_chart(fig, width="stretch")

with right:
    st.markdown("**Industry breakdown**")

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
        color_discrete_sequence=["#347D72"]
    )

    fig = style_figure(fig)
    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )
    fig.update_layout(
        height=420,
        showlegend=False,
        margin=dict(l=10, r=35, t=30, b=30),
        xaxis_title="Number of stocks",
        yaxis_title=None
    )

    st.plotly_chart(fig, width="stretch")

st.caption(
    "Breakdowns are based on stock counts, "
    "not portfolio weights."
)

st.divider()

# ESG analysis
st.subheader("ESG analysis")

a, b, c = st.columns(3)

scores = pd.to_numeric(selected["esg_score"], errors="coerce")

a.metric("Average ESG score", f"{scores.mean():.2f}")
b.metric("Median ESG score", f"{scores.median():.2f}")
c.metric("ESG score coverage", f"{scores.notna().mean():.1%}")

fig = px.histogram(
    selected,
    x="esg_score",
    nbins=20,
    title="ESG score distribution",
    color_discrete_sequence=["#2E7D5B"]
)

st.plotly_chart(style_figure(fig))

with st.expander("ESG screening adjustments"):
    for warning in result["warnings"]:
        st.warning(warning)

    st.dataframe(result["effective_table"], hide_index=True)

st.divider()

# Interactive stock table
st.subheader("Selected companies")

search = st.text_input("Search for a company")

regions_filter = st.multiselect(
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
     "sector", "esg_score", "isin"]
].rename(columns={
    "name": "Company",
    "zone": "Region",
    "country": "Country",
    "industry": "Industry",
    "sector": "Sector",
    "esg_score": "ESG Score",
    "isin": "ISIN"
})

table = table.sort_values("ESG Score", ascending=False)

st.dataframe(table, hide_index=True, width="stretch")

st.caption(f"{len(table)} companies displayed.")

st.download_button(
    "Download selected companies",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="leman_investment_universe.csv",
    mime="text/csv"
)

st.divider()

st.page_link(
    PAGES["preferences"],
    label="Modify investor preferences"
)
