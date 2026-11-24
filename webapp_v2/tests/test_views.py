"""C) Universe explorer and portfolio-composition views: filters, sums, ranking, risk contributions, site text."""

import re

import numpy as np
import pytest

import config as cfg
from logic import composition, data, universe
from test_pages import app, walk
from conftest import profiles

SITE_TEXT = [*sorted((cfg.APP_DIR / "pages").glob("*.py")), *sorted((cfg.APP_DIR / "ui").glob("*.py")),
             cfg.APP_DIR / "content.py", cfg.APP_DIR / "config.py", cfg.APP_DIR / "app.py"]


def test_universe_counts_filters_and_coverage():
    """Region counts sum to the stocks shown; region filter and search shrink the table; coverage is computed."""
    everything = universe.explore(tuple(data.regions()))
    assert everything["zone"].value_counts().sum() == len(everything) == len(data.stocks())
    one = universe.explore(("Eurozone",))
    banks = universe.explore(tuple(data.regions()), "bank")
    assert 0 < len(one) < len(everything) and set(one["zone"]) == {"Eurozone"}
    assert 0 < len(banks) < len(everything) and banks["name"].str.contains("BANK", case=False).all()
    summary, small = universe.esg_summary(everything), universe.esg_summary(one)
    assert summary["coverage"] == pytest.approx(everything["esg_score"].notna().mean()) and small != summary
    assert everything["esg_score"].dropna().is_monotonic_decreasing


def test_universe_page_follows_the_filters():
    """AppTest: the region filter and the search change the table and the "N companies displayed" line."""
    at = app()
    at.switch_page(cfg.PAGES["universe"]).run()
    assert len(at.dataframe[0].value) == len(data.stocks())
    at.multiselect(key="uni_regions").set_value(["Pacific"]).run()
    assert len(at.dataframe[0].value) == (data.stocks()["zone"] == "Pacific").sum()
    at.text_input(key="uni_search").set_value("bank").run()
    shown = len(at.dataframe[0].value)
    assert 0 < shown < (data.stocks()["zone"] == "Pacific").sum() and f"{shown} companies" in at.caption[-1].value
    assert not at.exception


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_sleeve_table_sums_and_risk_contributions(built, name):
    """Weights sum to 100% (also with the risk-free row × α), every sleeve has RC = 1/n."""
    table = composition.sleeves(built[name])
    assert table["weight"].sum() == pytest.approx(1.0)
    assert np.allclose(table["rc"], 1 / len(table), atol=cfg.RC_TOLERANCE)
    total = composition.sleeves(built[name], total_money=True)
    assert total["weight"].sum() == pytest.approx(1.0)
    assert total.loc[cfg.RISK_FREE, "weight"] == pytest.approx(1 - built[name]["alpha"])
    assert composition.extremes(table)["rc"] == pytest.approx(1 / len(table))


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_largest_positions_are_the_top_holdings_sorted(built, name):
    """Top 15 = the 15 largest of x_s × inner weight, in descending order, × α in total-money mode."""
    top = composition.positions(built[name], cfg.TOP_POSITIONS)
    assert len(top) == cfg.TOP_POSITIONS and top["weight"].is_monotonic_decreasing
    every = composition.positions(built[name], 10_000)
    assert every["weight"].sum() == pytest.approx(1.0) and np.allclose(top["weight"], every["weight"].head(len(top)))
    scaled = composition.positions(built[name], cfg.TOP_POSITIONS, total_money=True)
    assert np.allclose(scaled["weight"], built[name]["alpha"] * top["weight"])


@pytest.mark.parametrize("name", ["a", "c"])
def test_every_asset_has_rc_one_over_n_inside_its_sleeve(built, name):
    """Inside each sleeve: weights sum to 1 and RC*_i = 1/N, N = number of assets held (the target line)."""
    for sleeve, row in composition.sleeves(built[name]).iterrows():
        inner = composition.inner(built[name], sleeve)
        assert len(inner) == row["assets"] and inner["weight"].sum() == pytest.approx(1.0)
        assert np.allclose(inner["rc"], 1 / len(inner), atol=cfg.RC_TOLERANCE)
        assert inner["weight"].is_monotonic_decreasing


def test_portfolio_tabs_and_total_money_toggle():
    """AppTest on 3f: four tabs; the toggle adds the risk-free row and keeps the table at 100%."""
    at = walk(profiles()["b"])
    assert [t.label for t in at.tabs] == ["Allocation", "Risk contribution", "Performance", "Projection"]
    sleeves = at.dataframe[0].value
    assert cfg.RISK_FREE not in sleeves.index and sleeves.iloc[:, 1].sum() == pytest.approx(100)
    at.toggle(key="total_money").set_value(True).run()
    sleeves = at.dataframe[0].value
    assert cfg.RISK_FREE in sleeves.index and sleeves.iloc[:, 1].sum() == pytest.approx(100)


def test_no_course_mention_and_no_implementation_page_left():
    """No "LN x" or "lecture" in the site's code and text, and nothing points to the deleted page."""
    for path in SITE_TEXT:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bLN \d|lecture", text), path.name
        assert "implementation" not in text.lower(), path.name
    assert not (cfg.APP_DIR / "pages" / "implementation.py").exists()
