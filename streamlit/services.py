"""Data access and pure transformations for the Streamlit app.

Rules (see README / CLAUDE.md):
- read only ``data/processed/`` through the ``core.importation_data`` helpers;
- never touch ``data/raw/`` or run ``compute_erc.py``;
- never compute ERC weights, risk contributions or backtests here (future
  ``core`` work); this module only *describes* the available data.

Pure functions (no Streamlit import needed to test them) take DataFrames in and
return DataFrames out; the ``load_*`` wrappers add Streamlit caching.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from core.config import (
    BENCHMARK_LABELS,
    BENCHMARKS,
    DATA_START,
    ICB_INDUSTRIES,
    PORTFOLIO_START,
    REGION_LABELS,
    ZONES,
)
from core.esg import ESG_LEVELS, esg_level_from_label, investor_selection
from core.importation_data import read_esg_universe, read_processed

# Human-readable label of each investor zone (zone key -> "Asia (MSCI Pacific)").
ZONE_LABELS: dict[str, str] = {
    zone: f"{zone} ({REGION_LABELS[spec['source']].split('(')[-1].rstrip(')')})"
    for zone, spec in ZONES.items()
}


class DataUnavailableError(RuntimeError):
    """Processed data needed by the app is missing or unreadable."""


# --------------------------------------------------------------------------- #
# Cached loaders (read-only)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading stock universe…")
def load_universe() -> pd.DataFrame:
    """The ESG stock universe (``esg_universe.parquet``), indexed ``<zone>|<name>``."""
    try:
        return read_esg_universe()
    except FileNotFoundError as exc:
        raise DataUnavailableError(
            "`data/processed/esg_universe.parquet` was not found. "
            "A developer must run `python compute_erc.py` once to build the processed data."
        ) from exc
    except Exception as exc:  # corrupted file, missing parquet engine...
        raise DataUnavailableError(f"Could not read the stock universe: {exc}") from exc


@st.cache_data(show_spinner=False)
def load_series_names(asset_class: str) -> list[str]:
    """Column names of a small non-equity group (``bonds``, ``commodities``, ``benchmarks``)."""
    try:
        return list(read_processed("prices", asset_class).columns)
    except FileNotFoundError:
        return []
    except Exception as exc:
        raise DataUnavailableError(f"Could not read processed {asset_class} data: {exc}") from exc


@st.cache_data(show_spinner=False)
def load_data_window() -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """First and last date of the processed daily series (``None`` if unavailable).

    Uses the small bonds price file (all daily processed files share one calendar).
    """
    try:
        idx = read_processed("prices", "bonds").dropna(how="all").index
    except Exception:
        return None
    if idx.empty:
        return None
    return pd.Timestamp(idx.min()), pd.Timestamp(idx.max())


# --------------------------------------------------------------------------- #
# Pure transformations
# --------------------------------------------------------------------------- #
def coverage_by_zone(universe: pd.DataFrame) -> pd.DataFrame:
    """Per investor zone: stock count, start-eligible count, ESG coverage and median.

    ``esg_coverage`` is the share of stocks with a non-missing ESG score
    (denominator = all stocks of the zone). ``median_esg`` ignores missing
    scores. Zones absent from the file appear with zero stocks.
    """
    zones = list(ZONES)
    rows = []
    for zone in zones:
        df = universe[universe["zone"] == zone]
        n = len(df)
        eligible = int(df["eligible_at_start"].astype(bool).sum()) if "eligible_at_start" in df else None
        with_esg = int(df["esg_score"].notna().sum())
        rows.append(
            {
                "zone": zone,
                "source_index": REGION_LABELS[ZONES[zone]["source"]],
                "stocks": n,
                "eligible_at_start": eligible,
                "with_esg": with_esg,
                "esg_coverage": with_esg / n if n else float("nan"),
                "median_esg": float(df["esg_score"].median()) if with_esg else float("nan"),
                "industries": int(df["industry"].nunique()),
            }
        )
    return pd.DataFrame(rows).set_index("zone")


def universe_totals(universe: pd.DataFrame) -> dict[str, float | int | None]:
    """Headline counts for the whole equity universe."""
    n = len(universe)
    with_esg = int(universe["esg_score"].notna().sum())
    eligible = (
        int(universe["eligible_at_start"].astype(bool).sum())
        if "eligible_at_start" in universe.columns
        else None
    )
    return {
        "stocks": n,
        "eligible_at_start": eligible,
        "with_esg": with_esg,
        "esg_coverage": with_esg / n if n else float("nan"),
        "zones": int(universe["zone"].nunique()),
        "industries": int(universe["industry"].nunique()),
    }


def benchmark_status(benchmark_columns: list[str]) -> pd.DataFrame:
    """Availability of each benchmark declared in ``core.config``.

    A benchmark is *available* when its series is present in the processed
    benchmarks file, *missing* when configured but not found, and *planned*
    when the config has no source file for it yet (e.g. MSCI Pacific).
    """
    present = set(benchmark_columns)
    rows = []
    for key, label in BENCHMARK_LABELS.items():
        if key in present:
            status = "Available"
        elif key in BENCHMARKS:
            status = "Missing"
        else:
            status = "Planned"
        zones = [z for z, spec in ZONES.items() if spec["benchmark"] == key]
        rows.append(
            {
                "benchmark": label,
                "used_for": ", ".join(zones) if zones else "Commodities sleeve",
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def calendar_labels() -> dict[str, str]:
    """Fixed project dates from ``core.config`` (for display)."""
    return {"data_start": DATA_START, "portfolio_start": PORTFOLIO_START}


# --------------------------------------------------------------------------- #
# Investor screening (adapter around core.esg.investor_selection)
# --------------------------------------------------------------------------- #
# Fixed screening settings: shown to the user, not editable.
SCREENING_METHOD = "percentile"
MIN_STOCKS = 10

# What each questionnaire label really does with method="percentile".
ESG_LEVEL_DESCRIPTIONS: dict[str, str] = {
    "None": "No ESG screen: every candidate is kept, including stocks without an ESG score.",
    "Low": "Drops roughly the worst quarter of each zone × industry peer group (keeps scores ≥ 25th percentile).",
    "Medium": "Keeps roughly the better half of each zone × industry peer group (scores ≥ median).",
    "High": "Keeps roughly the best quarter of each zone × industry peer group (scores ≥ 75th percentile).",
    "Very high": "Keeps roughly the best 10% of each zone × industry peer group (scores ≥ 90th percentile).",
}

DEFAULT_PREFERENCES: dict = {
    "regions": list(ZONES),
    "all_industries": True,
    "sectors": [],
    "esg_label": "Medium",
    "eligible_only": True,
}


@dataclass(frozen=True)
class ScreeningParams:
    """Validated investor answers (hashable, so usable as a cache key)."""

    regions: tuple[str, ...]
    sectors: tuple[str, ...] | None  # None = all industries
    esg_label: str
    eligible_only: bool

    @property
    def esg_level(self) -> float:
        return esg_level_from_label(self.esg_label)


def _in_scope(universe: pd.DataFrame, regions, sectors) -> pd.DataFrame:
    df = universe[universe["zone"].isin(list(regions))]
    if sectors is not None:
        df = df[df["industry"].isin(list(sectors))]
    return df


def validate_preferences(
    regions: list[str] | None,
    all_industries: bool,
    sectors: list[str] | None,
    esg_label: str | None,
    eligible_only: bool,
    universe: pd.DataFrame | None = None,
) -> tuple[ScreeningParams | None, list[str]]:
    """Turn raw widget values into :class:`ScreeningParams`, or explain what is wrong.

    "All industries" maps to ``sectors=None`` (never an empty list). When the
    universe is given, a combination with no stock at all is rejected here
    with a readable message instead of reaching the screening.
    """
    errors: list[str] = []
    regions = list(regions or [])
    if not regions:
        errors.append("Select at least one investor region.")
    unknown = [r for r in regions if r not in ZONES]
    if unknown:
        errors.append(f"Unknown region(s): {', '.join(unknown)}.")
    if all_industries:
        sector_tuple = None
    else:
        chosen = list(sectors or [])
        if not chosen:
            errors.append("Select at least one industry, or switch on “All industries”.")
        bad = [s for s in chosen if s not in ICB_INDUSTRIES]
        if bad:
            errors.append(f"Unknown industry(ies): {', '.join(bad)}.")
        sector_tuple = tuple(s for s in ICB_INDUSTRIES if s in chosen)
    if esg_label not in ESG_LEVELS:
        errors.append("Choose an ESG ambition.")
    if errors:
        return None, errors

    params = ScreeningParams(
        regions=tuple(z for z in ZONES if z in regions),
        sectors=sector_tuple,
        esg_label=str(esg_label),
        eligible_only=bool(eligible_only),
    )
    if universe is not None:
        scope = _in_scope(universe, params.regions, params.sectors)
        if scope.empty:
            return None, ["No stock of the selected regions belongs to the selected industries."]
        if params.eligible_only and not scope["eligible_at_start"].astype(bool).any():
            return None, [
                f"None of these stocks is eligible on {PORTFOLIO_START}. "
                "Switch off “Eligible at portfolio start only” to explore them anyway."
            ]
    return params, []


def scope_counts(universe: pd.DataFrame, regions, sectors) -> dict[str, int]:
    """Live preview before screening: stocks in the chosen zones × industries."""
    df = _in_scope(universe, regions or [], sectors)
    return {
        "in_scope": len(df),
        "eligible": int(df["eligible_at_start"].astype(bool).sum()) if "eligible_at_start" in df else 0,
        "with_esg": int(df["esg_score"].notna().sum()),
    }


def industry_counts(universe: pd.DataFrame, regions) -> dict[str, int]:
    """Number of stocks per ICB industry across the chosen zones (0 if absent)."""
    df = universe[universe["zone"].isin(list(regions or []))]
    counts = df["industry"].value_counts()
    return {ind: int(counts.get(ind, 0)) for ind in ICB_INDUSTRIES}


def missing_industries_by_zone(universe: pd.DataFrame, regions) -> dict[str, list[str]]:
    """ICB industries with no stock in each chosen zone (only zones with gaps)."""
    out = {}
    for zone in regions or []:
        present = set(universe.loc[universe["zone"] == zone, "industry"])
        gaps = [i for i in ICB_INDUSTRIES if i not in present]
        if gaps:
            out[zone] = gaps
    return out


def effective_levels_table(effective: dict[str, float], requested: float) -> pd.DataFrame:
    """Requested vs effective ESG percentile cut per zone (relaxation made explicit)."""
    rows = []
    for zone, level in effective.items():
        if level is None or pd.isna(level):
            status = "No stocks in selected industries"
        elif level < requested - 1e-9:
            status = "Relaxed"
        else:
            status = "As requested"
        rows.append({"zone": zone, "requested": requested, "effective": level, "status": status})
    return pd.DataFrame(rows, columns=["zone", "requested", "effective", "status"])


def screening_funnel(universe: pd.DataFrame, params: ScreeningParams, screened: pd.DataFrame) -> dict[str, int]:
    """Counts at each step: in scope → eligible at start → candidates → ESG-selected.

    ``candidates`` are the stocks actually screened (= eligible ones when
    ``eligible_only``); ``selected_eligible`` counts ESG-selected stocks that
    are also eligible on the portfolio start date.
    """
    scope = _in_scope(universe, params.regions, params.sectors)
    selected = screened[screened["selected"]]
    elig = universe["eligible_at_start"].astype(bool)
    return {
        "in_scope": len(scope),
        "eligible_in_scope": int(elig.reindex(scope.index).sum()),
        "candidates": len(screened),
        "selected": len(selected),
        "selected_eligible": int(elig.reindex(selected.index).fillna(False).astype(bool).sum()),
    }


def run_screening(params: ScreeningParams, universe: pd.DataFrame) -> dict:
    """Run the real ``core.esg.investor_selection`` and package what the pages need.

    No time series are loaded here (``kinds=()``); the explorer reads them
    lazily for a few stocks only.
    """
    res = investor_selection(
        list(params.regions),
        list(params.sectors) if params.sectors is not None else None,
        params.esg_level,
        kinds=(),
        method=SCREENING_METHOD,
        min_stocks=MIN_STOCKS,
        eligible_only=params.eligible_only,
        esg_df=universe,
    )
    screened = res["universe"]
    effective = dict(screened.attrs.get("effective_level", {}))
    # Re-attach start eligibility (dropped by the core output columns), by asset id.
    screened = screened.copy()
    screened["eligible_at_start"] = (
        universe["eligible_at_start"].astype(bool).reindex(screened.index).fillna(False).astype(bool)
    )
    return {
        "params": params,
        "universe": screened,
        "selected": screened[screened["selected"]],
        "summary": res["summary"],
        "warnings": list(res["warnings"]),
        "effective_level": effective,
        "effective_table": effective_levels_table(effective, params.esg_level),
        "funnel": screening_funnel(universe, params, screened),
    }


@st.cache_data(show_spinner="Screening the universe…", max_entries=64)
def cached_screening(params: ScreeningParams) -> dict:
    """Cached :func:`run_screening` on the processed universe (key = the answers)."""
    return run_screening(params, load_universe())
