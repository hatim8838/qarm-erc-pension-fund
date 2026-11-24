"""B) Strategy tests on our data: baseline, ERC exactness, α mix, ESG screen, filters, choices, look-ahead."""

import numpy as np
import pandas as pd
import pytest
from conftest import profiles

import config as cfg
from core.utilities import covariance_matrix
from logic import data, portfolio, projection, universe
from logic.construction import level1
from logic.covariance import ledoit_wolf_cc
from logic.report import theorem_holds
from logic.risk import decomposition, volatility


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
def test_erc_across_sleeves_and_alpha_mix_at_every_rebalancing(built, name):
    """Level 2: RC*_i = 1/n, x ≥ 0, Σx = 1; mix: α of the level, risk-free 1 − α, weights ≥ 0, sum 1."""
    result = built[name]
    alpha = cfg.ALPHAS[result["choices"].level]
    assert result["alpha"] == alpha
    for d in result["decisions"].values():
        rc = decomposition(d["x"], d["cov"])["RC*"]
        assert np.allclose(rc, 1 / len(rc), atol=cfg.RC_TOLERANCE)
        assert (d["x"] >= 0).all() and d["x"].sum() == pytest.approx(1.0)
    w = result["weights"]
    assert (w >= 0).all().all() and np.allclose(w.sum(axis=1), 1.0)
    assert np.allclose(w[cfg.RISK_FREE], 1 - alpha) and np.allclose(w.drop(columns=cfg.RISK_FREE).sum(axis=1), alpha)
    assert theorem_holds(result).all()


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_mix_scales_risk_ex_ante(built, name):
    """σ(y) = α·σ(x_erc) on each date's Σ̂ (the risk-free asset has no risk)."""
    alpha = built[name]["alpha"]
    for d in built[name]["decisions"].values():
        assert volatility(alpha * d["x"], d["cov"]) == pytest.approx(alpha * d["sigma_hat"])


@pytest.mark.parametrize("sleeve, esg", [("Eurozone", "Off"), ("EM EMEA", "High")])
def test_level1_erc_holds_at_every_rebalancing(sleeve, esg):
    """Inside a sleeve: RC*_i = 1/n on that date's Σ̂, after the screen."""
    result = level1(sleeve, tuple(data.sectors()), esg)
    returns = data.sleeve_returns(sleeve)
    for t, w in result["weights"].iterrows():
        w = w[w > 0]
        if not w.empty:
            rc = decomposition(w, ledoit_wolf_cc(returns.loc[:t, w.index].tail(cfg.ESTIMATION_WINDOW)))["RC*"]
            assert np.allclose(rc, 1 / len(w), atol=cfg.RC_TOLERANCE)


@pytest.mark.parametrize("esg", list(cfg.ESG_LEVELS))
@pytest.mark.parametrize("sleeve", ["US", "EM EMEA"])
def test_esg_screen_excludes_exactly_the_worst_share(sleeve, esg):
    """At every date: X·n ± 1 stocks excluded, all worse than every kept one, and none of them held."""
    result = level1(sleeve, tuple(data.sectors()), esg)
    scores = data.stocks()["esg_score"].fillna(-np.inf)
    for t, (candidates, excluded) in result["screen"].items():
        assert abs(len(excluded) - cfg.ESG_LEVELS[esg] * len(candidates)) <= 1
        kept = candidates[~candidates.isin(excluded)]
        if len(excluded) and len(kept):
            assert scores[excluded].max() <= scores[kept].min()
        assert (result["weights"].loc[t].reindex(excluded).fillna(0.0) == 0).all()


def test_bonds_and_commodities_ignore_the_esg_screen(built):
    """The ESG level only changes the regional equity sleeves."""
    for name, sleeve in (("b", "Bonds"), ("c", "Commodities")):
        assert built[name]["choices"].esg != portfolio.NO_SCREEN
        pd.testing.assert_frame_equal(built[name]["level1"][sleeve]["weights"],
                                      built["baseline"]["level1"][sleeve]["weights"])


def test_esg_score_improves_with_the_level():
    """Portfolio ESG score today rises with every step of the screen."""
    scores = [universe.esg_score(portfolio.today(portfolio.baseline(e))) for e in cfg.ESG_LEVELS]
    assert all(a < b for a, b in zip(scores, scores[1:]))


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_live_snapshot_equals_the_last_rebalancing(built, name):
    """portfolio.today (shown live on 3d) = stock weights of the backtest at its last date, divided by α."""
    result = built[name]
    held = portfolio.stock_weights(result).drop(cfg.RISK_FREE, errors="ignore") / result["alpha"]
    snapshot = portfolio.today(result["choices"].but(level=portfolio.FULL))
    pd.testing.assert_series_equal(held.sort_index(), snapshot[snapshot > 0].sort_index(), check_names=False)


def test_filters_leave_no_excluded_holding(built):
    """Profile b: no stock outside its regions or sectors, at any rebalancing; no excluded class."""
    choices = profiles()["b"]
    for sleeve, result in built["b"]["level1"].items():
        held = result["weights"].columns[(result["weights"] > 0).any()]
        if sleeve in data.regions():
            table = data.stocks().loc[held]
            assert set(table["zone"]) <= set(choices.regions) and set(table["industry"]) <= set(choices.sectors)
    assert set(built["a"]["level1"]) == {"Eurozone", "Bonds"} and "Bonds" not in built["c"]["level1"]


@pytest.mark.parametrize("change", [dict(regions=("US", "Eurozone")), dict(classes=(cfg.EQUITIES, "Bonds")),
                                    dict(sectors=("Industrials", "Technology")), dict(esg="High"), dict(level=1)])
def test_each_choice_changes_the_portfolio(built, change):
    """Changing a region, class, sector, ESG level or risk level changes the weights."""
    other = portfolio.build(profiles()["b"].but(**change))
    assert not portfolio.stock_weights(other).equals(portfolio.stock_weights(built["b"]))


def test_no_look_ahead(built, monkeypatch):
    """A decision on date t (screen included) is the same when the data stop at t."""
    t = list(built["b"]["decisions"])[120]
    full_returns, full_rf = data.sleeve_returns, data.risk_free_daily
    monkeypatch.setattr(data, "sleeve_returns", lambda s: full_returns(s).loc[:t])
    monkeypatch.setattr(data, "risk_free_daily", lambda: full_rf().loc[:t])
    caches = (level1, portfolio.erc_part)
    for cache in caches:
        cache.cache_clear()
    try:
        truncated = portfolio.build(profiles()["b"])
    finally:
        for cache in caches:
            cache.cache_clear()
    pd.testing.assert_series_equal(truncated["decisions"][t]["x"], built["b"]["decisions"][t]["x"])
    pd.testing.assert_series_equal(truncated["weights"].loc[t], built["b"]["weights"].loc[t])


def test_projection_percentiles_are_ordered_and_widen(built):
    """5% ≤ 25% ≤ 50% ≤ 75% ≤ 95% at every horizon, and the 5–95% band widens with time."""
    e = projection.expected_return(built["b"]["returns"])
    fan = projection.fan(e["mu"], e["sigma"], cfg.MAX_HORIZON)
    assert (fan.diff(axis=1).iloc[:, 1:] >= 0).all().all()
    width = fan.iloc[:, -1] - fan.iloc[:, 0]
    assert (width.diff().iloc[1:] > 0).all()
    assert e["low"] < e["mu"] < e["high"]
