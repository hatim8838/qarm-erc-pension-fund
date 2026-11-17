"""Returns, volatility and (next step) risk budgeting / backtest.

Implemented now
---------------
- :func:`simple_returns`, :func:`excess_returns` (the pipeline's convention)
- :func:`log_returns`, :func:`excess_log_returns` (kept for reference)
- volatility: :func:`rolling_volatility` (1-year rolling, annualised) is the
  single volatility measure of the project; :func:`volatility_summary`
- eligibility: :func:`window_coverage`, :func:`eligible_assets`

Stubs for the next step (raise ``NotImplementedError``)
-------------------------------------------------------
:func:`covariance_matrix`, :func:`risk_contributions`, :func:`erc_weights`,
:func:`risk_budget_weights`, :func:`backtest`, :func:`performance_metrics`.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core.config import ESTIMATION_WINDOW, MIN_WINDOW_COVERAGE, PERIODS_PER_YEAR

logger = logging.getLogger(__name__)

FrameOrSeries = pd.DataFrame | pd.Series

_RESAMPLE_RULE = {"W": "W-FRI", "M": "ME"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def infer_periods_per_year(index: pd.DatetimeIndex) -> int:
    """Guess the annualisation factor (252 / 52 / 12) from the median date spacing."""
    if len(index) < 3:
        return PERIODS_PER_YEAR["D"]
    spacing = pd.Series(index).diff().dt.days.median()
    if spacing <= 4:
        return PERIODS_PER_YEAR["D"]
    if spacing <= 10:
        return PERIODS_PER_YEAR["W"]
    return PERIODS_PER_YEAR["M"]


def _as_frame(x: FrameOrSeries) -> tuple[pd.DataFrame, bool]:
    if isinstance(x, pd.Series):
        return x.to_frame(), True
    return x, False


def _restore(df: pd.DataFrame, was_series: bool, name=None) -> FrameOrSeries:
    if was_series:
        s = df.iloc[:, 0]
        s.name = name
        return s
    return df


# --------------------------------------------------------------------------- #
# Returns
# --------------------------------------------------------------------------- #
def _period_prices(prices: FrameOrSeries, freq: str) -> FrameOrSeries:
    """Prices sampled at ``freq`` (period-end ``last`` for W/M), non-positive -> NaN."""
    if freq not in {"D", "W", "M"}:
        raise ValueError("freq must be one of 'D', 'W', 'M'")
    p = prices.astype(float)
    if freq != "D":
        p = p.resample(_RESAMPLE_RULE[freq]).last()
    return p.where(p > 0)


def _winsorize(r: FrameOrSeries, q: float | None) -> FrameOrSeries:
    if q is None:
        return r
    if not 0 < q < 0.5:
        raise ValueError("winsorize must be in (0, 0.5)")
    lo, hi = r.quantile(q), r.quantile(1 - q)
    return r.clip(lower=lo, upper=hi, axis=1 if isinstance(r, pd.DataFrame) else None)


def simple_returns(
    prices: FrameOrSeries, freq: str = "D", winsorize: float | None = None
) -> FrameOrSeries:
    """Simple (arithmetic) returns from price levels: ``prices.pct_change()``,
    i.e. ``R_t = P_t / P_{t-1} - 1``.

    All equity, bond, commodity and benchmark files are levels (total return
    indices), so this is the return convention used for every asset class.

    Parameters
    ----------
    prices : prices / total-return indices (dates x assets, or a Series).
    freq : ``"D"`` (as given), ``"W"`` (Friday week-end) or ``"M"`` (month-end).
        For W/M, prices are first resampled to the period end with ``last``,
        so the period return compounds the daily returns of the period.
    winsorize : if given (e.g. ``0.001``), clip each asset's returns at its
        ``[q, 1-q]`` quantiles. Default ``None``.

    Notes
    -----
    A NaN price makes both the return into it and the return out of it NaN:
    no return is ever computed across a gap. ``fill_method=None`` is passed
    explicitly because pandas 2.x would otherwise forward-fill the gap first.
    """
    p = _period_prices(prices, freq)
    r = p.pct_change(fill_method=None)
    return _winsorize(r, winsorize)


def log_returns(
    prices: FrameOrSeries, freq: str = "D", winsorize: float | None = None
) -> FrameOrSeries:
    """Log returns ``r_t = ln(P_t / P_{t-1})`` (kept for reference / tests).

    The pipeline uses :func:`simple_returns`; ``log(1 + R) = r``.

    Parameters
    ----------
    prices : prices / total-return indices (dates x assets, or a Series).
    freq : ``"D"`` (as given), ``"W"`` (Friday week-end) or ``"M"`` (month-end).
        For W/M, prices are first resampled to the period end with ``last``
        (the last available price of the period), then log-differenced.
    winsorize : if given (e.g. ``0.001``), clip each asset's returns at its
        ``[q, 1-q]`` quantiles. Default ``None`` (no clipping).

    Notes
    -----
    A NaN price makes both the return into it and the return out of it NaN:
    no return is ever computed across a gap.
    """
    p = _period_prices(prices, freq)
    r = np.log(p).diff()  # NaN on either side -> NaN, never a jump across the gap
    return _winsorize(r, winsorize)


def _log_rf_per_period(rf: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Log risk-free return accrued between consecutive dates of ``index``.

    ``rf`` is the *simple daily* rate (``rf_daily``). The rate known at the
    start of each day is used (``rf_{t-1}``) and compounded over each period,
    so daily, weekly and monthly return indices all work. First row is NaN.
    """
    log_rf = np.log1p(rf.astype(float)).shift(1).fillna(0.0)
    cum = log_rf.cumsum()
    cum = cum.reindex(cum.index.union(index)).ffill().fillna(0.0)
    return cum.reindex(index).diff()


