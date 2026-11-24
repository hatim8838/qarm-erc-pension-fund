"""Investor filters on the stocks of a regional sleeve: sectors and the ESG screen (core/esg.py)."""

from __future__ import annotations

import pandas as pd

import config as cfg
from core.esg import esg_risk_budgets, screen_universe
from logic import data


def selected_stocks(region: str, sectors: tuple[str, ...], esg_mode: str) -> pd.Index:
    """Stocks of a region in the chosen sectors, minus the worst ESG scores when screening."""
    table = data.stocks()
    table = table[(table["zone"] == region) & table["industry"].isin(sectors)]
    if esg_mode == "off" or table.empty:
        return table.index
    # Best-in-class cut of core: within region x sector, drop scores below the ESG_SCREEN_LEVEL
    # quantile. min_stocks=0 turns off core's relaxation: the minimum is enforced by the journey.
    screened = screen_universe(data.stocks(), [region], list(sectors), cfg.ESG_SCREEN_LEVEL, min_stocks=0)
    return screened.index[screened["selected"]]


def stock_counts(regions, sectors: tuple[str, ...], esg_mode: str) -> pd.Series:
    """Number of stocks left in each chosen region after the filters."""
    return pd.Series({r: len(selected_stocks(r, sectors, esg_mode)) for r in regions}, dtype=int)


def thin_regions(regions, sectors: tuple[str, ...], esg_mode: str) -> list[str]:
    """Regions left with fewer stocks than config.MIN_STOCKS_PER_SLEEVE."""
    counts = stock_counts(regions, sectors, esg_mode)
    return list(counts[counts < cfg.MIN_STOCKS_PER_SLEEVE].index)


def esg_budgets(stock_ids: pd.Index) -> pd.Series:
    """LN 6 risk budgets b_i = score_i / Σ score (core): b ≥ 0, Σb = 1, unscored stocks excluded."""
    return esg_risk_budgets(data.stocks().loc[stock_ids, "esg_score"])


def esg_score(stock_weights: pd.Series) -> float:
    """Weighted average ESG score of the equity holdings (weights rescaled over scored stocks)."""
    scores = data.stocks()["esg_score"].reindex(stock_weights.index)
    held = stock_weights[scores.notna() & (stock_weights > 0)]
    return float((held * scores[held.index]).sum() / held.sum()) if held.sum() > 0 else float("nan")


def average_esg(regions, sectors: tuple[str, ...], esg_mode: str) -> float:
    """Equal-weighted ESG score of the stocks left by the filters."""
    ids = [i for r in regions for i in selected_stocks(r, sectors, esg_mode)]
    return float(data.stocks().loc[ids, "esg_score"].mean())
