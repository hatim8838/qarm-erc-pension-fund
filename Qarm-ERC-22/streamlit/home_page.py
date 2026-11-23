"""Home: who we are, the approach, the track record, how to use the app and the data behind it."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from core.config import PORTFOLIO_START
from services import (
    DataUnavailableError,
    coverage_by_zone,
    load_data_window,
    load_series_names,
    load_universe,
    universe_totals,
)
from web_util import (
    AMBER,
    APP_NAME,
    CHART_BLUE,
    FOOTER_GREY,
    PAGES,
    PEACH,
    SLEEVE_COLORS,
    chart_colors,
    fmt_date,
    fmt_int,
    is_dark,
    section_header,
    style_figure,
)

BANNER_PATH = Path(__file__).parent / "assets" / "leman_banner.png"
HERO_HEIGHT = "400px"   # fixed-height hero
BANNER_FOCUS_Y = "18%"  # vertical framing: 0% = top of the image, 100% = bottom


@st.cache_data(show_spinner=False)
def _banner_data_uri() -> str:
    """Banner as a light JPEG data URI (the PNG is 2 MB)."""
    from PIL import Image

    img = Image.open(BANNER_PATH).convert("RGB")
    img.thumbnail((1800, 1800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- #
# Hero
# --------------------------------------------------------------------------- #
try:
    st.markdown(
        f'<div role="img" aria-label="{APP_NAME}: Grow your wealth. Balance your risk." '
        f'style="width:100%; height:{HERO_HEIGHT}; border-radius:15px; '
        f"background:url({_banner_data_uri()}) center {BANNER_FOCUS_Y} / cover no-repeat;\"></div>",
        unsafe_allow_html=True,
    )
except Exception:  # Pillow or the image missing: fall back to the plain image
    st.image(str(BANNER_PATH), width="stretch")

st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Mandate
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="amber-top">A pension portfolio where no single risk dominates</div>
    <div class="amber-lead">We manage a <b>multi-asset portfolio for a pension fund</b>: global equities,
    US bonds and commodities. Instead of splitting the money equally, we split the <b>risk</b> equally:
    every building block contributes the same share of the portfolio's volatility. This is the
    <b>Equal Risk Contribution (ERC)</b> approach.</div>
    <div class="amber-lead">You choose where to invest and which asset classes to hold;
    we build the portfolio, show you where its risk comes from and how the same rules behaved in the past.</div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Approach
# --------------------------------------------------------------------------- #
section_header("Our approach")

# Sober cards: surface colour, thin border, amber only for the top line and the icon.
dark = is_dark()
SURFACE_BG = "#1A1D24" if dark else "#FFFFFF"
SURFACE_BORDER = "#2E323B" if dark else "#E6E6E6"
BODY = "#B8BCC4" if dark else "#555B66"
ICON_BG = "rgba(204,102,0,.18)" if dark else "#FFF1E3"
ICON = (
    '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="{c}" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">{p}</svg>'
)
ICONS = {  # scale (balance), globe (diversification), shield (robustness)
    "scale": '<path d="M12 3v18M5 21h14M7 7h10M7 7l-3 6a3 3 0 0 0 6 0zM17 7l-3 6a3 3 0 0 0 6 0z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
}
APPROACH = [
    ("scale", "Equal risk, not equal capital",
     "Calmer assets receive more capital, volatile ones less, so that each region, bonds and "
     "commodities carry the same share of risk."),
    ("globe", "Broad multi-asset diversification",
     "Four equity regions, US bonds and commodities: the risk is spread across assets that react "
     "differently to the same market events."),
    ("shield", "Robust by design",
     "No return forecasts: the allocation relies only on risk and correlations, which are far more "
     "stable to estimate."),
]
cards = "".join(
    f'<div class="hp-card"><div class="hp-icon">{ICON.format(c=AMBER, p=ICONS[icon])}</div>'
    f"<h4>{title}</h4><p>{text}</p></div>"
    for icon, title, text in APPROACH
)
st.markdown(
    f"""
<style>
.hp-grid {{display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;}}
.hp-card {{background: {SURFACE_BG}; border: 1px solid {SURFACE_BORDER}; border-top: 3px solid {AMBER};
    border-radius: 12px; padding: 22px 24px 24px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,{'.0' if dark else '.04'}); transition: box-shadow .2s ease, transform .2s ease;}}
.hp-card:hover {{transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,{'.35' if dark else '.08'});}}
.hp-icon {{width: 44px; height: 44px; border-radius: 10px; background: {ICON_BG};
    display: flex; align-items: center; justify-content: center; margin-bottom: 16px;}}
.hp-card h4 {{font-size: 1.12rem !important; font-weight: 700 !important; margin: 0 0 8px 0 !important;
    padding: 0 !important; line-height: 1.3;}}
