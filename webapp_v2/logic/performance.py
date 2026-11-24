"""LN 2 performance (SR, TE, IR), drawdowns and crisis returns, reusing core's metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg
from core.utilities import drawdown, performance_metrics, period_performance
from logic import data


def aligned(returns: pd.DataFrame) -> pd.DataFrame:
    """Dates where every series has a return, so that comparisons are fair."""
    return returns.dropna()


def metrics_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Annual return μ, volatility σ, SR(x | r), max drawdown, historical VaR/ES (core)."""
    returns = aligned(returns)
    rf = data.risk_free_daily()
    return pd.DataFrame({name: performance_metrics(returns[name], rf) for name in returns}).T


def relative(portfolio: pd.Series, benchmark: pd.Series) -> dict[str, float]:
    """Tracking error σ(x | b) and information ratio IR(x | b) = (μ(x) − μ(b)) / σ(x | b)."""
    both = aligned(pd.concat([portfolio, benchmark], axis=1))
    active = both.iloc[:, 0] - both.iloc[:, 1]  # R(x) − R(b)
    te = float(active.std() * np.sqrt(cfg.TRADING_DAYS))
    return {"tracking_error": te, "information_ratio": float(active.mean() * cfg.TRADING_DAYS / te)}


def crisis_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Cumulative return of each series during each crisis of core.CRISIS_PERIODS."""
    return period_performance(aligned(returns))


def wealth(returns: pd.DataFrame) -> pd.DataFrame:
    """Value of 100 invested at the common start."""
    return 100 * (1 + aligned(returns)).cumprod()


def drawdowns(returns: pd.DataFrame) -> pd.DataFrame:
    """Drawdown of each series from its running peak."""
    returns = aligned(returns)
    return pd.DataFrame({name: drawdown(returns[name]) for name in returns})


def realised_volatility(returns: pd.Series) -> float:
    """Annualised realised σ of daily returns."""
    return float(returns.std() * np.sqrt(cfg.TRADING_DAYS))
