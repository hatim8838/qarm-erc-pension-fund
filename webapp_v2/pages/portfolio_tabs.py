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


@st.fragment
def performance_tab(result: dict, net: pd.Series, alpha: float) -> None:
    """The one comparison with a benchmark: your portfolio vs 60/40 or 1/N given the same α (value of 100,
    drawdown, SR, MDD, TE, IR), then gross vs net, turnover and weights over time."""
    benchmark = st.selectbox(T["benchmark"], cfg.COMPOSITE_BENCHMARKS, key="benchmark")  # 60/40 and 1/N
    mine = net.rename("Your portfolio")
    bench = performance.with_alpha(data.benchmarks()[benchmark], alpha, data.risk_free_daily()).rename(benchmark)
    both = pd.concat([mine, bench], axis=1)
    blocks.section(T["bench_title"].format(b=benchmark, rf=blocks.pct(1 - alpha, 0)) if alpha < 1 else benchmark)
    charts.lines(performance.wealth(both), log_y=True, key="perf_wealth")
    blocks.section(T["drawdown_title"].format(b=benchmark))
    charts.lines(performance.drawdown(both), percent_y=True, height=300, key="perf_drawdown")
    st.caption(T["drawdown_note"])
    table = performance.metrics_table(both)[["ann_return", "ann_volatility", "sharpe", "max_drawdown"]]
    # tracking error and IR compare a portfolio with the benchmark: empty on the benchmark row itself
    for col in ("tracking_error", "information_ratio"):
        table[col] = float("nan")
    for col, value in performance.relative(mine, bench).items():
        table.loc[mine.name, col] = value
    tables.show(table.rename(columns=content.METRIC_LABELS), plain={content.METRIC_LABELS["sharpe"],
                content.METRIC_LABELS["information_ratio"]})
    st.caption(T["bench_note"].format(rf=blocks.pct(1 - alpha, 0)))
    blocks.section(T["gross_net"])
    gross = pd.concat([result["returns"].rename("Gross"), net.rename("Net")], axis=1)
    costs = performance.metrics_table(gross)[["ann_return", "sharpe"]]
    tables.show(costs.rename(columns=content.METRIC_LABELS), plain={content.METRIC_LABELS["sharpe"]})
    drag = costs.loc["Gross", "ann_return"] - costs.loc["Net", "ann_return"]
    st.caption(T["cost_note"].format(bps=cfg.TRANSACTION_COST_BPS, drag=blocks.pct(drag, 2)))
    blocks.section(T["turnover"])
    charts.bars(result["total_turnover"].iloc[1:].to_frame(T["turnover"]), height=240, key="perf_turnover")
    st.caption(T["turnover_note"])
    blocks.section(T["weights_time"])
    charts.stacked_area(result["weights"], key="perf_weights")


@st.fragment
def projection_tab(net: pd.Series) -> None:
    """μ̂ with its 95% estimation interval and the log-normal fan of 10,000."""
    e = projection.expected_return(net)
    blocks.section(T["expected"])
    blocks.figures([(blocks.count_up(100 * e["mu"], 1, "%"), T["expected"]),
                    (blocks.count_up(100 * e["margin"], 1, "%"), "± 95%"),
                    (blocks.count_up(100 * e["sigma"], 1, "%"), T["expected_vol"])])
    st.caption(T["ci_note"].format(margin=blocks.pct(e["margin"]), years=e["years"]))
    horizon = st.slider(T["horizon"], 1, cfg.MAX_HORIZON, cfg.DEFAULT_HORIZON, key="horizon")
    blocks.section(T["fan"].format(start=f"{cfg.START_VALUE:,}"))
    charts.fan(projection.fan(e["mu"], e["sigma"], horizon), key="proj_fan")
    st.warning(content.NOT_A_GUARANTEE, icon=":material/info:")


def render(result: dict, choices, values: dict) -> None:
    """The four tabs, on returns net of the transaction cost."""
    net = net_returns(result, cfg.TRANSACTION_COST_BPS)
    tabs = st.tabs(T["tabs"])
    with tabs[0]:
        composition_tabs.allocation(result)
        classes_and_sectors(result, choices)
        blocks.method_box()
    with tabs[1]:
        composition_tabs.risk_contribution(result)
        blocks.method_box()
    with tabs[2]:
        performance_tab(result, net, choices.alpha())
    with tabs[3]:
        projection_tab(net)
