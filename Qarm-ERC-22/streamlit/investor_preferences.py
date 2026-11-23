"""Investor Preferences (Amber design): regions, industries, asset classes, plus one advanced option.

UX: three short steps with live feedback (step check marks, counts on every choice, the risk
split of the portfolio), a summary panel with one main action, and clear next steps.

ESG is not used by the web app: the selection always runs with the ESG level "None"
(no ESG filter), so every stock of the chosen regions and industries is kept.
The result is stored in session state and explored on the Universe Explorer page.
"""

from __future__ import annotations

import logging
import re
from copy import copy

import streamlit as st

from core.config import ESTIMATION_WINDOW, ICB_INDUSTRIES, PORTFOLIO_START, ZONES
from services import (
    DEFAULT_PREFERENCES,
    ZONE_LABELS,
    DataUnavailableError,
    cached_screening,
    industry_counts,
    load_universe,
    missing_industries_by_zone,
    scope_counts,
    validate_preferences,
)
from web_util import (
    PAGES,
    PREFS_KEY,
    RESULT_KEY,
    SLEEVE_COLORS,
    fmt_int,
    page_header,
    section_header,
    step_title,
)

logger = logging.getLogger(__name__)

# Widget keys. "Industries" is a two-choice radio (all / choose) stored as a bool in the prefs.
W_REGIONS = "w_regions"
W_IND_MODE = "w_industry_mode"
W_SECTORS = "w_sectors"
W_COMMOD = "w_include_commodities"
W_ELIGIBLE = "w_eligible_only"
ALL_IND, CHOOSE_IND = "All industries", "Let me choose"
LIGHT_TILES = {"Eurozone", "Bonds", "Commodities"}  # dark text on the light colours

st.markdown(
    """
<style>
.ip-blocks {display:flex; flex-wrap:wrap; gap:8px; margin:.3rem 0 .4rem 0;}
.ip-block {border-radius:10px; padding:.45rem .8rem; font-size:.85rem; font-weight:700; line-height:1.2;}
.ip-block small {display:block; font-weight:500; font-size:.72rem; opacity:.9;}
.ip-big {font-size:2.6rem; font-weight:700; line-height:1.05; margin:.1rem 0 0 0;}
.ip-big-sub {color:#6B7078; font-size:.9rem; margin-bottom:.2rem;}
.ip-check {font-size:.95rem; line-height:1.5; margin:.25rem 0;}
.ip-check b {display:inline-block; width:1.3rem;}
.ip-ok {color:#2E7D32;} .ip-miss {color:#C62828;}
.ip-fixed {display:inline-block; padding:.15rem .6rem; border-radius:999px; font-size:.75rem; font-weight:700;
           background:#F0F2F6; color:#555; margin-left:.4rem;}
</style>
""",
    unsafe_allow_html=True,
)

page_header(
    "Investor Preferences",
    "Three quick choices define where your money can be invested. We then build a portfolio in which "
    "every block carries the same share of risk.",
    eyebrow="Léman Wealth Management · Step 1 of 3",
)

try:
    universe = load_universe()
except DataUnavailableError as exc:
    st.error(str(exc))
    st.stop()

# --------------------------------------------------------------------------- #
# State: answers persist across pages in PREFS_KEY; widgets are seeded from it.
# --------------------------------------------------------------------------- #
prefs = st.session_state.setdefault(PREFS_KEY, copy(DEFAULT_PREFERENCES))
_seed = {
    W_REGIONS: lambda: copy(prefs.get("regions", DEFAULT_PREFERENCES["regions"])),
    W_IND_MODE: lambda: ALL_IND if prefs.get("all_industries", True) else CHOOSE_IND,
    W_SECTORS: lambda: copy(prefs.get("sectors", [])),
    W_COMMOD: lambda: prefs.get("include_commodities", True),
    W_ELIGIBLE: lambda: prefs.get("eligible_only", True),
}
for key, value in _seed.items():
    if key not in st.session_state:
        st.session_state[key] = value()


def _plain_warning(text: str) -> str | None:
    """Rewrite the selection warnings of ``core`` in plain words, without ESG vocabulary."""
    m = re.match(r"(.+?): only (\d+) stocks exist in the selected sectors \(minimum (\d+)\)", text)
    if m:
        zone, n, minimum = m.groups()
        return (f"{zone} has only {n} stock(s) in the chosen industries (we recommend at least {minimum}). "
                "The portfolio still works, but this region will rely on very few companies.")
    m = re.match(r"(.+?): no stocks in the selected sectors", text)
    if m:
        return f"{m.group(1)} has no stock in the chosen industries, so it is left out of your universe."
    return None if "ESG" in text else text


def _reset() -> None:
    d = DEFAULT_PREFERENCES
    st.session_state.update({
        W_REGIONS: copy(d["regions"]), W_IND_MODE: ALL_IND if d["all_industries"] else CHOOSE_IND,
        W_SECTORS: copy(d["sectors"]), W_COMMOD: d["include_commodities"], W_ELIGIBLE: d["eligible_only"],
    })
    st.session_state[PREFS_KEY] = copy(d)
    st.session_state.pop(RESULT_KEY, None)


