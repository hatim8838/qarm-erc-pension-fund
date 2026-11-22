"""Methodology & transparency (Amber design): one page, the essentials, in plain language.

Static explanations; the only figures come from the processed data (data window).
Every rule described here is the one implemented in ``core/``.
"""

from __future__ import annotations

import streamlit as st

from core.config import ESTIMATION_WINDOW
from services import load_data_window
from web_util import AMBER, CARD_BORDER, PEACH, SLEEVE_COLORS, fmt_date, page_header, section_header

st.markdown(
    f"""
<style>
.m-grid {{display:grid; gap:18px;}}
.m-g4 {{grid-template-columns:repeat(4, 1fr);}}
.m-g3 {{grid-template-columns:repeat(3, 1fr);}}
.m-g6 {{grid-template-columns:repeat(6, 1fr); gap:12px;}}
.m-card {{border:1px solid {CARD_BORDER}; border-radius:12px; padding:1.2rem 1.3rem; background:#FFFFFF; height:100%;
         box-shadow:0 2px 5px rgba(0,0,0,.05); transition:transform .2s ease, box-shadow .2s ease;}}
.m-card:hover {{transform:translateY(-2px); box-shadow:0 6px 14px rgba(0,0,0,.08);}}
.m-card h4 {{margin:.1rem 0 .5rem 0; font-size:1.15rem; font-weight:700;}}
.m-card p, .m-card li {{font-size:.95rem; line-height:1.55; color:#444; margin:0;}}
.m-card ul {{margin:.2rem 0 0 0; padding-left:1.1rem;}}
.m-card li {{margin-bottom:.3rem;}}
.m-num {{display:inline-flex; width:2rem; height:2rem; border-radius:50%; background:{PEACH}; color:#000;
        font-size:1rem; font-weight:700; align-items:center; justify-content:center; margin-bottom:.7rem;}}
.m-idea {{background:{PEACH}; border-radius:15px; padding:1.9rem 2.1rem; margin:.2rem 0 1rem 0;}}
.m-idea h3 {{margin:0 0 .6rem 0; font-size:1.7rem; font-weight:700; color:#000;}}
.m-idea p {{font-size:1.05rem; line-height:1.65; margin:0; max-width:56rem; color:#222;}}
.m-tile {{border-radius:12px; padding:1rem .5rem; text-align:center; font-size:.95rem; font-weight:700;}}
.m-tile small {{display:block; font-weight:500; opacity:.9; margin-top:.15rem; font-size:.78rem;}}
.m-cap {{color:#555; font-size:.95rem; margin-top:1.1rem !important; line-height:1.6;}}
.m-warn {{border-top:4px solid {AMBER}; background:#FFF8F1; border-radius:10px; padding:1rem 1.15rem; height:100%;}}
.m-warn b {{display:block; font-size:1rem; font-weight:700; margin-bottom:.25rem;}}
.m-warn span {{color:#444; font-size:.9rem; line-height:1.5;}}
@media (max-width: 1000px) {{.m-g4 {{grid-template-columns:1fr 1fr;}} .m-g3 {{grid-template-columns:1fr;}} .m-g6 {{grid-template-columns:repeat(3,1fr);}}}}
</style>
""",
    unsafe_allow_html=True,
)

page_header(
    "Methodology",
    "A transparent, rules-based approach: you choose where to invest and how demanding the ESG "
    "screen should be; we build a portfolio in which no single position drives the risk.",
    eyebrow="Léman Wealth Management · Transparency",
)

