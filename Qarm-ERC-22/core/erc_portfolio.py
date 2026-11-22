"""ERC portfolio at one date, for the Streamlit "ERC Portfolio" page (no Streamlit import here).

Same construction as ``core.utilities.two_level_weights`` (LN 5 / Lab 5 risk budgeting):

1. inside each sleeve (US, Eurozone, ..., Bonds, Commodities): risk-budgeting weights
   (ERC = equal budgets; optionally ESG budgets proportional to the ESG scores),
2. across sleeves: ERC on the sleeve returns,
3. weight of an asset = sleeve weight x weight inside the sleeve.

Differences with ``two_level_weights``: the covariance estimator can be chosen
(``core.shrinkage``) and every intermediate result needed for the charts is returned.
Nothing here changes the pre-computed backtest of ``compute_erc.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from core.config import ASSET_ID_SEP, ESTIMATION_WINDOW, NON_EQUITY_SLEEVES, TRADING_DAYS
from core.utilities import covariance_matrix, eligible_assets, risk_budget_weights, risk_contributions


@dataclass
class ERCPortfolio:
    as_of: pd.Timestamp
    esg_budgets: bool
    weights: pd.Series                      # "<sleeve>|<asset>" -> capital weight (sums to 1)
    inner_weights: dict[str, pd.Series]     # sleeve -> weights inside the sleeve (sum to 1)
    inner_rc: dict[str, pd.Series]          # sleeve -> relative risk contributions inside the sleeve
    inner_budgets: dict[str, pd.Series]     # sleeve -> risk budgets used inside the sleeve
    sleeve_weights: pd.Series               # capital weight of each sleeve
    sleeve_rc: pd.Series                    # relative risk contribution of each sleeve (= 1/n for ERC)
    sleeve_cov: pd.DataFrame                # annualised covariance of the sleeve portfolios
    sleeve_vol: pd.Series                   # stand-alone annualised volatility of each sleeve portfolio
    diagnostics: pd.DataFrame               # per sleeve: assets, delta, mean correlation, ...
    asset_vol: pd.Series                    # stand-alone annualised volatility of each asset
    volatility: float                       # annualised volatility of the portfolio (model)
    comparison: pd.DataFrame                # across sleeves: ERC vs Equal Weight vs Minimum Variance
    dropped: list[str] = field(default_factory=list)  # selected assets without a complete window

    @property
    def risk_share(self) -> pd.Series:
        """Hierarchical risk share of each asset in the total portfolio risk
        (sleeve risk contribution x risk contribution inside the sleeve; sums to 1)."""
        parts = {s: self.sleeve_rc[s] * rc for s, rc in self.inner_rc.items()}
        return pd.concat(parts.values()).rename("risk_share")

    @property
    def max_rc_gap(self) -> float:
        """Largest gap between a relative risk contribution and its budget, at both levels."""
        gaps = [float((self.sleeve_rc - 1 / len(self.sleeve_rc)).abs().max())]
        for s, rc in self.inner_rc.items():
            gaps.append(float((rc - self.inner_budgets[s]).abs().max()))
        return max(gaps)


def split_sleeves(columns) -> dict[str, list[str]]:
    """``"<sleeve>|<asset>"`` columns -> {sleeve: [columns]} (order of first appearance)."""
    out: dict[str, list[str]] = {}
    for c in columns:
        out.setdefault(str(c).split(ASSET_ID_SEP, 1)[0], []).append(c)
    return out


def _min_variance(cov: np.ndarray) -> np.ndarray:
    """Long-only fully-invested minimum-variance weights (small problems: the sleeves)."""
    n = len(cov)
    scale = np.mean(np.diag(cov))
    res = minimize(
        lambda w: 0.5 * w @ (cov / scale) @ w,
        np.full(n, 1 / n),
        jac=lambda w: (cov / scale) @ w,
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        method="SLSQP",
        options={"ftol": 1e-14, "maxiter": 500},
    )
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def estimation_window(returns: pd.DataFrame, as_of, window: int = ESTIMATION_WINDOW) -> tuple[pd.DataFrame, list[str]]:
    """Last ``window`` days up to ``as_of`` and the assets without a complete history (dropped)."""
    ok = eligible_assets(returns, as_of, window)
    win = returns.loc[:as_of].tail(window)
    dropped = [str(c) for c in ok.index[~ok]]
    return win.loc[:, ok], dropped


def build_erc_portfolio(
    window: pd.DataFrame,
    esg_scores: pd.Series | None = None,
    dropped: list[str] | None = None,
) -> ERCPortfolio:
    """Two-level ERC on one complete estimation window (columns ``"<sleeve>|<asset>"``).

    ``esg_scores`` (indexed like the columns): if given, the equity sleeves use risk budgets
    proportional to the ESG scores instead of equal budgets (stocks without a score are left out).

    The sleeves are whatever the columns contain: with N sleeves (e.g. 5 when the investor
    excludes commodities) the across-sleeve ERC gives each sleeve a risk budget of 1/N.
    """
    sleeves = split_sleeves(window.columns)
    if len(sleeves) < 2:
        held = ", ".join(sleeves) or "none"
        raise ValueError(
            f"At least two sleeves are needed for the across-sleeve ERC (held on this date: {held}). "
            "Select more regions or include commodities."
        )
    inner_w, inner_rc, inner_b, diag, asset_vol = {}, {}, {}, [], {}
    for sleeve, cols in sleeves.items():
        budgets = None
        if esg_scores is not None and sleeve not in NON_EQUITY_SLEEVES:
            b = esg_scores.reindex(cols).dropna()
            b = b[b > 0]
            if b.empty:
                raise ValueError(f"No ESG score in sleeve {sleeve}.")
            cols, budgets = list(b.index), b / b.sum()
        cov = covariance_matrix(window[cols])
        w = risk_budget_weights(cov, budgets)
        b_used = budgets if budgets is not None else pd.Series(1 / len(cols), index=cols)
        inner_w[sleeve], inner_b[sleeve] = w, b_used
        inner_rc[sleeve] = risk_contributions(w, cov)
        asset_vol.update(zip(cols, np.sqrt(np.diag(cov))))
        diag.append(
            {
                "sleeve": sleeve,
                "assets": len(cols),
                "window_days": len(window),
                "assets_per_day": len(cols) / len(window),
            }
        )

    sleeve_ret = pd.DataFrame({s: window[w.index] @ w for s, w in inner_w.items()})
    cov_s = covariance_matrix(sleeve_ret)
    w_s = risk_budget_weights(cov_s)
    rc_s = risk_contributions(w_s, cov_s)
    vol_s = pd.Series(np.sqrt(np.diag(cov_s)), index=cov_s.index)
    diag.append(
        {
            "sleeve": "Across sleeves",
            "assets": len(sleeve_ret.columns),
            "window_days": len(window),
            "assets_per_day": len(sleeve_ret.columns) / len(window),
        }
    )

    weights = pd.concat([w_s[s] * w for s, w in inner_w.items()]).rename("weight")
    vol = float(np.sqrt(w_s.to_numpy() @ cov_s.to_numpy() @ w_s.to_numpy()))

    # LN 5: sigma(MV) <= sigma(ERC) <= sigma(EW), checked across the sleeves.
    n = len(w_s)
    w_ew = pd.Series(1 / n, index=w_s.index)
    w_mv = pd.Series(_min_variance(cov_s.to_numpy()), index=w_s.index)
    rows = {}
    for name, w in (("Equal Weight", w_ew), ("ERC", w_s), ("Minimum Variance", w_mv)):
        rows[name] = {
            "volatility": float(np.sqrt(w.to_numpy() @ cov_s.to_numpy() @ w.to_numpy())),
            "max_risk_contribution": float(risk_contributions(w, cov_s).max()),
            "min_risk_contribution": float(risk_contributions(w, cov_s).min()),
        }
    comparison = pd.DataFrame(rows).T
    weights_by = pd.DataFrame({"Equal Weight": w_ew, "ERC": w_s, "Minimum Variance": w_mv})
    rc_by = pd.DataFrame({k: risk_contributions(weights_by[k], cov_s) for k in weights_by})
    comparison.attrs["weights"] = weights_by
    comparison.attrs["risk_contributions"] = rc_by

    return ERCPortfolio(
        as_of=window.index[-1],
        esg_budgets=esg_scores is not None,
        weights=weights,
        inner_weights=inner_w,
        inner_rc=inner_rc,
        inner_budgets=inner_b,
        sleeve_weights=w_s,
        sleeve_rc=rc_s,
        sleeve_cov=cov_s,
        sleeve_vol=vol_s,
        diagnostics=pd.DataFrame(diag).set_index("sleeve"),
        asset_vol=pd.Series(asset_vol, name="volatility"),
        volatility=vol,
        comparison=comparison,
        dropped=list(dropped or []),
    )
