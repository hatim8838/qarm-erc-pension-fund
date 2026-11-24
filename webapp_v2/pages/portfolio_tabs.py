"""The four tabs of "Your portfolio": allocation, risk contribution, performance, projection."""

import pandas as pd
import streamlit as st

import config as cfg
import content
from logic import data, performance, portfolio, projection, report, universe
from logic.portfolio import net_returns, stock_weights
from pages import composition_tabs
from ui import blocks, charts, tables

T = content.TEXT


def classes_and_sectors(result: dict, choices) -> None:
    """Weights by asset class (with the risk-free asset) and by sector, and the ESG score vs the ESG-off version."""
    blocks.section(T["by_class"])
    charts.donut(report.by_class(result), key="alloc_class")
    sectors = report.by_sector(result)
    if not sectors.empty:
        blocks.section(T["by_sector"])
        charts.bars(sectors.to_frame(T["by_sector"]), horizontal=True, key="alloc_sector")
        score = universe.esg_score(stock_weights(result))
        off = universe.esg_score(portfolio.today(choices.but(esg=portfolio.NO_SCREEN, level=portfolio.FULL)))
        st.metric(T["esg_vs"], f"{score:.1f}", T["esg_delta"].format(delta=score - off))


def performance_tab(result: dict, net: pd.Series) -> None:
    """Backtest vs a chosen benchmark b: SR, TE, IR, gross vs net, turnover and weights over time."""
    benchmark = st.selectbox(T["benchmark"], list(data.benchmarks().columns), key="benchmark")
    both = pd.concat([net.rename("Your portfolio"), data.benchmarks()[benchmark]], axis=1)
    blocks.section(T["benchmark"] + f": {benchmark}")
    charts.lines(performance.wealth(both), log_y=True, key="perf_wealth")
    table = performance.metrics_table(both)[["ann_return", "ann_volatility", "sharpe", "max_drawdown"]]
    rel = performance.relative(net, data.benchmarks()[benchmark])
    tables.show(table.assign(**rel).rename(columns=content.METRIC_LABELS), plain={content.METRIC_LABELS["sharpe"],
                content.METRIC_LABELS["information_ratio"]})
    blocks.section(T["gross_net"])
    gross = pd.concat([result["returns"].rename("Gross"), net.rename("Net")], axis=1)
    tables.show(performance.metrics_table(gross)[["ann_return", "sharpe"]])
    st.caption(T["turnover"])
    charts.bars(result["total_turnover"].iloc[1:].to_frame(T["turnover"]), height=240, key="perf_turnover")
    st.caption(T["weights_time"])
    charts.stacked_area(result["weights"], key="perf_weights")


def projection_tab(net: pd.Series) -> None:
    """μ̂ with its 95% estimation interval and the log-normal fan of 10,000."""
    e = projection.expected_return(net)
    blocks.section(T["expected"])
    blocks.figures([(blocks.count_up(100 * e["mu"], 1, "%"), T["expected"]),
                    (blocks.count_up(100 * e["margin"], 1, "%"), "± 95%"),
                    (blocks.count_up(100 * e["sigma"], 1, "%"), "σ̂")])
    st.caption(T["ci_note"].format(margin=blocks.pct(e["margin"]), years=e["years"]))
    horizon = st.slider(T["horizon"], 1, cfg.MAX_HORIZON, cfg.DEFAULT_HORIZON, key="horizon")
    blocks.section(T["fan"].format(start=f"{cfg.START_VALUE:,}"))
    charts.fan(projection.fan(e["mu"], e["sigma"], horizon), key="proj_fan")
    st.warning(content.NOT_A_GUARANTEE, icon=":material/info:")


def render(result: dict, choices, values: dict) -> None:
    """The four tabs, on returns net of the chosen transaction cost."""
    net = net_returns(result, values["cost"])
    tabs = st.tabs(T["tabs"])
    with tabs[0]:
        composition_tabs.allocation(result)
        classes_and_sectors(result, choices)
        blocks.method_box()
    with tabs[1]:
        composition_tabs.risk_contribution(result)
        blocks.method_box()
    with tabs[2]:
        performance_tab(result, net)
    with tabs[3]:
        projection_tab(net)
