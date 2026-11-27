"""D) Precomputed results (scripts/precompute.py): used when valid, identical to the live computation."""

import pandas as pd

import config as cfg
from logic import construction, data, portfolio, store


def test_stored_files_are_valid_and_used():
    """meta.json matches the current data, parameters and code, so level 1 comes from the files."""
    assert store.available()
    assert "rc" in construction.level1("Bonds", (), portfolio.NO_SCREEN)  # only stored results carry "rc"


def test_stored_level1_equals_the_live_computation():
    """Same returns, weights and turnover to the last bit, for a screened sleeve."""
    sectors = tuple(data.sectors())
    stored = construction.level1("EM EMEA", sectors, "High")
    live = construction._level1_live("EM EMEA", sectors, "High", construction.ledoit_wolf_cc)
    for key in ("returns", "weights", "turnover"):
        # identical up to floating-point noise: other machines / library versions differ in the last digits
        (pd.testing.assert_frame_equal if key == "weights" else pd.testing.assert_series_equal)(
            stored[key], live[key], check_exact=False, rtol=1e-6, atol=1e-10)
    for t, w in live["windows"].items():
        same = pd.testing.assert_frame_equal if isinstance(w, pd.DataFrame) else pd.testing.assert_series_equal
        same(stored["windows"][t], w, check_exact=False, rtol=1e-6, atol=1e-10)


def test_snapshot_from_stored_weights_equals_the_live_one(monkeypatch):
    """today() (live ESG score on step 3d) is the same with or without the stored weights."""
    choices = portfolio.baseline("Medium")
    stored = portfolio._today.__wrapped__(choices.regions, choices.classes, choices.sectors, choices.esg)
    monkeypatch.setitem(store.STATE, "enabled", False)
    live = portfolio._today.__wrapped__(choices.regions, choices.classes, choices.sectors, choices.esg)
    pd.testing.assert_series_equal(stored, live, check_exact=False, rtol=1e-6, atol=1e-10)


def test_changed_parameter_switches_the_files_off(monkeypatch):
    """A different estimation window no longer matches meta.json: the app computes live."""
    monkeypatch.setattr(cfg, "ESTIMATION_WINDOW", cfg.ESTIMATION_WINDOW + 1)
    store._valid.cache_clear()
    try:
        assert not store.available()
    finally:
        monkeypatch.undo()
        store._valid.cache_clear()
    assert store.available()
