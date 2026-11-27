"""Project-wide constants: paths, asset universe and naming conventions.

Everything that the pipeline (``compute_erc.py``) and the web app need
to agree on lives here, so that both sides import the same keys.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths (relative to the repository root, resolved from this file's location)
# --------------------------------------------------------------------------- #
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
RAW_DIR: Path = ROOT_DIR / "data" / "raw"
PROCESSED_DIR: Path = ROOT_DIR / "data" / "processed"

# --------------------------------------------------------------------------- #
# Asset universe (exact keys used everywhere)
# --------------------------------------------------------------------------- #
REGIONS: dict[str, dict[str, str | None]] = {
    "US":       {"prices": "LS&PCOMP.xlsx", "esg": "LS&P500-ICB-ESG.xlsx", "benchmark": "S&PCOMP.xlsx"},
    "Eurozone": {"prices": "LMSEMUID.xlsx", "esg": "LMSEMUI-ICB-ESG.xlsx", "benchmark": "MSEMUI$.xlsx"},
    "EM EMEA":  {"prices": "LMSEMAFD.xlsx", "esg": "LMSEMAF-ICB-ESG.xlsx", "benchmark": "MSEMAF$.xlsx"},
    "Pacific":  {"prices": "LMSPACFD.xlsx", "esg": "LMSPACF-ICB-ESG.xlsx", "benchmark": "MSPACF$.xlsx"},
}

# --------------------------------------------------------------------------- #
# Equity sleeves: one asset class per source index (no country split).
# --------------------------------------------------------------------------- #
ZONES: dict[str, dict[str, str]] = {
    "US":       {"source": "US",       "asset_class": "equity_us",       "benchmark": "US"},
    "Eurozone": {"source": "Eurozone", "asset_class": "equity_eurozone", "benchmark": "Eurozone"},
    "Pacific":  {"source": "Pacific",  "asset_class": "equity_pacific",  "benchmark": "Pacific"},
    "EM EMEA":  {"source": "EM EMEA",  "asset_class": "equity_em_emea",  "benchmark": "EM EMEA"},
}

# AGG covers sovereign, corporate and MBS bonds (Treasuries are already ~40% of it).
BONDS: dict[str, str] = {"US Aggregate": "UAGG.xlsx"}
COMMODITIES: dict[str, str] = {
    "Energy": "GSENTOT.xlsx",
    "Precious Metals": "GSPMTOT.xlsx",
    "Agriculture": "GSAGTOT.xlsx",
}
COMMODITY_BENCHMARK: str = "GSCITOT.xlsx"
RISK_FREE: str = "TRUS1MT.xlsx"   # 1-month T-bill, % p.a. -> daily rate = rate / 100 / TRADING_DAYS

# Benchmarks keyed by source index (+ "Commodities"); ZONES[z]["benchmark"]
# says which one applies to each equity sleeve.
BENCHMARKS: dict[str, str] = {
    **{region: spec["benchmark"] for region, spec in REGIONS.items() if spec["benchmark"]},
    "Commodities": COMMODITY_BENCHMARK,
}
# Human-readable labels for display in the app.
BENCHMARK_LABELS: dict[str, str] = {
    "US": "S&P 500",
    "Eurozone": "MSCI EMU",
    "EM EMEA": "MSCI EM EMEA",
    "Pacific": "MSCI Pacific",
    "Commodities": "S&P GSCI",
}

# Constructed benchmarks (not Datastream files).
BENCHMARK_6040: dict[str, float] = {"US": 0.60, "US Aggregate": 0.40}  # S&P 500 / AGG
# 1/N: equal weight across the asset-class sleeves (computed in the backtest).

# The 11 ICB industries present in the ESG files.
ICB_INDUSTRIES: list[str] = [
    "Technology",
    "Telecommunications",
    "Health Care",
    "Financials",
    "Real Estate",
    "Consumer Discretionary",
    "Consumer Staples",
    "Industrials",
    "Basic Materials",
    "Energy",
    "Utilities",
]

# --------------------------------------------------------------------------- #
# Asset-class names used for output files in data/processed/
# --------------------------------------------------------------------------- #
EQUITY_ASSET_CLASS: dict[str, str] = {zone: spec["asset_class"] for zone, spec in ZONES.items()}

# Daily returns written to data/processed/ for every asset class ({ac} = asset-class name).
PROCESSED_FILES: dict[str, str] = {"returns_daily": "simple_returns_daily_{ac}"}

# Separator for unique stock identifiers: "<zone>|<stock>" (e.g. "Pacific|TOYOTA MOTOR").
ASSET_ID_SEP: str = "|"

# --------------------------------------------------------------------------- #
# Backtest calendar
# --------------------------------------------------------------------------- #
PORTFOLIO_START: str = "2005-01-01"   # first rebalancing; AGG starts 26/09/2003 + 1-year window
ESTIMATION_WINDOW: int = 252          # 1-year rolling estimation window (business days)
# A stock is eligible at a rebalancing date only if it has a return on every day of the estimation window
# and at most MAX_ZERO_SHARE zero returns (otherwise its prices are stale and its risk cannot be estimated).
MAX_ZERO_SHARE: float = 0.20          # a stock with more than 20% zero returns in its window is not traded enough
# Outputs in data/processed/ start one year before the portfolio, so the first
# estimation window (2004) is available. Cleaning is done on the full 2000-2026 history before trimming.
DATA_START: str = "2004-01-01"
REBALANCING_FREQ: str = "M"           # monthly
TRADING_DAYS: int = 261               # annualisation: Datastream daily files hold every weekday (~261 a year)
