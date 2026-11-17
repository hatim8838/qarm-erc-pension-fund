"""Investor screening of the equity universe: region, sector and ESG level.

This drives the website questionnaire: the investor picks region(s), ICB
industry(ies) and how ESG-friendly the portfolio should be.

Regions are the six investor zones of ``core.config.ZONES``:
``US``, ``Europe``, ``Asia``, ``Oceania``, ``Middle East & Africa``,
``Emerging Europe``. Source-index keys are accepted too and expand to their
zones (``"Pacific"`` -> Asia + Oceania, ``"EM EMEA"`` -> Middle East & Africa +
Emerging Europe, ``"Eurozone"`` -> Europe).

The stock table expected here is ``data/processed/esg_universe.parquet`` (or
``load_all()["esg"]``): indexed by ``"<zone>|<name>"`` with at least
``name, region, industry, sector, esg_score, isin`` (``zone`` and ``country``
are added from the ISIN when missing).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core.config import ASSET_ID_SEP, EQUITY_ASSET_CLASS, ICB_INDUSTRIES, REGIONS, ZONES
from core.importation_data import assign_zones, read_esg_universe, read_processed, sort_stock_table

logger = logging.getLogger(__name__)

ESG_LEVELS: dict[str, float] = {"None": 0.0, "Low": 0.25, "Medium": 0.5, "High": 0.75, "Very high": 0.9}
RELAX_STEP = 0.05
OUTPUT_COLUMNS = ["name", "zone", "country", "region", "industry", "sector", "esg_score", "isin"]


def esg_level_from_label(label: str) -> float:
    """Map a questionnaire label (``"None"/"Low"/"Medium"/"High"/"Very high"``) to [0, 1]."""
    try:
        return ESG_LEVELS[label]
    except KeyError:
        raise ValueError(f"Unknown ESG level {label!r}; expected one of {list(ESG_LEVELS)}") from None


def resolve_zones(regions: list[str]) -> list[str]:
    """Investor zones for a list of zones and/or source-index keys (ZONES order)."""
    if not regions:
        raise ValueError("Select at least one region")
    zones: set[str] = set()
    for r in regions:
        if r in ZONES:
            zones.add(r)
        elif r in REGIONS:
            zones.update(z for z, spec in ZONES.items() if spec["source"] == r)
        else:
            raise ValueError(f"Unknown region {r!r}; expected among {list(ZONES)}")
    return [z for z in ZONES if z in zones]


def _prepare(esg_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure ``name``, ``zone``, ``country`` columns and ``"<zone>|<name>"`` ids."""
    df = esg_df.copy()
    if "name" not in df.columns:
        df["name"] = df.index.astype(str).str.split(ASSET_ID_SEP, n=1).str[-1]
    if "zone" not in df.columns or "country" not in df.columns:
        df = assign_zones(df)
    df.index = pd.Index(df["zone"].astype(str) + ASSET_ID_SEP + df["name"].astype(str), name="asset_id")
    return df


def _select(group_scores: pd.DataFrame, level: float, method: str) -> pd.Series:
    """Boolean selection for one zone at ESG level ``level``."""
    scores = group_scores["esg_score"]
    if level <= 0:
        return pd.Series(True, index=group_scores.index)
    if method == "threshold":
        return scores >= 100.0 * level
    # best-in-class: per industry, keep scores >= the level-quantile of that industry
    cut = group_scores.groupby("industry")["esg_score"].transform(lambda s: s.quantile(level))
    return scores >= cut  # NaN scores -> False


