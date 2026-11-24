"""What the "Your portfolio" tabs show: breakdowns, risk tables and diversification, today."""

from __future__ import annotations

import pandas as pd

import config as cfg
from core.config import BENCHMARK_6040
from logic import data
from logic.covariance import ledoit_wolf_cc
from logic.diversification import diversification_ratio, measures
from logic.portfolio import stock_weights
from logic.risk import decomposition, min_variance, volatility


def last_decision(result: dict) -> dict:
    """Level-2 decision (x, Σ̂, α, σ̂) at the last rebalancing."""
    return result["decisions"][max(result["decisions"])]


def risk_table(result: dict) -> pd.DataFrame:
    """LN 5 decomposition of y = αx + (1−α)r: the risk-free row has MR = RC = 0, and ΣRC_i = σ(y)."""
    d = last_decision(result)
    cov = d["cov"].reindex(index=d["weights"].index, columns=d["weights"].index).fillna(0.0)
    return decomposition(d["weights"], cov)


def by_class(result: dict) -> pd.Series:
    """Weights by asset class: regional sleeves summed into equities."""
    w = result["weights"].iloc[-1]
    regional = [s for s in w.index if s in data.regions()]
    out = pd.concat([pd.Series({cfg.EQUITIES: w[regional].sum()}), w.drop(regional)])
    return out[out > 0]


def by_sector(result: dict) -> pd.Series:
    """Equity weight in each sector (ICB industry)."""
    w = stock_weights(result)
    industry = data.stocks()["industry"].reindex(w.index).dropna()
    return w[industry.index].groupby(industry).sum().sort_values(ascending=False)


def compare_ew_erc_mv(cov: pd.DataFrame, x_erc: pd.Series) -> pd.DataFrame:
    """LN 5: σ and RC*_i of EW, ERC and MV on the same Σ̂ (σ(x_mv) ≤ σ(x_erc) ≤ σ(x_ew))."""
    portfolios = {"MV": min_variance(cov), "ERC": x_erc, "EW": pd.Series(1 / len(cov), index=cov.index)}
    rows = {}
    for name, x in portfolios.items():
        rows[name] = {"σ": volatility(x, cov), **decomposition(x, cov)["RC*"].to_dict()}
    return pd.DataFrame(rows).T


def theorem_holds(result: dict, tol: float = 1e-8) -> pd.Series:
    """At each rebalancing: True when σ(x_mv) ≤ σ(x_erc) ≤ σ(x_ew) on that date's Σ̂."""
    out = {}
    for t, d in result["decisions"].items():
        sig = compare_ew_erc_mv(d["cov"], d["x"])["σ"]
        out[t] = sig["MV"] <= sig["ERC"] + tol and sig["ERC"] <= sig["EW"] + tol
    return pd.Series(out)


def _sixty_forty_cov() -> tuple[pd.Series, pd.DataFrame]:
    """60/40 weights and Σ̂ of its two legs on the last window (core's BENCHMARK_6040)."""
    legs = {"US": data.benchmarks()[cfg.INDEX_LABELS["US"]],
            "US Aggregate": data.sleeve_returns("Bonds").iloc[:, 0]}
    window = pd.DataFrame(legs).dropna().tail(cfg.ESTIMATION_WINDOW)
    return pd.Series(BENCHMARK_6040), ledoit_wolf_cc(window)


def diversification_table(result: dict) -> pd.DataFrame:
    """H*, Gini, I* on weights and on RC, and DR, for your risky x, EW and 60/40."""
    d = last_decision(result)
    w6040, cov6040 = _sixty_forty_cov()
    cases = {"Your portfolio": (d["x"], d["cov"]), "EW": (pd.Series(1 / len(d["x"]), index=d["x"].index), d["cov"]),
             "60/40": (w6040, cov6040)}
    rows = {}
    for name, (x, cov) in cases.items():
        rc = decomposition(x, cov)["RC"]
        rows[name] = {**measures(x, rc), "DR": diversification_ratio(x, cov)}
    return pd.DataFrame(rows).T


def holdings_count(result: dict) -> int:
    """Number of lines held today (stocks, bond and commodity indices; not the risk-free asset)."""
    return int((stock_weights(result).drop(cfg.RISK_FREE, errors="ignore") > 0).sum())
