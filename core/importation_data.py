"""Loading and cleaning of the Datastream exports in ``data/raw/``.

Public API
----------
- :func:`load_single_series`  one-column Datastream file -> ``pd.Series``
- :func:`load_constituents`   constituent price grid -> dates x stocks ``pd.DataFrame``
- :func:`load_esg`            ICB sector / ESG score table for a region
- :func:`load_risk_free`      daily risk-free rate from the 1M T-bill yield
- :func:`clean_prices`        the cleaning rules (non-numeric, stale prices, short holes)
- :func:`match_prices_to_esg` align constituent price columns with ESG names
- :func:`load_all`            everything above, read from the Excel files

Nothing in ``data/raw/`` is ever written to.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from core.config import (
    ASSET_ID_SEP,
    BENCHMARKS,
    BONDS,
    COMMODITIES,
    COMMODITY_BENCHMARK,
    COUNTRY_OVERRIDES,
    COUNTRY_ZONE,
    EQUITY_ASSET_CLASS,
    PROCESSED_DIR,
    PROCESSED_FILES,
    RAW_DIR,
    ICB_INDUSTRIES,
    REGIONS,
    RISK_FREE,
    ROOT_DIR,
    SOURCE_ASSET_CLASS,
    ZONES,
)

# Re-exported so that ``from core.importation_data import REGIONS`` works too.
__all__ = [
    "REGIONS",
    "BONDS",
    "COMMODITIES",
    "COMMODITY_BENCHMARK",
    "RISK_FREE",
    "BENCHMARKS",
    "load_single_series",
    "load_constituents",
    "load_esg",
    "load_risk_free",
    "clean_prices",
    "match_prices_to_esg",
    "sort_stock_table",
    "assign_zones",
    "load_all",
    "read_processed",
    "read_esg_universe",
]

logger = logging.getLogger(__name__)

PRICE_SUFFIX = " - TOT RETURN IND"
MISSING_TOKENS = {"NA", "", "N/A", "NAN"}  # Datastream "not available" (not an error)

STALE_MIN_RUN = 10   # >= this many identical prices at the start/end of a series is stale
MAX_FFILL = 5        # forward-fill interior holes of at most this many days

ESG_COLUMNS = {
    "ISIN CODE": "isin",
    "ICB INDUSTRY NAME": "industry",
    "ICB INDUSTRY CODE": "industry_code",
    "ICB SECTOR NAME": "sector",
    "ICB SECTOR CODE": "sector_code",
    "ESG Score": "esg_score",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _raw_path(file: str | Path) -> Path:
    path = Path(file)
    return path if path.is_absolute() or path.exists() else RAW_DIR / path


def _key_for_file(file: str) -> str | None:
    """Return the universe key (e.g. ``"US Aggregate"``) that points to ``file``."""
    name = Path(file).name
    for mapping in (BONDS, COMMODITIES, BENCHMARKS):
        for key, fname in mapping.items():
            if fname == name:
                return key
    if name == RISK_FREE:
        return "rf"
    return None


def _coerce_numeric(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Coerce an object frame to float.

    Returns the float frame and, per column, the number of *error* entries
    (non-numeric strings such as ``$$ER``) that became NaN. Datastream's ``NA``
    marker means "not available" and is not counted as an error.
    """
    numeric = raw.apply(pd.to_numeric, errors="coerce").astype(float)
    was_text = raw.notna() & numeric.isna()
    is_missing_token = raw.apply(
        lambda col: col.astype(str).str.strip().str.upper().isin(MISSING_TOKENS)
    )
    errors = (was_text & ~is_missing_token).sum()
    return numeric, errors.astype(int)


def _dedupe_names(names: list[str]) -> list[str]:
    """Make column names unique by appending `` (2)``, `` (3)``... to repeats."""
    seen: dict[str, int] = {}
    out = []
    for name in names:
        if name in seen:
            seen[name] += 1
            new = f"{name} ({seen[name]})"
            logger.warning("Duplicate column name %r renamed to %r", name, new)
            out.append(new)
        else:
            seen[name] = 1
            out.append(name)
    return out