def excess_returns(returns: FrameOrSeries, rf: pd.Series) -> FrameOrSeries:
    """Simple excess returns ``R_t - Rf_t``, with ``Rf_t`` the compounded
    risk-free return over the same period (see :func:`_log_rf_per_period`)."""
    rf_period = np.expm1(_log_rf_per_period(rf, returns.index))
    if isinstance(returns, pd.DataFrame):
        return returns.sub(rf_period, axis=0)
    return returns - rf_period


def excess_log_returns(returns: FrameOrSeries, rf: pd.Series) -> FrameOrSeries:
    """Log excess returns ``r_t - ln(1 + Rf_t)`` (for log returns)."""
    rf_period = _log_rf_per_period(rf, returns.index)
    if isinstance(returns, pd.DataFrame):
        return returns.sub(rf_period, axis=0)
    return returns - rf_period


# --------------------------------------------------------------------------- #
# Volatility (one measure for the whole project)
# --------------------------------------------------------------------------- #
VOL_MIN_PERIODS = ESTIMATION_WINDOW // 2  # 126 days: first value after ~6 months of data


def rolling_volatility(
    returns: FrameOrSeries,
    window: int = ESTIMATION_WINDOW,
    min_periods: int = VOL_MIN_PERIODS,
    periods_per_year: int | None = None,
) -> FrameOrSeries:
    """Annualised 1-year rolling volatility: THE volatility used in the project.

    ``sigma_t = std(R_{t-window+1..t}) * sqrt(252)`` on daily simple returns,
    with a 252-day window (at least 126 observations). The window is the same
    as the 1-year estimation window of the ERC / backtest, so this volatility
    is the square root of the diagonal of the covariance matrix used to build
    the portfolio. The value on date ``t`` uses returns up to ``t`` included.
    """
    ppy = periods_per_year or infer_periods_per_year(returns.index)
    return returns.rolling(window, min_periods=min_periods).std() * np.sqrt(ppy)


def _last_valid(df: pd.DataFrame) -> pd.Series:
    return df.ffill().iloc[-1] if len(df) else pd.Series(np.nan, index=df.columns)


def volatility_summary(
    returns: pd.DataFrame,
    volatility: pd.DataFrame | None = None,
    periods_per_year: int | None = None,
) -> pd.DataFrame:
    """One row per asset with the volatility statistics (annualised).

    Columns: ``full_sample_vol`` (std of all daily returns in the file),
    ``vol_latest`` (last value of the 1-year rolling volatility),
    ``vol_mean``, ``vol_median``, ``vol_min``, ``vol_max`` (of the rolling
    volatility), ``n_obs``, ``first_valid``, ``last_valid``.
    """
    df, _ = _as_frame(returns)
    ppy = periods_per_year or infer_periods_per_year(df.index)
    vol = rolling_volatility(df, periods_per_year=ppy) if volatility is None else volatility
    vol, _ = _as_frame(vol)
    out = pd.DataFrame(
        {
            "full_sample_vol": df.std() * np.sqrt(ppy),
            "vol_latest": _last_valid(vol),
            "vol_mean": vol.mean(),
            "vol_median": vol.median(),
            "vol_min": vol.min(),
            "vol_max": vol.max(),
            "n_obs": df.count().astype(int),
            "first_valid": [df[c].first_valid_index() for c in df.columns],
            "last_valid": [df[c].last_valid_index() for c in df.columns],
        }
    )
    out.index.name = "series"
    return out


