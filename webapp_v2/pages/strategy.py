"""Our strategy: why ERC, EW vs ERC on our data and σ(mv) ≤ σ(erc) ≤ σ(ew).

The comparison with the benchmarks is done once, in the Client journey (Performance tab)."""

import config as cfg
import content
import services
from ui import blocks, charts

T = content.TEXT


def lab(table, holds) -> None:
    """Our sleeves today: RC* of EW vs ERC, and σ(mv) ≤ σ(erc) ≤ σ(ew) at every rebalancing."""
    blocks.section(T["lab"], T["lab_sub"].format(date=holds.index.max().date()))
    blocks.figures([(blocks.count_up(100 * table.loc[n, "σ"], 2, "%"), f"σ({n})") for n in ("MV", "ERC", "EW")])
    charts.bars(table.drop(columns="σ").loc[["EW", "ERC"]].T, key="lab_rc")
    blocks.section(T["theorem"].format(share=blocks.pct(holds.mean(), 0), n=len(holds)))


blocks.hero("strategy", cfg.PAGES["journey"])
blocks.section(T["why_rb"])
blocks.cards([{"title": t, "body": body} for t, body in content.WHY_RB], columns=2)
lab(*services.strategy_lab())
blocks.cta_band(T["closing_cta"], content.HERO["strategy"][2], cfg.PAGES["journey"])
