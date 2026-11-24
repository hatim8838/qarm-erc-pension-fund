"""Who we are: photo hero with live figures, mandate, team, approach, 3 steps, FAQ and CTA."""

import config as cfg
import content
from logic import data, performance
from ui import blocks

T = content.TEXT


def key_figures() -> None:
    """Universe size, history length and the Sharpe ratio of core's ERC, all from the data."""
    erc = data.portfolio_returns()[[cfg.CORE_ERC]].dropna()
    sharpe = performance.metrics_table(erc).loc[cfg.CORE_ERC, "sharpe"]
    years = (erc.index[-1] - erc.index[0]).days / 365.25
    n_assets = sum(data.sleeve_returns(s).shape[1] for s in data.sleeves())
    blocks.figures([
        (blocks.count_up(n_assets), T["who_figures"][0].format(n=len(data.sleeves()))),
        (blocks.count_up(years), T["who_figures"][1].format(year=erc.index[0].year)),
        (blocks.count_up(sharpe, 2), T["who_figures"][2]),
    ])


blocks.hero("who", cfg.PAGES["journey"], photo=True)
key_figures()
blocks.cards([{"badge": "LN 5 · LN 6", "title": content.MANDATE[0], "body": content.MANDATE[1]}], columns=1)
blocks.section(T["team"], content.COURSE)
blocks.cards([{"avatar": m["name"][0], "kicker": m["role"], "title": m["name"], "body": m["bio"], "tags": m["tags"]}
              for m in content.TEAM])
blocks.section(T["approach"])
blocks.cards([{"badge": b, "title": t, "body": body} for b, t, body in content.APPROACH])
blocks.section(T["steps"])
blocks.steps(T["three_steps"])
blocks.section(T["faq"])
blocks.faq(content.FAQ)
blocks.cta_band(T["closing_cta"], content.HERO["who"][2], cfg.PAGES["journey"])
