"""Investor Preferences: regions, industries, ESG ambition and start eligibility.

Runs the real ``core.esg.investor_selection`` (through ``services``) when the
investor clicks *Screen universe*; the result is stored in session state and
explored on the Universe Explorer page.
"""

from __future__ import annotations

import logging
from copy import copy

import streamlit as st

from core.config import ESTIMATION_WINDOW, ICB_INDUSTRIES, MIN_WINDOW_COVERAGE, PORTFOLIO_START, ZONES
from core.esg import ESG_LEVELS, RELAX_STEP
from services import (
    DEFAULT_PREFERENCES,
    ESG_LEVEL_DESCRIPTIONS,
    MIN_STOCKS,
    ZONE_LABELS,
    DataUnavailableError,
    cached_screening,
    industry_counts,
    load_universe,
    missing_industries_by_zone,
    scope_counts,
    validate_preferences,
)
from web_util import PAGES, PREFS_KEY, RESULT_KEY, fmt_int, fmt_pct, page_header

logger = logging.getLogger(__name__)

# Widget key of each preference field.
WIDGETS = {
    "regions": "w_regions",
    "all_industries": "w_all_industries",
    "sectors": "w_sectors",
    "esg_label": "w_esg_label",
    "eligible_only": "w_eligible_only",
}

