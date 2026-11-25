"""Loading and cleaning of the Datastream files in ``data/raw/``.

Main function: :func:`load_all` reads every file, cleans the prices and
returns one dictionary with all the data. Nothing in ``data/raw/`` is written.
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
    ICB_INDUSTRIES,
    PROCESSED_DIR,
    PROCESSED_FILES,
    TRADING_DAYS,
    RAW_DIR,
    REGIONS,
    RISK_FREE,
    ZONES,
    EQUITY_ASSET_CLASS,
)

logger = logging.getLogger(__name__)

PRICE_SUFFIX = " - TOT RETURN IND"

# Cleaning rules (see clean_prices)
MIN_PRICE = 1.0      # Datastream gives 2 decimals: below 1.0, rounding creates fake returns
STALE_MIN_RUN = 10   # >= 10 identical prices at the start / end of a series = no real trading
SPIKE_JUMP = 0.5     # a spike: a move of +50% (or -33%) ...
SPIKE_MAX_DAYS = 5   # ... reversed within 5 days ...
SPIKE_TOL = 0.10     # ... to within 10% of the price before the jump
MAX_FFILL = 5        # holes of at most 5 days are filled with the last price

ESG_COLUMNS = {
    "ISIN CODE": "isin",
    "ICB INDUSTRY NAME": "industry",
    "ICB SECTOR NAME": "sector",
    "ESG Score": "esg_score",
}


# --------------------------------------------------------------------------- #
# Reading the Excel files
# --------------------------------------------------------------------------- #
def _read_excel(file: str) -> pd.DataFrame:
    return pd.read_excel(RAW_DIR / file, header=None, sheet_name=0)


def _strip_suffix(name) -> str:
    name = str(name).strip()
    return name[: -len(PRICE_SUFFIX)].strip() if name.upper().endswith(PRICE_SUFFIX) else name


def _dedupe(names: list[str]) -> list[str]:
    """Make names unique by adding " (2)", " (3)"... to repeats."""
    seen: dict[str, int] = {}
    out = []
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        out.append(n if seen[n] == 1 else f"{n} ({seen[n]})")
    return out


def _to_grid(raw: pd.DataFrame, first_row: int) -> pd.DataFrame:
    """Rows from ``first_row`` on: column 0 = dates, other columns = values."""
    body = raw.iloc[first_row:]
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce", format="mixed")
    body = body.loc[dates.notna()]
    grid = body.iloc[:, 1:].apply(pd.to_numeric, errors="coerce").astype(float)
    grid.index = pd.DatetimeIndex(dates[dates.notna()], name="date")
    return grid[~grid.index.duplicated(keep="last")].sort_index()


def load_single_series(file: str, name: str) -> pd.Series:
    """One-series file (bond, commodity, benchmark, T-bill): header row ``Name``,
    then an optional ``CURRENCY`` row, then ``date, value`` rows."""
    raw = _read_excel(file)
    header = int(np.flatnonzero(raw.iloc[:, 0].astype(str).str.strip().eq("Name"))[0])
    series = _to_grid(raw.iloc[:, :2], header + 1).iloc[:, 0]
    series.name = name
    return series


def load_constituents(region: str) -> pd.DataFrame:
    """Stock prices of a region: dates x stocks (total return indices, USD)."""
    raw = _read_excel(REGIONS[region]["prices"])
    names = _dedupe([_strip_suffix(n) for n in raw.iloc[0, 1:]])
    first_row = 2 if str(raw.iat[1, 0]).strip().upper() == "CURRENCY" else 1
    if first_row == 2:
        currencies = set(raw.iloc[1, 1:].dropna().astype(str).str.strip()) - {"U$"}
        if currencies:
            logger.warning("%s: non-USD currencies %s", region, currencies)
    prices = _to_grid(raw, first_row)
    prices.columns = names
    return prices


def load_esg(region: str) -> pd.DataFrame:
    """ICB sector and ESG score of each stock of a region (index = stock name)."""
    df = pd.read_excel(RAW_DIR / REGIONS[region]["esg"], sheet_name=0)
    df["NAME"] = _dedupe(df["NAME"].astype(str).str.strip().tolist())
    out = df.set_index("NAME")[list(ESG_COLUMNS)].rename(columns=ESG_COLUMNS)
    out.index.name = "name"
    out["esg_score"] = pd.to_numeric(out["esg_score"], errors="coerce")
    for col in ("isin", "industry", "sector"):
        out[col] = out[col].astype(str).str.strip()
    out["region"] = region
    return out


def load_risk_free(calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily risk-free rate: ``rf_daily = TRUS1MT / 100 / TRADING_DAYS`` (missing days filled)."""
    y = load_single_series(RISK_FREE, "yield_pct")
    y = y.reindex(y.index.union(calendar)).ffill().reindex(calendar)
    return pd.DataFrame({"yield_pct": y, "rf_daily": (y / 100 / TRADING_DAYS).fillna(0.0)})


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def _remove_spikes(col: np.ndarray) -> np.ndarray:
    """Remove temporary spikes: a jump of +50% (or -33%) after which the price
    comes back within 10% of its previous level in at most 5 days."""
    out = col.copy()
    valid = np.flatnonzero(~np.isnan(out))
    logp = np.log(out[valid])
    i = 1
    while i < len(valid):
        if abs(logp[i] - logp[i - 1]) >= np.log1p(SPIKE_JUMP):
            for j in range(i + 1, min(i + 1 + SPIKE_MAX_DAYS, len(valid))):
                if abs(logp[j] - logp[i - 1]) <= np.log1p(SPIKE_TOL):
                    out[valid[i:j]] = np.nan
                    logp[i:j] = logp[i - 1]
                    i = j
                    break
        i += 1
    return out


