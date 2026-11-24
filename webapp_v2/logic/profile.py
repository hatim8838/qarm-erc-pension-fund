"""Risk questionnaire: answers -> score s in [0, 1] -> risk level 1-5 -> target volatility σ*."""

from __future__ import annotations

import config as cfg
import content


def max_points() -> int:
    """Highest possible total: the last option of every question."""
    return sum(len(options) - 1 for _, _, options in content.QUESTIONS)


def is_complete(answers: dict) -> bool:
    """True when every question has an answer."""
    return all(answers.get(key) is not None for key, _, _ in content.QUESTIONS)


def score(answers: dict[str, int]) -> float:
    """s = chosen option positions (0 = most cautious) over the maximum."""
    return sum(answers.values()) / max_points()


def level(s: float) -> int:
    """Risk level: the score split into equal bands, one per target volatility."""
    n = len(cfg.TARGET_VOLS)
    return min(n, 1 + int(s * n))


def horizon(answers: dict[str, int]) -> int:
    """Default projection horizon (years) from the horizon answer."""
    return cfg.HORIZON_YEARS[answers.get("horizon", len(cfg.HORIZON_YEARS) - 1)]


def answers_for_level(lvl: int) -> dict[str, int]:
    """Answers whose score sits in the middle of the band of ``lvl`` (used by the adjust panel)."""
    remaining = round((lvl - 0.5) / len(cfg.TARGET_VOLS) * max_points())
    answers = {}
    for key, _, options in content.QUESTIONS:
        answers[key] = min(len(options) - 1, remaining)
        remaining -= answers[key]
    return answers
