"""Pipeline runner: data/raw/ -> data/processed/.

Usage
-----
    python compute_erc.py                 # reads data/raw/, writes data/processed/ (~1 min)
    python compute_erc.py --full-history  # write 2000-2026 instead of DATA_START onwards

The portfolio starts on PORTFOLIO_START (2015-01-01). Outputs start on
DATA_START (2014-01-01) so the first 1-year estimation window is included;
everything is computed on the full history first, then trimmed.

Current scope: loading/cleaning, simple returns and the 1-year rolling volatility.
The ERC / ESG risk-budgeting / backtest step plugs in at
:func:`run_portfolio_construction` (not implemented yet).
"""

from __future__ import annotations

import argparse
import logging
import time

import pandas as pd

from core.config import (
    DATA_START,
    EQUITY_ASSET_CLASS,
    ESTIMATION_WINDOW,
    MIN_WINDOW_COVERAGE,
    PORTFOLIO_START,
    PROCESSED_DIR,
    PROCESSED_FILES,
    ROOT_DIR,
    SOURCE_ASSET_CLASS,
    ZONES,
)
from core.importation_data import load_all
from core.utilities import (
    eligible_assets,
    rolling_volatility,
    simple_returns,
    volatility_summary,
    window_coverage,
)

logger = logging.getLogger("compute_erc")

PARQUET_KW = {"compression": "zstd"}


def _save(df: pd.DataFrame | pd.Series, name: str) -> None:
    if isinstance(df, pd.Series):
        df = df.to_frame()
    path = PROCESSED_DIR / f"{name}.parquet"
    df.to_parquet(path, **PARQUET_KW)
    logger.debug("Saved %s %s", path.relative_to(ROOT_DIR), df.shape)


def price_frames(data: dict) -> dict[str, pd.DataFrame]:
    """Cleaned prices keyed by asset-class name (``equity_us``, ``equity_asia``, ...,
    ``benchmarks``); equities are one frame per investor zone."""
    frames = {EQUITY_ASSET_CLASS[z]: df for z, df in data["equities"].items()}
    frames.update({"bonds": data["bonds"], "commodities": data["commodities"], "benchmarks": data["benchmarks"]})
    return frames


OUTPUT_FILES = PROCESSED_FILES  # see core.config
# Outputs of earlier versions: log returns, and per-source-index equity files
# (replaced by the per-zone files).
OBSOLETE_PATTERNS = (
    "log_returns_daily_*.parquet",
    "log_returns_monthly_*.parquet",
    "vol_rolling_*.parquet",          # renamed to volatility_<ac>.parquet
    "vol_ewma_*.parquet",             # other volatility proxies: no longer used
    "vol_realized_monthly_*.parquet",
    "vol_abs_daily_*.parquet",
    *(f"*_{ac}.parquet" for ac in set(SOURCE_ASSET_CLASS.values()) - set(EQUITY_ASSET_CLASS.values())),
)


