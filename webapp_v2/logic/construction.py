"""Two-level ERC (LN 5) on the LN 3 covariance, with the ESG screen inside the regional sleeves."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

import config as cfg
from core.utilities import backtest, erc_weights
from logic import data, universe
from logic.covariance import ledoit_wolf_cc
from logic.risk import volatility


def erc(window: pd.DataFrame, covariance=ledoit_wolf_cc) -> pd.Series:
    """x_erc on Σ̂ of the window: RC_i = σ(x)/n (LN 5, log-barrier of core); empty when no asset."""
    if window.shape[1] == 0:  # no stock with a complete window yet: the sleeve waits
        return pd.Series(dtype=float)
    return erc_weights(covariance(window))


def screened_erc(window: pd.DataFrame, esg: str, covariance=ledoit_wolf_cc) -> tuple[pd.Series, pd.Index]:
    """Level 1 on one date: drop the worst X% ESG of the investable stocks, then ERC on the rest."""
    candidates = universe.investable(window)
    excluded = universe.worst_esg(candidates, esg)
    return erc(window[candidates[~candidates.isin(excluded)]], covariance), excluded


@lru_cache(maxsize=64)
def level1(sleeve: str, sectors: tuple[str, ...], esg: str, covariance=ledoit_wolf_cc) -> dict:
    """Level 1 inside one sleeve at every monthly rebalancing, held with drift (core.backtest).
    Bonds and commodities ignore the sector and ESG filters (see portfolio.filters)."""
    returns = data.sleeve_returns(sleeve)
    if sleeve in data.regions():
        returns = returns[returns.columns.intersection(universe.sector_stocks(sleeve, sectors))]
    screen = {}

    def weight_fn(window: pd.DataFrame) -> pd.Series:
        """Screen and ERC on the window of date t; records (candidates, excluded) of t."""
        x, excluded = screened_erc(window, esg, covariance)
        screen[window.index[-1]] = (universe.investable(window), excluded)
        return x

    result = backtest(returns, weight_fn, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    result.update(screen=screen, windows=sleeve_windows(returns, result["weights"]))
    return result


def sleeve_windows(returns: pd.DataFrame, weights: pd.DataFrame) -> dict[pd.Timestamp, pd.Series]:
    """For each rebalancing t: last-window returns of the sleeve with the level-1 weights of t."""
    out = {}
    for t, w in weights.iterrows():
        w = w[w > 0]
        if not w.empty:
            out[t] = returns.loc[:t, w.index].tail(cfg.ESTIMATION_WINDOW) @ w
    return out


def level2(window: pd.DataFrame, covariance=ledoit_wolf_cc) -> dict:
    """ERC across the sleeves on Σ̂ of the sleeve window (independent of the risk level α)."""
    cov = covariance(window)
    x = erc(window, covariance)
    return {"x": x, "cov": cov, "sigma_hat": volatility(x, cov)}
