"""Ledoit-Wolf shrinkage towards the constant-correlation target, Σ̂ = δF + (1−δ)S."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg


def _target(sample: np.ndarray) -> tuple[np.ndarray, float]:
    """Constant-correlation target F: f_ii = s_ii, f_ij = ρ̄ √(s_ii s_jj); returns (F, ρ̄)."""
    n = len(sample)
    sd = np.sqrt(np.diag(sample))
    corr = sample / np.outer(sd, sd)
    rho_bar = (corr.sum() - n) / (n * (n - 1))
    target = rho_bar * np.outer(sd, sd)
    np.fill_diagonal(target, np.diag(sample))
    return target, rho_bar


def shrinkage_intensity(x: np.ndarray, sample: np.ndarray, target: np.ndarray, rho_bar: float) -> float:
    """Optimal δ = max(0, min(1, (π̂ − ρ̂) / (γ̂ T))) of Ledoit and Wolf (2004)."""
    t = len(x)
    var, sd = np.diag(sample), np.sqrt(np.diag(sample))
    pi_mat = (x**2).T @ (x**2) / t - sample**2  # asymptotic variances of the sample covariances
    cross = (x**3).T @ x / t - var[:, None] * sample
    np.fill_diagonal(cross, 0.0)
    rho = np.trace(pi_mat) + rho_bar * ((sd[None, :] / sd[:, None]) * cross).sum()
    gamma = ((target - sample) ** 2).sum()  # misspecification of the target
    return float(np.clip((pi_mat.sum() - rho) / gamma / t, 0.0, 1.0)) if gamma > 0 else 1.0


def ledoit_wolf_cc(returns: pd.DataFrame) -> pd.DataFrame:
    """Annualised Σ̂ = δF + (1−δ)S of the window (no missing returns allowed)."""
    x = returns.to_numpy(dtype=float)
    x = x - x.mean(axis=0)
    sample = x.T @ x / len(x)
    if sample.shape[0] == 1:  # a single asset has nothing to shrink
        shrunk, delta = sample, 0.0
    else:
        target, rho_bar = _target(sample)
        delta = shrinkage_intensity(x, sample, target, rho_bar)
        shrunk = delta * target + (1 - delta) * sample
    cov = pd.DataFrame(shrunk * cfg.TRADING_DAYS, index=returns.columns, columns=returns.columns)
    cov.attrs["delta"] = delta
    return cov
