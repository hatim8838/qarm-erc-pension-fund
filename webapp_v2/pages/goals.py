"""Our goals: mission, commitments and next steps."""

import config as cfg
import content
from ui import blocks

T, G = content.TEXT, content.GOALS

blocks.hero("goals", cfg.PAGES["journey"])
blocks.cards([{"kicker": T["mission"], "title": content.APP_NAME, "body": G["mission"]}], columns=1)
blocks.cards([
    {"title": T["commitments"], "list": G["commitments"]},
    {"title": T["next"], "list": G["next"]},
], columns=2)
blocks.cta_band(T["closing_cta"], content.HERO["goals"][2], cfg.PAGES["journey"])
