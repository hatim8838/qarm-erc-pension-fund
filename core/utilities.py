"""Returns, volatility, risk budgeting (ERC), backtest and performance metrics.

- returns:        simple_returns, excess_returns, rolling_volatility
- risk budgeting: covariance_matrix, risk_contributions, risk_budget_weights,
                  erc_weights, two_level_weights
- backtest:       rebalancing_dates, eligible_assets, backtest
- metrics:        drawdown, performance_metrics, period_performance
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from core.config import ESTIMATION_WINDOW, REBALANCING_FREQ, TRADING_DAYS

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Returns and volatility
# --------------------------------------------------------------------------- #
def simple_returns(prices: pd.DataFrame | pd.Series, freq: str = "D") -> pd.DataFrame | pd.Series:
    """Simple returns ``R_t = P_t / P_{t-1} - 1`` (daily ``"D"`` or month-end ``"M"``).

    No return is computed across a missing price (``fill_method=None``).
    """
    if freq == "M":
        prices = prices.resample("ME").last()
    return prices.pct_change(fill_method=None)


def excess_returns(returns: pd.DataFrame | pd.Series, rf_daily: pd.Series) -> pd.DataFrame | pd.Series:
    """Daily excess returns ``R_t - rf_t``."""
    rf = rf_daily.reindex(returns.index).fillna(0.0)
    return returns.sub(rf, axis=0) if isinstance(returns, pd.DataFrame) else returns - rf


def rolling_volatility(returns: pd.DataFrame | pd.Series, window: int = ESTIMATION_WINDOW):
    """Annualised 1-year rolling volatility ``std(R) * sqrt(252)`` (same window as the ERC)."""
    return returns.rolling(window, min_periods=window // 2).std() * np.sqrt(TRADING_DAYS)


# --------------------------------------------------------------------------- #
# Risk budgeting (LN5)
# --------------------------------------------------------------------------- #
LEDOIT_WOLF_MIN_ASSETS = 30  # Ledoit-Wolf shrinkage for sleeves with at least 30 assets


def covariance_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Annualised covariance of the estimation-window returns (no NaN allowed).

    Sample covariance, or Ledoit-Wolf shrinkage when the sleeve has many stocks
    (hundreds of stocks for 252 days: the sample covariance is too noisy).
    """
    x = returns.to_numpy(dtype=float)
    if x.shape[1] >= LEDOIT_WOLF_MIN_ASSETS:
        cov = LedoitWolf().fit(x).covariance_
    else:
        cov = np.atleast_2d(np.cov(x, rowvar=False))
    return pd.DataFrame(cov * TRADING_DAYS, index=returns.columns, columns=returns.columns)


def risk_contributions(weights: pd.Series, cov: pd.DataFrame, relative: bool = True) -> pd.Series:
    """Risk contributions ``RC_i = w_i (Sigma w)_i / sigma_p`` (relative: divided by sigma_p, sum = 1)."""
    w, s = weights.to_numpy(), cov.to_numpy()
    vol = np.sqrt(w @ s @ w)
    rc = w * (s @ w) / vol
    return pd.Series(rc / vol if relative else rc, index=weights.index)


def risk_budget_weights(cov: pd.DataFrame, budgets: pd.Series | None = None) -> pd.Series:
    """Long-only weights summing to 1 with relative risk contributions = budgets.

    Same problem as in LN5, ``min 1/2 y' Sigma y`` s.t. ``sum b_i ln y_i >= c``
    then ``w = y / sum(y)``, solved in its equivalent form
    ``min 1/2 y' Sigma y - sum b_i ln y_i`` (fast for hundreds of stocks).
    ``budgets=None`` gives the ERC portfolio (``b_i = 1/N``).
    """
    n = len(cov)
    if n == 1:
        return pd.Series(1.0, index=cov.index)
    b = np.full(n, 1 / n) if budgets is None else budgets.reindex(cov.index).to_numpy(dtype=float)
    s = cov.to_numpy() / np.mean(np.diag(cov))  # rescaled for numerical stability
    res = minimize(
        lambda y: 0.5 * y @ s @ y - b @ np.log(y),
        x0=b / np.sqrt(np.diag(s)),
        jac=lambda y: s @ y - b / y,
        method="L-BFGS-B",
        bounds=[(1e-12, None)] * n,
        options={"maxiter": 10_000, "ftol": 1e-15, "gtol": 1e-10},
    )
    return pd.Series(res.x / res.x.sum(), index=cov.index)


def erc_weights(cov: pd.DataFrame) -> pd.Series:
    """Equal Risk Contribution weights (``b_i = 1/N``)."""
    return risk_budget_weights(cov)