.hp-card p {{color: {BODY}; font-size: .95rem; line-height: 1.6; margin: 0;}}
@media (max-width: 900px) {{ .hp-grid {{grid-template-columns: 1fr;}} }}

/* Stepper: numbered circles on a thin line, one link per step */
.st-key-hp_steps {{position: relative;}}
.st-key-hp_steps::before {{content: ""; position: absolute; top: 19px; left: 12.5%; right: 12.5%;
    height: 2px; background: {SURFACE_BORDER}; z-index: 0;}}
.hp-step {{text-align: center; position: relative; z-index: 1;}}
.hp-num {{width: 40px; height: 40px; border-radius: 50%; margin: 0 auto 14px auto; background: {SURFACE_BG};
    border: 2px solid {AMBER}; color: {AMBER}; font-weight: 700; font-size: 1rem;
    display: flex; align-items: center; justify-content: center;}}
.hp-step h4 {{font-size: 1.02rem !important; font-weight: 700 !important; margin: 0 0 6px 0 !important;
    padding: 0 !important;}}
.hp-step p {{color: {BODY}; font-size: .9rem; line-height: 1.55; margin: 0 auto; max-width: 15rem;}}
.st-key-hp_steps [data-testid="stPageLink"] {{display: flex; justify-content: center;}}
.st-key-hp_steps [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{
    align-self: center; width: auto !important; margin-top: 4px;}}
.st-key-hp_steps [data-testid="stPageLink"] a p {{color: {AMBER}; font-weight: 600; font-size: .9rem;}}
.st-key-hp_steps [data-testid="stPageLink"] a:hover {{background: {ICON_BG};}}

