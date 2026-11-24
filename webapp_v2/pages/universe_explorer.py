"""Universe explorer: every stock we can invest in, by region, industry and ESG score, with live filters."""

import pandas as pd
import streamlit as st

import config as cfg
import content
from logic import data, universe
from ui import blocks, charts

U = content.UNIVERSE


def held_note(regions: list[str]) -> None:
    """One line when the portfolio can hold fewer stocks than the universe lists (1-year history rule)."""
    table = universe.held_vs_listed(regions)
    gaps = table[table["held"] < table["listed"]]
    if not gaps.empty:
        pairs = ", ".join(U["held_pair"].format(held=row["held"], listed=row["listed"], region=name)
                          for name, row in gaps.iterrows())
        st.caption(U["held_note"].format(pairs=pairs, n=cfg.ESTIMATION_WINDOW))


def breakdown(table: pd.DataFrame, regions: list[str]) -> None:
    """Stocks per region (vertical bars) and per industry (horizontal bars, largest first)."""
    blocks.section(U["breakdown"])
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"**{U['geo']}**")
        by_region = table["zone"].value_counts().reindex(regions, fill_value=0)
        charts.counts(by_region, axis_title=U["stocks"], key="uni_geo")
    with right:
        st.markdown(f"**{U['industry']}**")
        charts.counts(table["industry"].value_counts(), horizontal=True, axis_title=U["stocks"], key="uni_industry")
    st.caption(U["counts_caption"])
    held_note(regions)


def esg(table: pd.DataFrame) -> None:
    """Average, median and coverage of the ESG scores, and their distribution."""
    blocks.section(U["esg"])
    s = universe.esg_summary(table)
    blocks.figures([(blocks.count_up(s["mean"], 2), U["esg_mean"]), (blocks.count_up(s["median"], 2), U["esg_median"]),
                    (blocks.count_up(100 * s["coverage"], 1, "%"), U["esg_coverage"])])
    st.markdown(f"**{U['esg_hist']}**")
    charts.histogram(table["esg_score"], U["esg_axis"], cfg.HIST_BINS, key="uni_hist")


blocks.hero("universe")
top = st.container()  # filled after the filters below, so every chart follows them
blocks.section(U["companies"])
search = st.text_input(U["search"], key="uni_search")
regions = st.multiselect(U["region_filter"], data.regions(), default=data.regions(), key="uni_regions")
table = universe.explore(tuple(regions), search)
with top:
    if table.empty:
        st.info(U["empty"])
    else:
        breakdown(table, regions)
        esg(table)
st.dataframe(table[list(content.UNIVERSE_COLUMNS)].rename(columns=content.UNIVERSE_COLUMNS), hide_index=True,
             width="stretch")
st.caption(U["displayed"].format(n=len(table)))
