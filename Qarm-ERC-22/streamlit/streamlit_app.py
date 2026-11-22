"""Entry point of the web app (Qarm-ERC-22, "Amber" design).

Launch from the project root (the folder that contains ``.streamlit/config.toml``):

    python -m streamlit run streamlit/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
# `core` lives at the repo root; app helpers live next to this file.
for _p in (str(ROOT_DIR), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

from services import load_data_window  # noqa: E402
from web_util import APP_NAME, PAGES, apply_theme, fmt_date, render_footer, render_navbar  # noqa: E402

st.set_page_config(
    page_title=APP_NAME,
    page_icon=":material/account_balance:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

# Pages (same as the original app); the built-in menu is hidden and replaced by our navbar.
home = st.Page(APP_DIR / PAGES["home"], title="Home", icon=":material/home:", default=True)
preferences = st.Page(APP_DIR / PAGES["preferences"], title="Investor Preferences", icon=":material/tune:")
explorer = st.Page(APP_DIR / PAGES["explorer"], title="Universe Explorer", icon=":material/travel_explore:")
portfolio = st.Page(APP_DIR / "portfolio.py", title="ERC Portfolio", icon=":material/donut_large:")
methodology = st.Page(APP_DIR / PAGES["methodology"], title="Methodology", icon=":material/menu_book:")
team = st.Page(APP_DIR / "team.py", title="About us", icon=":material/groups:")

navigation = st.navigation([home, preferences, explorer, portfolio, methodology, team], position="hidden")

render_navbar(
    [
        ("Home", home),
        ("Investors", [("Investor Preferences", preferences), ("Universe Explorer", explorer)]),
        ("Portfolio", portfolio),
        ("Methodology", methodology),
        ("About Us", team),
    ],
    current=navigation,
)

navigation.run()

# Footer
window = load_data_window()
data_line = (
    f"Historical data: {fmt_date(window[0])} → {fmt_date(window[1])} (daily, USD)"
    if window is not None
    else "Historical data window unavailable."
)
render_footer([
    f"© 2026 {APP_NAME} · {data_line}",
    "Educational project, HEC Lausanne (QARM II). Not investment advice. Investments involve risk.",
])
