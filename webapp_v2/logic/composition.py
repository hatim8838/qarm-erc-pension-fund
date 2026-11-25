"""Composition of the ERC portfolio at the last rebalancing: sleeves, positions, risk contributions."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as cfg
from logic import data
from logic.covariance import ledoit_wolf_cc
from logic.risk import decomposition


def _last(result: dict) -> tuple[pd.Timestamp, dict]:
    """Date and level-2 decision of the last rebalancing."""
    t = max(result["decisions"])
    return t, result["decisions"][t]


def _inner_weights(result: dict, sleeve: str, t: pd.Timestamp) -> pd.Series:
    """Level-1 weights held inside a sleeve on date t."""
    w = result["level1"][sleeve]["weights"].loc[t]
    return w[w > 0]


def sleeves(result: dict, total_money: bool = False) -> pd.DataFrame:
    """Per sleeve: assets, capital weight, risk contribution RC*, stand-alone σ. Sums to 1 inside the ERC
    portfolio; with ``total_money`` the weights are × α and a risk-free row (no risk) is added."""
    t, d = _last(result)
    x, cov = d["x"], d["cov"]
    table = pd.DataFrame({"assets": [len(_inner_weights(result, s, t)) for s in x.index], "weight": x,
                          "rc": decomposition(x, cov)["RC*"], "vol": np.sqrt(np.diag(cov.loc[x.index, x.index]))})
    if total_money:
        table["weight"] *= result["alpha"]
        table.loc[cfg.RISK_FREE] = {"assets": 1, "weight": 1 - result["alpha"], "rc": 0.0, "vol": 0.0}
    return table


def extremes(table: pd.DataFrame) -> dict:
    """Largest and smallest sleeve by capital, and the equal risk share 1/n (risk-free row ignored)."""
    w = table["weight"].drop(cfg.RISK_FREE, errors="ignore")
    return {"top": w.idxmax(), "top_w": w.max(), "low": w.idxmin(), "low_w": w.min(), "rc": 1 / len(w)}


def positions(result: dict, n: int, total_money: bool = False) -> pd.DataFrame:
    """The n largest holdings: capital weight x_s × (weight inside s), × α with ``total_money``."""
    t, d = _last(result)
    w = pd.concat([d["x"][s] * _inner_weights(result, s, t) for s in d["x"].index])
    w = w.nlargest(n) * (result["alpha"] if total_money else 1.0)
    sleeve, name = zip(*(i.split(cfg.ASSET_ID_SEP, 1) for i in w.index))
    return pd.DataFrame({"weight": w.to_numpy(), "sleeve": sleeve, "name": name}, index=w.index)


def sleeve_rc(sleeve: str, w: pd.Series, t: pd.Timestamp) -> pd.Series:
    """RC*_i of the weights held inside a sleeve on date t, on that date's Σ̂."""
    window = data.sleeve_returns(sleeve).loc[:t, w.index].tail(cfg.ESTIMATION_WINDOW)
    return decomposition(w, ledoit_wolf_cc(window))["RC*"]


def rc_frame(sleeve: str, weights: pd.DataFrame) -> pd.DataFrame:
    """sleeve_rc at every rebalancing, aligned on the level-1 weights (NaN where not held)."""
    rows = {t: sleeve_rc(sleeve, w[w > 0], t) for t, w in weights.iterrows() if (w > 0).any()}
    return pd.DataFrame(rows).T.reindex(index=weights.index, columns=weights.columns)


def inner(result: dict, sleeve: str) -> pd.DataFrame:
    """Weights inside a sleeve and their RC*_i on that date's Σ̂, largest weight first (stored RC when the
    level 1 comes from precomputed/)."""
    t, _ = _last(result)
    w = _inner_weights(result, sleeve, t)
    stored = result["level1"][sleeve].get("rc")
    rc = stored.loc[t, w.index] if stored is not None else sleeve_rc(sleeve, w, t)
    names = [i.split(cfg.ASSET_ID_SEP, 1)[1] for i in w.index]
    return pd.DataFrame({"weight": w.to_numpy(), "rc": rc.to_numpy()}, index=names).sort_values("weight",
                                                                                                ascending=False)
