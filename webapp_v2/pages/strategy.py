"""Our strategy: the problem (a 60/40 is all stock risk), our answer (ERC), how the portfolio is built,
why risk budgeting, and the same problem on our six sleeves (1/N vs ERC).

The comparison of performance with the benchmarks is done once, in the Client journey (Performance tab)."""

import pandas as pd
import streamlit as st

import config as cfg
import content
import services
from logic import data, portfolio, report
from logic.risk import decomposition
from ui import blocks, charts

T = content.TEXT
NAMES = {"EW": "1/N (equal weights)", "ERC": "ERC"}


# Kept here, not in logic/report.py: that module is fingerprinted by the precomputed store (logic/store.py)
def money_vs_risk(x: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    """Share of the money (x_i) and share of the risk (RC*_i) of each component."""
    d = decomposition(x, cov)
    return pd.DataFrame({"money": d["x"], "risk": d["RC*"]})


def sixty_forty_split() -> pd.DataFrame:
    """The classic 60/40 over the whole backtest: 60% of the money in stocks carries almost all of the risk."""
    returns = data.index_returns()[[cfg.INDEX_LABELS["US"], cfg.BOND_INDEX]].dropna()
    return money_vs_risk(pd.Series([0.6, 0.4], index=returns.columns), returns.cov())


def _split_chart(split, key: str) -> None:
    """Share of the money next to share of the risk, one pair of bars per component."""
    charts.bars(split.rename(columns={"money": T["money"], "risk": T["risk"]}), key=key)


def problem() -> None:
    """1. A 60/40 holds 60% of its money in stocks but almost all of its risk."""
    blocks.section(T["problem"], T["problem_sub"])
    split = sixty_forty_split()
    split = split.rename(index=dict(zip(split.index, (f"Stocks ({split.index[0]})", f"Bonds ({split.index[1]})"))))
    stocks = split.index[0]
    _split_chart(split, "strategy_6040")
    start, end = data.index_returns().index[[0, -1]]
    st.caption(T["problem_note"].format(start=start.year, end=end.year,
                                        money=blocks.pct(split.loc[stocks, "money"], 0),
                                        risk=blocks.pct(split.loc[stocks, "risk"], 0)))


def answer() -> None:
    """2. Our ERC portfolio: unequal money, equal risk across the six sleeves."""
    blocks.section(T["answer"], T["answer_sub"])
    result, _ = services.build_with_loader(portfolio.baseline())
    d = report.last_decision(result)
    _split_chart(money_vs_risk(d["x"], d["cov"]), "strategy_erc")
    st.caption(T["answer_note"].format(date=max(result["decisions"]).date()))


def build() -> None:
    """3. The three steps of the two-level ERC and the α mix."""
    blocks.section(T["build"])
    blocks.cards([{"title": t, "body": body} for t, body in content.BUILD_STEPS], columns=3)


def lab(table, holds) -> None:
    """5. Our six sleeves today: share of the risk with 1/N vs ERC, and how often ERC was the less risky one.

    ``holds`` is True when σ(mv) ≤ σ(erc) ≤ σ(ew): its share is a lower bound for σ(erc) ≤ σ(ew) alone."""
    blocks.section(T["lab"], T["lab_sub"])
    blocks.figures([(blocks.count_up(100 * table.loc[n, "σ"], 2, "%"), T["lab_vol"].format(name=NAMES[n]))
                    for n in ("EW", "ERC")])
    shares = table.drop(columns="σ").loc[["EW", "ERC"]]
    charts.bars(shares.rename(index=NAMES).T, key="lab_rc")
    st.caption(T["lab_note"].format(date=holds.index.max().date(), euro=blocks.pct(shares.loc["EW", "Eurozone"], 0),
                                    bonds=blocks.pct(shares.loc["EW", "Bonds"], 0)) + " "
               + T["theorem"].format(share=blocks.pct(holds.mean(), 0), n=len(holds)))


blocks.hero("strategy", cfg.PAGES["journey"])
problem()
answer()
build()
blocks.section(T["why_rb"])
blocks.cards([{"title": t, "body": body} for t, body in content.WHY_RB], columns=3)
lab(*services.strategy_lab())
blocks.cta_band(T["closing_cta"], content.HERO["strategy"][2], cfg.PAGES["journey"])
