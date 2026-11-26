"""Who we are: photo hero, an opening paragraph with live figures, editorial sections, team, FAQ and CTA."""

from html import escape

import streamlit as st

import config as cfg
import content
from logic import data, performance, universe
from ui import blocks

T = content.TEXT


def figures() -> dict:
    """Universe size (stocks, then the bond and commodity indices apart), history length and Sharpe ratios of
    core's ERC and 60/40, all from the data."""
    returns = data.portfolio_returns()[[cfg.CORE_ERC, "60/40"]].dropna()
    sharpe = performance.metrics_table(returns)["sharpe"]
    alphas = cfg.ALPHAS.values()
    counts = universe.stock_counts(tuple(data.regions()), tuple(data.sectors()), next(iter(cfg.ESG_LEVELS)))
    return {"stocks": blocks.stock_line(counts), "indices": blocks.index_line(universe.index_counts()),
            "n_sleeves": len(data.sleeves()),
            "years": round((returns.index[-1] - returns.index[0]).days / 365.25), "year": returns.index[0].year,
            "sharpe": f"{sharpe[cfg.CORE_ERC]:.2f}", "sharpe_bench": f"{sharpe['60/40']:.2f}",
            "low": blocks.pct(min(alphas), 0), "high": blocks.pct(max(alphas), 0)}


def faq() -> None:
    """Questions in the same two-column layout as the text sections."""
    with st.container(key="prose_faq"):
        left, right = st.columns([1, 2.2], gap="large")
        left.html(f"<h2>{escape(T['faq'])}</h2>")
        with right:
            blocks.faq(content.FAQ, blocks.universe_values())


values = figures()
blocks.hero("who", cfg.PAGES["journey"], photo=True)
blocks.lead(content.WHO_INTRO, values)
for title, paragraphs in content.WHO:
    blocks.prose(title, paragraphs, values)
blocks.people(T["team"], content.TEAM_INTRO, content.TEAM)
faq()
blocks.cta_band(T["closing_cta"], content.HERO["who"][2], cfg.PAGES["journey"])