def two_level_weights(
    window: pd.DataFrame, sleeves: dict[str, list[str]], esg_budgets: dict[str, pd.Series] | None = None
) -> pd.Series:
    """Two-level ERC on one estimation window.

    1. Within each sleeve: ERC weights (or ESG risk budgets for the equity
       sleeves; stocks without a budget are left out).
    2. Across sleeves: ERC on the sleeve returns (window returns x sleeve weights).
    3. Weight of an asset = sleeve weight x weight within the sleeve.
    """
    inner = {}
    for sleeve, cols in sleeves.items():
        cols = [c for c in cols if c in window.columns]
        budgets = None
        if esg_budgets and sleeve in esg_budgets:
            budgets = esg_budgets[sleeve].reindex(cols).dropna()
            cols = list(budgets.index)
            budgets = budgets / budgets.sum()
        if cols:
            inner[sleeve] = risk_budget_weights(covariance_matrix(window[cols]), budgets)
    sleeve_returns = pd.DataFrame({s: window[w.index] @ w for s, w in inner.items()})
    outer = erc_weights(covariance_matrix(sleeve_returns))
    weights = pd.concat([outer[s] * w for s, w in inner.items()])
    weights.attrs["sleeve_weights"] = outer
    return weights


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #
def rebalancing_dates(index: pd.DatetimeIndex, start, freq: str = REBALANCING_FREQ) -> pd.DatetimeIndex:
    """Last trading day of each month (``"M"``) or quarter (``"Q"``), from the
    last trading day before ``start``. Weights computed on day t are held from t+1."""
    days = pd.Series(index, index=index)
    ends = days.groupby(pd.Grouper(freq={"M": "ME", "Q": "QE"}[freq])).last().dropna()
    first = days[days < pd.Timestamp(start)].iloc[-1]
    return pd.DatetimeIndex([first, *ends[ends >= pd.Timestamp(start)]], name="date")


def eligible_assets(returns: pd.DataFrame, as_of, window: int = ESTIMATION_WINDOW) -> pd.Series:
    """True for assets with a return on every one of the last ``window`` days up to ``as_of``."""
    past = returns.loc[:as_of].tail(window)
    return past.notna().all() & (len(past) == window)


def backtest(returns: pd.DataFrame, weight_fn, start, rebalance: str = REBALANCING_FREQ) -> dict:
    """Backtest with monthly rebalancing and weights drifting between rebalancings.

    At each rebalancing date t: estimation window = last 252 days up to t,
    eligible assets = complete window, weights = ``weight_fn(window)``.
    The weights are held from t+1 (no look-ahead). A missing return during the
    holding period (e.g. a delisting) counts as 0.

    Returns ``returns`` (daily portfolio returns), ``weights`` (at each
    rebalancing), ``sleeve_weights`` (if provided by ``weight_fn``), ``turnover``.
    """
    dates = rebalancing_dates(returns.index, start, rebalance)
    weights, sleeve_weights, turnover = {}, {}, {}
    port = pd.Series(np.nan, index=returns.index, name="portfolio")
    current = pd.Series(dtype=float)

    for k, t in enumerate(dates):
        window = returns.loc[:t].tail(ESTIMATION_WINDOW)
        window = window.loc[:, eligible_assets(returns, t)]
        w = weight_fn(window)
        weights[t] = w
        if "sleeve_weights" in w.attrs:
            sleeve_weights[t] = w.attrs["sleeve_weights"]
        turnover[t] = 0.5 * w.sub(current, fill_value=0).abs().sum() if len(current) else 1.0

        end = dates[k + 1] if k + 1 < len(dates) else returns.index[-1]
        hold = returns.loc[(returns.index > t) & (returns.index <= end), w.index].fillna(0.0)
        wt = w.to_numpy()
        for day, r in zip(hold.index, hold.to_numpy()):
            rp = wt @ r
            port[day] = rp
            wt = wt * (1 + r) / (1 + rp)  # weights drift with returns
        current = pd.Series(wt, index=w.index)

    out = {
        "returns": port.dropna(),
        "weights": pd.DataFrame(weights).T.fillna(0.0),
        "turnover": pd.Series(turnover, name="turnover"),
    }
    if sleeve_weights:
        out["sleeve_weights"] = pd.DataFrame(sleeve_weights).T
    return out


# --------------------------------------------------------------------------- #
# Performance and risk metrics
# --------------------------------------------------------------------------- #
CRISIS_PERIODS: dict[str, tuple[str, str]] = {
    "Global Financial Crisis": ("2007-10-09", "2009-03-09"),
    "Covid crash": ("2020-02-19", "2020-03-23"),
    "2022 inflation shock": ("2022-01-03", "2022-10-12"),
}


def drawdown(returns: pd.Series) -> pd.Series:
    """Drawdown ``W_t / max(W) - 1`` of the wealth index."""
    wealth = (1 + returns.fillna(0)).cumprod()
    return wealth / wealth.cummax() - 1


def performance_metrics(returns: pd.Series, rf_daily: pd.Series | None = None) -> pd.Series:
    """Annualised return and volatility, Sharpe ratio, max drawdown, and
    historical daily VaR / Expected Shortfall at 95% and 99% (positive = loss)."""
    r = returns.dropna()
    rf = 0.0 if rf_daily is None else rf_daily.reindex(r.index).fillna(0.0)
    vol = r.std() * np.sqrt(TRADING_DAYS)
    out = {
        "ann_return": (1 + r).prod() ** (TRADING_DAYS / len(r)) - 1,
        "ann_volatility": vol,
        "sharpe": (r - rf).mean() * TRADING_DAYS / vol,
        "max_drawdown": drawdown(r).min(),
    }
    for level in (95, 99):
        var = -r.quantile(1 - level / 100)
        out[f"VaR_{level}"] = var
        out[f"ES_{level}"] = -r[r <= -var].mean()
    return pd.Series(out, name=returns.name)


def period_performance(returns: pd.DataFrame | pd.Series, periods=CRISIS_PERIODS) -> pd.DataFrame:
    """Cumulative return of each series over each period (crises)."""
    df = returns.to_frame() if isinstance(returns, pd.Series) else returns
    return pd.DataFrame({name: (1 + df.loc[a:b].fillna(0)).prod() - 1 for name, (a, b) in periods.items()}).T
