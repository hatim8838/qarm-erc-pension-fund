"""Shared layout, theme and formatting helpers for the Streamlit pages."""

from __future__ import annotations

import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

APP_NAME = "Léman Wealth Management"

# Page files (relative to the entry point) - one place for st.Page / st.page_link.
PAGES = {
    "home": "home_page.py",
    "preferences": "investor_preferences.py",
    "explorer": "universe_explorer.py",
    "methodology": "methodology.py",
}

# Session-state keys shared across pages.
PREFS_KEY = "investor_prefs"        # last answers of the questionnaire (survive page switches)
RESULT_KEY = "screening_result"     # last applied screening (dict from services.run_screening)

# Modules planned by the quant team; shown as text only, never as working pages.
COMING_LATER = ["ERC Optimization", "Backtesting", "Performance Analytics"]

# --------------------------------------------------------------------------- #
# Brand palette: the Léman identity (logo + banner) is black & white with serif
# type. UI chrome is charcoal and greys only; colour is reserved for data series.
# --------------------------------------------------------------------------- #
CHARCOAL = "#2B2F36"   # primary ink / brand colour (logo grey)
INK = "#1A1F2B"        # body text
SLATE = "#6B7078"      # secondary text, eyebrows
MUTED = "#A9AFB8"      # neutral reference series (light grey)
NEUTRAL = "#8A919B"    # neutral reference series (mid grey)
LIGHT_GRID = "#E3E3E0"
SURFACE = "#F7F7F5"    # cards / callouts
SERIF = "'EB Garamond', Georgia, 'Times New Roman', serif"

# Data palette: ONE hue family (slate blue, from charcoal-navy to pale grey-blue),
# so charts stay calm and on-brand. Validated as a single-hue ramp (monotone
# lightness, visible steps, lightest step >= 2:1 on white). Because the shades are
# close, charts add direct labels / line styles so identity never relies on colour alone.
# Colour follows the sleeve everywhere in the app.
SLEEVE_COLORS = {          # Amber design: blue / gold / amber / navy family
    "US": "#1976D2",
    "Eurozone": "#F9A825",
    "Pacific": "#CC6600",
    "EM EMEA": "#1A2A6C",
    "Bonds": "#7FA7D9",
    "Commodities": "#E8A15C",
}
SLATE_BLUE = "#5F7D9C"     # mid step: the one "coloured" series next to charcoal
ACCENT = SLATE_BLUE
# Portfolio / benchmark series: charcoal = the house portfolio, slate/greys = others.
SERIES_COLORS = {          # Amber design: blue = house ERC, amber / grey = references
    "ERC": "#1976D2",
    "60/40": "#CC6600",
    "1/N": "#9E9E9E",
    "S&P 500": SLEEVE_COLORS["Pacific"],
    "AGG": SLEEVE_COLORS["Bonds"],
}
# Line style per series (second cue besides the close colours).
SERIES_DASH = {"ERC": "solid", "60/40": "dash", "1/N": "dot"}
# Default sequence for charts without an explicit colour per series.
COLORWAY = [CHARCOAL, *SLEEVE_COLORS.values()]

# --------------------------------------------------------------------------- #
# Light / dark mode
# --------------------------------------------------------------------------- #
# The choice lives in session state; Streamlit's own theme (widgets, tables, menus) is
# switched through its theme config, which Streamlit re-sends to the browser at the start
# of every script run. Our CSS and the Plotly colours follow the same choice.
THEME_KEY = "theme_mode"
STREAMLIT_THEMES = {
    "Light": {"base": "light", "primaryColor": "#CC6600", "backgroundColor": "#FFFFFF",
              "secondaryBackgroundColor": "#F0F2F6", "textColor": "#262730"},
    "Dark": {"base": "dark", "primaryColor": "#FF9933", "backgroundColor": "#0F1117",
             "secondaryBackgroundColor": "#1C1F26", "textColor": "#F2F2F2"},
}
_CHART = {
    "Light": {"text": "#262730", "grid": "#F0F0F0", "line": "#E3E3E0", "axis": "#6B7078", "sep": "#FFFFFF"},
    "Dark": {"text": "#E6E6E6", "grid": "#2A2E36", "line": "#3A3F48", "axis": "#A9AFB8", "sep": "#0F1117"},
}


