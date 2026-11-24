"""Two-level ERC / risk budgeting (LN 5, LN 6) on the LN 3 covariance, then volatility targeting (LN 2)."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

import config as cfg
from core.utilities import backtest, risk_budget_weights
from logic import data, universe
from logic.covariance import ledoit_wolf_cc
from logic.risk import volatility


def risk_budgeting(window: pd.DataFrame, budgets: pd.Series | None, covariance=ledoit_wolf_cc) -> pd.Series:
    """x = RB(Σ̂, b): RC*_i = b_i (LN 6, log-barrier of core); ERC when b = None (b_i = 1/n, LN 5)."""
    cols = window.columns if budgets is None else window.columns.intersection(budgets.index)
    cols = cols[window[cols].std() > 0]  # a flat price has no measurable risk: RC_i = 0 has no ERC solution
    if len(cols) == 0:  # no stock with a complete window yet: the sleeve waits
        return pd.Series(dtype=float)
    b = None if budgets is None else budgets[cols] / budgets[cols].sum()
    return risk_budget_weights(covariance(window[cols]), b)


@lru_cache(maxsize=64)
def level1(sleeve: str, sectors: tuple[str, ...], esg_mode: str, covariance=ledoit_wolf_cc) -> dict:
    """Level 1 inside one sleeve at every monthly rebalancing, held with drift (core.backtest)."""
    returns = data.sleeve_returns(sleeve)
    budgets = None
    if sleeve in data.regions():
        ids = universe.selected_stocks(sleeve, sectors, esg_mode)
        returns = returns[returns.columns.intersection(ids)]
        budgets = universe.esg_budgets(returns.columns) if esg_mode == "screen_rb" else None
    result = backtest(returns, lambda w: risk_budgeting(w, budgets, covariance), cfg.PORTFOLIO_START,
                      cfg.REBALANCING_FREQ)
    result["windows"] = _sleeve_windows(returns, result["weights"])
    return result


def _sleeve_windows(returns: pd.DataFrame, weights: pd.DataFrame) -> dict[pd.Timestamp, pd.Series]:
    """For each rebalancing t: last-window returns of the sleeve with the level-1 weights of t."""
    out = {}
    for t, w in weights.iterrows():
        w = w[w > 0]
        if not w.empty:
            out[t] = returns.loc[:t, w.index].tail(cfg.ESTIMATION_WINDOW) @ w
    return out


def risky_share(x: pd.Series, cov: pd.DataFrame, target: float | None) -> float:
    """Vol targeting: α = σ* / σ̂(x), capped at MAX_ALPHA (no leverage); α = 1 without a target."""
    return 1.0 if target is None else min(cfg.MAX_ALPHA, target / volatility(x, cov))


def level2(window: pd.DataFrame, target: float | None, covariance=ledoit_wolf_cc) -> dict:
    """ERC across the sleeves on Σ̂ of the sleeve window, scaled by α; the rest earns r."""
    cov = covariance(window)
    x = risk_budgeting(window, None, covariance)
    alpha = risky_share(x, cov, target)
    weights = pd.concat([alpha * x, pd.Series({cfg.RISK_FREE: 1.0 - alpha})])
    return {"weights": weights, "x": x, "cov": cov, "alpha": alpha, "sigma_hat": volatility(x, cov)}
