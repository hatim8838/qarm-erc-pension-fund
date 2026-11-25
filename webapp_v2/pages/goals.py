"""Our goals: an opening paragraph, then what we aim for and our commitments, as text sections."""

import config as cfg
import content
from ui import blocks

blocks.hero("goals", cfg.PAGES["journey"])
blocks.lead(content.GOALS_INTRO)
for title, paragraphs in content.GOALS:
    blocks.prose(title, paragraphs)
blocks.cta_band(content.TEXT["closing_cta"], content.HERO["goals"][2], cfg.PAGES["journey"])
