"""Entry point of the web app.

Launch from the repository root:

    streamlit run streamlit/streamlit_app.py
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
from web_util import APP_NAME, COMING_LATER, PAGES, apply_theme, fmt_date  # noqa: E402

st.set_page_config(page_title=APP_NAME, page_icon=":material/account_balance:", layout="wide")
apply_theme()

navigation = st.navigation(
    {
        "Overview": [
            st.Page(APP_DIR / PAGES["home"], title="Home", icon=":material/home:", default=True),
        ],
        "Investor": [
            st.Page(APP_DIR / PAGES["preferences"], title="Investor Preferences", icon=":material/tune:"),
            st.Page(APP_DIR / PAGES["explorer"], title="Universe Explorer", icon=":material/travel_explore:"),
        ],
        "Transparency": [
            st.Page(APP_DIR / PAGES["methodology"], title="Methodology", icon=":material/menu_book:"),
        ],
        "About us": [
            st.Page(APP_DIR / "team.py", title="Team", icon=":material/groups:"),
        ],
    }
)

with st.sidebar:
    st.markdown(f"**{APP_NAME}**")
    window = load_data_window()
    if window is not None:
        st.caption(f"Historical data: {fmt_date(window[0])} → {fmt_date(window[1])} (daily, USD)")
    else:
        st.caption("Historical data window unavailable.")
    st.divider()
    st.caption("Coming later (in development)")
    st.caption("\n".join(f"- {name}" for name in COMING_LATER))
    st.divider()
    st.caption("Educational project, HEC Lausanne (QARM II). Not investment advice.")

navigation.run()
