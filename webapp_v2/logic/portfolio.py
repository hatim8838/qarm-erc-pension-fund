"""The client's portfolio: choices -> sleeves -> two-level ERC -> α mix with the risk-free asset -> backtest."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np
import pandas as pd

import config as cfg
from core.utilities import rebalancing_dates
from logic import data
from logic.construction import last_erc, level1, level2
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
def erc_part(regions: tuple, classes: tuple, sectors: tuple, esg: str, covariance=ledoit_wolf_cc) -> dict:
    """The part that does not depend on α (never in the key): level 1 of each sleeve and the level-2 x_erc
    at each date."""
    choices = Choices(regions, classes, sectors, esg)
    sleeves = {s: level1(s, *filters(choices, s), covariance=covariance) for s in client_sleeves(choices)}
    held = _held_returns(sleeves)
    dates = rebalancing_dates(held.index, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    decisions = {t: level2(pd.DataFrame({s: r["windows"][t] for s, r in sleeves.items() if t in r["windows"]}),
                           covariance) for t in dates}
    return {"level1": sleeves, "held": held, "decisions": decisions}


def build(choices: Choices, covariance=ledoit_wolf_cc) -> dict:
    """Backtest of y = α·x_erc + (1 − α)·r, rebalanced monthly back to α, with every decision."""
    return mix(erc_part(choices.regions, choices.classes, choices.sectors, choices.esg, covariance), choices)


def _hold(held: pd.DataFrame, w: pd.Series, t, end, port: np.ndarray) -> pd.Series:
    """Hold w from t+1 to end with drift, writing the daily returns into port (core.backtest's arithmetic)."""
    i0, i1 = held.index.searchsorted(t, "right"), held.index.searchsorted(end, "right")
    wt = w.to_numpy()
    for i, r in enumerate(held.iloc[i0:i1][w.index].fillna(0.0).to_numpy(), start=i0):
        rp = wt @ r
        port[i] = rp
        wt = wt * (1 + r) / (1 + rp)
    return pd.Series(wt, index=w.index)


def mix(part: dict, choices: Choices) -> dict:
    """The α mix applied after the (cached) ERC part: α in the ERC sleeves, 1 − α in the risk-free asset,
    held with drift and rebalanced monthly. The same steps and arithmetic as core.backtest, without its
    estimation windows (the mix only needs the date), so a change of α costs a few milliseconds."""
    alpha, held = choices.alpha(), part["held"]
    dates = rebalancing_dates(held.index, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
    port, weights, turnover, current = np.full(len(held), np.nan), {}, {}, pd.Series(dtype=float)
    for t, end in zip(dates, [*dates[1:], held.index[-1]]):
        w = pd.concat([alpha * part["decisions"][t]["x"], pd.Series({cfg.RISK_FREE: 1.0 - alpha})])
        weights[t] = w
        turnover[t] = 0.5 * w.sub(current, fill_value=0).abs().sum() if len(current) else 1.0
        current = _hold(held, w, t, end, port)
    result = {"returns": pd.Series(port, index=held.index, name="portfolio").dropna(),
              "weights": pd.DataFrame(weights).T.fillna(0.0), "turnover": pd.Series(turnover, name="turnover")}
    result.update(decisions=part["decisions"], level1=part["level1"], choices=choices, alpha=alpha)
    result["total_turnover"] = total_turnover(result)
    return result


def today(choices: Choices) -> pd.Series:
    """Stock weights of the ERC portfolio (α = 1) at the last rebalancing, from the last windows only."""
    return _today(choices.regions, choices.classes, choices.sectors, choices.esg)


@lru_cache(maxsize=64)
def _today(regions: tuple, classes: tuple, sectors: tuple, esg: str) -> pd.Series:
    """today() keyed by the α-free choices."""
    choices = Choices(regions, classes, sectors, esg)
    inner = {}
    for s in client_sleeves(choices):
        w, window = last_erc(s, *filters(choices, s))
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
    """Returns net of costs c·Σ|Δx| = c·2·turnover, paid on the first day after each rebalancing."""
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
