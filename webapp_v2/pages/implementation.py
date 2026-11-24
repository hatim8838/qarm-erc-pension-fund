"""How we implement it: the pipeline step by step, each with its lecture badge and formula."""

import config as cfg
import content
from core.utilities import rebalancing_dates
from logic import data
from ui import blocks, diagram

T = content.TEXT

blocks.hero("implementation")
dates = rebalancing_dates(data.sleeve_returns(data.sleeves()[-1]).index, cfg.PORTFOLIO_START, cfg.REBALANCING_FREQ)
blocks.figures([
    (blocks.count_up(cfg.ESTIMATION_WINDOW), T["impl_window"]),
    (blocks.count_up(len(dates)), T["impl_rebalancings"].format(start=dates[0].year, end=dates[-1].year)),
    (blocks.count_up(len(data.sleeves())), T["impl_sleeves"]),
])
blocks.section(T["formulas"])
diagram.pipeline(content.PIPELINE)
