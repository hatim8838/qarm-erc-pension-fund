"""Entry point of the web app.

Launch from the repository root:

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
from web_util import APP_NAME, PAGES, apply_theme, fmt_date  # noqa: E402

st.set_page_config(page_title=APP_NAME, page_icon=":material/account_balance:", layout="wide")
apply_theme()

# Logo (top left) and centred top menu
LOGO_PATH = APP_DIR / "assets" / "Logo Leman.png"
if LOGO_PATH.exists():
    from PIL import Image  # noqa: E402

    _logo = Image.open(LOGO_PATH).convert("RGBA")
    _box = _logo.getchannel("A").getbbox()  # crop the transparent margins around the logo
    st.logo(_logo.crop(_box) if _box else _logo, size="large")
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] [data-testid="stTopNav"] { position: absolute; left: 50%; transform: translateX(-50%); justify-content: center; }
    [data-testid="stHeaderLogo"] { height: 5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top navigation menu (one flat list of pages)
navigation = st.navigation(
    [
        st.Page(APP_DIR / PAGES["home"], title="Home", icon=":material/home:", default=True),
        st.Page(APP_DIR / PAGES["preferences"], title="Investor Preferences", icon=":material/tune:"),
        st.Page(APP_DIR / PAGES["explorer"], title="Universe Explorer", icon=":material/travel_explore:"),
        st.Page(APP_DIR / "portfolio.py", title="ERC Portfolio", icon=":material/donut_large:"),
        st.Page(APP_DIR / PAGES["methodology"], title="Methodology", icon=":material/menu_book:"),
        st.Page(APP_DIR / "team.py", title="About us", icon=":material/groups:"),
    ],
    position="top",
)

navigation.run()

# Footer (replaces the old sidebar)
st.divider()
window = load_data_window()
if window is not None:
    st.caption(f"{APP_NAME} · Historical data: {fmt_date(window[0])} → {fmt_date(window[1])} (daily, USD)")
else:
    st.caption(f"{APP_NAME} · Historical data window unavailable.")
st.caption("Educational project, HEC Lausanne (QARM II). Not investment advice.")