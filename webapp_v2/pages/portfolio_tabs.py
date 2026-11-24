"""The five tabs of "Your portfolio": allocation, risk, diversification, performance, projection."""

import pandas as pd
import streamlit as st

import config as cfg
import content
import services
from logic import data, performance, profile, projection, report, universe
from logic.portfolio import net_returns, stock_weights
from logic.risk import var_es_table
from ui import blocks, charts, tables

T = content.TEXT


def allocation(result: dict, choices) -> None:
    """α vs risk-free, weights by class, sleeve and sector, and the ESG score vs the ESG-off version."""
    left, right = st.columns(2)
    with left:
        blocks.section(T["by_class"], lecture="LN 2")
        charts.donut(report.by_class(result), key="alloc_class")
    with right:
        blocks.section(T["by_region"])
        charts.bars(result["weights"].iloc[-1].to_frame(T["by_region"]), horizontal=True, key="alloc_sleeve")
    sectors = report.by_sector(result)
    if not sectors.empty:
        blocks.section(T["by_sector"])
        charts.bars(sectors.to_frame(T["by_sector"]), horizontal=True, key="alloc_sector")
        score = universe.esg_score(stock_weights(result))
        off = universe.esg_score(stock_weights(services.build(choices.but(esg="off"))))
        st.metric(T["esg_vs"], f"{score:.1f}", f"{score - off:+.1f} vs {content.ESG_LABELS['off']}")


def risk(result: dict, choices, net: pd.Series) -> None:
    """Target vs realised σ, LN 5 decomposition, LN 6 VaR/ES, drawdowns and crisis returns."""
    blocks.section(T["target_vs"], lecture="LN 2")
    ex_ante = pd.Series({t: d["alpha"] * d["sigma_hat"] for t, d in result["decisions"].items()}, name=T["ex_ante"])
    blocks.figures([(blocks.count_up(100 * choices.target(), 1, "%"), "σ*"),
                    (blocks.count_up(100 * performance.realised_volatility(net), 1, "%"), "σ realised"),
                    (blocks.count_up(100 * ex_ante.mean(), 1, "%"), T["ex_ante"])])
    charts.lines(ex_ante.to_frame().assign(**{"σ*": choices.target()}), percent_y=True, height=300, key="risk_ex_ante")
    blocks.section(T["decomp"], lecture="LN 5")
    tables.show(report.risk_table(result))
    blocks.section(T["var_es"], lecture="LN 6")
    tables.show(var_es_table(net))
    both = pd.concat([net.rename("Your portfolio"), data.benchmarks()[cfg.COMPOSITE_BENCHMARKS]], axis=1)
    charts.lines(performance.drawdowns(both), percent_y=True, height=300, key="risk_dd")
    blocks.section(T["crises"])
    tables.show(performance.crisis_table(both))


def diversification(result: dict) -> None:
    """H*, Gini, I* on weights and on RC, and DR, vs EW and 60/40."""
    blocks.section(T["diversification"], lecture="LN 6")
    table = report.diversification_table(result)
    tables.show(table, plain=set(table.columns))


def performance_tab(result: dict, net: pd.Series) -> None:
    """Backtest vs a chosen benchmark b: SR, TE, IR, gross vs net, turnover and weights over time."""
    benchmark = st.selectbox(T["benchmark"], list(data.benchmarks().columns), key="benchmark")
    both = pd.concat([net.rename("Your portfolio"), data.benchmarks()[benchmark]], axis=1)
    blocks.section(T["benchmark"] + f": {benchmark}", lecture="LN 2")
    charts.lines(performance.wealth(both), log_y=True, key="perf_wealth")
    table = performance.metrics_table(both)[["ann_return", "ann_volatility", "sharpe", "max_drawdown"]]
    rel = performance.relative(net, data.benchmarks()[benchmark])
    tables.show(table.assign(**rel).rename(columns=content.METRIC_LABELS), plain={content.METRIC_LABELS["sharpe"],
                content.METRIC_LABELS["information_ratio"]})
    blocks.section(T["gross_net"], lecture="LN 3")
    gross = pd.concat([result["returns"].rename("Gross"), net.rename("Net")], axis=1)
    tables.show(performance.metrics_table(gross)[["ann_return", "sharpe"]])
    st.caption(T["turnover"])
    charts.bars(result["total_turnover"].iloc[1:].to_frame(T["turnover"]), height=240, key="perf_turnover")
    st.caption(T["weights_time"])
    charts.stacked_area(result["weights"], key="perf_weights")


def projection_tab(net: pd.Series, values: dict) -> None:
    """μ̂ with its 95% estimation interval (LN 3) and the log-normal fan of 10,000 (LN 6)."""
    e = projection.expected_return(net)
    blocks.section(T["expected"], lecture="LN 3")
    blocks.figures([(blocks.count_up(100 * e["mu"], 1, "%"), T["expected"]),
                    (blocks.count_up(100 * e["margin"], 1, "%"), "± 95%"),
                    (blocks.count_up(100 * e["sigma"], 1, "%"), "σ̂")])
    st.caption(T["ci_note"].format(margin=blocks.pct(e["margin"]), years=e["years"]))
    horizon = st.slider(T["horizon"], 1, cfg.MAX_HORIZON, profile.horizon(values["answers"]), key="horizon")
    blocks.section(T["fan"].format(start=f"{cfg.START_VALUE:,}"), lecture="LN 6")
    charts.fan(projection.fan(e["mu"], e["sigma"], horizon), key="proj_fan")
    st.warning(content.NOT_A_GUARANTEE, icon=":material/info:")


def render(result: dict, choices, values: dict) -> None:
    """The five tabs, on returns net of the chosen transaction cost."""
    net = net_returns(result, values["cost"])
    tabs = st.tabs(T["tabs"])
    with tabs[0]:
        allocation(result, choices)
    with tabs[1]:
        risk(result, choices, net)
    with tabs[2]:
        diversification(result)
    with tabs[3]:
        performance_tab(result, net)
    with tabs[4]:
        projection_tab(net, values)
