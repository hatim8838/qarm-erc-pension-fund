"""Breakdowns of the client portfolio today, and the comparison of EW, ERC and MV."""

from __future__ import annotations

import pandas as pd

import config as cfg
from logic import data, universe
from logic.portfolio import stock_weights
from logic.risk import decomposition, min_variance, volatility


def last_decision(result: dict) -> dict:
    """Level-2 decision (x, Σ̂, σ̂) at the last rebalancing."""
    return result["decisions"][max(result["decisions"])]


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
    """σ and RC*_i of EW, ERC and MV on the same Σ̂ (σ(x_mv) ≤ σ(x_erc) ≤ σ(x_ew))."""
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


def strategy_lab(result: dict) -> tuple[pd.DataFrame, pd.Series]:
    """"Our strategy": EW / ERC / MV on the last rebalancing, and the theorem at every rebalancing."""
    d = last_decision(result)
    return compare_ew_erc_mv(d["cov"], d["x"]), theorem_holds(result)


def holdings_count(result: dict) -> dict[str, int]:
    """Lines held today, never added together: "stocks" (universe.stock_counts, the number every page shows)
    when equities are held, then the indices held in each non-equity sleeve (not the risk-free asset)."""
    choices, held = result["choices"], result["level1"]
    regions = tuple(r for r in choices.regions if r in held)
    out = {"stocks": universe.stock_counts(regions, choices.sectors, choices.esg)["kept"]} if regions else {}
    out.update({s: int((held[s]["weights"].iloc[-1] > 0).sum()) for s in data.other_classes() if s in held})
    return out
