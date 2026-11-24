"""B) Strategy tests on our data: baseline, ERC/RB exactness, theorem, filters, vol targeting, choices, look-ahead."""

import numpy as np
import pandas as pd
import pytest
from conftest import profiles

import config as cfg
from core.utilities import covariance_matrix
from logic import data, performance, portfolio, projection, universe
from logic.construction import level1
from logic.covariance import ledoit_wolf_cc
from logic.report import theorem_holds
from logic.risk import decomposition

VOL_TOLERANCE = 0.25  # realised σ within ±25% of σ* when σ* is reachable at ≥ 85% of rebalancings


def first_flat_window() -> pd.Timestamp:
    """First rebalancing where an eligible asset has a flat price over the whole window (σ = 0)."""
    for t in data.portfolio_returns().resample("ME").last().index:
        for sleeve in data.sleeves():
            window = data.sleeve_returns(sleeve).loc[:t].tail(cfg.ESTIMATION_WINDOW).dropna(axis=1)
            if (window.std() == 0).any():
                return t
    return data.portfolio_returns().index[-1]


def test_baseline_reproduces_core_erc_with_core_estimator():
    """Same pipeline with core's estimator = core's ERC backtest, until core first holds a flat-price
    (suspended) stock: we leave σ_i = 0 assets out because RC_i = 0 has no ERC solution."""
    mine = portfolio.build(portfolio.baseline(), covariance=covariance_matrix)["returns"]
    both = pd.concat([mine, data.portfolio_returns()[cfg.CORE_ERC]], axis=1).dropna().loc[:first_flat_window()]
    assert len(both) > cfg.TRADING_DAYS * 15
    assert (both.iloc[:, 0] - both.iloc[:, 1]).abs().max() < 1e-6


def test_baseline_with_ln3_shrinkage_stays_close_to_core(built):
    """LN 3 constant-correlation target instead of core's identity target: same strategy, small gap."""
    both = pd.concat([built["baseline"]["returns"], data.portfolio_returns()[cfg.CORE_ERC]], axis=1).dropna()
    assert both.corr().iloc[0, 1] > 0.99
    years = len(both) / cfg.TRADING_DAYS
    annual = (1 + both).prod() ** (1 / years) - 1
    assert abs(annual.iloc[0] - annual.iloc[1]) < 0.005


@pytest.mark.parametrize("name", ["a", "b", "c", "baseline"])
def test_level2_erc_weights_and_mix_at_every_rebalancing(built, name):
    """Across sleeves: RC*_i = 1/n, x ≥ 0, α + (1 − α) = 1, and σ(mv) ≤ σ(erc) ≤ σ(ew)."""
    for d in built[name]["decisions"].values():
        rc = decomposition(d["x"], d["cov"])["RC*"]
        assert np.allclose(rc, 1 / len(rc), atol=cfg.RC_TOLERANCE)
        assert (d["weights"] >= -1e-12).all() and d["weights"].sum() == pytest.approx(1.0)
        assert 0 <= d["alpha"] <= cfg.MAX_ALPHA
    assert theorem_holds(built[name]).all()


@pytest.mark.parametrize("sleeve, sectors, esg", [("Eurozone", tuple(data.sectors()), "off"),
                                                   ("EM EMEA", tuple(data.sectors()), "screen_rb")])
def test_level1_risk_budgets_hold_at_every_rebalancing(sleeve, sectors, esg):
    """Inside a sleeve: RC*_i = 1/n (ERC) or RC*_i = b_i (ESG budgets) on that date's Σ̂."""
    result = level1(sleeve, sectors, esg)
    returns = data.sleeve_returns(sleeve)
    for t, w in result["weights"].iterrows():
        w = w[w > 0]
        if w.empty:
            continue
        rc = decomposition(w, ledoit_wolf_cc(returns.loc[:t, w.index].tail(cfg.ESTIMATION_WINDOW)))["RC*"]
        budget = universe.esg_budgets(w.index) if esg == "screen_rb" else pd.Series(1 / len(w), index=w.index)
        assert np.allclose(rc, budget / budget.sum(), atol=cfg.RC_TOLERANCE)