def _strip_suffix(name: str) -> str:
    name = str(name).strip()
    if name.upper().endswith(PRICE_SUFFIX):
        name = name[: -len(PRICE_SUFFIX)]
    return name.strip()


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_single_series(file: str | Path, name: str | None = None) -> pd.Series:
    """Load a single-series Datastream export.

    Layout: a ``Name`` header row (column 0 = ``"Name"``, column 1 = series
    description) followed by ``date, value`` rows. The header row is located
    by searching for ``"Name"`` in column 0, which handles ``TRUS1MT.xlsx``
    whose header is offset by one (empty) row.

    Parameters
    ----------
    file : file name inside ``data/raw/`` (or a path).
    name : series name; defaults to the universe key of the file
        (e.g. ``"US Aggregate"``), else the Datastream description.

    Returns
    -------
    pd.Series of floats on a sorted DatetimeIndex. Non-numeric entries are NaN.
    Leading NaNs are kept (e.g. UAGG before its 2003 launch).
    """
    path = _raw_path(file)
    raw = pd.read_excel(path, header=None, sheet_name=0)
    first_col = raw.iloc[:, 0].astype(str).str.strip()
    header_rows = np.flatnonzero(first_col.eq("Name").to_numpy())
    if len(header_rows) == 0:
        raise ValueError(f"No 'Name' header row found in {path.name}")
    h = int(header_rows[0])
    description = str(raw.iat[h, 1])

    body = raw.iloc[h + 1 :, :2].copy()
    body.columns = ["date", "value"]
    body["date"] = pd.to_datetime(body["date"], errors="coerce")
    body = body.dropna(subset=["date"])
    values, errors = _coerce_numeric(body[["value"]])

    series = pd.Series(values["value"].to_numpy(), index=pd.DatetimeIndex(body["date"], name="date"))
    series = series[~series.index.duplicated(keep="last")].sort_index()
    series.name = name or _key_for_file(path.name) or description
    if errors.iloc[0]:
        logger.info("%s: %d non-numeric entries coerced to NaN", path.name, errors.iloc[0])
    logger.debug("Loaded %s (%s): %d rows, header at row %d", path.name, description, len(series), h)
    return series


def _read_constituents_raw(region: str) -> tuple[pd.DataFrame, pd.Series]:
    """Read a constituent Excel grid. Returns (float prices, error counts per column)."""
    if region not in REGIONS:
        raise KeyError(f"Unknown region {region!r}; expected one of {list(REGIONS)}")
    path = _raw_path(REGIONS[region]["prices"])
    logger.info("Reading %s (this can take a while for large files)...", path.name)
    raw = pd.read_excel(path, header=None, sheet_name=0)

    names = _dedupe_names([_strip_suffix(n) for n in raw.iloc[0, 1:].tolist()])
    start = 1
    # Row 1 is a CURRENCY row in most files, but not in LS&PCOMP.xlsx.
    if str(raw.iat[1, 0]).strip().upper() == "CURRENCY":
        currencies = set(raw.iloc[1, 1:].dropna().astype(str).str.strip())
        if currencies - {"U$"}:
            logger.warning("%s: non-USD currencies found: %s", path.name, currencies)
        start = 2

    body = raw.iloc[start:].copy()
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce")
    body = body.loc[dates.notna()]
    dates = pd.DatetimeIndex(dates[dates.notna()], name="date")

    grid = body.iloc[:, 1:]
    grid.columns = names
    grid.index = dates
    prices, errors = _coerce_numeric(grid)
    prices = prices[~prices.index.duplicated(keep="last")].sort_index()
    prices.columns.name = "stock"
    return prices, errors


def load_constituents(region: str) -> pd.DataFrame:
    """Load the constituent total-return-index grid of ``region``.

    Returns
    -------
    pd.DataFrame, dates x stocks, floats. Column names have the
    ``" - TOT RETURN IND"`` suffix stripped. Stocks are NaN before listing.
    The data are *not* cleaned here (see :func:`clean_prices`).
    """
    prices, errors = _read_constituents_raw(region)
    if errors.sum():
        logger.info("%s: %d non-numeric error entries coerced to NaN", region, int(errors.sum()))
    return prices


