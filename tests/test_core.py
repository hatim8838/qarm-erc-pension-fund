"""Sanity tests for the data layer (run with ``pytest -q`` from the repo root)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROCESSED_DIR, RAW_DIR  # noqa: E402
import core.importation_data as imp  # noqa: E402
from core.esg import (  # noqa: E402
    available_sectors,
    esg_level_from_label,
    esg_scores_vector,
    get_screened_returns,
    investor_selection,
    screen_universe,
    screening_warnings,
    universe_summary,
)
from core.importation_data import (  # noqa: E402
    clean_prices,
    load_risk_free,
    load_single_series,
    sort_stock_table,
)
from core.utilities import (  # noqa: E402
    eligible_assets,
    window_coverage,
    erc_weights,
    excess_log_returns,
    excess_returns,
    log_returns,
    rolling_volatility,
    simple_returns,
    volatility_summary,
)


# --------------------------------------------------------------------------- #
# Log returns
# --------------------------------------------------------------------------- #
@pytest.fixture
def prices() -> pd.Series:
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2020-01-01", periods=300)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx)))), index=idx, name="p")


def test_log_returns_match_numpy(prices):
    r = log_returns(prices)
    pd.testing.assert_series_equal(r, np.log(prices).diff(), check_names=False)


def test_log_returns_dataframe(prices):
    df = pd.DataFrame({"a": prices, "b": prices * 2})
    r = log_returns(df)
    np.testing.assert_allclose(r["a"].dropna(), r["b"].dropna())


def test_nan_gap_does_not_create_jump(prices):
    p = prices.copy()
    p.iloc[100:105] = np.nan
    r = log_returns(p)
    assert r.iloc[100:106].isna().all()  # into the gap and the first return after it
    assert r.iloc[106] == pytest.approx(np.log(p.iloc[106] / p.iloc[105]))
    assert r.iloc[99] == pytest.approx(np.log(p.iloc[99] / p.iloc[98]))


def test_monthly_uses_month_end_prices(prices):
    r = log_returns(prices, freq="M")
    month_end = prices.groupby(prices.index.to_period("M")).last()
    expected = np.log(month_end).diff()
    np.testing.assert_allclose(r.to_numpy()[1:], expected.to_numpy()[1:])
    assert (r.index == r.index.to_period("M").to_timestamp("M")).all()


def test_weekly_and_winsorize(prices):
    rw = log_returns(prices, freq="W")
    assert (rw.index.dayofweek == 4).all()
    p = prices.copy()
    p.iloc[150:] *= 3  # a +110% jump
    rwin = log_returns(p, winsorize=0.01)
    assert rwin.max() < np.log(3)
    with pytest.raises(ValueError):
        log_returns(prices, freq="Q")


def test_excess_log_returns_daily():
    idx = pd.bdate_range("2021-01-01", periods=5)
    r = pd.Series([np.nan, 0.01, 0.02, -0.01, 0.0], index=idx)
    rf = pd.Series(0.0001, index=idx)
    ex = excess_log_returns(r, rf)
    np.testing.assert_allclose(ex.iloc[1:], r.iloc[1:] - np.log1p(0.0001))


def test_simple_returns_match_definition(prices):
    r = simple_returns(prices)
    expected = prices / prices.shift(1) - 1
    pd.testing.assert_series_equal(r, expected, check_names=False)
    np.testing.assert_allclose(np.log1p(r.dropna()), log_returns(prices).dropna())


def test_simple_returns_nan_gap_and_monthly(prices):
    p = prices.copy()
    p.iloc[100:105] = np.nan
    r = simple_returns(p)
    assert r.iloc[100:106].isna().all()
    assert r.iloc[106] == pytest.approx(p.iloc[106] / p.iloc[105] - 1)
    rm = simple_returns(prices, freq="M")
    month_end = prices.groupby(prices.index.to_period("M")).last()
    np.testing.assert_allclose(rm.to_numpy()[1:], (month_end / month_end.shift(1) - 1).to_numpy()[1:])
    # a monthly simple return compounds the daily simple returns of the month
    daily = simple_returns(prices)
    feb = daily[(daily.index.month == 2) & (daily.index.year == 2020)]
    assert rm.loc["2020-02-29"] == pytest.approx((1 + feb).prod() - 1)


def test_excess_simple_returns():
    idx = pd.bdate_range("2021-01-01", periods=5)
    r = pd.Series([np.nan, 0.01, 0.02, -0.01, 0.0], index=idx)
    rf = pd.Series(0.0001, index=idx)
    np.testing.assert_allclose(excess_returns(r, rf).iloc[1:], r.iloc[1:] - 0.0001)
    # monthly: rf compounds over the period
    didx = pd.bdate_range("2021-01-01", "2021-03-31")
    rf_d = pd.Series(0.0001, index=didx)
    rm = pd.Series([np.nan, 0.02, 0.01], index=pd.to_datetime(["2021-01-31", "2021-02-28", "2021-03-31"]))
    n_feb = ((didx > "2021-01-31") & (didx <= "2021-02-28")).sum()
    assert excess_returns(rm, rf_d).iloc[1] == pytest.approx(0.02 - ((1.0001) ** n_feb - 1))


# --------------------------------------------------------------------------- #
# Volatility proxies
# --------------------------------------------------------------------------- #
def test_rolling_vol_iid_normal():
    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2000-01-03", periods=5000)
    r = pd.DataFrame({"x": rng.normal(0, 0.01, len(idx))}, index=idx)
    vol = rolling_volatility(r)
    assert vol["x"].iloc[:125].isna().all() and vol["x"].iloc[125:].notna().all()
    assert vol["x"].mean() == pytest.approx(0.01 * np.sqrt(252), rel=0.03)  # ~15.9%


def test_volatility_summary():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2015-01-01", periods=1500)
    r = pd.DataFrame({"a": rng.normal(0, 0.01, len(idx))}, index=idx)
    summ = volatility_summary(r)
    assert list(summ.columns) == ["full_sample_vol", "vol_latest", "vol_mean", "vol_median",
                                  "vol_min", "vol_max", "n_obs", "first_valid", "last_valid"]
    assert summ.loc["a", "full_sample_vol"] == pytest.approx(0.1587, rel=0.05)
    assert summ.loc["a", "vol_latest"] == pytest.approx(rolling_volatility(r)["a"].iloc[-1])


def test_rolling_vol_uses_one_year_window():
    idx = pd.bdate_range("2015-01-01", periods=400)
    r = pd.Series(np.r_[np.full(200, 0.02), np.full(200, 0.0)] * np.tile([1, -1], 200), index=idx)
    v = rolling_volatility(r)
    assert np.isnan(v.iloc[124]) and not np.isnan(v.iloc[125])   # 126 obs minimum
    expected = r.iloc[300 - 251 : 301].std() * np.sqrt(252)       # last 252 returns
    assert v.iloc[300] == pytest.approx(expected)


def test_next_step_stubs_not_implemented():
    with pytest.raises(NotImplementedError):
        erc_weights(np.eye(2))


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def test_clean_prices_rules():
    idx = pd.bdate_range("2020-01-01", periods=60)
    a = np.linspace(10, 20, 60)
    a[:12] = 10.0                         # leading stale run (12 >= 10)
    a[30:33] = np.nan                     # short hole -> ffilled
    b = np.linspace(5, 6, 60)
    b[45:] = b[45]                        # trailing stale run (15 identical values)
    b[20:28] = np.nan                     # long hole (8) -> not filled
    b[5] = -1.0                           # non-positive
    c = np.linspace(1, 2, 60)
    c[20:24] = c[20]                      # short flat run in the middle -> untouched
    df = pd.DataFrame({"a": a, "b": b, "c": c}, index=idx)
    out, rep = clean_prices(df)
    assert out["a"].iloc[:12].isna().all() and out["a"].iloc[12:].notna().all()
    assert rep.loc["a", "n_stale_leading"] == 12 and rep.loc["a", "n_ffilled"] == 3
    assert out["b"].iloc[45] == pytest.approx(b[45]) and out["b"].iloc[46:].isna().all()
    assert rep.loc["b", "n_stale_trailing"] == 14
    assert out["b"].iloc[20:28].isna().all()
    # the non-positive price becomes a 1-day hole, which is then forward-filled
    assert rep.loc["b", "n_non_positive"] == 1 and out["b"].iloc[5] == pytest.approx(b[4])
    assert (out["c"] == c).all()


# --------------------------------------------------------------------------- #
# ESG screening
# --------------------------------------------------------------------------- #
@pytest.fixture
def esg_df() -> pd.DataFrame:
    rows = []
    for region in ("US", "Eurozone"):
        for ind in ("Energy", "Technology"):
            for k in range(20):
                score = np.nan if k == 0 else float(k * 5)  # 5..95, one missing per group
                name = f"{ind[:3]}{k}"
                rows.append(dict(asset_id=f"{region}|{name}", name=name, region=region, industry=ind,
                                 sector=ind + " sector", esg_score=score, isin=f"XX{region}{name}"))
    return pd.DataFrame(rows).set_index("asset_id")


def test_screen_level_zero_keeps_everything(esg_df):
    s = screen_universe(esg_df, ["US"], ["Energy"], 0.0)
    assert len(s) == 20 and s["selected"].all()  # incl. the missing ESG score
    assert set(s.columns) >= {"region", "industry", "sector", "esg_score", "isin", "selected"}


def test_screen_half_keeps_top_half_per_group(esg_df):
    s = screen_universe(esg_df, ["US", "Eurozone"], None, 0.5, min_stocks=5)
    assert len(s) == 80
    for (_, _), g in s.groupby(["region", "industry"]):
        kept = g[g["selected"]]
        assert 9 <= len(kept) <= 11
        assert kept["esg_score"].min() >= g["esg_score"].median()
        assert kept["esg_score"].notna().all()  # missing ESG excluded when level > 0
    assert screening_warnings(s) == []


def test_screen_threshold_method(esg_df):
    s = screen_universe(esg_df, ["US"], ["Technology"], 0.6, min_stocks=1, method="threshold")
    assert (s.loc[s["selected"], "esg_score"] >= 60).all()
    assert s["selected"].sum() == 8  # 60..95


def test_screen_relaxation_warning(esg_df):
    s = screen_universe(esg_df, ["US"], ["Energy"], 0.9, min_stocks=10)
    assert s["selected"].sum() >= 10
    warns = screening_warnings(s)
    assert warns and "relaxed" in warns[0] and warns[0].startswith("US:")
    assert s.attrs["effective_level"]["US"] < 0.9


def test_screen_never_silently_empty(esg_df):
    s = screen_universe(esg_df, ["US"], ["Utilities"], 0.5)
    assert s.empty and screening_warnings(s)


def test_sort_stock_table_region_industry_esg(esg_df):
    shuffled = esg_df.sample(frac=1.0, random_state=0)
    out = sort_stock_table(shuffled)
    assert list(out["region"].unique()) == ["US", "Eurozone"]  # REGIONS order
    us = out[out["region"] == "US"]
    assert list(us["industry"].unique()) == ["Technology", "Energy"]  # ICB order
    tech = us[us["industry"] == "Technology"]
    scores = tech["esg_score"].to_numpy()
    assert np.all(np.diff(scores[~np.isnan(scores)]) <= 0) and np.isnan(scores[-1])  # best first, NaN last
    assert tech["esg_rank_in_industry"].iloc[0] == 1
    assert tech["esg_percentile_in_industry"].iloc[0] == 1.0


def test_screen_output_sorted(esg_df):
    s = screen_universe(esg_df.sample(frac=1.0, random_state=1), ["US", "Eurozone"], None, 0.5, min_stocks=5)
    assert s.index.equals(sort_stock_table(s).index)
    assert set(s["zone"]) == {"US", "Europe"}


def test_esg_helpers(esg_df):
    assert esg_level_from_label("High") == 0.75
    assert available_sectors(esg_df, ["US"]) == ["Technology", "Energy"]
    s = screen_universe(esg_df, ["US"], None, 0.5, min_stocks=5)
    summ = universe_summary(s)
    assert (summ["n_before"] == 20).all() and (summ["n_after"] < 20).all()
    vec = esg_scores_vector(s)
    assert vec.index.equals(s.index[s["selected"]])
    idx = pd.bdate_range("2020-01-01", periods=3)
    rets = {"US": pd.DataFrame(0.01, index=idx, columns=esg_df.loc[esg_df.region == "US", "name"])}
    m = get_screened_returns(rets, s)
    assert list(m.columns) == list(vec.index) and all(c.startswith("US|") for c in m.columns)


# --------------------------------------------------------------------------- #
# Loader smoke tests on real files
# --------------------------------------------------------------------------- #
needs_raw = pytest.mark.skipif(not (RAW_DIR / "S&PCOMP.xlsx").exists(), reason="raw data not available")


@needs_raw
def test_load_sp500_benchmark():
    s = load_single_series("S&PCOMP.xlsx")
    assert s.name == "US"
    assert isinstance(s.index, pd.DatetimeIndex) and s.index.is_monotonic_increasing
    assert s.dtype == float and s.notna().all()
    assert s.index[0] == pd.Timestamp("1999-12-31") and s.index[-1] == pd.Timestamp("2026-11-16")


@needs_raw
def test_load_trus1mt_offset():
    y = load_single_series("TRUS1MT.xlsx")
    assert isinstance(y.index, pd.DatetimeIndex)
    assert y.index[0] == pd.Timestamp("1999-12-31")  # header offset handled: first row is a date
    assert np.isnan(y.iloc[0]) and y.notna().any()
    assert 0 <= y.dropna().max() < 10  # yield in percent
    rf = load_risk_free()
    # T-bill yields were slightly negative on a few days (2011-2020): kept as is
    assert rf["rf_daily"].notna().all() and rf["rf_daily"].min() > -0.001 / 252
    first = y.first_valid_index()
    assert rf.loc[first, "rf_daily"] == pytest.approx(y[first] / 100 / 252)
    assert (rf.loc[: first - pd.Timedelta(days=1), "rf_daily"] == 0).all()


def test_zones_split_pacific_and_emea(esg_df):
    df = esg_df.copy()
    us = df["region"] == "US"
    df.loc[~us, "region"] = "Pacific"
    df.loc[~us, "isin"] = np.where(np.arange((~us).sum()) % 2 == 0, "JP0000000001", "AU0000000001")
    s = screen_universe(df, ["Pacific"], None, 0.0)
    assert set(s["zone"]) == {"Asia", "Oceania"}
    assert list(dict.fromkeys(s["zone"])) == ["Asia", "Oceania"]  # ZONES order
    only_asia = screen_universe(df, ["Asia"], None, 0.0)
    assert set(only_asia["zone"]) == {"Asia"} and set(only_asia["country"]) == {"JP"}
    s2 = screen_universe(df, ["Oceania"], ["Energy"], 0.9, min_stocks=10)
    assert screening_warnings(s2)[0].startswith("Oceania:")
    with pytest.raises(ValueError):
        screen_universe(df, ["Atlantis"], None, 0.5)


def test_country_overrides_for_offshore_listings():
    tbl = pd.DataFrame({
        "name": ["CK ASSET HOLDINGS", "ALLEGRO", "NEPI ROCKCASTLE", "BHP GROUP", "QATAR NATIONAL BANK"],
        "region": ["Pacific", "EM EMEA", "EM EMEA", "Pacific", "EM EMEA"],
        "isin": ["KYG2177B1014", "LU2237380790", "NL0015000RT3", "AU000000BHP4", "QA0006929895"],
    })
    out = imp.assign_zones(tbl)
    assert out["country"].tolist() == ["HK", "PL", "ZA", "AU", "QA"]
    assert out["zone"].tolist() == ["Asia", "Emerging Europe", "Middle East & Africa", "Oceania",
                                    "Middle East & Africa"]


needs_processed = pytest.mark.skipif(
    not (PROCESSED_DIR / "esg_universe.parquet").exists(), reason="run compute_erc.py first"
)


@needs_processed
def test_investor_selection_on_processed_data():
    res = investor_selection(["US", "Pacific"], ["Energy", "Technology"], 0.75,
                             kinds=("returns_daily", "volatility", "returns_monthly"))
    sel = res["selected"]
    assert len(sel) > 0 and set(sel["region"]) == {"US", "Pacific"}
    assert set(sel["industry"]) <= {"Energy", "Technology"}
    assert sel.index.equals(sort_stock_table(sel).index)       # region -> industry -> ESG
    for kind in ("returns_daily", "volatility", "returns_monthly"):
        assert list(res[kind].columns) == list(sel.index)        # same order as the table
    assert res["returns_daily"].index.equals(res["volatility"].index)
    assert res["esg_scores"].index.equals(sel.index)
    us_tech = sel[(sel["region"] == "US") & (sel["industry"] == "Technology")]["esg_score"]
    assert us_tech.is_monotonic_decreasing
    # eligibility filter: every selected stock has a full window at the start
    res2 = investor_selection(["US"], None, 0.5, kinds=(), eligible_only=True)
    esg = imp.read_esg_universe()
    assert esg.loc[res2["selected"].index, "eligible_at_start"].all()


@needs_processed
def test_processed_universe_split_by_zone():
    esg = imp.read_esg_universe()
    assert esg["zone"].notna().all() and len(esg) == 1108
    counts = esg["zone"].value_counts()
    assert counts["Asia"] + counts["Oceania"] == 255
    assert counts["Middle East & Africa"] + counts["Emerging Europe"] == 137
    assert set(esg.loc[esg["zone"] == "Oceania", "country"]) <= {"AU", "NZ"}
    assert set(esg.loc[esg["zone"] == "Emerging Europe", "country"]) <= {"PL", "TR", "GR", "HU", "CZ", "RO"}
    assert esg.index.equals(sort_stock_table(esg).index)
    for zone in ("Asia", "Oceania", "Middle East & Africa", "Emerging Europe"):
        cols = list(imp.read_processed("returns_daily", zone).columns)
        assert cols == esg.loc[esg["zone"] == zone, "name"].tolist()


@needs_processed
def test_one_volatility_file_per_asset_class():
    from core.config import ASSET_CLASSES
    files = {f.name for f in PROCESSED_DIR.glob("*.parquet")}
    assert not any(f.startswith(("vol_ewma", "vol_realized", "vol_abs", "vol_rolling")) for f in files)
    for ac in ASSET_CLASSES:
        if ac == "rf":
            continue
        assert f"volatility_{ac}.parquet" in files
        vol = imp.read_processed("volatility", ac)
        ret = imp.read_processed("returns_daily", ac)
        assert vol.index.equals(ret.index) and list(vol.columns) == list(ret.columns)
