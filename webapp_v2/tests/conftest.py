"""Shared setup: import paths, the three test profiles and their (expensive) backtests, built once."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402  (adds the repository root, so core/ imports work)
from logic import data, portfolio  # noqa: E402
from logic.portfolio import Choices  # noqa: E402


def profiles() -> dict[str, Choices]:
    """(a) level 1, Eurozone, equities + bonds; (b) level 3, 3 regions, all classes, 3 sectors, ESG screen;
    (c) level 5, all regions, equities + commodities, ESG screen + risk budgets."""
    bonds, commodities = data.other_classes()
    return {
        "a": Choices(("Eurozone",), (cfg.EQUITIES, bonds), tuple(data.sectors()), "off", 1),
        "b": Choices(("US", "Eurozone", "Pacific"), tuple(data.asset_classes()),
                     ("Health Care", "Industrials", "Technology"), "screen", 3),
        "c": Choices(tuple(data.regions()), (cfg.EQUITIES, commodities), tuple(data.sectors()), "screen_rb", 5),
    }


@pytest.fixture(scope="session")
def built() -> dict[str, dict]:
    """Backtests of the three profiles and of the baseline (computed once per test session)."""
    out = {name: portfolio.build(choices) for name, choices in profiles().items()}
    out["baseline"] = portfolio.build(portfolio.baseline())
    return out