def load_esg(region: str) -> pd.DataFrame:
    """Load the ICB sector / ESG score table of ``region``.

    Returns
    -------
    pd.DataFrame indexed by stock name (Datastream ``NAME``), with columns
    ``isin, industry, industry_code, sector, sector_code, esg_score, region``.
    Missing ESG scores are NaN.
    """
    if region not in REGIONS:
        raise KeyError(f"Unknown region {region!r}; expected one of {list(REGIONS)}")
    path = _raw_path(REGIONS[region]["esg"])
    df = pd.read_excel(path, sheet_name=0)
    df["NAME"] = df["NAME"].astype(str).str.strip()
    if df["NAME"].duplicated().any():
        dups = df.loc[df["NAME"].duplicated(), "NAME"].tolist()
        logger.warning("%s: duplicate ESG names %s; renaming", region, dups)
        df["NAME"] = _dedupe_names(df["NAME"].tolist())
    out = df.set_index("NAME")[list(ESG_COLUMNS)].rename(columns=ESG_COLUMNS)
    out.index.name = "name"
    out["esg_score"] = pd.to_numeric(out["esg_score"], errors="coerce").astype(float)
    out["industry_code"] = pd.to_numeric(out["industry_code"], errors="coerce").astype("Int64")
    out["sector_code"] = pd.to_numeric(out["sector_code"], errors="coerce").astype("Int64")
    for col in ("isin", "industry", "sector"):
        out[col] = out[col].astype(str).str.strip()
    out["region"] = region
    logger.info(
        "%s ESG: %d stocks, %d missing ESG scores", region, len(out), int(out["esg_score"].isna().sum())
    )
    return out