def screen_universe(
    esg_df: pd.DataFrame,
    regions: list[str],
    sectors: list[str] | None,
    esg_level: float,
    min_stocks: int = 10,
    method: str = "percentile",
) -> pd.DataFrame:
    """Screen the stock universe on region, ICB industry and ESG level.

    Parameters
    ----------
    esg_df : stock table (see module docstring).
    regions : investor zones (``ZONES`` keys); source-index keys expand to
        their zones (see :func:`resolve_zones`).
    sectors : ICB industry names to keep; ``None`` = all.
    esg_level : in [0, 1], how ESG-friendly (see :data:`ESG_LEVELS`).
    min_stocks : minimum number of selected stocks per zone. If the cut
        leaves fewer, the level is relaxed for that zone by steps of 0.05
        until enough stocks survive (or the level reaches 0), with a warning.
    method : ``"percentile"`` (default, best-in-class within each
        zone x industry: keep ``esg_score >= quantile(esg_level)`` of the
        group) or ``"threshold"`` (keep ``esg_score >= 100 * esg_level``).

    Missing ESG scores are kept only when the (effective) level is 0.

    Returns
    -------
    DataFrame indexed by ``"<zone>|<name>"`` with columns
    ``name, zone, country, region, industry, sector, esg_score, isin, selected``
    containing all candidate stocks of the chosen zones/sectors, sorted by
    zone -> ICB industry -> ESG score (best first); ``selected`` flags the
    ones that pass the ESG screen. Warnings (relaxation, too few stocks) are in
    ``result.attrs["warnings"]`` and logged; the effective level per zone is
    in ``result.attrs["effective_level"]``.
    """
    if not 0.0 <= esg_level <= 1.0:
        raise ValueError("esg_level must be in [0, 1]")
    if method not in {"percentile", "threshold"}:
        raise ValueError("method must be 'percentile' or 'threshold'")
    zones = resolve_zones(regions)
    if sectors is not None:
        bad = set(sectors) - set(ICB_INDUSTRIES)
        if bad:
            raise ValueError(f"Unknown ICB industries {sorted(bad)}")

    df = _prepare(esg_df)
    df = df[df["zone"].isin(zones)]
    if sectors is not None:
        df = df[df["industry"].isin(sectors)]
    df = df[OUTPUT_COLUMNS].copy()
    df = df.loc[sort_stock_table(df).index]  # zone -> industry -> ESG (best first)
    df["selected"] = False

    warnings: list[str] = []
    effective: dict[str, float] = {}
    for zone in zones:
        mask = df["zone"] == zone
        group = df.loc[mask]
        if group.empty:
            warnings.append(f"{zone}: no stocks in the selected sectors; region left out of the universe.")
            effective[zone] = np.nan
            continue
        target = min(min_stocks, len(group))
        level = esg_level
        sel = _select(group, level, method)
        n_pass = int(sel.sum())
        while sel.sum() < target and level > 0:
            level = max(0.0, round(level - RELAX_STEP, 10))
            sel = _select(group, level, method)
        if level < esg_level:
            too_few = (
                f"only {len(group)} stocks exist in the selected sectors"
                if len(group) < min_stocks
                else f"the minimum is {min_stocks} stocks"
            )
            warnings.append(
                f"{zone}: {n_pass} stock(s) pass the ESG level {esg_level:.2f} but {too_few}; "
                f"the ESG cut was relaxed to {level:.2f}, keeping {int(sel.sum())} stocks."
            )
        elif len(group) < min_stocks:
            warnings.append(
                f"{zone}: only {len(group)} stocks exist in the selected sectors "
                f"(minimum {min_stocks}); {int(sel.sum())} pass the ESG level {esg_level:.2f}."
            )
        df.loc[mask, "selected"] = sel.to_numpy()
        effective[zone] = level

    for w in warnings:
        logger.warning(w)
    df.attrs["warnings"] = warnings
    df.attrs["effective_level"] = effective
    df.attrs["esg_level"] = esg_level
    df.attrs["method"] = method
    return df


def screening_warnings(screened: pd.DataFrame) -> list[str]:
    """Warnings produced by :func:`screen_universe` (empty list if none)."""
    return list(screened.attrs.get("warnings", []))


def universe_summary(screened: pd.DataFrame) -> pd.DataFrame:
    """Counts and average ESG score by zone x industry, before vs after screening.

    Rows follow the app order (ZONES order, then ICB order).
    """
    screened = screened.loc[sort_stock_table(screened).index]
    sel = screened[screened["selected"]]
    keys = ["zone", "industry"]
    before = screened.groupby(keys, sort=False).agg(
        n_before=("esg_score", "size"), avg_esg_before=("esg_score", "mean")
    )
    after = sel.groupby(keys, sort=False).agg(
        n_after=("esg_score", "size"), avg_esg_after=("esg_score", "mean")
    )
    out = before.join(after, how="left")
    out.index.names = ["region", "industry"]
    out["n_after"] = out["n_after"].fillna(0).astype(int)
    return out[["n_before", "n_after", "avg_esg_before", "avg_esg_after"]].round(2)


def available_sectors(esg_df: pd.DataFrame, regions: list[str]) -> list[str]:
    """ICB industries present in the chosen zones (in the canonical ICB order)."""
    df = _prepare(esg_df)
    present = set(df.loc[df["zone"].isin(resolve_zones(regions)), "industry"].dropna())
    return [s for s in ICB_INDUSTRIES if s in present] + sorted(present - set(ICB_INDUSTRIES))