def _all_regions() -> None:
    st.session_state[W_REGIONS] = list(ZONES)


def _no_regions() -> None:
    st.session_state[W_REGIONS] = []


zone_counts = universe["zone"].value_counts()
# Top to bottom: the three questions, the advanced option, then the summary with "Build my universe".
form_col = st.container()
side_col = st.container()

with form_col:
    # 1. Regions ------------------------------------------------------------
    regions = st.session_state[W_REGIONS] or []
    with st.container(key="card_regions"):
        step_title(1, "Where do you want to invest?", done=bool(regions),
                   hint="Pick one or more equity regions. The number is the stocks in each index.")
        st.pills(
            "Equity regions",
            options=list(ZONES),
            selection_mode="multi",
            format_func=lambda z: f"{ZONE_LABELS[z]} · {int(zone_counts.get(z, 0))}",
            key=W_REGIONS,
            label_visibility="collapsed",
        )
        q1, q2, _ = st.columns([1, 1, 7], gap="small")
        q1.button("Select all", on_click=_all_regions, type="tertiary", icon=":material/done_all:")
        q2.button("Clear", on_click=_no_regions, type="tertiary", icon=":material/close:")
        with st.expander("What is in each region?"):
            st.markdown(
                "- **US**: the S&P 500, the 500 largest US companies.\n"
                "- **Eurozone**: MSCI EMU, large and mid caps of the euro-area countries.\n"
                "- **Pacific**: MSCI Pacific (Japan, Australia, Hong Kong, Singapore, New Zealand).\n"
                "- **EM EMEA**: MSCI Emerging Markets Europe, Middle East & Africa."
            )
    regions = st.session_state[W_REGIONS] or []

    # 2. Industries ---------------------------------------------------------
    with st.container(key="card_industries"):
        mode = st.session_state.get(W_IND_MODE) or ALL_IND
        sectors = st.session_state[W_SECTORS] or []
        step_title(2, "Which industries?", done=(mode == ALL_IND or bool(sectors)),
                   hint="Keep them all for the broadest diversification, or focus on a few.")
        mode = st.radio("Industries", [ALL_IND, CHOOSE_IND], key=W_IND_MODE, horizontal=True,
                        label_visibility="collapsed")
        all_industries = mode == ALL_IND
        if not all_industries:
            counts = industry_counts(universe, regions)
            st.pills(
                "ICB industries",
                options=ICB_INDUSTRIES,
                selection_mode="multi",
                format_func=lambda i: f"{i} · {counts[i]}",
                key=W_SECTORS,
                label_visibility="collapsed",
            )
            st.caption("The number is the stocks of that industry in your regions.")
            gaps = missing_industries_by_zone(universe, regions)
            if gaps:
                st.caption("Not available: " + "; ".join(f"{z} has no {', '.join(i)}" for z, i in gaps.items()) + ".")
    sectors = st.session_state[W_SECTORS] or []

    # 3. Asset classes -----------------------------------------------------
    with st.container(key="card_assets"):
        step_title(3, "Which other asset classes?", done=True,
                   hint="Bonds are the calm core of a pension portfolio; commodities are optional.")
        st.markdown('**Bonds** (US Aggregate)<span class="ip-fixed">Always included</span>', unsafe_allow_html=True)
        include_commodities = st.toggle("Add commodities (Energy, Precious Metals, Agriculture)", key=W_COMMOD,
                                        help="They protect against inflation, as in 2022, but have low long-run returns.")
        blocks = list(regions) + ["Bonds"] + (["Commodities"] if include_commodities else [])
        n = len(blocks)
        if regions:
            tiles = "".join(
                f'<span class="ip-block" style="background:{SLEEVE_COLORS[b]};'
                f'color:{"#000" if b in LIGHT_TILES else "#FFF"}">{b}<small>1/{n} of risk</small></span>'
                for b in blocks
            )
            st.markdown(f"Your portfolio will have **{n} blocks**, each carrying the same share of risk:"
                        f'<div class="ip-blocks">{tiles}</div>', unsafe_allow_html=True)

    # Advanced ---------------------------------------------------------------
    with st.expander("Advanced option"):
        eligible_only = st.toggle("Only stocks with a full price history (recommended)", key=W_ELIGIBLE)
        st.caption(
            f"Keeps the stocks that already had one full year of prices ({ESTIMATION_WINDOW} trading days) "
            f"on {PORTFOLIO_START}, the portfolio start, so that their risk can be measured. "
            "Switch it off only to explore the whole index."
        )

# Remember the answers for the next visit.
prefs.update({
    "regions": copy(regions), "all_industries": all_industries, "sectors": copy(sectors),
    "eligible_only": eligible_only, "include_commodities": include_commodities,
})

params, errors = validate_preferences(regions, all_industries, sectors, "None", eligible_only, universe,
                                     include_commodities=include_commodities)
