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


COUNT_KEYS = ("listed", "investable", "recent", "unusable", "excluded_esg", "kept")


@lru_cache(maxsize=64)
def _region_status(region: str, sectors: tuple[str, ...]) -> pd.Series:
    """Status of every listed stock of a region at the last rebalancing, from the last estimation window only
    (no heavy computation): "investable", "recent" (history starts inside the window) or "unusable"."""
    listed = sector_stocks(region, sectors)
    present = data.sleeve_tail(region).reindex(columns=listed).notna()  # a stock with no price has no column
    trailing = present.iloc[::-1].cummin().sum()  # consecutive returns up to the last rebalancing
    recent = present.iloc[-1] & ~present.iloc[0] & (trailing == present.sum())
    ok = listed.isin(investable(last_window(region, sectors)))
    return pd.Series(np.select([ok, recent.to_numpy()], ["investable", "recent"], "unusable"), index=listed)


@lru_cache(maxsize=256)
def _region_counts(region: str, sectors: tuple[str, ...], esg: str) -> dict[str, int]:
    """stock_counts() of one region."""
    status = _region_status(region, sectors)
    n = int((status == "investable").sum())
    out = n_excluded(n, esg)
    return {"listed": len(status), "investable": n, "recent": int((status == "recent").sum()),
            "unusable": int((status == "unusable").sum()), "excluded_esg": out, "kept": n - out}


@lru_cache(maxsize=256)
def stock_counts(regions: tuple[str, ...], sectors: tuple[str, ...], esg: str) -> dict[str, int]:
    """The single source of every number of stocks shown in the app, for the chosen regions and sectors:

    listed        stocks of the universe (esg_universe)
    investable    eligible at the last rebalancing: a complete return window and a moving price
    recent        not investable yet: their history starts inside the last window (listed less than a year ago)
    unusable      neither: no usable price in the last window
    excluded_esg  investable stocks removed by the ESG screen (the worst X% of each region)
    kept          investable stocks left after the screen: the stocks the portfolio holds
    """
    per_region = [_region_counts(r, tuple(sectors), esg) for r in regions]
    return {k: sum(c[k] for c in per_region) for k in COUNT_KEYS}


def stock_names(regions: tuple[str, ...], sectors: tuple[str, ...], status: str) -> list[str]:
    """Names of the listed stocks with a status ("recent" or "unusable"), classified as in stock_counts."""
    names = data.stocks()["name"]
    return [names[a] for r in regions for a, s in _region_status(r, tuple(sectors)).items() if s == status]


def index_counts() -> dict[str, int]:
    """Number of indices in each non-equity sleeve (bonds, commodities)."""
    return {s: data.sleeve_tail(s).shape[1] for s in data.other_classes()}


def thin_regions(regions, sectors: tuple[str, ...], esg: str) -> list[str]:
    """Regions left with fewer stocks than config.MIN_STOCKS_PER_SLEEVE."""
    return [r for r in regions if stock_counts((r,), tuple(sectors), esg)["kept"] < cfg.MIN_STOCKS_PER_SLEEVE]


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
