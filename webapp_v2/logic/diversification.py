"""LN 6 concentration and diversification measures, on weights or on risk contributions π."""

from __future__ import annotations

import numpy as np
import pandas as pd

from logic.risk import volatility


def _shares(values: pd.Series) -> np.ndarray:
    """π_i ≥ 0 summing to 1."""
    pi = np.clip(values.to_numpy(dtype=float), 0.0, None)
    return pi / pi.sum()


def herfindahl_star(values: pd.Series) -> float:
    """H* = (nH − 1)/(n − 1) with H = Σπ_i²: 0 when equal, 1 when concentrated in one line."""
    pi, n = _shares(values), len(values)
    return float((n * (pi**2).sum() - 1) / (n - 1)) if n > 1 else 1.0


def gini(values: pd.Series) -> float:
    """Gini index of the Lorenz curve of π (0 when equal, (n−1)/n for one line)."""
    pi, n = np.sort(_shares(values)), len(values)
    return float(2 * (np.arange(1, n + 1) * pi).sum() / n - (n + 1) / n)


def shannon_star(values: pd.Series) -> float:
    """I* = exp(−Σπ_i ln π_i): the effective number of lines (n when equal)."""
    pi = _shares(values)
    pi = pi[pi > 0]  # 0·ln 0 = 0
    return float(np.exp(-(pi * np.log(pi)).sum()))


def diversification_ratio(x: pd.Series, cov: pd.DataFrame) -> float:
    """DR = x⊤σ / σ(x) (≥ 1; 1 means no diversification)."""
    w = x.reindex(cov.index).fillna(0.0)
    return float(w.to_numpy() @ np.sqrt(np.diag(cov.to_numpy())) / volatility(w, cov))


def measures(weights: pd.Series, rc: pd.Series) -> dict[str, float]:
    """H*, Gini and I* on the weights and on the risk contributions."""
    out = {}
    for name, values in (("weights", weights), ("risk contributions", rc)):
        out[f"H* ({name})"] = herfindahl_star(values)
        out[f"Gini ({name})"] = gini(values)
        out[f"I* ({name})"] = shannon_star(values)
    return out