def _remove_stale_ends(col: np.ndarray) -> np.ndarray:
    """A run of >= 10 identical prices at the start of a series (before trading
    starts) or at the end (after delisting, the last price is kept) -> NaN."""
    out = col.copy()
    valid = np.flatnonzero(~np.isnan(out))
    if len(valid) == 0:
        return out
    v = out[valid]
    start = np.flatnonzero(v != v[0])
    run = start[0] if len(start) else len(v)
    if run >= STALE_MIN_RUN:
        out[valid[:run]] = np.nan
    end = np.flatnonzero(v[::-1] != v[-1])
    run = end[0] if len(end) else len(v)
    if run >= STALE_MIN_RUN:
        out[valid[len(v) - run + 1:]] = np.nan
    return out


def clean_prices(prices: pd.DataFrame, name: str = "") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cleaning rules, in this order:

    1. Prices <= 0 or below ``MIN_PRICE`` -> NaN (rounding to 2 decimals makes
       their returns meaningless, e.g. 0.01 -> 0.02 = +100%).
    2. Weekends and dates with no data at all are dropped.
    3. Stale prices at the start / end of a series -> NaN.
    4. Temporary spikes (data errors) -> NaN.
    5. Holes of at most ``MAX_FFILL`` days are filled with the last price.

    Returns the cleaned prices and a small report (one row per series).
    """
    df = prices.where(prices >= MIN_PRICE)
    df = df.loc[df.index.dayofweek < 5].dropna(how="all")
    n_before = df.notna().sum()
    arr = df.to_numpy(copy=True)
    for j in range(arr.shape[1]):
        arr[:, j] = _remove_spikes(_remove_stale_ends(arr[:, j]))
    out = pd.DataFrame(arr, index=df.index, columns=df.columns)
    n_removed = n_before - out.notna().sum()
    # fill short interior holes only (never before the first / after the last price)
    filled = out.ffill(limit=MAX_FFILL).where(out.bfill().notna())
    out = filled.dropna(how="all")
    report = pd.DataFrame({
        "asset_class": name,
        "n_low_price": (prices.loc[df.index] < MIN_PRICE).sum(),
        "n_removed_stale_or_spike": n_removed,
        "first_valid": [out[c].first_valid_index() for c in out.columns],
        "last_valid": [out[c].last_valid_index() for c in out.columns],
    })
    report.index.name = "series"
    logger.info("[%s] %d series cleaned, %d prices removed", name, out.shape[1], int(n_removed.sum()))
    return out, report


# --------------------------------------------------------------------------- #
# Stock table (sector + ESG), used by core/esg.py and the app
# --------------------------------------------------------------------------- #
def assign_zones(esg: pd.DataFrame) -> pd.DataFrame:
    """Add ``country`` (ISIN prefix) and ``zone`` (= the source region)."""
    df = esg.copy()
    df["country"] = df["isin"].astype(str).str[:2].str.upper()
    df.loc[df["region"] == "US", "country"] = "US"
    zone_of_source = {spec["source"]: zone for zone, spec in ZONES.items()}
    df["zone"] = df["region"].map(zone_of_source)
    return df


def sort_stock_table(esg: pd.DataFrame) -> pd.DataFrame:
    """Sort stocks by zone -> ICB industry -> ESG score (best first)."""
    df = esg.copy()
    zc = "zone" if "zone" in df.columns else "region"
    order = list(ZONES) if zc == "zone" else list(REGIONS)
    keys = pd.DataFrame({
        "z": df[zc].map({k: i for i, k in enumerate(order)}),
        "i": df["industry"].map({k: i for i, k in enumerate(ICB_INDUSTRIES)}).fillna(len(ICB_INDUSTRIES)),
        "e": -df["esg_score"].fillna(-np.inf),
    }, index=df.index)
    return df.loc[keys.sort_values(["z", "i", "e"], kind="mergesort").index]


# --------------------------------------------------------------------------- #
# Everything at once
# --------------------------------------------------------------------------- #
def load_all() -> dict:
    """Load and clean every dataset (about a minute).

    Returns a dict with
        ``equities``    {zone: cleaned stock prices}
        ``esg``         stock table indexed by ``"<zone>|<name>"``
        ``bonds``, ``commodities``, ``benchmarks``  cleaned prices
        ``rf``          ``yield_pct, rf_daily`` on the common calendar
        ``quality``     cleaning report (one row per series)
    """
    out: dict = {}
    reports = []

    for key, mapping in (("bonds", BONDS), ("commodities", COMMODITIES), ("benchmarks", BENCHMARKS)):
        raw = pd.concat([load_single_series(f, k) for k, f in mapping.items()], axis=1)
        out[key], rep = clean_prices(raw, key)
        reports.append(rep)

    equities, tables = {}, []
    for zone, spec in ZONES.items():
        region = spec["source"]
        prices = load_constituents(region)
        esg = assign_zones(load_esg(region))
        missing = set(prices.columns) - set(esg.index)
        if missing:
            logger.warning("%s: %d stocks without an ESG row: %s", zone, len(missing), sorted(missing)[:5])
        esg = sort_stock_table(esg)
        prices = prices[[n for n in esg.index if n in prices.columns]]  # same order as the table
        equities[zone], rep = clean_prices(prices, EQUITY_ASSET_CLASS[zone])
        reports.append(rep)
        esg["name"] = esg.index
        esg["has_prices"] = esg.index.isin(equities[zone].columns)
        tables.append(esg)

    esg_all = pd.concat(tables, ignore_index=True)
    esg_all.index = pd.Index(esg_all["zone"] + ASSET_ID_SEP + esg_all["name"], name="asset_id")
    out["equities"] = equities
    out["esg"] = esg_all[["name", "zone", "country", "region", "isin", "industry", "sector",
                          "esg_score", "has_prices"]]

    calendar = out["benchmarks"].index
    for df in (out["bonds"], out["commodities"], *equities.values()):
        calendar = calendar.union(df.index)
    out["rf"] = load_risk_free(calendar)
    out["quality"] = pd.concat(reports).reset_index()
    return out


# --------------------------------------------------------------------------- #
# Read side: what the Streamlit pages use (only reads data/processed/)
# --------------------------------------------------------------------------- #
def read_processed(kind: str, asset_class: str, columns: list[str] | None = None) -> pd.DataFrame:
    """Read one output of ``compute_erc.py``: ``kind`` is a key of
    ``PROCESSED_FILES`` (or ``"rf"``), ``asset_class`` a zone (``"US"``...) or
    ``bonds`` / ``commodities`` / ``benchmarks``."""
    if kind == "rf":
        return pd.read_parquet(PROCESSED_DIR / "rf.parquet", columns=columns)
    asset_class = EQUITY_ASSET_CLASS.get(asset_class, asset_class)
    path = PROCESSED_DIR / f"{PROCESSED_FILES[kind].format(ac=asset_class)}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found; run `python compute_erc.py` first")
    df = pd.read_parquet(path, columns=columns)
    return df[columns] if columns is not None else df


def read_esg_universe() -> pd.DataFrame:
    """Stock table (all zones), indexed by ``"<zone>|<name>"``."""
    return pd.read_parquet(PROCESSED_DIR / "esg_universe.parquet")
