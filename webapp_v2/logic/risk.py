"""LN 5 / LN 6 risk analytics in course notation: σ(x), MR, RC, RC*, VaR, ES, minimum variance."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

import config as cfg


def volatility(x: pd.Series, cov: pd.DataFrame) -> float:
    """σ(x) = √(x⊤Σx)."""
    w = x.reindex(cov.index).fillna(0.0).to_numpy()
    return float(np.sqrt(w @ cov.to_numpy() @ w))


def decomposition(x: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    """LN 5 table: x_i, MR_i = (Σx)_i/σ(x), RC_i = x_i·MR_i, RC*_i = RC_i/σ(x) (Euler: ΣRC_i = σ(x))."""
    w = x.reindex(cov.index).fillna(0.0)
    sigma = volatility(w, cov)
    mr = (cov.to_numpy() @ w.to_numpy()) / sigma
    rc = w.to_numpy() * mr
    return pd.DataFrame({"x": w.to_numpy(), "MR": mr, "RC": rc, "RC*": rc / sigma}, index=cov.index)


def min_variance(cov: pd.DataFrame) -> pd.Series:
    """Long-only minimum-variance portfolio x_mv = argmin x⊤Σx s.t. 1⊤x = 1, x ≥ 0."""
    n, s = len(cov), cov.to_numpy() / np.mean(np.diag(cov.to_numpy()))  # rescaled for the solver
    res = minimize(lambda w: w @ s @ w, np.full(n, 1 / n), jac=lambda w: 2 * s @ w, bounds=[(0, 1)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], method="SLSQP",
                   options={"ftol": 1e-14, "maxiter": 1000})
    w = np.clip(res.x, 0, None)
    return pd.Series(w / w.sum(), index=cov.index)


def gaussian_var_es(mu: float, sigma: float, level: float) -> tuple[float, float]:
    """LN 6 on losses L = −R: VaR_α = −μ + Φ⁻¹(α)σ, ES_α = −μ + σ·φ(Φ⁻¹(α))/(1−α)."""
    z = norm.ppf(level)
    return -mu + z * sigma, -mu + sigma * norm.pdf(z) / (1 - level)


def historical_var_es(returns: pd.Series, level: float) -> tuple[float, float]:
    """Historical VaR (loss quantile) and ES (mean loss beyond the VaR)."""
    losses = -returns.dropna()
    var = float(losses.quantile(level))
    return var, float(losses[losses >= var].mean())


def var_es_table(returns: pd.Series) -> pd.DataFrame:
    """Daily Gaussian vs historical VaR and ES at every level in config.VAR_LEVELS."""
    mu, sigma = returns.mean(), returns.std()
    rows = {}
    for level in cfg.VAR_LEVELS:
        g_var, g_es = gaussian_var_es(mu, sigma, level)
        h_var, h_es = historical_var_es(returns, level)
        rows[f"{level:.0%}"] = {"Gaussian VaR": g_var, "Historical VaR": h_var,
                                "Gaussian ES": g_es, "Historical ES": h_es}
    return pd.DataFrame(rows).T


def sharpe(mu: float, sigma: float, r: float) -> float:
    """LN 2: SR(x | r) = (μ(x) − r)/σ(x)."""
    return (mu - r) / sigma if sigma > 0 else float("nan")
