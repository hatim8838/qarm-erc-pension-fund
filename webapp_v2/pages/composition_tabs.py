"""Allocation and risk-contribution views of "Your portfolio": what the ERC portfolio holds, and why."""

from html import escape

import pandas as pd
import streamlit as st

import config as cfg
import content
from logic import composition
from ui import blocks, charts, tables

C, pct = content.COMPOSITION, blocks.pct


def _sleeves(result: dict, total_money: bool) -> None:
    """Donut and table of the sleeves, and the insight sentence computed from them."""
    table = composition.sleeves(result, total_money)
    n = len(table.drop(cfg.RISK_FREE, errors="ignore"))
    left, right = st.columns([4, 6], gap="large")
    with left:
        st.markdown(f"**{C['donut']}**")
        charts.donut(table["weight"], height=340, center=C["n_sleeves"].format(n=n), colors=charts.sleeve_colors(),
                     key="alloc_sleeves")
    with right:
        st.markdown(f"**{C['table']}**")
        tables.progress(table, content.SLEEVE_COLUMNS, bars={"weight", "rc"}, counts={"assets"})
    e = composition.extremes(table)
    blocks.insight(C["insight"].format(top=escape(e["top"]), low=escape(e["low"]), top_w=pct(e["top_w"]),
                                       low_w=pct(e["low_w"]), rc=pct(e["rc"])))


def _positions(result: dict, total_money: bool) -> None:
    """Largest holdings, labelled "Name · Sleeve" and coloured like the donut."""
    top = composition.positions(result, cfg.TOP_POSITIONS, total_money)
    labels = [C["position"].format(name=n, sleeve=s) for n, s in zip(top["name"], top["sleeve"])]
    colors = [charts.sleeve_colors()[s] for s in top["sleeve"]]
    charts.ranked(pd.Series(top["weight"].to_numpy(), index=labels), colors, C["weight_axis"], key="alloc_top")


@st.fragment
def allocation(result: dict) -> None:
    """Inside the ERC portfolio (sums to 100%), or × α with a risk-free slice when the toggle is on."""
    blocks.section(C["inside"].format(alpha=pct(result["alpha"], 0)))
    total_money = st.toggle(C["total"], key="total_money")
    _sleeves(result, total_money)
    blocks.section(C["positions"])
    _positions(result, total_money)


@st.fragment
def _inside_sleeve(result: dict, sleeves: list[str]) -> None:
    """Weight inside the chosen sleeve vs RC*_i for its largest assets, against the target 1/N."""
    blocks.section(C["inside_sleeve"])
    sleeve = st.selectbox(C["sleeve"], sleeves, key="rc_sleeve")
    inner = composition.inner(result, sleeve)
    if len(inner) == 1:
        st.info(C["single"].format(sleeve=sleeve))
        return
    top = inner.head(cfg.TOP_INNER)
    st.markdown(C["top_of" if len(inner) > len(top) else "all"].format(k=len(top), n=len(inner)))
    names = {"weight": content.BAR_NAMES["inner_weight"], "rc": content.BAR_NAMES["rc"]}
    charts.versus(top.rename(columns=names), 1 / len(inner), C["target_inner"], C["sleeve_axis"], tilt=True,
                  key="rc_inner")


def risk_contribution(result: dict) -> None:
    """Capital weight vs risk contribution of each sleeve (target 1/n), then inside one sleeve (target 1/N)."""
    table = composition.sleeves(result)
    n = len(table)
    blocks.section(C["across"])
    charts.versus(table[["weight", "rc"]].rename(columns=content.BAR_NAMES), 1 / n,
                  C["target_n"].format(n=n, pct=pct(1 / n)), C["portfolio_axis"], key="rc_across")
    st.caption(C["across_caption"])
    _inside_sleeve(result, list(table.index))