def build_data_layer(start: str | None = DATA_START) -> dict:
    """Load, clean, compute simple returns + volatility, write data/processed/.

    All asset classes (equity regions, bonds, commodities, benchmarks) use
    simple returns ``R_t = P_t / P_{t-1} - 1``. The single volatility measure
    is the annualised 1-year rolling volatility of the daily simple returns
    (same window as the ERC estimation). Equity columns are ordered by ICB
    industry then ESG score (best first), identically in every file.

    Everything is computed on the full history, then trimmed to ``start``
    (default ``DATA_START`` = one year before ``PORTFOLIO_START``) before
    saving; ``start=None`` keeps the full history.

    Returns a dict with ``data`` (output of :func:`load_all`), one dict per
    output family of :data:`OUTPUT_FILES` keyed by asset-class name, and
    ``vol_summary``.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in OBSOLETE_PATTERNS:  # outputs of earlier versions
        for f in PROCESSED_DIR.glob(pattern):
            f.unlink()
            logger.info("Removed obsolete output %s", f.name)

    data = load_all()
    prices = price_frames(data)

    res: dict = {"data": data, "start": start, **{k: {} for k in OUTPUT_FILES}}
    summaries = []
    elig: dict[str, pd.DataFrame] = {}
    for ac, px in prices.items():
        logger.info("Simple returns and 1-year rolling volatility for %s (%d series)", ac, px.shape[1])
        r_d = simple_returns(px, freq="D")
        if ac in EQUITY_ASSET_CLASS.values():
            elig[ac] = pd.DataFrame({
                "window_coverage_at_start": window_coverage(r_d, PORTFOLIO_START).round(4),
                "eligible_at_start": eligible_assets(r_d, PORTFOLIO_START),
            })
        frames = {
            "prices": px,
            "returns_daily": r_d,
            "returns_monthly": simple_returns(px, freq="M"),
            "volatility": rolling_volatility(r_d),
        }
        if start is not None:
            frames = {k: df.loc[df.index >= pd.Timestamp(start)] for k, df in frames.items()}
        for key, df in frames.items():
            _save(df, OUTPUT_FILES[key].format(ac=ac))
            res[key][ac] = df

        summ = volatility_summary(frames["returns_daily"], volatility=frames["volatility"])
        summ.insert(0, "asset_class", ac)
        summaries.append(summ)

    rf = data["rf"] if start is None else data["rf"].loc[data["rf"].index >= pd.Timestamp(start)]
    _save(rf, "rf")

    esg = data["esg"].copy()
    esg["asset_class"] = esg["zone"].map(EQUITY_ASSET_CLASS)
    # eligibility at the portfolio start: >= 95% of the 1-year window + alive
    cov = pd.Series(pd.NA, index=esg.index, dtype="Float64")
    ok = pd.Series(False, index=esg.index)
    for zone, ac in EQUITY_ASSET_CLASS.items():
        mask = (esg["zone"] == zone) & esg["has_prices"]
        cov[mask] = elig[ac].loc[esg.loc[mask, "name"], "window_coverage_at_start"].to_numpy()
        ok[mask] = elig[ac].loc[esg.loc[mask, "name"], "eligible_at_start"].to_numpy()
    esg["window_coverage_at_start"] = cov
    esg["eligible_at_start"] = ok
    data["esg"] = esg
    _save(esg, "esg_universe")
    esg.to_csv(PROCESSED_DIR / "esg_universe.csv")

    vol_summary = pd.concat(summaries).reset_index()
    num_cols = vol_summary.select_dtypes("number").columns
    vol_summary[num_cols] = vol_summary[num_cols].round(6)
    vol_summary.to_csv(PROCESSED_DIR / "volatility_summary.csv", index=False)
    data["quality"].to_csv(PROCESSED_DIR / "data_quality_report.csv", index=False)
    data["matching"].to_csv(PROCESSED_DIR / "esg_matching_report.csv", index=False)
    res["vol_summary"] = vol_summary
    res["alignment"] = check_alignment(res)
    return res


def check_alignment(res: dict) -> pd.DataFrame:
    """Check that, per asset class, prices / daily returns / volatility share
    the same dates and columns, and monthly returns the same columns."""
    rows = []
    for ac, px in res["prices"].items():
        daily = [res[k][ac] for k in ("prices", "returns_daily", "volatility")]
        monthly = res["returns_monthly"][ac]
        same_cols = all(list(df.columns) == list(px.columns) for df in [*daily, monthly])
        same_daily_idx = all(df.index.equals(px.index) for df in daily)
        rows.append({"asset_class": ac, "n_series": px.shape[1], "same_columns": same_cols,
                     "same_daily_dates": same_daily_idx, "n_daily": len(px), "n_monthly": len(monthly)})
    out = pd.DataFrame(rows).set_index("asset_class")
    bad = out[~out[["same_columns", "same_daily_dates"]].all(axis=1)]
    if not bad.empty:
        raise RuntimeError(f"Outputs are not aligned:\n{bad}")
    return out


def run_portfolio_construction(res: dict) -> None:
    """Next step: ERC within / across asset classes, ESG risk budgets, backtest.

    Planned flow (see ``core.utilities`` stubs):
    1. ``core.esg.screen_universe`` + ``get_screened_returns`` for the equity sleeve;
    2. ``covariance_matrix`` on a 1-year rolling window, ``erc_weights`` /
       ``risk_budget_weights`` (budgets from ``esg_scores_vector``);
    3. ``backtest`` with monthly rebalancing and ``performance_metrics`` vs the
       benchmarks; write results to data/processed/.
    """
    raise NotImplementedError("ERC / ESG risk budgeting / backtest: next step")


def print_summary(res: dict) -> None:
    """Short console summary of the data layer."""
    data = res["data"]
    esg = data["esg"]
    matching = data["matching"]

    print("\n" + "=" * 78)
    print("DATA LAYER SUMMARY")
    print("=" * 78)

    print("\nStocks per investor region (ESG coverage)")
    for zone, px in data["equities"].items():
        sub = esg[esg["zone"] == zone]
        n_esg = int(sub["esg_score"].notna().sum())
        countries = ", ".join(f"{c} {n}" for c, n in sub["country"].value_counts().items())
        print(f"  {zone:<21} {px.shape[1]:>4} stocks | ESG score {n_esg}/{len(sub)} "
              f"({n_esg / len(sub):.1%}) | mean ESG {sub['esg_score'].mean():.1f} | "
              f"from {ZONES[zone]['source']} | {countries}")
    n_esg = int(esg["esg_score"].notna().sum())
    print(f"  {'Total':<21} {sum(df.shape[1] for df in data['equities'].values()):>4} price series | "
          f"ESG score {n_esg}/{len(esg)} ({n_esg / len(esg):.1%})")

    print("\nPrice <-> ESG matching")
    counts = matching.groupby(["region", "match"]).size().unstack(fill_value=0)
    print("  " + counts.to_string().replace("\n", "\n  "))
    unmatched = matching[~matching["match"].isin(["exact"])]
    if unmatched.empty:
        print("  Unmatched / position-matched names: none (all names matched exactly)")
    else:
        print("  Not matched exactly:")
        print("  " + unmatched.to_string(index=False).replace("\n", "\n  "))

    print(f"\nPortfolio start {PORTFOLIO_START} | estimation window {ESTIMATION_WINDOW} days | "
          f"outputs from {res['start'] or 'full history'}")
    print(f"Stocks eligible at the start (>= {MIN_WINDOW_COVERAGE:.0%} of the 1-year window, "
          f"price on the last day before the start)")
    for zone in data["equities"]:
        sub = esg[esg["zone"] == zone]
        print(f"  {zone:<21} {int(sub['eligible_at_start'].sum()):>4} / {len(sub):>4} "
              f"({int((~sub['eligible_at_start']).sum())} join later)")
    print(f"  {'Total':<21} {int(esg['eligible_at_start'].sum()):>4} / {len(esg):>4}")

    print("\nDate range per asset class in the saved files (first date -> last date)")
    for ac, px in res["prices"].items():
        print(f"  {ac:<16} {px.index.min().date()} -> {px.index.max().date()} | {len(px):>5} dates")
    rf = data["rf"]
    rf_saved = rf if res["start"] is None else rf.loc[rf.index >= pd.Timestamp(res["start"])]
    first_rf = rf["yield_pct"].first_valid_index()
    print(f"  {'rf':<16} {rf_saved.index.min().date()} -> {rf_saved.index.max().date()} | "
          f"T-bill yield available from {first_rf.date()}")

    print(f"\nAnnualised volatility of daily simple returns, {res['start'] or 'full sample'} -> end")
    vs = res["vol_summary"]
    vs = vs[vs["asset_class"].isin(["bonds", "commodities", "benchmarks"])]
    print(f"  {'asset class':<12} {'series':<16} {'full':>7} {'1y.last':>8} {'1y.mean':>8} "
          f"{'1y.min':>7} {'1y.max':>7}")
    for _, row in vs.iterrows():
        print(f"  {row['asset_class']:<12} {row['series']:<16} {row['full_sample_vol']:>7.1%} "
              f"{row['vol_latest']:>8.1%} {row['vol_mean']:>8.1%} "
              f"{row['vol_min']:>7.1%} {row['vol_max']:>7.1%}")

    q = data["quality"]
    flagged = q[(q["n_stale_leading"] > 0) | (q["n_stale_trailing"] > 0) | (q["n_non_positive"] > 0)]
    print("\nCleaning: series with stale or non-positive prices removed")
    print("  " + flagged[["asset_class", "series", "n_non_positive", "n_stale_leading",
                          "n_stale_trailing", "n_ffilled"]].to_string(index=False).replace("\n", "\n  "))

    print("\nAlignment check (prices, returns and volatility share columns and dates)")
    print("  " + res["alignment"].to_string().replace("\n", "\n  "))

    files = sorted(PROCESSED_DIR.glob("*.*"))
    total = sum(f.stat().st_size for f in files)
    print(f"\nWrote {len(files)} files to {PROCESSED_DIR.relative_to(ROOT_DIR)}/ ({total / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="QARM ERC pension fund: data pipeline")
    parser.add_argument("--full-history", action="store_true",
                        help="save 2000-2026 instead of starting at DATA_START")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    t0 = time.time()
    res = build_data_layer(start=None if args.full_history else DATA_START)
    print_summary(res)
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
