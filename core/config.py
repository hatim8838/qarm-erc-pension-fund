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
    "Pacific":  {"prices": "LMSPACFD.xlsx", "esg": "LMSPACF-ICB-ESG.xlsx", "benchmark": None},
}
# Short labels of the four source indices (one Datastream file each).
REGION_LABELS: dict[str, str] = {
    "US": "US (S&P 500)",                 # LS&PCOMP
    "Eurozone": "Europe (MSCI EMU)",      # LMSEMUID
    "EM EMEA": "MSCI EM EMEA",            # LMSEMAFD: Middle East, Africa, Emerging Europe
    "Pacific": "MSCI Pacific",            # LMSPACFD: Asia + Oceania
}

# --------------------------------------------------------------------------- #
# Investor regions ("zones"): what the investor selects in the app.
# Each zone comes from exactly one source index; Pacific and EM EMEA are split
# by the stock's country.
# --------------------------------------------------------------------------- #
ZONES: dict[str, dict[str, str]] = {
    "US":                   {"source": "US",       "asset_class": "equity_us",                 "benchmark": "US"},
    "Europe":               {"source": "Eurozone", "asset_class": "equity_europe",             "benchmark": "Eurozone"},
    "Asia":                 {"source": "Pacific",  "asset_class": "equity_asia",               "benchmark": "Pacific"},
    "Oceania":              {"source": "Pacific",  "asset_class": "equity_oceania",            "benchmark": "Pacific"},
    "Middle East & Africa": {"source": "EM EMEA",  "asset_class": "equity_middle_east_africa", "benchmark": "EM EMEA"},
    "Emerging Europe":      {"source": "EM EMEA",  "asset_class": "equity_emerging_europe",    "benchmark": "EM EMEA"},
}
# Zone of each country (ISO 2-letter code) for the source indices that are split.
COUNTRY_ZONE: dict[str, str] = {
    # Pacific
    "JP": "Asia", "HK": "Asia", "SG": "Asia", "MO": "Asia", "CN": "Asia",
    "AU": "Oceania", "NZ": "Oceania",
    # EM EMEA
    "SA": "Middle East & Africa", "AE": "Middle East & Africa", "QA": "Middle East & Africa",
    "KW": "Middle East & Africa", "BH": "Middle East & Africa", "OM": "Middle East & Africa",
    "ZA": "Middle East & Africa", "EG": "Middle East & Africa", "MA": "Middle East & Africa",
    "NG": "Middle East & Africa", "KE": "Middle East & Africa",
    "PL": "Emerging Europe", "TR": "Emerging Europe", "GR": "Emerging Europe",
    "HU": "Emerging Europe", "CZ": "Emerging Europe", "RO": "Emerging Europe",
}
# Listing country of stocks whose ISIN is from an offshore / foreign domicile
# (Cayman, Bermuda, Luxembourg, US ADRs...). Others use the ISIN prefix.
COUNTRY_OVERRIDES: dict[str, str] = {
    # Pacific
    "WHARF REAL ESTATE INVESTMENT COMPANY": "HK", "CK ASSET HOLDINGS": "HK", "SANDS CHINA": "HK",
    "GRAB HOLDINGS A": "SG", "WH GROUP": "HK", "CK HUTCHISON HOLDINGS": "HK",
    "SITC INTERNATIONAL HDG.": "HK", "HONG KONG LAND HDG.": "SG", "JARDINE MATHESON HDG.": "SG",
    "CKI HOLDINGS": "HK", "SEA 'A' SPN.ADR 1:1": "SG", "FUTU HOLDINGS ADR 1:8": "HK",
    # EM EMEA
    "REINET INVESTMENTS (JSE) SCA": "ZA", "ALLEGRO": "PL", "ZABKA GROUP SOCIETE ANONYME": "PL",
    "NEPI ROCKCASTLE": "ZA", "ANGLOGOLD ASHANTI (JSE)": "ZA",
}

BONDS: dict[str, str] = {"US Aggregate": "UAGG.xlsx", "US Government": "AUSGVAL.xlsx"}
COMMODITIES: dict[str, str] = {
    "Energy": "GSENTOT.xlsx",
    "Precious Metals": "GSPMTOT.xlsx",
    "Agriculture": "GSAGTOT.xlsx",
}
COMMODITY_BENCHMARK: str = "GSCITOT.xlsx"
RISK_FREE: str = "TRUS1MT.xlsx"

# Benchmarks keyed by source index (+ "Commodities"); ZONES[z]["benchmark"]
# says which one applies to each investor region.
BENCHMARKS: dict[str, str] = {
    **{region: spec["benchmark"] for region, spec in REGIONS.items() if spec["benchmark"]},
    "Commodities": COMMODITY_BENCHMARK,
}
# Human-readable labels for display in the app.
BENCHMARK_LABELS: dict[str, str] = {
    "US": "S&P 500",
    "Eurozone": "MSCI EMU",
    "EM EMEA": "MSCI EM EMEA",
    "Pacific": "MSCI Pacific",  # used once REGIONS["Pacific"]["benchmark"] is set
    "Commodities": "S&P GSCI",
}

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
# Keys of the four source files (used in the cleaning / data-quality report).
SOURCE_ASSET_CLASS: dict[str, str] = {
    "US": "equity_us",
    "Eurozone": "equity_eurozone",
    "EM EMEA": "equity_em_emea",
    "Pacific": "equity_pacific",
}
# Output asset classes of the equity zones.
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

# Separator for unique stock identifiers: "<zone>|<stock>" (e.g. "Asia|TOYOTA MOTOR").
ASSET_ID_SEP: str = "|"

# --------------------------------------------------------------------------- #
# Backtest calendar
# --------------------------------------------------------------------------- #
PORTFOLIO_START: str = "2015-01-01"   # first portfolio date (first rebalancing)
ESTIMATION_WINDOW: int = 252          # 1-year rolling estimation window (business days)
# Outputs in data/processed/ start one year before the portfolio, so the first
# estimation window (2014) is available. Cleaning and the volatility proxies
# are computed on the full 2000-2026 history before trimming, so they are
# already warmed up on DATA_START.
DATA_START: str = "2014-01-01"
# A stock is eligible at a rebalancing date if it has valid returns on at
# least this share of the estimation window.
MIN_WINDOW_COVERAGE: float = 0.95

# Annualisation factors by sampling frequency.
PERIODS_PER_YEAR: dict[str, int] = {"D": 252, "W": 52, "M": 12}