# --------------------------------------------------------------------------- #
# The idea
# --------------------------------------------------------------------------- #
st.markdown(
    """
<div class="m-idea">
  <h3>Equal risk, not equal capital</h3>
  <p>Splitting money evenly does not split risk evenly: stocks fluctuate far more than bonds, so they dominate the
  risk of an equally weighted portfolio. In an <b>Equal Risk Contribution</b> portfolio, calmer assets receive more
  capital and more volatile ones less, so that each building block contributes the same share of the total risk.</p>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# How it works
# --------------------------------------------------------------------------- #
section_header("How it works")
st.markdown(
    """
<div class="m-grid m-g4">
  <div class="m-card"><div class="m-num">1</div><h4>You set your preferences</h4>
    <p>Regions, industries and the level of ESG ambition.</p></div>
  <div class="m-card"><div class="m-num">2</div><h4>We screen the universe</h4>
    <p>Only stocks with a strong ESG score compared with their peers are kept.</p></div>
  <div class="m-card"><div class="m-num">3</div><h4>We balance the risk</h4>
    <p>Capital is allocated so that every block of the portfolio carries the same share of risk.</p></div>
  <div class="m-card"><div class="m-num">4</div><h4>We test it on history</h4>
    <p>The same rules are simulated on past data and compared with simple alternatives.</p></div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Structure: up to six blocks (commodities optional), an equal share of the risk each
# --------------------------------------------------------------------------- #
section_header("Portfolio structure")
# Same colour per block as in the charts of the app; dark text on the light tiles.
tiles = [
    ("US", "equal risk share"),
    ("Eurozone", "equal risk share"),
    ("Pacific", "equal risk share"),
    ("EM EMEA", "equal risk share"),
    ("Bonds", "always held"),
    ("Commodities", "optional"),
]
DARK_TEXT = {"Eurozone", "Bonds", "Commodities"}
st.markdown(
    '<div class="m-grid m-g6">'
    + "".join(
        f'<div class="m-tile" style="background:{SLEEVE_COLORS[n]};color:{"#000" if n in DARK_TEXT else "#FFF"}">'
        f"{n}<small>{note}</small></div>"
        for n, note in tiles
    )
    + "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="m-cap">The portfolio has <b>up to six blocks</b>: '
    "the equity regions you choose, bonds (always held) and, if you wish, commodities. Every block carries the "
    "<b>same share of the total risk</b>: one sixth with all six blocks, one fifth without commodities. Inside "
    "each equity region, every selected stock in turn contributes the same share of that region's risk.</p>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Data / ESG / Risk
# --------------------------------------------------------------------------- #
window = load_data_window()
window_txt = f"{fmt_date(window[0])} → {fmt_date(window[1])}" if window else "daily history"
section_header("Behind the numbers")
st.markdown(
    f"""
<div class="m-grid m-g3">
  <div class="m-card"><h4>Data</h4><ul>
    <li>Daily total returns in US dollars, {window_txt}.</li>
    <li>Four equity indices (US, Eurozone, Pacific, EM EMEA), a US bond index and three commodity indices (optional).</li>
    <li>Prices are cleaned; a stock needs a full year of history to be included.</li></ul></div>
  <div class="m-card"><h4>ESG screening</h4><ul>
    <li>Each stock is compared with peers of the same region and industry.</li>
    <li>You choose the cut-off, from "no filter" to the best 10%.</li>
    <li>Optional: ESG-tilted risk budgets, proportional to each stock's ESG score.</li></ul></div>
  <div class="m-card"><h4>Risk estimation</h4><ul>
    <li>Volatility and correlations measured over the last {ESTIMATION_WINDOW} business days.</li>
    <li>Statistical shrinkage keeps large groups of stocks stable.</li>
    <li>Long-only, fully invested, rebalanced monthly.</li></ul></div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Good to know
# --------------------------------------------------------------------------- #
section_header("Good to know")
st.markdown(
    """
<div class="m-grid m-g4">
  <div class="m-warn"><b>Not a forecast</b><span>Past results show how the rules behaved, not how they will behave.</span></div>
  <div class="m-warn"><b>Risk, not returns</b><span>The method balances risk; it does not predict which assets will perform best.</span></div>
  <div class="m-warn"><b>Historical data</b><span>Stock lists are today's index members and ESG scores are a recent snapshot.</span></div>
  <div class="m-warn"><b>Simplified</b><span>Backtests ignore transaction costs and taxes. Educational project, not investment advice.</span></div>
</div>
""",
    unsafe_allow_html=True,
)
