"""Tests for the Streamlit app's pure data transformations (``streamlit/services.py``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "streamlit"))  # app helpers (no __init__.py on purpose)

services = pytest.importorskip("services")
from core.config import PROCESSED_DIR, ZONES  # noqa: E402


def _toy_universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone": ["US", "US", "US", "Oceania"],
            "industry": ["Technology", "Technology", "Energy", "Energy"],
            "esg_score": [80.0, np.nan, 40.0, 60.0],
            "eligible_at_start": [True, False, True, True],
        },
        index=["US|A", "US|B", "US|C", "Oceania|D"],
    )


def test_coverage_by_zone_counts_and_denominators():
    cov = services.coverage_by_zone(_toy_universe())
    assert list(cov.index) == list(ZONES)  # every zone, canonical order
    us = cov.loc["US"]
    assert us["stocks"] == 3 and us["eligible_at_start"] == 2 and us["with_esg"] == 2
    assert us["esg_coverage"] == pytest.approx(2 / 3)  # denominator = all stocks
    assert us["median_esg"] == pytest.approx(60.0)  # NaN ignored
    empty = cov.loc["Europe"]
    assert empty["stocks"] == 0 and np.isnan(empty["esg_coverage"]) and np.isnan(empty["median_esg"])


def test_universe_totals():
    t = services.universe_totals(_toy_universe())
    assert t["stocks"] == 4 and t["with_esg"] == 3 and t["eligible_at_start"] == 3
    assert t["esg_coverage"] == pytest.approx(0.75)


def test_benchmark_status_flags_planned_and_missing():
    status = services.benchmark_status(["US", "Commodities"]).set_index("benchmark")["status"]
    assert status["S&P 500"] == "Available"
    assert status["MSCI EMU"] == "Missing"  # configured but absent from the file
    assert status["MSCI Pacific"] == "Planned"  # no source file in config


@pytest.mark.skipif(not (PROCESSED_DIR / "esg_universe.parquet").exists(), reason="processed data absent")
def test_coverage_matches_real_universe():
    from core.importation_data import read_esg_universe

    u = read_esg_universe()
    cov = services.coverage_by_zone(u)
    assert cov["stocks"].sum() == len(u)
    assert (cov["eligible_at_start"] <= cov["stocks"]).all()


# --------------------------------------------------------------------------- #
# Investor Preferences adapter
# --------------------------------------------------------------------------- #
def test_validate_all_industries_maps_to_none():
    params, errors = services.validate_preferences(["Europe", "US"], True, ["Energy"], "High", True)
    assert errors == []
    assert params.sectors is None  # never an empty list
    assert params.regions == ("US", "Europe")  # canonical ZONES order
    assert params.esg_level == pytest.approx(0.75)


@pytest.mark.parametrize(
    "regions, all_ind, sectors, label",
    [([], True, [], "High"), (["US"], False, [], "High"), (["US"], False, ["Crypto"], "High"),
     (["Mars"], True, [], "High"), (["US"], True, [], None)],
)
def test_validate_rejects_bad_answers(regions, all_ind, sectors, label):
    params, errors = services.validate_preferences(regions, all_ind, sectors, label, True)
    assert params is None and errors


def test_validate_rejects_empty_intersection():
    u = _toy_universe()
    params, errors = services.validate_preferences(["Oceania"], False, ["Technology"], "Low", False, u)
    assert params is None and "No stock" in errors[0]


def test_scope_and_industry_counts():
    u = _toy_universe()
    assert services.scope_counts(u, ["US"], None) == {"in_scope": 3, "eligible": 2, "with_esg": 2}
    assert services.industry_counts(u, ["US"])["Technology"] == 2
    gaps = services.missing_industries_by_zone(u, ["Oceania"])
    assert "Technology" in gaps["Oceania"] and "Energy" not in gaps["Oceania"]


def test_effective_levels_table_flags_relaxation():
    t = services.effective_levels_table({"US": 0.75, "Oceania": 0.5, "Europe": float("nan")}, 0.75)
    status = t.set_index("zone")["status"]
    assert status["US"] == "As requested"
    assert status["Oceania"] == "Relaxed"
    assert status["Europe"].startswith("No stocks")


@pytest.mark.skipif(not (PROCESSED_DIR / "esg_universe.parquet").exists(), reason="processed data absent")
def test_run_screening_uses_core_and_counts_are_consistent():
    from core.esg import investor_selection
    from core.importation_data import read_esg_universe

    u = read_esg_universe()
    params, _ = services.validate_preferences(["US", "Emerging Europe"], True, [], "High", True, u)
    res = services.run_screening(params, u)
    core = investor_selection(["US", "Emerging Europe"], None, 0.75, kinds=(), eligible_only=True, esg_df=u)
    assert list(res["selected"].index) == list(core["selected"].index)  # same result as core
    f = res["funnel"]
    assert f["selected"] <= f["candidates"] == f["eligible_in_scope"] <= f["in_scope"]
    assert res["universe"]["eligible_at_start"].all()  # eligible_only honoured
    assert set(res["effective_level"]) == {"US", "Emerging Europe"}


@pytest.mark.skipif(not (PROCESSED_DIR / "esg_universe.parquet").exists(), reason="processed data absent")
def test_run_screening_reports_relaxation():
    from core.importation_data import read_esg_universe

    u = read_esg_universe()
    params, _ = services.validate_preferences(["Emerging Europe"], False, ["Utilities", "Energy"], "Very high", False, u)
    res = services.run_screening(params, u)
    assert res["warnings"]
    assert (res["effective_table"]["status"] == "Relaxed").all()
