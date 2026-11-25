"""Read-only access to data/processed/: sleeves, stock table, returns, risk-free rate, benchmarks."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

import config as cfg
from core.importation_data import read_esg_universe, read_processed
from core.utilities import rebalancing_dates
from logic import store


@lru_cache(maxsize=1)
def sleeves() -> tuple[str, ...]:
    """All sleeves in display order (equity regions first, then bonds and commodities)."""
    return tuple(pd.read_parquet(cfg.SLEEVE_WEIGHTS_FILE).columns)


@lru_cache(maxsize=1)
def stocks() -> pd.DataFrame:
    """Stock table indexed ``"<region>|<name>"``: zone, country, industry (= sector), ESG score..."""
    return read_esg_universe()


def regions() -> list[str]:
    """Regional equity sleeves: the sleeves that are zones of the stock table."""
    zones = set(stocks()["zone"])
    return [s for s in sleeves() if s in zones]


def other_classes() -> list[str]:
    """Non-equity sleeves (each one is an asset class of its own: bonds, commodities)."""
    return [s for s in sleeves() if s not in regions()]


def asset_classes() -> list[str]:
    """Investor-facing asset classes: equities plus every non-equity sleeve."""
    return [cfg.EQUITIES, *other_classes()]


def sectors() -> list[str]:
    """Sectors present in the data (ICB industries), alphabetical."""
    return sorted(stocks()["industry"].dropna().unique())


@lru_cache(maxsize=None)
def sleeve_returns(sleeve: str) -> pd.DataFrame:
    """Daily returns of every asset of a sleeve, columns ``"<sleeve>|<asset>"``."""
    source = sleeve if sleeve in regions() else sleeve.lower()  # bonds / commodities files
    df = read_processed("returns_daily", source)
    df.columns = [f"{sleeve}{cfg.ASSET_ID_SEP}{c}" for c in df.columns]
    return df.loc[:, df.notna().any()]


@lru_cache(maxsize=None)
def sleeve_tail(sleeve: str) -> pd.DataFrame:
    """Returns of every asset of a sleeve over the last estimation window (up to the last rebalancing):
    precomputed when available, so the full history is not read."""
    stored = store.load_tail(sleeve)
    if stored is not None:
        return stored
    returns = sleeve_returns(sleeve)
    t = rebalancing_dates(returns.index, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)[-1]
    return returns.loc[:t].tail(cfg.ESTIMATION_WINDOW)


@lru_cache(maxsize=1)
def risk_free_daily() -> pd.Series:
    """Daily risk-free rate r (1-month T-bill), forward-filled."""
    return read_processed("rf", "rf")["rf_daily"].ffill()


@lru_cache(maxsize=1)
def portfolio_returns() -> pd.DataFrame:
    """core's pre-computed backtests and composite benchmarks."""
    return pd.read_parquet(cfg.PORTFOLIO_RETURNS_FILE)


@lru_cache(maxsize=1)
def index_returns() -> pd.DataFrame:
    """Daily returns of each sleeve's official index (no survivorship bias), from the portfolio start:
    S&P 500, MSCI EMU, MSCI Pacific, MSCI EM EMEA, AGG (bonds) and S&P GSCI (commodities)."""
    indices = read_processed("returns_daily", "benchmarks").rename(columns=cfg.INDEX_LABELS)
    bonds = read_processed("returns_daily", "bonds").rename(columns={"US Aggregate": cfg.BOND_INDEX})
    both = pd.concat([indices, bonds], axis=1)
    return both.loc[portfolio_returns().index[0]:]


@lru_cache(maxsize=1)
def benchmarks() -> pd.DataFrame:
    """Benchmarks b: 60/40, 1/N and every index of the benchmark file, by display name."""
    indices = read_processed("returns_daily", "benchmarks").rename(columns=cfg.INDEX_LABELS)
    return pd.concat([portfolio_returns()[cfg.COMPOSITE_BENCHMARKS], indices], axis=1)
