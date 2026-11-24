"""The client's portfolio: choices -> sleeves -> two-level ERC/RB -> vol targeting -> backtest."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

import config as cfg
from core.utilities import backtest
from logic import data
from logic.construction import level1, level2
from logic.covariance import ledoit_wolf_cc


@dataclass(frozen=True)
class Choices:
    """Everything the investor decides (hashable, so it can key a cache)."""

    regions: tuple[str, ...]
    classes: tuple[str, ...]
    sectors: tuple[str, ...]
    esg: str = "off"
    level: int | None = None  # risk level 1-5; None = fully invested (α = 1)

    def target(self) -> float | None:
        """σ* of the risk level."""
        return None if self.level is None else cfg.TARGET_VOLS[self.level]

    def but(self, **changes) -> "Choices":
        """A copy with some choices changed."""
        return replace(self, **changes)


def baseline(esg: str = "off") -> Choices:
    """Every region, class and sector, fully invested: the house portfolio."""
    return Choices(tuple(data.regions()), tuple(data.asset_classes()), tuple(data.sectors()), esg)


def client_sleeves(choices: Choices) -> list[str]:
    """Sleeves held: chosen regions (if equities are on) and chosen non-equity classes, in data order."""
    held = set(choices.classes)
    if cfg.EQUITIES in held:
        held |= set(choices.regions)
    return [s for s in data.sleeves() if s in held]


def _level1_all(choices: Choices, covariance) -> dict[str, dict]:
    """Level-1 results of each held sleeve (filters only matter for regional sleeves)."""
    out = {}
    for s in client_sleeves(choices):
        regional = s in data.regions()
        key = (choices.sectors, choices.esg) if regional else ((), "off")
        out[s] = level1(s, *key, covariance=covariance)
    return out


def build(choices: Choices, covariance=ledoit_wolf_cc) -> dict:
    """Backtest of the client's portfolio (sleeves + risk-free) with every rebalancing decision."""
    sleeves = _level1_all(choices, covariance)
    held = pd.DataFrame({s: r["returns"] for s, r in sleeves.items()})
    first = min(r["weights"].index[0] for r in sleeves.values())
    held = held.reindex(held.index.union([first]))  # the first decision date precedes the first return
    held[cfg.RISK_FREE] = data.risk_free_daily().reindex(held.index).ffill()
    decisions = {}

    def weight_fn(window: pd.DataFrame) -> pd.Series:
        """Level 2 on the level-1 sleeve windows of the date (not on the realised window)."""
        t = window.index[-1]
        frame = pd.DataFrame({s: r["windows"][t] for s, r in sleeves.items() if t in r["windows"]})
        decisions[t] = level2(frame, choices.target(), covariance)
        return decisions[t]["weights"]

    result = backtest(held, weight_fn, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    result.update(decisions=decisions, level1=sleeves, choices=choices)
    result["total_turnover"] = total_turnover(result)
    return result


def total_turnover(result: dict) -> pd.Series:
    """Stock-level turnover ≈ sleeve turnover + Σ_s (new sleeve weight × level-1 turnover of s)."""
    inner = pd.DataFrame({s: r["turnover"] for s, r in result["level1"].items()})
    sleeve_w = result["weights"].reindex(columns=inner.columns).fillna(0.0)
    return result["turnover"] + (sleeve_w * inner.reindex(sleeve_w.index).fillna(0.0)).sum(axis=1)


def net_returns(result: dict, cost_bps: float) -> pd.Series:
    """LN 3: returns net of costs c·Σ|Δx| = c·2·turnover, paid on the first day after each rebalancing."""
    r = result["returns"].copy()
    for t, turnover in result["total_turnover"].items():
        after = r.index[r.index > t]
        if len(after):
            r[after[0]] -= cost_bps / 1e4 * 2 * turnover
    return r


def stock_weights(result: dict, t=None) -> pd.Series:
    """Weight of every holding on a rebalancing date: α·x_s·(level-1 weight), plus the risk-free asset."""
    t = result["weights"].index[-1] if t is None else t
    sleeve_w = result["weights"].loc[t]
    parts = [sleeve_w[s] * r["weights"].loc[t] for s, r in result["level1"].items() if t in r["weights"].index]
    out = pd.concat([*parts, pd.Series({cfg.RISK_FREE: sleeve_w[cfg.RISK_FREE]})])
    return out[out > 0]
