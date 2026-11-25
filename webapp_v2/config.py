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
BOND_INDEX = "AGG"  # index shown for the bond sleeve
ASSET_ID_SEP = core_config.ASSET_ID_SEP
# Precomputed results (scripts/precompute.py), used only while these inputs are unchanged
PRECOMPUTED_DIR = APP_DIR / "precomputed"
PRECOMPUTE_INPUTS = sorted([*PROCESSED_DIR.glob(core_config.PROCESSED_FILES["returns_daily"].format(ac="*") + ".parquet"),
                            PROCESSED_DIR / "esg_universe.parquet", PROCESSED_DIR / "rf.parquet", SLEEVE_WEIGHTS_FILE])
EQUITIES = "Equities"  # asset-class label of the regional equity sleeves

# --------------------------------------------------------------------------- #
# Model (same calendar and window as the team's backtest)
# --------------------------------------------------------------------------- #
ESTIMATION_WINDOW = core_config.ESTIMATION_WINDOW
REBALANCING_FREQ = core_config.REBALANCING_FREQ
PORTFOLIO_START = core_config.PORTFOLIO_START
TRADING_DAYS = core_config.TRADING_DAYS
RISK_FREE = "Risk-free"

# Risk level -> alpha = weight in the ERC portfolio x_erc; 1 - alpha earns the risk-free rate.
# The mix is rebalanced back to alpha every month. alpha <= 1: no leverage.
ALPHAS = {1: 0.20, 2: 0.40, 3: 0.60, 4: 0.80, 5: 1.00}
DEFAULT_LEVEL = 3
TRANSACTION_COST_BPS = 10  # fixed cost per unit of traded value (institutional investor, liquid assets)
MIN_STOCKS_PER_SLEEVE = 10
# ESG screen: share X of the worst-ESG stocks excluded from each regional equity sleeve, at each
# rebalancing, among the stocks investable on that date. Unscored stocks rank as the worst.
ESG_LEVELS = {"Off": 0.0, "Low": 0.10, "Medium": 0.30, "High": 0.50}
RC_TOLERANCE = 1e-4  # max gap between RC*_i and 1/n to call the ERC solution exact

# Projection (log-normal) and estimation error of the expected return
CI_Z = 1.96
START_VALUE = 10_000
FAN_PERCENTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
DEFAULT_HORIZON = 10  # years, projection slider default
MAX_HORIZON = 40

# Composition views (3f tabs) and the universe explorer
TOP_POSITIONS = 15  # largest holdings shown on the allocation tab
TOP_INNER = 25  # assets shown inside a sleeve on the risk-contribution tab
HIST_BINS = 20  # bins of the ESG score histogram

# --------------------------------------------------------------------------- #
# Look and feel
# --------------------------------------------------------------------------- #
CSS_FILE = APP_DIR / "assets" / "style.css"
LOGO_FILES = {"dark": APP_DIR / "assets" / "logo.svg", "light": APP_DIR / "assets" / "logo_light.svg"}
HERO_PHOTO = APP_DIR / "assets" / "leman_hero.jpg"
THEMES = {  # Streamlit theme options and chart colours of each mode (weight / risk: light and dark bars)
    "dark": {"base": "dark", "primaryColor": "#7CC4FF", "backgroundColor": "#0B0D11",
             "secondaryBackgroundColor": "#14171D", "textColor": "#E8ECF2", "grid": "rgba(255,255,255,0.07)",
             "weight": "#A9B6C8", "risk": "#2F6FC0"},
    "light": {"base": "light", "primaryColor": "#1F6FC5", "backgroundColor": "#F6F7F9",
              "secondaryBackgroundColor": "#FFFFFF", "textColor": "#151A23", "grid": "rgba(0,0,0,0.07)",
              "weight": "#C9D0DA", "risk": "#1B365D"},
}
# clearly different hues so that the lines can be told apart: blue = ours, coral = 60/40, amber = 1/N
SERIES_COLORS = {"Your portfolio": "#7CC4FF", "ERC": "#7CC4FF", "60/40": "#F08A6C", "1/N": "#F2C66D", "EW": "#9AA5B8", RISK_FREE: "#3D4656"}
PALETTE = ["#7CC4FF", "#4D8FD6", "#9B8CFF", "#5ED3B6", "#F2C66D", "#F08A6C", "#C77DD8", "#8FD694"]
CHART_TRANSITION_MS = 600

PAGES = {  # navbar order; titles and icons are in content.NAV
    "who": "pages/who_we_are.py",
    "strategy": "pages/strategy.py",
    "universe": "pages/universe_explorer.py",
    "journey": "pages/journey.py",
    "goals": "pages/goals.py",
}
PORT = 8503  # ``python run.py`` starts Streamlit on this port
