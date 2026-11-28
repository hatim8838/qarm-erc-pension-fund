"""Expected return with its estimation error and a log-normal projection."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

import config as cfg


def expected_return(returns: pd.Series) -> dict[str, float]:
    """μ̂ and σ̂ (annual) and the 95% interval μ̂ ± z·σ̂/√T, T = years of data."""
    r = returns.dropna()
    mu, sigma = r.mean() * cfg.TRADING_DAYS, r.std() * np.sqrt(cfg.TRADING_DAYS)
    years = len(r) / cfg.TRADING_DAYS
    margin = cfg.CI_Z * sigma / np.sqrt(years)
    return {"mu": mu, "sigma": sigma, "years": years, "margin": margin, "low": mu - margin, "high": mu + margin}


def fan(mu: float, sigma: float, horizon: int) -> pd.DataFrame:
    """Percentiles of the value of START_VALUE: ln V_h ~ N(ln V_0 + (μ − σ²/2)h, σ²h), for h = 0..horizon."""
    h = np.arange(horizon + 1)
    drift = np.log(cfg.START_VALUE) + (mu - sigma**2 / 2) * h
    spread = sigma * np.sqrt(h)
    return pd.DataFrame({p: np.exp(drift + norm.ppf(p) * spread) for p in cfg.FAN_PERCENTILES}, index=h)

