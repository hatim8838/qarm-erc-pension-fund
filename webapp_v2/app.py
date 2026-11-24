"""Entry point of the web app: ``cd webapp_v2 && python -m streamlit run app.py``."""

from __future__ import annotations

import streamlit as st

import config as cfg
import content
from ui import theme
from ui.blocks import footer


def navigation():
    """Top navbar with the five pages (the first one is the landing page)."""
    pages = [st.Page(cfg.PAGES[key], title=title, icon=icon, default=(i == 0))
             for i, (key, (title, icon)) in enumerate(content.NAV.items())]
    return st.navigation(pages, position="top")


st.set_page_config(page_title=content.APP_NAME, page_icon=":material/waves:", layout="wide")
theme.inject_css()
theme.toggle_button()
st.logo(str(cfg.LOGO_FILES[theme.mode()]), size="large")
navigation().run()
footer()