def theme_mode() -> str:
    return st.session_state.get(THEME_KEY, "Light")


def is_dark() -> bool:
    return theme_mode() == "Dark"


def chart_colors() -> dict[str, str]:
    """Text / grid / separator colours for Plotly in the current mode."""
    return _CHART[theme_mode()]


def _set_streamlit_theme(mode: str) -> bool:
    """Write Streamlit's theme options for ``mode``; True if anything changed."""
    from streamlit import config as st_config

    changed = False
    for name, value in STREAMLIT_THEMES[mode].items():
        if st_config.get_option(f"theme.{name}") != value:
            st_config.set_option(f"theme.{name}", value)
            changed = True
    return changed


def _toggle_theme() -> None:
    st.session_state[THEME_KEY] = "Light" if is_dark() else "Dark"
    _set_streamlit_theme(theme_mode())  # ready before the rerun that follows the click


def theme_toggle() -> None:
    """Moon / sun button that switches between light and dark mode."""
    dark = is_dark()
    st.button(
        "",
        key="theme_toggle",
        icon=":material/light_mode:" if dark else ":material/dark_mode:",
        help="Switch to light mode" if dark else "Switch to dark mode",
        on_click=_toggle_theme,
    )


# --------------------------------------------------------------------------- #
# "Amber" design layer (Qarm-ERC-22): Inter everywhere, peach / amber accents,
# navy section bars, white bordered cards and a custom top navbar.
# --------------------------------------------------------------------------- #
PEACH = "#FFCC99"        # hover fills, feature cards
AMBER = "#CC6600"        # active underline, accent borders, live badge
NAVY = "#1A2A6C"         # section-header bar
CHART_BLUE = "#1976D2"   # main chart series
CHART_GOLD = "#F9A825"   # second chart series
CARD_BORDER = "#E0E0E0"
SOFT_BG = "#F8F9FA"      # call-to-action box
FOOTER_GREY = "#888888"
SANS = "'Inter', 'Segoe UI', sans-serif"
WORDMARK = "'Playfair Display', 'EB Garamond', Georgia, serif"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea {{font-family: {SANS};}}
h1, h2, h3, h4, h5 {{font-family: {SANS} !important; font-weight: 700 !important;}}

/* Wide page with generous side margins */
.block-container {{padding: 2rem 150px 2rem 150px; max-width: none;}}
@media (max-width: 1400px) {{ .block-container {{padding-left: 4rem; padding-right: 4rem;}} }}
@media (max-width: 1100px) {{ .block-container {{padding-left: 2rem; padding-right: 2rem;}} }}

