"""Project-wide constants: paths, asset universe and naming conventions.

Everything that the pipeline (``compute_erc.py``) and the Streamlit pages need
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
# Short labels of the four source indices (one Datastream file each).
REGION_LABELS: dict[str, str] = {
    "US": "US (S&P 500)",              # LS&PCOMP
    "Eurozone": "Eurozone (MSCI EMU)", # LMSEMUID: euro-area countries only
    "EM EMEA": "MSCI EM EMEA",         # LMSEMAFD: Emerging Europe, Middle East, Africa
    "Pacific": "MSCI Pacific",         # LMSPACFD: Japan, Australia, Hong Kong, Singapore, New Zealand
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

# AGG covers sovereign, corporate and MBS. AUSGVAL (US Treasuries) is not used:
# Treasuries are already ~40% of AGG, so adding it would double-count govt risk.
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
ASSET_CLASSES: list[str] = [*EQUITY_ASSET_CLASS.values(), "bonds", "commodities", "benchmarks", "rf"]

# Files written to data/processed/ for every asset class ({ac} = asset-class name).
# prices / returns_daily / volatility share the same dates and columns;
# returns_monthly has the same columns on month-end dates.
PROCESSED_FILES: dict[str, str] = {
    "prices": "prices_{ac}",
    "returns_daily": "simple_returns_daily_{ac}",
    "returns_monthly": "simple_returns_monthly_{ac}",
    "volatility": "volatility_{ac}",  # 1-year rolling, annualised (the only vol measure)
}

# Separator for unique stock identifiers: "<zone>|<stock>" (e.g. "Pacific|TOYOTA MOTOR").
ASSET_ID_SEP: str = "|"

# --------------------------------------------------------------------------- #
# Backtest calendar
# --------------------------------------------------------------------------- #
PORTFOLIO_START: str = "2005-01-01"   # first rebalancing; AGG starts 26/09/2003 + 1-year window
ESTIMATION_WINDOW: int = 252          # 1-year rolling estimation window (business days)
# Outputs in data/processed/ start one year before the portfolio, so the first
# estimation window (2004) is available. Cleaning and the volatility proxies
# are computed on the full 2000-2026 history before trimming.
DATA_START: str = "2004-01-01"
# A stock is eligible at a rebalancing date only if it has returns on the
# full estimation window (no missing data in the covariance).
REBALANCING_FREQ: str = "M"           # monthly ("Q" for robustness tests)

# --------------------------------------------------------------------------- #
# ESG risk budgeting (risk budgets proportional to ESG scores)
# --------------------------------------------------------------------------- #
# ESG scores are a single (latest) Datastream snapshot, applied over the whole
# backtest: look-ahead bias, stated as a limitation in the report.
ESG_PORTFOLIO_START: str = PORTFOLIO_START  # same period as ERC, for a direct comparison
ESG_MISSING: str = "exclude"                # stocks without an ESG score are excluded

TRADING_DAYS: int = 261               # annualisation: Datastream daily files hold every weekday (~261 a year)

# Debugging for "Investor Preferences"
MIN_WINDOW_COVERAGE: float = 1.0