def load_risk_free(calendar: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    """Daily risk-free rate from the US 1-month T-bill yield (``TRUS1MT``).

    ``rf_t = TRUS1MT_t / 100 / 252`` (simple daily rate). Missing days are
    forward-filled; dates before the first available yield get ``rf = 0``.

    Parameters
    ----------
    calendar : dates to align on (typically the union of the other asset
        classes' calendars). Defaults to the file's own dates.

    Returns
    -------
    pd.DataFrame with columns ``yield_pct`` (raw, annual %) and ``rf_daily``.
    """
    y = load_single_series(RISK_FREE, name="yield_pct")
    if calendar is not None:
        y = y.reindex(y.index.union(calendar))
    first = y.first_valid_index()
    y_ff = y.ffill()
    n_before = int(y_ff.isna().sum())
    if n_before:
        logger.info(
            "Risk-free: %d days before the first T-bill yield (%s) set to rf = 0",
            n_before, None if first is None else first.date(),
        )
    rf = (y_ff / 100.0 / 252.0).fillna(0.0)
    out = pd.DataFrame({"yield_pct": y_ff, "rf_daily": rf})
    if calendar is not None:
        out = out.reindex(calendar)
    out.index.name = "date"
    return out


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def _run_length_at_start(values: np.ndarray) -> int:
    """Length of the run of identical values at the start of a NaN-free array."""
    if len(values) == 0:
        return 0
    diff = np.flatnonzero(values != values[0])
    return int(diff[0]) if len(diff) else len(values)


def _fill_short_holes(col: np.ndarray, max_len: int) -> tuple[np.ndarray, int]:
    """Forward-fill interior NaN runs of length <= ``max_len``; return filled, # filled."""
    isna = np.isnan(col)
    valid = np.flatnonzero(~isna)
    if len(valid) < 2:
        return col, 0
    out = col.copy()
    n_filled = 0
    first, last = valid[0], valid[-1]
    i = first
    while i <= last:
        if isna[i]:
            j = i
            while isna[j]:
                j += 1
            if j - i <= max_len:
                out[i:j] = out[i - 1]
                n_filled += j - i
            i = j
        else:
            i += 1
    return out, n_filled


def clean_prices(
    prices: pd.DataFrame | pd.Series,
    name: str = "",
    stale_min_run: int = STALE_MIN_RUN,
    max_ffill: int = MAX_FFILL,
    errors: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the cleaning rules to a price / total-return-index frame.

    Rules (applied in this order, each one logged):

    1. Non-numeric entries -> NaN (also done at load time; ``errors`` passes the
       load-time error counts through to the report); non-positive prices -> NaN.
    2. Drop dates where every series is NaN (and weekend dates), keeping a common
       business-day calendar for the asset class.
    3. Stale prices: a run of >= ``stale_min_run`` identical prices at the start
       of a series is set to NaN (placeholder before real trading starts); at the
       end of a series the repeats after the first value of the run are set to NaN
       (Datastream repeats the last genuine price after delisting). Short flat
       runs in the middle are untouched.
    4. Forward-fill interior holes of at most ``max_ffill`` days; longer gaps stay
       NaN. Leading/trailing NaNs are never filled.

    Returns
    -------
    (cleaned prices as DataFrame, per-series report DataFrame)
    """
    df = prices.to_frame() if isinstance(prices, pd.Series) else prices.copy()
    df = df.apply(pd.to_numeric, errors="coerce").astype(float)
    report = pd.DataFrame(index=df.columns)
    report.index.name = "series"
    report["n_non_numeric"] = (
        errors.reindex(df.columns).fillna(0).astype(int) if errors is not None else 0
    )

    # Rule 1: non-positive prices
    nonpos = df <= 0
    report["n_non_positive"] = nonpos.sum().astype(int)
    df = df.mask(nonpos)

    # Rule 2: drop weekend dates and dates with no data at all
    n_dates = len(df)
    df = df.loc[df.index.dayofweek < 5]
    df = df.dropna(how="all")
    n_dropped_dates = n_dates - len(df)

    # Rule 3: stale runs at the start / end of each series
    arr = df.to_numpy(copy=True)
    lead = np.zeros(arr.shape[1], dtype=int)
    trail = np.zeros(arr.shape[1], dtype=int)
    for j in range(arr.shape[1]):
        col = arr[:, j]
        valid = np.flatnonzero(~np.isnan(col))
        if len(valid) == 0:
            continue
        v = col[valid]
        run = _run_length_at_start(v)
        if run >= stale_min_run:
            col[valid[:run]] = np.nan
            lead[j] = run
            valid, v = valid[run:], v[run:]
        if len(v):
            run_end = _run_length_at_start(v[::-1])
            if run_end >= stale_min_run:
                # keep the first value of the trailing run (last genuine price)
                col[valid[len(v) - run_end + 1 :]] = np.nan
                trail[j] = run_end - 1
    report["n_stale_leading"] = lead
    report["n_stale_trailing"] = trail

    # Rule 4: forward-fill short interior holes only
    filled = np.zeros(arr.shape[1], dtype=int)
    for j in range(arr.shape[1]):
        arr[:, j], filled[j] = _fill_short_holes(arr[:, j], max_ffill)
    report["n_ffilled"] = filled

    out = pd.DataFrame(arr, index=df.index, columns=df.columns)
    out.index.name = "date"
    out = out.dropna(how="all")

    report["n_obs"] = out.notna().sum().astype(int)
    report["n_nan"] = out.isna().sum().astype(int)
    report["first_valid"] = [out[c].first_valid_index() for c in out.columns]
    report["last_valid"] = [out[c].last_valid_index() for c in out.columns]

    tag = f"[{name}] " if name else ""
    logger.info(
        "%sclean_prices: %d series | non-numeric->NaN: %d | non-positive->NaN: %d | "
        "dates dropped (weekend/all-NaN): %d | stale leading: %d values in %d series | "
        "stale trailing: %d values in %d series | short holes ffilled: %d values",
        tag, df.shape[1], int(report["n_non_numeric"].sum()), int(report["n_non_positive"].sum()),
        n_dropped_dates, int(lead.sum()), int((lead > 0).sum()),
        int(trail.sum()), int((trail > 0).sum()), int(filled.sum()),
    )
    for col in report.index[(lead > 0) | (trail > 0)]:
        logger.debug(
            "%s%s: stale leading=%d trailing=%d", tag, col,
            report.at[col, "n_stale_leading"], report.at[col, "n_stale_trailing"],
        )
    return out, report


# --------------------------------------------------------------------------- #
# Price <-> ESG matching
# --------------------------------------------------------------------------- #
def match_prices_to_esg(
    prices: pd.DataFrame, esg: pd.DataFrame, region: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rename constituent price columns to the ESG ``NAME`` they belong to.

    1. Exact match on the (suffix-stripped) name.
    2. Fallback by column position: the price and ESG files list stocks in the
       same order, so price column ``i`` is paired with ESG row ``i`` when both
       are still unmatched.
    3. Anything left is reported as ``unmatched_price`` / ``unmatched_esg``
       (never silently dropped; unmatched price columns keep their own name).

    Returns
    -------
    (renamed prices, matching report with columns
     ``region, position, price_name, esg_name, match``)
    """
    price_names = list(prices.columns)
    esg_names = list(esg.index)
    esg_set = set(esg_names)
    mapping: dict[str, str] = {}
    rows = []
    used_esg: set[str] = set()

    for pos, pname in enumerate(price_names):
        if pname in esg_set and pname not in used_esg:
            mapping[pname] = pname
            used_esg.add(pname)

    for pos, pname in enumerate(price_names):
        if pname in mapping:
            rows.append((region, pos, pname, pname, "exact"))
            continue
        cand = esg_names[pos] if pos < len(esg_names) else None
        if cand is not None and cand not in used_esg:
            mapping[pname] = cand
            used_esg.add(cand)
            rows.append((region, pos, pname, cand, "position"))
        else:
            rows.append((region, pos, pname, None, "unmatched_price"))

    for pos, ename in enumerate(esg_names):
        if ename not in used_esg:
            rows.append((region, pos, None, ename, "unmatched_esg"))

    report = pd.DataFrame(rows, columns=["region", "position", "price_name", "esg_name", "match"])
    counts = report["match"].value_counts().to_dict()
    logger.info("%s price<->ESG matching: %s", region, counts)
    renamed = prices.rename(columns=mapping)
    return renamed, report


def assign_zones(esg: pd.DataFrame) -> pd.DataFrame:
    """Add ``country`` (listing country) and ``zone`` (investor region).

    - US and Eurozone constituents map to the zones ``US`` and ``Europe``.
    - Pacific and EM EMEA constituents are split by country (``COUNTRY_ZONE``):
      Asia / Oceania and Middle East & Africa / Emerging Europe.
    - ``country`` is the ISIN prefix, except for offshore-domiciled stocks
      listed in ``COUNTRY_OVERRIDES`` (Cayman/Bermuda holdings in Hong Kong,
      JSE-listed stocks domiciled in Luxembourg, ...). US constituents are ``US``.

    Unknown countries in a split index are logged and assigned to the first
    zone of that index, so no stock is ever dropped silently.
    """
    df = esg.copy()
    names = df["name"] if "name" in df.columns else df.index.to_series()
    isin_cc = df["isin"].astype(str).str[:2].str.upper()
    country = pd.Series(
        [COUNTRY_OVERRIDES.get(str(n), cc) for n, cc in zip(names, isin_cc)], index=df.index
    )
    country[df["region"] == "US"] = "US"
    zone = pd.Series(pd.NA, index=df.index, dtype="object")
    for region in df["region"].unique():
        zones = [z for z, spec in ZONES.items() if spec["source"] == region]
        mask = df["region"] == region
        if len(zones) == 1:
            zone[mask] = zones[0]
            continue
        z = country[mask].map(COUNTRY_ZONE)
        unknown = z.isna() | ~z.isin(zones)
        if unknown.any():
            logger.warning("%s: no zone for countries %s (%s); assigned to %s",
                           region, sorted(set(country[mask][unknown])),
                           list(names[mask][unknown])[:5], zones[0])
            z[unknown] = zones[0]
        zone[mask] = z
    df["country"] = country
    df["zone"] = zone
    return df


def _zone_col(df: pd.DataFrame) -> str:
    return "zone" if "zone" in df.columns else "region"


def sort_stock_table(esg: pd.DataFrame) -> pd.DataFrame:
    """Sort a stock table by zone -> ICB industry -> ESG score (best first).

    Zones follow the ``ZONES`` order (US, Europe, Asia, Oceania, Middle East &
    Africa, Emerging Europe), industries the ``ICB_INDUSTRIES`` order; missing
    ESG scores come last within their industry, ties by name. Without a
    ``zone`` column, the source ``region`` (``REGIONS`` order) is used.
    Adds the best-in-class columns ``esg_rank_in_industry`` (1 = best ESG in
    its zone x industry), ``esg_percentile_in_industry`` (1.0 = best) and
    ``n_in_industry``.
    """
    df = esg.copy()
    zc = _zone_col(df)
    order_keys = list(ZONES) if zc == "zone" else list(REGIONS)
    names = df["name"] if "name" in df.columns else df.index.to_series()
    grp = df.groupby([zc, "industry"])["esg_score"]
    df["esg_rank_in_industry"] = grp.rank(ascending=False, method="min").astype("Int64")
    df["esg_percentile_in_industry"] = grp.rank(ascending=True, pct=True).round(4)
    df["n_in_industry"] = df.groupby([zc, "industry"])["industry"].transform("size")
    keys = pd.DataFrame(
        {
            "r": df[zc].map({k: i for i, k in enumerate(order_keys)}).fillna(len(order_keys)),
            "i": df["industry"].map({k: i for i, k in enumerate(ICB_INDUSTRIES)}).fillna(len(ICB_INDUSTRIES)),
            "e": -df["esg_score"].fillna(-np.inf),
            "n": names.astype(str).to_numpy(),
        },
        index=df.index,
    )
    order = keys.sort_values(["r", "i", "e", "n"], kind="mergesort").index
    return df.loc[order]


# --------------------------------------------------------------------------- #
# load_all
# --------------------------------------------------------------------------- #
def _read_series_group(mapping: dict[str, str]) -> tuple[pd.DataFrame, pd.Series]:
    series = [load_single_series(f, name=k) for k, f in mapping.items()]
    df = pd.concat(series, axis=1)
    df.columns.name = "series"
    return df, pd.Series(0, index=df.columns, dtype=int)


def load_all() -> dict:
    """Load, clean and align every dataset.

    Every Excel file in ``data/raw/`` is read (about a minute, mostly the
    S&P 500 constituents file).
    Cleaning is done per source file; equities are then split into the
    investor zones (``ZONES``).

    Returns
    -------
    dict with keys
        ``equities``    {zone: cleaned prices, columns = stock names, ordered by
                        ICB industry then ESG score (best first)}
        ``equities_by_source`` {source index: cleaned prices} (before the split)
        ``esg``         stock table indexed by ``"<zone>|<name>"``, sorted
                        zone -> industry -> ESG score (see sort_stock_table)
        ``bonds``       cleaned prices DataFrame
        ``commodities`` cleaned prices DataFrame
        ``benchmarks``  cleaned prices DataFrame (columns = BENCHMARKS keys)
        ``rf``          DataFrame ``yield_pct, rf_daily`` on the common calendar
        ``quality``     per-series data-quality report
        ``matching``    price<->ESG matching report
    """
    quality_parts = []

    def _clean(df: pd.DataFrame, errs: pd.Series, asset_class: str) -> pd.DataFrame:
        cleaned, rep = clean_prices(df, name=asset_class, errors=errs)
        rep.insert(0, "asset_class", asset_class)
        quality_parts.append(rep)
        return cleaned

    out: dict = {}
    for key, mapping in (("bonds", BONDS), ("commodities", COMMODITIES), ("benchmarks", BENCHMARKS)):
        raw, errs = _read_series_group(mapping)
        out[key] = _clean(raw, errs, key)

    by_source: dict[str, pd.DataFrame] = {}
    esg_frames = []
    match_reports = []
    for region, source_key in SOURCE_ASSET_CLASS.items():
        raw, errs = _read_constituents_raw(region)
        esg = load_esg(region)
        raw, match_rep = match_prices_to_esg(raw, esg, region)
        # renaming keeps column order, so carry the error counts over by position
        errs = pd.Series(errs.to_numpy(), index=raw.columns, dtype=int)
        esg["name"] = esg.index
        esg = sort_stock_table(assign_zones(esg))
        # order stocks by zone, ICB industry, then ESG score (best first); unmatched last
        order = [n for n in esg.index if n in raw.columns]
        order += [c for c in raw.columns if c not in set(order)]
        raw, errs = raw[order], errs[order]
        cleaned = _clean(raw, errs, source_key)
        by_source[region] = cleaned
        match_reports.append(match_rep)

        esg["has_prices"] = esg.index.isin(cleaned.columns)
        esg["first_valid_date"] = [
            cleaned[n].first_valid_index() if n in cleaned.columns else pd.NaT for n in esg.index
        ]
        esg_frames.append(esg)

    esg_all = sort_stock_table(pd.concat(esg_frames, ignore_index=True))
    esg_all.index = pd.Index(esg_all["zone"] + ASSET_ID_SEP + esg_all["name"], name="asset_id")
    out["esg"] = esg_all[
        ["name", "zone", "country", "region", "isin", "industry", "industry_code", "sector",
         "sector_code", "esg_score", "esg_rank_in_industry", "esg_percentile_in_industry",
         "n_in_industry", "has_prices", "first_valid_date"]
    ]

    # split each source index into its zones (same column order as the stock table)
    equities: dict[str, pd.DataFrame] = {}
    for zone, spec in ZONES.items():
        px = by_source[spec["source"]]
        names = esg_all.loc[(esg_all["zone"] == zone) & esg_all["has_prices"], "name"].tolist()
        equities[zone] = px[names]
    for region, px in by_source.items():
        in_zones = set(esg_all.loc[esg_all["region"] == region, "name"])
        orphans = [c for c in px.columns if c not in in_zones]
        if orphans:
            logger.warning("%s: %d price series without ESG row, not in any zone: %s",
                           region, len(orphans), orphans[:10])
    out["equities"] = equities
    out["equities_by_source"] = by_source

    calendar = out["benchmarks"].index
    for df in (out["bonds"], out["commodities"], *by_source.values()):
        calendar = calendar.union(df.index)
    out["rf"] = load_risk_free(calendar)

    quality = pd.concat(quality_parts).reset_index()
    matching = pd.concat(match_reports, ignore_index=True)
    ok = matching["match"].isin(["exact", "position"])
    matched = set(zip(matching.loc[ok, "region"].map(SOURCE_ASSET_CLASS), matching.loc[ok, "esg_name"]))
    is_equity = quality["asset_class"].isin(SOURCE_ASSET_CLASS.values())
    quality["matched_esg"] = [
        ((ac, s) in matched) if eq else pd.NA
        for ac, s, eq in zip(quality["asset_class"], quality["series"], is_equity)
    ]
    zone_of = {(SOURCE_ASSET_CLASS[r], n): z for r, n, z in zip(esg_all["region"], esg_all["name"], esg_all["zone"])}
    quality.insert(2, "zone", [zone_of.get((ac, s), pd.NA) for ac, s in zip(quality["asset_class"], quality["series"])])
    out["quality"] = quality
    out["matching"] = matching
    return out


# --------------------------------------------------------------------------- #
# Read side: what the Streamlit pages use (only reads data/processed/)
# --------------------------------------------------------------------------- #
def read_processed(kind: str, asset_class: str, columns: list[str] | None = None) -> pd.DataFrame:
    """Read one output of ``compute_erc.py`` from ``data/processed/``.

    Parameters
    ----------
    kind : a key of ``PROCESSED_FILES`` (``"prices"``, ``"returns_daily"``,
        ``"returns_monthly"``, ``"volatility"``), or ``"rf"``.
    asset_class : an equity zone (``"US"``, ``"Europe"``, ``"Asia"``,
        ``"Oceania"``, ``"Middle East & Africa"``, ``"Emerging Europe"``) or its
        file name (``equity_asia``...), or ``bonds``, ``commodities``,
        ``benchmarks`` (ignored for ``"rf"``).
    columns : read only these series (fast column selection in parquet); the
        result keeps the requested order.
    """
    if kind == "rf":
        return pd.read_parquet(PROCESSED_DIR / "rf.parquet", columns=columns)
    if kind not in PROCESSED_FILES:
        raise KeyError(f"Unknown kind {kind!r}; expected one of {list(PROCESSED_FILES)} or 'rf'")
    asset_class = EQUITY_ASSET_CLASS.get(asset_class, asset_class)
    path = PROCESSED_DIR / f"{PROCESSED_FILES[kind].format(ac=asset_class)}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found; run `python compute_erc.py` first")
    df = pd.read_parquet(path, columns=columns)
    return df[columns] if columns is not None else df


def read_esg_universe() -> pd.DataFrame:
    """Stock table (all zones) sorted zone -> ICB industry -> ESG score,
    indexed by ``"<zone>|<name>"``; see ``compute_erc.py`` for the columns."""
    return pd.read_parquet(PROCESSED_DIR / "esg_universe.parquet")