/* ---------- Top navbar ---------- */
.amber-rule {{border: none; border-top: 1px solid #DDDDDD; margin: 0;}}
.amber-brand {{display: flex; align-items: center; gap: .7rem; white-space: nowrap; padding: 4px 0;}}
.amber-brand img {{height: clamp(26px, 2.4vw, 38px); flex-shrink: 0;}}
.amber-brand span {{font-family: {WORDMARK}; font-size: clamp(18px, 1.65vw, 26px); font-weight: 700;
                    letter-spacing: .6px; color: #000; line-height: 1.3;}}
.st-key-navbar {{flex-wrap: wrap; row-gap: .4rem;}}
.st-key-navlinks {{flex-wrap: wrap;}}
.st-key-navbar [data-testid="stMarkdownContainer"] p {{margin: 0;}}
.st-key-navbar button {{
    border: none !important; background: transparent; color: #000;
    border-bottom: 3px solid transparent !important; border-radius: 8px;
    transition: all .3s ease; box-shadow: none !important;
}}
.st-key-navbar button p {{font-weight: 600; font-size: clamp(14px, 1.1vw, 17px); white-space: nowrap;}}
.st-key-navbar button {{padding: .35rem 1rem !important;}}
.st-key-navbar button:hover {{background: {PEACH}; color: #000;}}
.st-key-navbar button:focus:not(:active) {{color: #000;}}
/* dropdown (popover) panel */
div[data-testid="stPopoverBody"] {{border-radius: 5px; box-shadow: 0 8px 16px rgba(0,0,0,.2);}}
div[data-testid="stPopoverBody"] a {{border-radius: 5px; transition: all .2s ease;}}
div[data-testid="stPopoverBody"] a:hover {{background: {PEACH};}}
div[data-testid="stPopoverBody"] a p {{color: #000; font-weight: 500;}}

/* ---------- Building blocks ---------- */
div[data-testid="stMetric"] {{background: #FFFFFF; padding: 15px; border-radius: 10px;
    border: 1px solid {CARD_BORDER}; box-shadow: 0 2px 5px rgba(0,0,0,.05);}}
.section-header {{font-size: 2rem; font-weight: 600; margin: 3rem 0 1.5rem 0;
    border-left: 5px solid {NAVY}; padding-left: 15px; line-height: 1.2;}}
.amber-top {{font-size: 42px; font-weight: 700; line-height: 1.15; margin-bottom: 12px;}}
.amber-lead {{font-size: 18px; margin-bottom: 8px;}}
.feature-title {{font-size: 22px !important; font-weight: 700; margin-bottom: 8px;}}
.feature-card {{background: {PEACH}; padding: 20px; border-radius: 12px; min-height: 120px;
    display: flex; align-items: center; font-size: 16px; color: #1A1A1A;}}
/* Cards side by side get the height of the tallest one */
[data-testid="stHorizontalBlock"]:has(.feature-card) {{align-items: stretch;}}
[data-testid="stElementContainer"]:has(.feature-card) {{flex: 1 1 auto;}}
[data-testid="stElementContainer"]:has(.feature-card) > div,
[data-testid="stElementContainer"]:has(.feature-card) [data-testid="stMarkdownContainer"] {{
    height: 100%; display: flex; flex-direction: column;}}
.feature-card {{flex: 1 1 auto;}}
[class*="st-key-cta"] {{background: {SOFT_BG}; border-radius: 15px; padding: 30px; text-align: center;
    border: 1px solid #DDDDDD;}}
[class*="st-key-cta"] [data-testid="stPageLink"] {{display: flex; justify-content: center;}}
[class*="st-key-cta"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{align-self: center; width: auto !important;}}
[class*="st-key-cta"] [data-testid="stPageLink"] a {{padding: 10px 20px; border-radius: 8px;
    border: 2px solid transparent; transition: all .18s ease;}}
[class*="st-key-cta"] [data-testid="stPageLink"] a p {{color: #2E86C1; font-weight: 600; font-size: 17px;}}
[class*="st-key-cta"] [data-testid="stPageLink"] a:hover {{background: {PEACH}; border-color: {AMBER};}}
[class*="st-key-cta"] [data-testid="stPageLink"] a:hover p {{color: #000;}}
/* Page header */
.amber-eyebrow {{color: {AMBER}; font-size: .8rem; letter-spacing: .12em; font-weight: 700;
    text-transform: uppercase; margin-bottom: .2rem;}}
.amber-sub {{font-size: 18px; color: #555; margin: -4px 0 1.2rem 0; max-width: 60rem;}}
/* White cards: any container whose key starts with card_ */
[class*="st-key-card_"] {{background: #FFFFFF; border: 1px solid {CARD_BORDER}; border-radius: 12px;
    padding: 18px 20px; box-shadow: 0 2px 5px rgba(0,0,0,.05);}}
[class*="st-key-card_summary"] {{background: #FFF8F1; border-color: {PEACH};
    border-top: 4px solid {AMBER};}}
.amber-step {{display: flex; align-items: center; gap: .7rem; font-size: 20px; font-weight: 700;
    margin-bottom: .4rem;}}
.amber-step.done b {{background: {AMBER}; color: #FFFFFF;}}
.amber-step-hint {{color: #6B7078; font-size: .92rem; margin: -.2rem 0 .7rem 2.7rem;}}
.amber-step b {{display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px;
    border-radius: 50%; background: {PEACH}; color: #000; font-size: 16px; flex-shrink: 0;}}
/* Buttons outside the navbar: peach hover, amber primary */
[data-testid="stBaseButton-secondary"] {{border-radius: 8px; border: 1px solid #DDDDDD;}}
[data-testid="stBaseButton-secondary"]:hover {{background: {PEACH}; border-color: {AMBER}; color: #000;}}
[data-testid="stBaseButton-primary"] {{border-radius: 8px; font-weight: 600;}}
[data-testid="stDownloadButton"] button:hover {{background: {PEACH}; border-color: {AMBER}; color: #000;}}
/* Expanders */
[data-testid="stExpander"] details {{border-radius: 10px; border-color: {CARD_BORDER};}}
[data-testid="stExpander"] summary:hover {{background: #FFF8F1;}}
/* Smaller sub-heading inside sections and tabs */
.amber-h4 {{font-size: 18px; font-weight: 700; margin: .4rem 0 .5rem 0;}}
/* Peach callout and tags */
.amber-callout {{border-left: 4px solid {AMBER}; background: #FFF8F1; padding: .9rem 1.1rem; border-radius: 8px;
    font-size: .97rem; line-height: 1.55; margin: .4rem 0 1rem 0;}}
.amber-tag {{display: inline-block; padding: .2rem .7rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
    margin: 0 .35rem .35rem 0; background: {PEACH}; color: #000;}}
/* Tabs: bold labels, peach hover, amber underline (theme primary) */
[data-baseweb="tab-list"] {{gap: .4rem; border-bottom: 1px solid {CARD_BORDER};}}
[data-baseweb="tab"] {{padding: .5rem 1rem; border-radius: 8px 8px 0 0;}}
[data-baseweb="tab"] p {{font-size: 16px; font-weight: 600;}}
[data-baseweb="tab"]:hover {{background: #FFF8F1;}}
[data-baseweb="tab"][aria-selected="true"] p {{color: {AMBER};}}
.amber-footer {{text-align: center; color: {FOOTER_GREY}; font-size: .8rem; line-height: 1.7;}}

/* ---------- Kept from the original app ---------- */
[data-testid="stMetricValue"] {{font-weight: 600;}}
.qarm-eyebrow {{color: {SLATE}; font-size: 0.78rem; letter-spacing: .1em; font-weight: 600;
               text-transform: uppercase; margin-bottom: .1rem;}}
.qarm-badge {{display: inline-block; padding: .2rem .7rem; border-radius: 999px;
             font-size: .76rem; font-weight: 600; margin-right: .3rem;}}
.qarm-live {{background: {AMBER}; color: #FFFFFF;}}
.qarm-dev {{background: #FFFFFF; color: {AMBER}; box-shadow: inset 0 0 0 1px {AMBER};}}
</style>
"""


_DARK_CSS = f"""
<style>
.amber-rule {{border-top-color: #2E323B;}}
.amber-brand span {{color: #F2F2F2;}}
.amber-brand img {{filter: invert(1) brightness(1.4);}}
.st-key-navbar button p, .st-key-navbar button span {{color: #F2F2F2;}}
.st-key-navbar button:hover p, .st-key-navbar button:hover span {{color: #000;}}
div[data-testid="stPopoverBody"] a p {{color: #F2F2F2;}}
div[data-testid="stPopoverBody"] a:hover p {{color: #000;}}
.st-key-navbar button svg {{color: #F2F2F2; fill: currentColor;}}
.st-key-navbar button:hover svg {{color: #000;}}
[data-baseweb="tab-list"] {{border-bottom-color: #2E323B;}}
div[data-testid="stMetric"], [class*="st-key-card_"], .m-card, .qt-card, [class*="st-key-cta"] {{
    background: #1A1D24; border-color: #2E323B; box-shadow: none;}}
[class*="st-key-card_summary"] {{background: rgba(255,204,153,.07); border-color: #5A4330;
    border-top-color: {AMBER};}}
.section-header, .qt-section {{border-left-color: #6C8CFF;}}
.amber-sub, .amber-step-hint, .qt-sub, .m-cap, .m-card p, .m-card li, .qt-bio, .m-warn span {{color: #B8BCC4 !important;}}
.m-card h4, .m-warn b, .qt-name {{color: #F2F2F2;}}
[class*="st-key-cta"] [data-testid="stPageLink"] a p, .qt-link {{color: #5DADE2 !important;}}
[class*="st-key-cta"] [data-testid="stPageLink"] a:hover p, .qt-link:hover {{color: #000 !important;}}
.amber-callout, .m-warn {{background: rgba(255,204,153,.07);}}
.feature-card, .m-idea {{background: {AMBER}; color: #FFFFFF;}}
.m-idea h3, .m-idea p, .m-idea b {{color: #FFFFFF !important;}}
.qt-avatar {{border-color: #1A1D24;}}
.qt-link-off {{border-color: #3A3F48; color: #6B7078;}}
.qarm-dev {{background: transparent;}}
[data-baseweb="tab"]:hover, [data-testid="stExpander"] summary:hover {{background: rgba(255,204,153,.08);}}
[data-testid="stBaseButton-secondary"] {{border-color: #3A3F48;}}
[data-testid="stBaseButton-secondary"]:hover p, [data-testid="stDownloadButton"] button:hover p {{color: #000;}}
</style>
"""


def apply_theme() -> None:
    """Sync Streamlit's theme with the chosen mode, then inject the design CSS.

    Call once per run, from the entry point. Streamlit's theme config is shared by the
    server, so a session whose mode differs from it re-applies its own mode and reruns once.
    """
    st.session_state.setdefault(THEME_KEY, "Light")
    if _set_streamlit_theme(theme_mode()):
        st.rerun()
    st.markdown(_CSS + (_DARK_CSS if is_dark() else ""), unsafe_allow_html=True)


def section_header(title: str) -> None:
    """Large section title with the navy left bar."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def feature_card(title: str, body_html: str) -> None:
    """Bold title above a peach card (body may contain simple HTML)."""
    st.markdown(
        f"<p class='feature-title'>{title}</p><div class='feature-card'><div>{body_html}</div></div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def image_data_uri(path_str: str) -> str:
    """Local PNG as a base64 data URI (for small images inside HTML)."""
    import base64

    return "data:image/png;base64," + base64.b64encode(Path(path_str).read_bytes()).decode()


def render_navbar(items: list, current) -> None:
    """Custom top navbar: brand on the left, nav links and dropdowns on the right.

    ``items`` holds ``(label, page)`` for a link or ``(label, [(label, page), ...])`` for a
    dropdown; ``current`` is the page returned by ``st.navigation``. Navigation stays inside
    the Streamlit session (switch_page / page_link), so session state survives page changes.

    Layout is a flex row (not fixed-width columns): the brand and the links each take their
    natural width, so they can never overlap; on narrow screens the links wrap below the brand.
    """
    active_key = None
    for i, (_, target) in enumerate(items, start=1):
        pages = [p for _, p in target] if isinstance(target, list) else [target]
        if any(p.url_path == current.url_path for p in pages):
            active_key = i

    st.markdown(
        '<hr class="amber-rule">'
        + (f"<style>.st-key-navlinks > div:nth-child({active_key}) button "
           f"{{border-bottom: 3px solid {AMBER} !important;}}</style>"
           if active_key else ""),
        unsafe_allow_html=True,
    )
    with st.container(key="navbar", horizontal=True, horizontal_alignment="distribute",
                      vertical_alignment="center", gap="medium"):
        icon = APP_DIR / "assets" / "leman_icon.png"
        icon_html = f'<img src="{image_data_uri(str(icon))}" alt="">' if icon.exists() else ""
        st.markdown(f'<div class="amber-brand">{icon_html}<span>LÉMAN WEALTH</span></div>',
                    unsafe_allow_html=True, width="content")
        with st.container(key="navlinks", horizontal=True, horizontal_alignment="right",
                          vertical_alignment="center", gap="small"):
            for i, (label, target) in enumerate(items, start=1):
                if isinstance(target, list):  # dropdown
                    with st.popover(label):
                        for sub_label, page in target:
                            st.page_link(page, label=sub_label, width="stretch")
                elif st.button(label, key=f"nav_btn_{i}"):
                    st.switch_page(target)
            theme_toggle()
    st.markdown('<hr class="amber-rule" style="margin-bottom:10px">', unsafe_allow_html=True)


def render_footer(lines: list[str]) -> None:
    """Thin rule and centred grey footer."""
    st.markdown("---")
    st.markdown('<div class="amber-footer">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Page title block: amber eyebrow, large bold title, grey lead text."""
    html = f'<div class="amber-eyebrow">{eyebrow}</div>' if eyebrow else ""
    html += f'<div class="amber-top">{title}</div>'
    if subtitle:
        html += f'<div class="amber-sub">{subtitle}</div>'
    st.markdown(html, unsafe_allow_html=True)


def sub_title(text: str) -> None:
    """Small bold heading inside a section or a tab."""
    st.markdown(f'<p class="amber-h4">{text}</p>', unsafe_allow_html=True)


def step_title(number: int | str, title: str, done: bool = False, hint: str = "") -> None:
    """Numbered step heading used inside cards: peach circle, amber with a check mark once done.

    ``hint`` is a short grey line under the title (what the step is for).
    """
    badge_ = "✓" if done else number
    cls = "amber-step done" if done else "amber-step"
    sub = f'<div class="amber-step-hint">{hint}</div>' if hint else ""
    st.markdown(f'<div class="{cls}"><b>{badge_}</b>{title}</div>{sub}', unsafe_allow_html=True)


def badge(text: str, live: bool) -> str:
    """HTML status pill: green for live features, grey for in-development ones."""
    cls = "qarm-live" if live else "qarm-dev"
    return f'<span class="qarm-badge {cls}">{text}</span>'


def style_figure(fig: go.Figure, height: int = 340) -> go.Figure:
    """Common Plotly styling (fonts, margins, grid, legend)."""
    fig.update_layout(
        template="plotly_dark" if is_dark() else "plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=chart_colors()["text"]),
        colorway=COLORWAY,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(font_size=12),
        bargap=0.25,
    )
    # Style the title only when the chart has one: a title object without text is
    # shown as "undefined" in Streamlit's full-screen view.
    if fig.layout.title.text:
        fig.update_layout(title_font=dict(family="Inter, sans-serif", size=17, color=chart_colors()["text"]))
    c = chart_colors()
    fig.update_xaxes(showgrid=False, linecolor=c["line"], title_font=dict(color=c["axis"]))
    fig.update_yaxes(gridcolor=c["grid"], zeroline=False, title_font=dict(color=c["axis"]))
    return fig


# --------------------------------------------------------------------------- #
# Formatting (missing values stay visibly missing)
# --------------------------------------------------------------------------- #
MISSING = "—"


def _is_missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def fmt_int(x) -> str:
    return MISSING if _is_missing(x) else f"{int(x):,}"


def fmt_pct(x, digits: int = 1) -> str:
    """0.214 -> '21.4%'."""
    return MISSING if _is_missing(x) else f"{100 * float(x):.{digits}f}%"


def fmt_score(x, digits: int = 1) -> str:
    """ESG score on its native 0-100 scale."""
    return MISSING if _is_missing(x) else f"{float(x):.{digits}f}"


def fmt_date(ts) -> str:
    return MISSING if ts is None else ts.strftime("%d %b %Y")