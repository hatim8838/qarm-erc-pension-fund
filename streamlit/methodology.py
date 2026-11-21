"""Methodology & transparency: one page, the essentials, in plain language.

Static explanations; the only figures come from the processed data (data window).
Every rule described here is the one implemented in ``core/``.
"""

from __future__ import annotations

import streamlit as st

from core.config import ESTIMATION_WINDOW
from services import load_data_window
from web_util import fmt_date, page_header

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600&display=swap');
h1, .m-card h4, .m-idea h3, .m-warn b {font-family:'EB Garamond', Georgia, 'Times New Roman', serif !important;}
h1 {font-weight:500 !important; letter-spacing:-.01em;}
.m-card h4 {font-size:1.25rem; font-weight:600;}
.m-warn b {font-size:1.05rem; font-weight:600;}
.m-idea h3 {font-size:1.7rem; font-weight:500;}
.m-lead {color:#4A4F57; font-size:1.08rem; line-height:1.65; max-width:56rem; margin:.2rem 0 2rem 0;}
.m-sec {font-size:.74rem; letter-spacing:.1em; text-transform:uppercase; color:#5B6B7F; font-weight:600;
        margin:2.4rem 0 .9rem 0;}
.m-grid {display:grid; gap:16px;}
.m-g4 {grid-template-columns:repeat(4, 1fr);}
.m-g3 {grid-template-columns:repeat(3, 1fr);}
.m-g6 {grid-template-columns:repeat(6, 1fr); gap:12px;}
.m-card {border:1px solid #E3E8EF; border-radius:12px; padding:1.15rem 1.25rem; background:#FFFFFF; height:100%;}
.m-card h4 {margin:.1rem 0 .45rem 0; font-size:1.05rem; color:#1A1F2B;}
.m-card p, .m-card li {font-size:.9rem; line-height:1.55; color:#4A4F57; margin:0;}
.m-card ul {margin:.2rem 0 0 0; padding-left:1.1rem;}
.m-card li {margin-bottom:.3rem;}
.m-num {display:inline-flex; width:1.9rem; height:1.9rem; border-radius:50%; background:linear-gradient(135deg,#2B2F36,#6B7480); font-family:"EB Garamond",Georgia,serif; color:#fff;
        font-size:1rem; font-weight:600; align-items:center; justify-content:center; margin-bottom:.7rem;}
.m-idea {background:linear-gradient(135deg,#2B2F36 0%,#4A5058 100%); color:#F3F5F8; border-radius:14px; padding:1.8rem 2rem; margin:.2rem 0 1rem 0;}
.m-idea h3 {color:#FFFFFF; margin:0 0 .5rem 0; font-size:1.35rem; font-weight:600;}
.m-idea p {color:#D5DAE1; font-size:1rem; line-height:1.65; margin:0; max-width:52rem;}
.m-tile {border-radius:10px; padding:.9rem .5rem; text-align:center; color:#fff; font-size:.85rem; font-weight:600;}
.m-tile small {display:block; font-weight:400; opacity:.85; margin-top:.15rem; font-size:.74rem;}
.m-cap {color:#6B7480; font-size:.85rem; margin-top:.7rem; line-height:1.5;}
.m-warn {border-top:3px solid #C9D0DA; background:#F7F8FA; border-radius:8px; padding:.9rem 1.1rem; height:100%;}
.m-warn b {display:block; color:#1A1F2B; font-size:.92rem; margin-bottom:.2rem;}
.m-warn span {color:#4A4F57; font-size:.84rem; line-height:1.5;}
@media (max-width: 1000px) {.m-g4 {grid-template-columns:1fr 1fr;} .m-g3 {grid-template-columns:1fr;} .m-g6 {grid-template-columns:repeat(3,1fr);}}
</style>
""",
    unsafe_allow_html=True,
)

page_header("Methodology", None, eyebrow="Léman Wealth Management · Transparency")
st.markdown(
    '<p class="m-lead">A transparent, rules-based approach: you choose where to invest and how demanding the ESG '
    "screen should be; we build a portfolio in which no single position drives the risk.</p>",
    unsafe_allow_html=True,
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
st.markdown('<div class="m-sec">How it works</div>', unsafe_allow_html=True)
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
# Structure: six blocks, one sixth of the risk each
# --------------------------------------------------------------------------- #
st.markdown('<div class="m-sec">Portfolio structure</div>', unsafe_allow_html=True)
tiles = [
    ("US", "#2B2F36"),
    ("Eurozone", "#3A3F47"),
    ("Pacific", "#4A5058"),
    ("EM EMEA", "#5B616A"),
    ("Bonds", "#6D737D"),
    ("Commodities", "#80868F"),
]
st.markdown(
    '<div class="m-grid m-g6">'
    + "".join(f'<div class="m-tile" style="background:{c}">{n}<small>⅙ of the risk</small></div>' for n, c in tiles)
    + "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="m-cap" style="margin-top:1rem;font-size:.9rem;color:#6B7480">The portfolio has <b>six blocks</b>: four equity regions, bonds and commodities. '
    "Each block carries one sixth of the total risk. Inside each equity region, every selected stock in turn "
    "contributes the same share of that region's risk.</p>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Data / ESG / Risk
# --------------------------------------------------------------------------- #
window = load_data_window()
window_txt = f"{fmt_date(window[0])} → {fmt_date(window[1])}" if window else "daily history"
st.markdown('<div class="m-sec">Behind the numbers</div>', unsafe_allow_html=True)
st.markdown(
    f"""
<div class="m-grid m-g3">
  <div class="m-card"><h4>Data</h4><ul>
    <li>Daily total returns in US dollars, {window_txt}.</li>
    <li>Four equity indices (US, Eurozone, Pacific, EM EMEA), a US bond index and three commodity indices.</li>
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
st.markdown('<div class="m-sec">Good to know</div>', unsafe_allow_html=True)
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
