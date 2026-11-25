"""The stock universe: explorer filters, sector filter, and the ESG screen applied at each rebalancing."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

import config as cfg
from core.utilities import eligible_assets
from logic import data


def sector_stocks(region: str, sectors: tuple[str, ...]) -> pd.Index:
    """Stocks of a region in the chosen sectors (ICB industries)."""
    table = data.stocks()
    return table.index[(table["zone"] == region) & table["industry"].isin(sectors)]


def investable(window: pd.DataFrame) -> pd.Index:
    """Assets with a complete window and some risk: a flat price (σ_i = 0) has no ERC solution."""
    return window.columns[window.std() > 0]


def n_excluded(n: int, esg: str) -> int:
    """Number of the n candidates dropped by the screen: X·n rounded to the nearest stock."""
    return int(np.floor(cfg.ESG_LEVELS[esg] * n + 0.5))


def worst_esg(candidates: pd.Index, esg: str) -> pd.Index:
    """The worst X% of the candidates by ESG score (unscored stocks rank as the worst)."""
    scores = data.stocks()["esg_score"].reindex(candidates).fillna(-np.inf)
    return scores.sort_values(kind="stable").index[:n_excluded(len(candidates), esg)]


def last_window(sleeve: str, sectors: tuple[str, ...]) -> pd.DataFrame:
    """Estimation window of the last rebalancing, on the eligible assets of the sleeve (core's rule)."""
    tail = data.sleeve_tail(sleeve)
    if sleeve in data.regions():
        tail = tail[tail.columns.intersection(sector_stocks(sleeve, sectors))]
    return tail.loc[:, eligible_assets(tail, tail.index[-1])]


@lru_cache(maxsize=256)
def counts(region: str, sectors: tuple[str, ...], esg: str) -> dict[str, int]:
    """Stocks of a region today: investable candidates, excluded by the screen, kept."""
    n = len(investable(last_window(region, sectors)))
    out = n_excluded(n, esg)
    return {"candidates": n, "excluded": out, "kept": n - out}


def thin_regions(regions, sectors: tuple[str, ...], esg: str) -> list[str]:
    """Regions left with fewer stocks than config.MIN_STOCKS_PER_SLEEVE."""
    return [r for r in regions if counts(r, tuple(sectors), esg)["kept"] < cfg.MIN_STOCKS_PER_SLEEVE]


def esg_score(stock_weights: pd.Series) -> float:
    """Weighted average ESG score of the equity holdings (weights rescaled over scored stocks)."""
    scores = data.stocks()["esg_score"].reindex(stock_weights.index)
    held = stock_weights[scores.notna() & (stock_weights > 0)]
    return float((held * scores[held.index]).sum() / held.sum()) if held.sum() > 0 else float("nan")


def explore(regions: tuple[str, ...], search: str = "") -> pd.DataFrame:
    """Stocks of the chosen regions whose name contains the search text, best ESG score first."""
    table = data.stocks()
    table = table[table["zone"].isin(regions)]
    if search:
        table = table[table["name"].str.contains(search, case=False, regex=False, na=False)]
    return table.sort_values("esg_score", ascending=False)


def esg_summary(table: pd.DataFrame) -> dict[str, float]:
    """Average and median ESG score, and the share of stocks that have a score."""
    scores = table["esg_score"]
    return {"mean": scores.mean(), "median": scores.median(), "coverage": scores.notna().mean()}


def held_vs_listed(regions) -> pd.DataFrame:
    """Per region: stocks in the universe vs stocks investable today (complete, non-flat window)."""
    listed = data.stocks()["zone"].value_counts()
    return pd.DataFrame({r: {"listed": int(listed.get(r, 0)), "held": counts(r, tuple(data.sectors()),
                                                                            next(iter(cfg.ESG_LEVELS)))["candidates"]}
                         for r in regions}).T
