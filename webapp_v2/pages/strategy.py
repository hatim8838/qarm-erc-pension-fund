"""Our strategy: why ERC, EW vs ERC on our data, σ(mv) ≤ σ(erc) ≤ σ(ew), and the real backtest."""

import pandas as pd

import config as cfg
import content
import services
from logic import data, performance, portfolio, report
from logic.portfolio import net_returns
from ui import blocks, charts, tables

T = content.TEXT


def lab(result: dict) -> None:
    """Our sleeves today: RC* of EW vs ERC, and σ(mv) ≤ σ(erc) ≤ σ(ew)."""
    d = report.last_decision(result)
    table = report.compare_ew_erc_mv(d["cov"], d["x"])
    blocks.section(T["lab"], T["lab_sub"].format(date=max(result["decisions"]).date()))
    blocks.figures([(blocks.count_up(100 * table.loc[n, "σ"], 2, "%"), f"σ({n})") for n in ("MV", "ERC", "EW")])
    charts.bars(table.drop(columns="σ").loc[["EW", "ERC"]].T, key="lab_rc")
    holds = report.theorem_holds(result)
    blocks.section(T["theorem"].format(share=blocks.pct(holds.mean(), 0), n=len(holds)))


def backtest(erc: dict, esg: dict) -> None:
    """ERC without and with the ESG screen (fully invested, net of costs) against 60/40 and 1/N."""
    series = pd.DataFrame({name: net_returns(r, cfg.TRANSACTION_COST_BPS) for name, r in (("ERC", erc),
                                                                                         (cfg.ESG_SERIES, esg))})
    returns = performance.aligned(pd.concat([series, data.benchmarks()[cfg.COMPOSITE_BENCHMARKS]], axis=1))
    blocks.section(T["backtest"], T["backtest_sub"].format(
        esg=cfg.STRATEGY_ESG, share=blocks.pct(cfg.ESG_LEVELS[cfg.STRATEGY_ESG], 0), start=returns.index[0].year,
        end=returns.index[-1].year, bps=cfg.TRANSACTION_COST_BPS))
    charts.lines(performance.wealth(returns), log_y=True, key="strategy_wealth")
    tables.show(performance.metrics_table(returns)[["ann_return", "ann_volatility", "sharpe", "max_drawdown"]])


blocks.hero("strategy", cfg.PAGES["journey"])
blocks.section(T["why_rb"])
blocks.cards([{"title": t, "body": body} for t, body in content.WHY_RB], columns=2)
erc_result, _ = services.build_with_loader(portfolio.baseline())
esg_result, _ = services.build_with_loader(portfolio.baseline(esg=cfg.STRATEGY_ESG))
lab(erc_result)
backtest(erc_result, esg_result)
blocks.cta_band(T["closing_cta"], content.HERO["strategy"][2], cfg.PAGES["journey"])
