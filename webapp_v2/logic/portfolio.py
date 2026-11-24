"""The client's portfolio: choices -> sleeves -> two-level ERC -> α mix with the risk-free asset -> backtest."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache

import pandas as pd

import config as cfg
from core.utilities import backtest, rebalancing_dates
from logic import data, universe
from logic.construction import level1, level2, screened_erc
from logic.covariance import ledoit_wolf_cc

FULL = max(cfg.ALPHAS)  # the risk level with α = 1: the ERC portfolio itself
NO_SCREEN = next(iter(cfg.ESG_LEVELS))  # the "Off" ESG level (X = 0)


@dataclass(frozen=True)
class Choices:
    """Everything the investor decides (hashable, so it can key a cache)."""

    regions: tuple[str, ...]
    classes: tuple[str, ...]
    sectors: tuple[str, ...]
    esg: str = NO_SCREEN  # key of config.ESG_LEVELS
    level: int = FULL  # risk level, key of config.ALPHAS

    def alpha(self) -> float:
        """α of the risk level: weight of the ERC portfolio."""
        return cfg.ALPHAS[self.level]

    def but(self, **changes) -> "Choices":
        """A copy with some choices changed."""
        return replace(self, **changes)


def baseline(esg: str = NO_SCREEN) -> Choices:
    """Every region, class and sector, fully invested: the house portfolio."""
    return Choices(tuple(data.regions()), tuple(data.asset_classes()), tuple(data.sectors()), esg)


def client_sleeves(choices: Choices) -> list[str]:
    """Sleeves held: chosen regions (if equities are on) and chosen non-equity classes, in data order."""
    held = set(choices.classes)
    if cfg.EQUITIES in held:
        held |= set(choices.regions)
    return [s for s in data.sleeves() if s in held]


def filters(choices: Choices, sleeve: str) -> tuple[tuple[str, ...], str]:
    """(sectors, ESG level) applied to a sleeve: only the regional equity sleeves are filtered."""
    return (choices.sectors, choices.esg) if sleeve in data.regions() else ((), NO_SCREEN)


def _held_returns(sleeves: dict[str, dict]) -> pd.DataFrame:
    """Daily returns of the held sleeves (level 1, with drift) and of the risk-free asset."""
    held = pd.DataFrame({s: r["returns"] for s, r in sleeves.items()})
    first = min(r["weights"].index[0] for r in sleeves.values())
    held = held.reindex(held.index.union([first]))  # the first decision date precedes the first return
    held[cfg.RISK_FREE] = data.risk_free_daily().reindex(held.index).ffill()
    return held


@lru_cache(maxsize=16)
def erc_part(choices: Choices, covariance=ledoit_wolf_cc) -> dict:
    """The part that does not depend on α: level 1 of each sleeve and the level-2 x_erc at each date."""
    sleeves = {s: level1(s, *filters(choices, s), covariance=covariance) for s in client_sleeves(choices)}
    held = _held_returns(sleeves)
    dates = rebalancing_dates(held.index, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    decisions = {t: level2(pd.DataFrame({s: r["windows"][t] for s, r in sleeves.items() if t in r["windows"]}),
                           covariance) for t in dates}
    return {"level1": sleeves, "held": held, "decisions": decisions}


def build(choices: Choices, covariance=ledoit_wolf_cc) -> dict:
    """Backtest of y = α·x_erc + (1 − α)·r, rebalanced monthly back to α (LN 2), with every decision."""
    part, alpha = erc_part(choices.but(level=FULL), covariance), choices.alpha()

    def weight_fn(window: pd.DataFrame) -> pd.Series:
        """α in the ERC sleeves, 1 − α in the risk-free asset."""
        x = part["decisions"][window.index[-1]]["x"]
        return pd.concat([alpha * x, pd.Series({cfg.RISK_FREE: 1.0 - alpha})])

    result = backtest(part["held"], weight_fn, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    result.update(decisions=part["decisions"], level1=part["level1"], choices=choices, alpha=alpha)
    result["total_turnover"] = total_turnover(result)
    return result


@lru_cache(maxsize=64)
def today(choices: Choices) -> pd.Series:
    """Stock weights of the ERC portfolio (α = 1) at the last rebalancing, from the last windows only."""
    inner = {}
    for s in client_sleeves(choices):
        sectors, esg = filters(choices, s)
        window = universe.last_window(s, sectors)
        w = screened_erc(window, esg)[0]
        if not w.empty:
            inner[s] = (w, window)
    x = level2(pd.DataFrame({s: win[w.index] @ w for s, (w, win) in inner.items()}))["x"]
    return pd.concat([x[s] * w for s, (w, _) in inner.items()])


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