/* The one solid amber button of the page */
.st-key-cta_main [data-testid="stPageLink"] a {{background: {AMBER}; border-color: {AMBER};}}
.st-key-cta_main [data-testid="stPageLink"] a p,
.st-key-cta_main [data-testid="stPageLink"] a span {{color: #FFFFFF !important;}}
.st-key-cta_main [data-testid="stPageLink"] a:hover {{background: #B35900; border-color: #B35900;}}
</style>
<div class="hp-grid">{cards}</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# How it works: a 4-step process
# --------------------------------------------------------------------------- #
section_header("How it works")
STEPS = [
    ("Your preferences", "Choose regions, industries and asset classes.", PAGES["preferences"], "Set preferences"),
    ("Your universe", "Explore the stocks that match your choices.", PAGES["explorer"], "Explore"),
    ("Your portfolio", "The allocation, where the risk comes from and its history.", "portfolio.py", "View portfolio"),
    ("Our methodology", "The method in plain language, the data and its limits.", PAGES["methodology"], "Read more"),
]
with st.container(key="hp_steps"):
    for col, (i, (title, text, page, link)) in zip(st.columns(4, gap="medium"), enumerate(STEPS, start=1)):
        with col:
            st.markdown(f'<div class="hp-step"><div class="hp-num">{i}</div><h4>{title}</h4><p>{text}</p></div>',
                        unsafe_allow_html=True)
            st.page_link(page, label=link, icon=":material/arrow_forward:")

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
_, cta_col, _ = st.columns([1, 2, 1])
with cta_col, st.container(key="cta_main"):
    st.markdown("### Ready to build your portfolio?")
    st.markdown("Set your preferences in a few clicks; the risk-balanced portfolio follows.")
    st.page_link(PAGES["preferences"], label="Start with your preferences", icon=":material/arrow_forward:")

# --------------------------------------------------------------------------- #
# Data behind the portfolio
# --------------------------------------------------------------------------- #
section_header("The data behind it")

try:
    universe = load_universe()
except DataUnavailableError as exc:
    st.error(str(exc))
    st.stop()

totals = universe_totals(universe)
window = load_data_window()
bonds = load_series_names("bonds")
commodities = load_series_names("commodities")
cov = coverage_by_zone(universe)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stocks in the universe", fmt_int(totals["stocks"]),
          help=f"Index constituents across the {len(cov)} equity regions.")
c2.metric("Equity regions", fmt_int(len(cov)), help="US, Eurozone, Pacific and EM EMEA.")
c3.metric("Eligible at portfolio start", fmt_int(totals["eligible_at_start"]),
          help=f"Stocks with a sufficiently complete one-year history on {PORTFOLIO_START}.")
c4.metric("Bond & commodity indices", fmt_int(len(bonds) + len(commodities)),
          help=f"Bonds: {', '.join(bonds) or '—'}. Commodities: {', '.join(commodities) or '—'}.")

st.write("")
chart_col, table_col = st.columns([5, 7], gap="large")
with chart_col:
    st.markdown("<p class='feature-title'>Stocks per region</p>", unsafe_allow_html=True)
    zones_rev = cov.index[::-1]  # first region on top
    fig = go.Figure()
    fig.add_bar(name="All constituents", y=zones_rev, x=cov.loc[zones_rev, "stocks"],
                orientation="h", marker_color=PEACH)
    fig.add_bar(name=f"Eligible on {PORTFOLIO_START}", y=zones_rev, x=cov.loc[zones_rev, "eligible_at_start"],
                orientation="h", marker_color=CHART_BLUE)
    fig.update_layout(barmode="overlay", xaxis_title="Number of stocks")
    fig = style_figure(fig, height=320)
    fig.update_layout(margin=dict(t=30))
    fig.update_xaxes(showgrid=True, gridcolor=chart_colors()["grid"])
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig)
with table_col:
    st.markdown("<p class='feature-title'>Coverage by region</p>", unsafe_allow_html=True)
    # Clean HTML table: colour dot per region, index name as a subtitle, eligible share as a thin bar.
    _dark = is_dark()
    _line = "#2E323B" if _dark else "#ECECEC"
    _sub = "#8B919B" if _dark else "#7A808A"
    _track = "#2A2E36" if _dark else "#F1F2F4"

    def _index_name(src: str) -> str:  # "US (S&P 500)" -> "S&P 500"
        return src[src.find("(") + 1:src.rfind(")")] if "(" in src else src

    def _dot(zone: str) -> str:  # navy is invisible on dark backgrounds
        c = SLEEVE_COLORS.get(zone, CHART_BLUE)
        return "#6C8CFF" if _dark and c.upper() == "#1A2A6C" else c

    rows = ""
    for zone, r in cov.iterrows():
        share = r["eligible_at_start"] / r["stocks"] if r["stocks"] else 0.0
        rows += (
            f'<tr><td><span class="cv-dot" style="background:{_dot(zone)}"></span>'
            f'<span class="cv-zone">{zone}</span><span class="cv-idx">{_index_name(str(r["source_index"]))}</span></td>'
            f'<td class="num">{int(r["stocks"]):,}</td><td class="num">{int(r["eligible_at_start"]):,}</td>'
            f'<td><div class="cv-share"><div class="cv-bar"><span style="width:{share:.0%}"></span></div>'
            f'<span class="cv-pct">{share:.0%}</span></div></td></tr>'
        )
    tot_s, tot_e = int(cov["stocks"].sum()), int(cov["eligible_at_start"].sum())
    tot_share = tot_e / tot_s if tot_s else 0.0
    st.markdown(
        f"""
<style>
.cv-table {{width: 100%; border-collapse: collapse; font-size: .95rem; font-variant-numeric: tabular-nums;
    border: none !important; background: transparent !important;}}
.cv-table th, .cv-table td {{border-left: none !important; border-right: none !important; border-top: none !important;
    background: transparent !important;}}
.cv-table th {{text-align: left; font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: {_sub}; padding: 0 12px 10px 0; border-bottom: 2px solid {_line} !important;}}
.cv-table td {{padding: 13px 12px 13px 0; border-bottom: 1px solid {_line} !important; vertical-align: middle;}}
.cv-table th.num, .cv-table td.num {{text-align: right; padding-right: 24px;}}
.cv-dot {{display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px;}}
.cv-zone {{font-weight: 600;}}
.cv-idx {{display: block; margin-left: 20px; color: {_sub}; font-size: .8rem;}}
.cv-share {{display: flex; align-items: center; gap: 10px;}}
.cv-bar {{flex: 1; height: 6px; border-radius: 3px; background: {_track}; overflow: hidden; min-width: 60px;}}
.cv-bar span {{display: block; height: 100%; background: {AMBER}; border-radius: 3px;}}
.cv-pct {{width: 3rem; text-align: right; font-weight: 600;}}
.cv-table tr.cv-total td {{border-bottom: none !important; font-weight: 700; padding-top: 14px;}}
.cv-note {{color: {_sub}; font-size: .8rem; margin-top: 10px;}}
</style>
<table class="cv-table">
  <thead><tr><th>Region</th><th class="num">Stocks</th><th class="num">Eligible</th><th>Share eligible</th></tr></thead>
  <tbody>{rows}
  <tr class="cv-total"><td>Total</td><td class="num">{tot_s:,}</td><td class="num">{tot_e:,}</td>
  <td><div class="cv-share"><div class="cv-bar"><span style="width:{tot_share:.0%}"></span></div>
  <span class="cv-pct">{tot_share:.0%}</span></div></td></tr></tbody>
</table>
<div class="cv-note">Eligible: a full one-year price history on {PORTFOLIO_START}, the portfolio start.</div>
""",
        unsafe_allow_html=True,
    )

window_txt = f"{fmt_date(window[0])} to {fmt_date(window[1])}" if window is not None else "the full history"
st.markdown(
    f'<span style="color:{FOOTER_GREY};font-size:.85rem">Source: Datastream, daily total returns in USD, '
    f"{window_txt}. Historical data, not live quotes.</span>",
    unsafe_allow_html=True,
)
