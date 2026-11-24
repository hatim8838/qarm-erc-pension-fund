"""Dark / light mode: one session value drives the CSS variables, Streamlit's theme and Plotly."""

from __future__ import annotations

import streamlit as st
from streamlit import config as st_config

import config as cfg
import content

THEME_KEY = "theme"
STREAMLIT_OPTIONS = ("base", "primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor")


def mode() -> str:
    """Current mode. A new session starts in the mode Streamlit's theme is in, which is a
    server-wide option: reusing it keeps the first page consistent with the widgets."""
    return st.session_state.get(THEME_KEY, st_config.get_option("theme.base") or "dark")


def colors() -> dict[str, str]:
    """Colours of the current mode (text, background, grid...) for the charts."""
    return cfg.THEMES[mode()]


def _apply_streamlit_theme() -> None:
    """Streamlit's own widgets follow its theme options, re-sent to the browser on each run."""
    for name in STREAMLIT_OPTIONS:
        if st_config.get_option(f"theme.{name}") != colors()[name]:
            st_config.set_option(f"theme.{name}", colors()[name])


def _toggle() -> None:
    """Switch mode before the rerun that follows the click."""
    st.session_state[THEME_KEY] = "light" if mode() == "dark" else "dark"
    _apply_streamlit_theme()


def inject_css() -> None:
    """Stylesheet plus a marker element: :root:has(.theme-light) swaps the CSS variables."""
    _apply_streamlit_theme()
    css = cfg.CSS_FILE.read_text(encoding="utf-8")
    marker = '<div class="theme-light"></div>' if mode() == "light" else ""
    # st.markdown keeps <style> tags; st.html drops a style-only block in this Streamlit version.
    st.markdown(f"<style>{css}</style>{marker}", unsafe_allow_html=True)


def toggle_button() -> None:
    """Moon / sun button, pinned into the top navbar by CSS (.st-key-theme_toggle)."""
    st.button("", key="theme_toggle", icon=content.THEME_BUTTON[mode()], on_click=_toggle)
