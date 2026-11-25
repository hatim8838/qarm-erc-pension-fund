"""LN 2 performance (SR, TE, IR) and wealth paths, reusing core's metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg
from core.utilities import performance_metrics
from logic import data


def aligned(returns: pd.DataFrame) -> pd.DataFrame:
    """Dates where every series has a return, so that comparisons are fair."""
    return returns.dropna()


def with_alpha(returns: pd.Series, alpha: float, rf: pd.Series) -> pd.Series:
    """α in the series and 1 − α in the risk-free asset (LN2), the client's own mix applied to a benchmark."""
    return alpha * returns + (1 - alpha) * rf.reindex(returns.index).fillna(0.0)


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


def wealth(returns: pd.DataFrame) -> pd.DataFrame:
    """Value of 100 invested at the common start."""
    return 100 * (1 + aligned(returns)).cumprod()
