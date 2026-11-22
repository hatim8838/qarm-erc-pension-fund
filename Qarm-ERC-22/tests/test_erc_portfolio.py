"""ERC maths when the investor includes or excludes the commodity sleeve (``core.erc_portfolio``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

erc = pytest.importorskip("core.erc_portfolio")  # needs scikit-learn (Ledoit-Wolf)


def _window(include_commodities: bool, days: int = 252, seed: int = 0) -> pd.DataFrame:
    """Synthetic daily returns: 2 equity regions, bonds and (optionally) 2 commodities."""
    rng = np.random.default_rng(seed)
    market = rng.normal(0, 0.010, days)
    cols = {}
    for zone, beta in (("US", 1.0), ("Pacific", 0.8)):
        for k in range(3):
            cols[f"{zone}|S{k}"] = beta * market + rng.normal(0, 0.008 + 0.002 * k, days)
    cols["Bonds|AGG"] = -0.1 * market + rng.normal(0, 0.003, days)
    if include_commodities:
        oil = rng.normal(0, 0.020, days)
        cols["Commodities|Energy"] = 0.3 * market + oil
        cols["Commodities|Gold"] = rng.normal(0, 0.011, days)
    idx = pd.bdate_range("2024-01-01", periods=days)
    return pd.DataFrame(cols, index=idx)


@pytest.mark.parametrize("include_commodities, n_sleeves", [(True, 4), (False, 3)])
def test_across_sleeve_erc_uses_one_over_n_held_sleeves(include_commodities, n_sleeves):
    port = erc.build_erc_portfolio(_window(include_commodities))
    assert len(port.sleeve_weights) == n_sleeves
    assert ("Commodities" in port.sleeve_weights.index) == include_commodities
    # every sleeve carries 1/N of the risk, with N = sleeves actually held
    assert np.allclose(port.sleeve_rc, 1 / n_sleeves, atol=1e-6)
    assert port.max_rc_gap < 1e-6
    # long-only, fully invested, risk shares add up to 1
    assert port.weights.min() >= 0
    assert port.weights.sum() == pytest.approx(1.0)
    assert port.risk_share.sum() == pytest.approx(1.0)


def test_excluding_commodities_keeps_inner_weights_and_reallocates_capital():
    with_c = erc.build_erc_portfolio(_window(True))
    without = erc.build_erc_portfolio(_window(False))
    # same returns for the common sleeves -> same weights inside each of them
    for sleeve in ("US", "Pacific", "Bonds"):
        pd.testing.assert_series_equal(with_c.inner_weights[sleeve], without.inner_weights[sleeve], atol=1e-8)
    # the commodity capital is redistributed: every remaining sleeve gets more capital
    common = without.sleeve_weights.index
    assert (without.sleeve_weights > with_c.sleeve_weights[common]).all()


def test_single_sleeve_is_rejected_with_a_clear_message():
    only_bonds = _window(False)[["Bonds|AGG"]]
    with pytest.raises(ValueError, match="At least two sleeves"):
        erc.build_erc_portfolio(only_bonds)