page_header(
    "Investor Preferences",
    "Tell us where you want to invest and how demanding the ESG screen should be. "
    "The result is a screened stock universe, the input of the future ERC optimization.",
    eyebrow="Step 1 · Investor",
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
for field, key in WIDGETS.items():
    if key not in st.session_state:
        st.session_state[key] = copy(prefs[field])


def _reset() -> None:
    for f, k in WIDGETS.items():
        st.session_state[k] = copy(DEFAULT_PREFERENCES[f])
    st.session_state[PREFS_KEY] = copy(DEFAULT_PREFERENCES)
    st.session_state.pop(RESULT_KEY, None)


form_col, side_col = st.columns([3, 2], gap="large")

with form_col:
    # 1. Regions ------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### 1 · Investor regions")
        st.pills(
            "Investor regions",
            options=list(ZONES),
            selection_mode="multi",
            format_func=lambda z: ZONE_LABELS[z],
            key=WIDGETS["regions"],
            label_visibility="collapsed",
        )
        st.caption(
            "Six investor zones built from four source indices: MSCI Pacific is split into Asia and "
            "Oceania, MSCI EM EMEA into Middle East & Africa and Emerging Europe (by listing country)."
        )
    regions = st.session_state[WIDGETS["regions"]] or []

    # 2. Industries ---------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### 2 · Industries (ICB)")
        all_industries = st.toggle("All industries", key=WIDGETS["all_industries"])
        counts = industry_counts(universe, regions)
        st.multiselect(
            "ICB industries",
            options=ICB_INDUSTRIES,
            format_func=lambda i: f"{i} · {counts[i]}" if counts[i] else f"{i} · none in selected regions",
            key=WIDGETS["sectors"],
            disabled=all_industries,
            placeholder="Choose one or more industries",
            help="The number after each industry is the count of stocks in the selected regions.",
        )
        gaps = missing_industries_by_zone(universe, regions)
        if gaps:
            st.caption(
                "Not represented: "
                + "; ".join(f"{zone} has no {', '.join(inds)}" for zone, inds in gaps.items())
                + "."
            )
    sectors = st.session_state[WIDGETS["sectors"]]

    # 3. ESG ambition -------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### 3 · ESG ambition")
        esg_label = st.select_slider("ESG ambition", options=list(ESG_LEVELS), key=WIDGETS["esg_label"],
                                     label_visibility="collapsed")
        st.markdown(f"**{esg_label}** (percentile cut {ESG_LEVELS[esg_label]:.2f}): "
                    f"{ESG_LEVEL_DESCRIPTIONS[esg_label]}")
        with st.expander("How the ESG screen works"):
            st.markdown(
                "- **Best-in-class, not an absolute threshold.** Each stock is compared with its peers "
                "in the same *investor zone × ICB industry*. “High” keeps scores at or above the 75th "
                "percentile of the peer group: it does **not** mean an ESG score ≥ 75/100.\n"
                "- Stocks **without an ESG score** are excluded as soon as the ambition is above None.\n"
                f"- **Automatic relaxation:** if fewer than {MIN_STOCKS} stocks of a zone pass the cut, "
                f"the cut is lowered for that zone in steps of {RELAX_STEP:.2f} until {MIN_STOCKS} "
                "stocks survive (or the cut reaches 0). Every relaxation is reported after screening.\n"
                "- ESG scores are the latest available (static) scores; see Methodology for the "
                "look-ahead caveat."
            )

    # 4. Eligibility --------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### 4 · Portfolio-start eligibility")
        eligible_only = st.toggle(f"Eligible at portfolio start only ({PORTFOLIO_START})",
                                  key=WIDGETS["eligible_only"])
        st.caption(
            f"A stock is eligible if it has valid returns on at least {MIN_WINDOW_COVERAGE:.0%} of the "
            f"{ESTIMATION_WINDOW}-business-day window before {PORTFOLIO_START}, the first rebalancing date. "
            "Eligibility is fixed at that date. Switch it off only for exploratory analysis."
        )

# Remember the answers for the next visit.
prefs.update({f: copy(st.session_state[k]) for f, k in WIDGETS.items()})

params, errors = validate_preferences(regions, all_industries, sectors, esg_label, eligible_only, universe)
applied = st.session_state.get(RESULT_KEY)

with side_col:
    with st.container(border=True):
        st.markdown("##### Your selection")
        preview = scope_counts(universe, regions, None if all_industries else sectors)
        m1, m2 = st.columns(2)
        m1.metric("Stocks in scope", fmt_int(preview["in_scope"]),
                  help="Constituents of the selected regions and industries, before any filter.")
        m2.metric(f"Eligible on {PORTFOLIO_START}", fmt_int(preview["eligible"]))
        st.markdown(
            f"**Regions:** {', '.join(regions) if regions else '—'}  \n"
            f"**Industries:** {'All' if all_industries else (', '.join(sectors) if sectors else '—')}  \n"
            f"**ESG ambition:** {esg_label}  \n"
            f"**Universe:** {'eligible at start only' if eligible_only else 'all constituents'}"
        )
        for err in errors:
            st.warning(err, icon=":material/error:")
        if applied is not None and params is not None and applied["params"] != params:
            st.caption(":orange[Your changes are not applied yet.]")

        b1, b2 = st.columns([3, 2])
        submitted = b1.button("Screen universe", type="primary", icon=":material/filter_alt:",
                              disabled=params is None, width="stretch")
        b2.button("Reset", on_click=_reset, icon=":material/restart_alt:", width="stretch")

    with st.expander("Fixed screening settings"):
        st.markdown(
            "- Method: best-in-class percentile within zone × industry\n"
            f"- Minimum stocks per zone: {MIN_STOCKS}\n"
            f"- Relaxation step: {RELAX_STEP:.2f}\n"
            "These settings belong to the team's screening model and are not editable here."
        )

# --------------------------------------------------------------------------- #
# Run the real screening
# --------------------------------------------------------------------------- #
if submitted and params is not None:
    try:
        st.session_state[RESULT_KEY] = cached_screening(params)
        applied = st.session_state[RESULT_KEY]
    except DataUnavailableError as exc:
        st.error(str(exc))
    except (ValueError, KeyError, FileNotFoundError) as exc:
        st.error(f"The screening could not run with these answers: {exc}")
    except Exception as exc:  # unexpected: log it and show a readable message
        logger.exception("Screening failed")
        st.error("Unexpected error while screening the universe. Please adjust the answers or reload the app.")
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")

# --------------------------------------------------------------------------- #
# Result summary (details in the Universe Explorer)
# --------------------------------------------------------------------------- #
if applied is not None:
    p, funnel = applied["params"], applied["funnel"]
    st.divider()
    st.subheader("Screening result")
    st.caption(
        f"{', '.join(p.regions)} · {'all industries' if p.sectors is None else ', '.join(p.sectors)} · "
        f"ESG {p.esg_label} · {'eligible at start only' if p.eligible_only else 'all constituents'}. "
        "This is an ESG-screened universe, not an optimized portfolio: no weights are computed yet."
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("In scope", fmt_int(funnel["in_scope"]), help="Stocks of the chosen regions and industries.")
    k2.metric(f"Eligible on {PORTFOLIO_START}", fmt_int(funnel["eligible_in_scope"]))
    k3.metric("Screened candidates", fmt_int(funnel["candidates"]),
              help="Stocks that entered the ESG screen (eligible ones only if that option is on).")
    share = funnel["selected"] / funnel["candidates"] if funnel["candidates"] else float("nan")
    k4.metric("ESG-selected", fmt_int(funnel["selected"]),
              help=f"{fmt_pct(share)} of the screened candidates.")
    if not p.eligible_only:
        st.caption(f"{fmt_int(funnel['selected_eligible'])} of the ESG-selected stocks are eligible on {PORTFOLIO_START}.")

    for w in applied["warnings"]:
        st.warning(w, icon=":material/info:")

    eff = applied["effective_table"]
    relaxed = bool((eff["status"] != "As requested").any())
    with st.expander("Requested vs effective ESG cut per zone", expanded=relaxed):
        st.dataframe(
            eff,
            hide_index=True,
            width="stretch",
            column_config={
                "zone": "Investor zone",
                "requested": st.column_config.NumberColumn("Requested percentile", format="%.2f"),
                "effective": st.column_config.NumberColumn("Effective percentile", format="%.2f"),
                "status": "Status",
            },
        )

    st.page_link(PAGES["explorer"], label="Explore the screened universe", icon=":material/arrow_forward:")