def test_filters_leave_no_excluded_holding(built):
    """Profile b: no stock outside its regions or sectors, at any rebalancing; no excluded class."""
    choices = profiles()["b"]
    for sleeve, result in built["b"]["level1"].items():
        held = result["weights"].columns[(result["weights"] > 0).any()]
        if sleeve in data.regions():
            table = data.stocks().loc[held]
            assert set(table["zone"]) <= set(choices.regions) and set(table["industry"]) <= set(choices.sectors)
    assert set(built["a"]["level1"]) == {"Eurozone", "Bonds"} and "Bonds" not in built["c"]["level1"]


def test_esg_screen_removes_only_stocks_below_the_threshold():
    """Kept stocks score ≥ the ESG_SCREEN_LEVEL quantile of their region x sector; removed ones are below."""
    for region in data.regions():
        table = data.stocks()[data.stocks()["zone"] == region]
        kept = universe.selected_stocks(region, tuple(data.sectors()), "screen")
        cut = table.groupby("industry")["esg_score"].transform(lambda s: s.quantile(cfg.ESG_SCREEN_LEVEL))
        below = table["esg_score"] < cut
        assert not below[kept].any()
        assert (below | table["esg_score"].isna())[table.index.difference(kept)].all()


def test_vol_targeting_hits_reachable_targets_and_caps_the_others(built):
    """Reachable σ*: realised σ within VOL_TOLERANCE; unreachable: α = 1 (no leverage)."""
    for name in ("a", "b", "c"):
        result, target = built[name], profiles()[name].target()
        sigma_hat = pd.Series({t: d["sigma_hat"] for t, d in result["decisions"].items()})
        alpha = pd.Series({t: d["alpha"] for t, d in result["decisions"].items()})
        assert (alpha[sigma_hat < target] == cfg.MAX_ALPHA).all()
        if (sigma_hat >= target).mean() >= 0.85:
            realised = performance.realised_volatility(result["returns"])
            assert abs(realised / target - 1) < VOL_TOLERANCE


@pytest.mark.parametrize("change", [dict(regions=("US", "Eurozone")), dict(classes=(cfg.EQUITIES,) + ("Bonds",)),
                                    dict(sectors=("Industrials", "Technology")), dict(esg="screen_rb"), dict(level=1)])
def test_each_choice_changes_the_portfolio(built, change):
    """Changing a region, class, sector, ESG option or risk level changes the weights."""
    other = portfolio.build(profiles()["b"].but(**change))
    assert not portfolio.stock_weights(other).equals(portfolio.stock_weights(built["b"]))


def test_no_look_ahead(built, monkeypatch):
    """A decision on date t is the same when the data stop at t."""
    t = list(built["a"]["decisions"])[120]
    full_returns, full_rf = data.sleeve_returns, data.risk_free_daily
    monkeypatch.setattr(data, "sleeve_returns", lambda s: full_returns(s).loc[:t])
    monkeypatch.setattr(data, "risk_free_daily", lambda: full_rf().loc[:t])
    level1.cache_clear()
    try:
        truncated = portfolio.build(profiles()["a"])["decisions"][t]["weights"]
    finally:
        level1.cache_clear()
    pd.testing.assert_series_equal(truncated, built["a"]["decisions"][t]["weights"])


def test_projection_percentiles_are_ordered_and_widen(built):
    """5% ≤ 25% ≤ 50% ≤ 75% ≤ 95% at every horizon, and the 5–95% band widens with time."""
    e = projection.expected_return(built["b"]["returns"])
    fan = projection.fan(e["mu"], e["sigma"], cfg.MAX_HORIZON)
    assert (fan.diff(axis=1).iloc[:, 1:] >= 0).all().all()
    width = fan.iloc[:, -1] - fan.iloc[:, 0]
    assert (width.diff().iloc[1:] > 0).all()
    assert e["low"] < e["mu"] < e["high"]
