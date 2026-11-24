"""Every parameter of the web app in one place: paths, model settings, colours, server."""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent  # repository root: core/ and data/processed/ are reused read-only from there

if str(ROOT) not in sys.path:  # core/ is imported, never copied
    sys.path.insert(0, str(ROOT))

from core import config as core_config  # noqa: E402

# --------------------------------------------------------------------------- #
# Data (read-only)
# --------------------------------------------------------------------------- #
PROCESSED_DIR = core_config.PROCESSED_DIR
PORTFOLIO_RETURNS_FILE = PROCESSED_DIR / "portfolio_returns.parquet"  # core's backtests and benchmarks
SLEEVE_WEIGHTS_FILE = PROCESSED_DIR / "sleeve_weights_erc.parquet"  # sleeves, in display order
CORE_ERC = "ERC"  # core's two-level ERC backtest (the baseline to reproduce)
CORE_SLEEVE_PREFIX = "ERC "  # core's level-1 ERC backtest of each sleeve: "ERC <sleeve>"
COMPOSITE_BENCHMARKS = ["60/40", "1/N"]  # pre-computed in portfolio_returns.parquet
INDEX_LABELS = core_config.BENCHMARK_LABELS  # benchmark file column -> index name
ASSET_ID_SEP = core_config.ASSET_ID_SEP
EQUITIES = "Equities"  # asset-class label of the regional equity sleeves

# --------------------------------------------------------------------------- #
# Model (same calendar and window as the team's backtest)
# --------------------------------------------------------------------------- #
ESTIMATION_WINDOW = core_config.ESTIMATION_WINDOW
REBALANCING_FREQ = core_config.REBALANCING_FREQ
PORTFOLIO_START = core_config.PORTFOLIO_START
TRADING_DAYS = core_config.TRADING_DAYS
RISK_FREE = "Risk-free"

# Target volatility sigma* of the five risk levels, proposed from the ex-ante sigma of our
# ERC portfolios (medians 2005-2026): full ERC with bonds 4.6%, Eurozone + bonds 4.0%,
# equities + commodities 8.6%, equities only 9.2%. Level 3 sits at the full ERC, level 5 at
# an all-equity ERC; without leverage a target above sigma_hat(x_erc) is capped (alpha = 1).
TARGET_VOLS = {1: 0.03, 2: 0.04, 3: 0.05, 4: 0.07, 5: 0.09}
MAX_ALPHA = 1.0  # no leverage: the risky share alpha = sigma* / sigma_hat(x_erc) is capped at 1
VAR_LEVELS = (0.95, 0.99)
TRANSACTION_COST_BPS = 10  # cost per unit of traded value (LN 3), adjustable with a slider
MAX_COST_BPS = 50
MIN_STOCKS_PER_SLEEVE = 10
ESG_MODES = ("off", "screen", "screen_rb")
ESG_SCREEN_LEVEL = 0.25  # screen = drop the worst 25% ESG scores within each region x sector
RC_TOLERANCE = 1e-4  # max gap between RC*_i and its budget to call the solution exact

# Projection (LN 6 Gaussian assumption) and estimation error (LN 3)
CI_Z = 1.96
START_VALUE = 10_000
FAN_PERCENTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
HORIZON_YEARS = (2, 5, 10, 20)  # default horizon for each answer to the horizon question
MAX_HORIZON = 40

# --------------------------------------------------------------------------- #
# Look and feel
# --------------------------------------------------------------------------- #
CSS_FILE = APP_DIR / "assets" / "style.css"
LOGO_FILES = {"dark": APP_DIR / "assets" / "logo.svg", "light": APP_DIR / "assets" / "logo_light.svg"}
HERO_PHOTO = APP_DIR / "assets" / "leman_hero.jpg"
THEMES = {  # Streamlit theme options and chart colours of each mode
    "dark": {"base": "dark", "primaryColor": "#7CC4FF", "backgroundColor": "#0B0D11",
             "secondaryBackgroundColor": "#14171D", "textColor": "#E8ECF2", "grid": "rgba(255,255,255,0.07)"},
    "light": {"base": "light", "primaryColor": "#1F6FC5", "backgroundColor": "#F6F7F9",
              "secondaryBackgroundColor": "#FFFFFF", "textColor": "#151A23", "grid": "rgba(0,0,0,0.07)"},
}
SERIES_COLORS = {"Your portfolio": "#7CC4FF", "ERC": "#7CC4FF", "ESG-RB": "#5ED3B6", "60/40": "#9AA5B8",
                 "1/N": "#5C6678", "EW": "#9AA5B8", RISK_FREE: "#3D4656"}
PALETTE = ["#7CC4FF", "#4D8FD6", "#9B8CFF", "#5ED3B6", "#F2C66D", "#F08A6C", "#C77DD8", "#8FD694"]
CHART_TRANSITION_MS = 600

PAGES = {  # navbar order; titles and icons are in content.NAV
    "who": "pages/who_we_are.py",
    "strategy": "pages/strategy.py",
    "journey": "pages/journey.py",
    "implementation": "pages/implementation.py",
    "goals": "pages/goals.py",
}
PORT = 8503  # ``python run.py`` starts Streamlit on this port