def esg_scores_vector(stocks: pd.DataFrame, fill: str | None = None) -> pd.Series:
    """ESG scores aligned on ``"<zone>|<name>"`` ids, for ESG risk budgets.

    If ``stocks`` has a ``selected`` column only selected stocks are returned.
    ``fill="median"`` replaces missing scores by the zone x industry median
    (then the zone median); default ``None`` leaves them NaN.
    """
    df = _prepare(stocks)
    if "selected" in df.columns:
        df = df[df["selected"]]
    scores = df["esg_score"].astype(float).copy()
    if fill == "median":
        med = df.groupby(["zone", "industry"])["esg_score"].transform("median")
        scores = scores.fillna(med).fillna(df.groupby("zone")["esg_score"].transform("median"))
    elif fill is not None:
        raise ValueError("fill must be None or 'median'")
    scores.name = "esg_score"
    return scores


def get_screened_returns(
    returns_by_zone: dict[str, pd.DataFrame], screened: pd.DataFrame
) -> pd.DataFrame:
    """Return matrix of the selected stocks only, from frames keyed by zone.

    Columns are ``"<zone>|<stock>"`` to avoid name clashes across zones.
    Stocks without a series are skipped with a warning.
    """
    sel = screened[screened["selected"]] if "selected" in screened.columns else screened
    cols = {}
    missing = []
    for asset_id, row in sel.iterrows():
        zone_df = returns_by_zone.get(row["zone"])
        if zone_df is not None and row["name"] in zone_df.columns:
            cols[asset_id] = zone_df[row["name"]]
        else:
            missing.append(asset_id)
    if missing:
        logger.warning("%d selected stocks have no return series: %s", len(missing), missing[:10])
    if not cols:
        return pd.DataFrame()
    out = pd.concat(cols, axis=1)
    out.columns.name = "asset_id"
    return out


def investor_selection(
    regions: list[str],
    sectors: list[str] | None,
    esg_level: float,
    kinds: tuple[str, ...] = ("returns_daily", "volatility"),
    method: str = "percentile",
    min_stocks: int = 10,
    eligible_only: bool = False,
    esg_df: pd.DataFrame | None = None,
) -> dict:
    """Everything the app needs after the investor's three answers, in one call.

    Reads ``data/processed/`` only. Steps: (optionally) keep stocks eligible at
    the portfolio start, :func:`screen_universe`, then read the requested
    outputs for the selected stocks only (one zone file at a time).

    Parameters
    ----------
    regions, sectors, esg_level, method, min_stocks : see :func:`screen_universe`.
    kinds : outputs to return for the selected stocks (keys of
        ``core.config.PROCESSED_FILES``).
    eligible_only : drop stocks without a full estimation window at
        ``PORTFOLIO_START`` before screening (``eligible_at_start``).
    esg_df : stock table to use instead of ``esg_universe.parquet``.

    Returns
    -------
    dict with ``universe`` (screened table, sorted zone -> industry -> ESG),
    ``selected`` (the selected rows), ``warnings``, ``summary``
    (:func:`universe_summary`), ``esg_scores`` (aligned scores) and one
    DataFrame per ``kind`` with columns ``"<zone>|<stock>"`` in the same
    order as ``selected``.
    """
    esg_df = read_esg_universe() if esg_df is None else esg_df
    if eligible_only and "eligible_at_start" in esg_df.columns:
        esg_df = esg_df[esg_df["eligible_at_start"].astype(bool)]
    screened = screen_universe(esg_df, regions, sectors, esg_level, min_stocks=min_stocks, method=method)
    selected = screened[screened["selected"]]
    out = {
        "universe": screened,
        "selected": selected,
        "warnings": screening_warnings(screened),
        "summary": universe_summary(screened),
        "esg_scores": esg_scores_vector(screened),
    }
    for kind in kinds:
        frames = []
        for zone in resolve_zones(regions):
            names = selected.loc[selected["zone"] == zone, "name"].tolist()
            if not names:
                continue
            df = read_processed(kind, EQUITY_ASSET_CLASS[zone], columns=names)
            df.columns = [f"{zone}{ASSET_ID_SEP}{n}" for n in df.columns]
            frames.append(df)
        out[kind] = pd.concat(frames, axis=1) if frames else pd.DataFrame()
        out[kind].columns.name = "asset_id"
    return out