applied = st.session_state.get(RESULT_KEY)
stale = applied is not None and params is not None and applied["params"] != params

with side_col:
    with st.container(key="card_summary"):
        st.markdown("<p class='feature-title'>Your selection</p>", unsafe_allow_html=True)
        preview = scope_counts(universe, regions, None if all_industries else sectors)
        n_universe = preview["eligible"] if eligible_only else preview["in_scope"]
        num_col, list_col, act_col = st.columns([2, 4, 3], gap="large", vertical_alignment="center")
        num_col.markdown(
            f'<div class="ip-big">{fmt_int(n_universe)}</div>'
            f'<div class="ip-big-sub">stocks in your universe'
            + (f" (out of {fmt_int(preview['in_scope'])} in these indices)" if eligible_only else "")
            + "</div>",
            unsafe_allow_html=True,
        )

        def _line(ok: bool, label: str, value: str) -> str:
            mark = '<b class="ip-ok">✓</b>' if ok else '<b class="ip-miss">✗</b>'
            return f'<div class="ip-check">{mark}<strong>{label}:</strong> {value}</div>'

        ind_txt = "all" if all_industries else (", ".join(sectors) if sectors else "choose at least one")
        list_col.markdown(
            _line(bool(regions), "Regions", ", ".join(regions) if regions else "choose at least one")
            + _line(all_industries or bool(sectors), "Industries", ind_txt)
            + _line(True, "Asset classes", "equities, bonds" + (", commodities" if include_commodities else "")),
            unsafe_allow_html=True,
        )
        with act_col:
            submitted = st.button("Build my universe", type="primary", icon=":material/arrow_forward:",
                                  disabled=params is None, width="stretch")
            st.button("Reset to defaults", on_click=_reset, type="tertiary", icon=":material/restart_alt:")
        for err in errors:
            st.warning(err, icon=":material/error:")
        if stale:
            st.markdown('<div class="amber-callout">You changed your answers. Click <b>Build my universe</b> '
                        "to update the results.</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Run the selection
# --------------------------------------------------------------------------- #
if submitted and params is not None:
    try:
        st.session_state[RESULT_KEY] = cached_screening(params)
        applied = st.session_state[RESULT_KEY]
        stale = False
        st.toast(f"Universe ready: {fmt_int(applied['funnel']['selected'])} stocks.", icon=":material/check_circle:")
    except DataUnavailableError as exc:
        st.error(str(exc))
    except (ValueError, KeyError, FileNotFoundError) as exc:
        st.error(f"The universe could not be built with these answers: {exc}")
    except Exception as exc:  # unexpected: log it and show a readable message
        logger.exception("Screening failed")
        st.error("Unexpected error while building the universe. Please adjust the answers or reload the app.")
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")

# --------------------------------------------------------------------------- #
# Result and next steps
# --------------------------------------------------------------------------- #
if applied is not None:
    p, funnel = applied["params"], applied["funnel"]
    section_header("Your universe" + (" (previous answers)" if stale else ""))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stocks", fmt_int(funnel["selected"]))
    k2.metric("Regions", len(p.regions), help=", ".join(p.regions))
    k3.metric("Industries", "All" if p.sectors is None else len(p.sectors),
              help=None if p.sectors is None else ", ".join(p.sectors))
    k4.metric("Portfolio blocks", p.n_sleeves, help=f"Each carries 1/{p.n_sleeves} of the risk.")
    if not p.eligible_only:
        st.caption(f"{fmt_int(funnel['selected_eligible'])} of these stocks have a full price history on "
                   f"{PORTFOLIO_START}.")
    for w in filter(None, map(_plain_warning, applied["warnings"])):
        st.warning(w, icon=":material/info:")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    # Same height for both boxes: the row stretches its columns, each box fills its column,
    # and the link sits at the bottom so the two links line up.
    st.markdown(
        """<style>
        [data-testid="stHorizontalBlock"]:has(.st-key-cta_explore) {align-items: stretch;}
        [data-testid="stLayoutWrapper"]:has(> .st-key-cta_explore),
        [data-testid="stLayoutWrapper"]:has(> .st-key-cta_portfolio) {flex: 1 1 auto;}
        .st-key-cta_explore, .st-key-cta_portfolio {display: flex; flex-direction: column;}
        .st-key-cta_explore > div:last-child, .st-key-cta_portfolio > div:last-child {margin-top: auto;}
        </style>""",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(key="cta_explore"):
        st.markdown("### Step 2 · Explore the stocks")
        st.markdown("See which companies are in your universe, by region and industry.")
        st.page_link(PAGES["explorer"], label="Open the Universe Explorer", icon=":material/travel_explore:")
    with c2, st.container(key="cta_portfolio"):
        st.markdown("### Step 3 · See your portfolio")
        st.markdown("The risk-balanced allocation built from this universe.")
        st.page_link("portfolio.py", label="Open the ERC Portfolio", icon=":material/donut_large:")