def window_coverage(
    returns: pd.DataFrame, as_of: str | pd.Timestamp, window: int = ESTIMATION_WINDOW
) -> pd.Series:
    """Share of the ``window`` business days strictly before ``as_of`` on which
    each asset has a valid return (1.0 = complete estimation window)."""
    as_of = pd.Timestamp(as_of)
    past = returns.loc[returns.index < as_of].tail(window)
    if len(past) < window:
        logger.warning("Only %d return dates before %s (window = %d)", len(past), as_of.date(), window)
    return past.count() / window


def eligible_assets(
    returns: pd.DataFrame,
    as_of: str | pd.Timestamp,
    window: int = ESTIMATION_WINDOW,
    min_coverage: float = MIN_WINDOW_COVERAGE,
) -> pd.Series:
    """Boolean flag per asset: enough history in the estimation window before
    ``as_of`` (coverage >= ``min_coverage``) *and* a valid price on the last
    date before ``as_of`` (excludes series that stopped, e.g. stale tails).

    Used for the universe at the portfolio start and, later, at every
    rebalancing date of the backtest.
    """
    as_of = pd.Timestamp(as_of)
    cov = window_coverage(returns, as_of, window)
    past = returns.loc[returns.index < as_of]
    alive = past.iloc[-1].notna() if len(past) else pd.Series(False, index=returns.columns)
    return (cov >= min_coverage) & alive


# --------------------------------------------------------------------------- #
# Next step: risk budgeting, backtest, performance (NOT IMPLEMENTED YET)
# --------------------------------------------------------------------------- #
def covariance_matrix(returns: pd.DataFrame, method: str = "sample", **kwargs) -> pd.DataFrame:
    """Annualised covariance matrix of returns over an estimation window.

    To implement: sample covariance (1-year rolling window in the backtest),
    optionally EWMA or shrinkage (Ledoit-Wolf); handle assets with missing data
    in the window (drop or pairwise).
    """
    raise NotImplementedError("covariance_matrix: next step (ERC)")


def risk_contributions(weights: pd.Series | np.ndarray, cov: pd.DataFrame | np.ndarray) -> pd.Series:
    """Risk contributions ``RC_i = w_i (Sigma w)_i / sqrt(w' Sigma w)``.

    To implement: return absolute contributions (summing to portfolio
    volatility) and/or relative contributions (summing to 1).
    """
    raise NotImplementedError("risk_contributions: next step (ERC)")


def erc_weights(cov: pd.DataFrame | np.ndarray, **kwargs) -> pd.Series:
    """Equal Risk Contribution weights (long-only, fully invested).

    To implement: special case of :func:`risk_budget_weights` with equal
    budgets ``b_i = 1/N``.
    """
    raise NotImplementedError("erc_weights: next step (ERC)")


def risk_budget_weights(
    cov: pd.DataFrame | np.ndarray, budgets: pd.Series | np.ndarray, **kwargs
) -> pd.Series:
    """Risk-budgeting weights such that ``RC_i / sigma_p = b_i``.

    To implement: e.g. minimise ``sqrt(w' Sigma w) - sum_i b_i ln w_i`` then
    normalise (Roncalli), with ``scipy.optimize``. ESG budgets come from
    :func:`core.esg.esg_scores_vector`.
    """
    raise NotImplementedError("risk_budget_weights: next step (ESG risk budgeting)")


def backtest(
    returns: pd.DataFrame,
    weight_fn,
    rebalance: str = "M",
    window: int = 252,
    **kwargs,
) -> dict:
    """Rolling backtest: monthly rebalancing, 1-year estimation window.

    To implement: at each rebalancing date estimate the covariance on the past
    ``window`` days, compute weights with ``weight_fn``, hold (drifting) until
    the next rebalancing; return weights history and portfolio returns.
    """
    raise NotImplementedError("backtest: next step")


def performance_metrics(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series | None = None, rf: pd.Series | None = None
) -> pd.Series:
    """Performance and risk metrics vs a benchmark.

    To implement: annualised return / vol, Sharpe, max drawdown, VaR / ES,
    tracking error, information ratio, beta, turnover.
    """
    raise NotImplementedError("performance_metrics: next step")
