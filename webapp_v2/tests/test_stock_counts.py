"""E) Stock counts: one function (universe.stock_counts) behind every number of stocks the app shows, the
ESG screen at Off, the risk-level names, and ERC risk contributions equal to the budgets."""

import re
from html import escape

import numpy as np
import pytest

import config as cfg
import content
from logic import composition, data, report, store, universe
from logic.portfolio import NO_SCREEN, baseline, stock_weights
from test_pages import app, walk
from ui import blocks

ALL = (tuple(data.regions()), tuple(data.sectors()), NO_SCREEN)


def _html(at) -> str:
    """Every st.html block of a page, joined."""
    return "\n".join(e.proto.body for e in at.get("html"))


def test_universe_counts():
    """(1) All regions, all sectors, ESG Off: 1,108 listed, 1,102 investable, 4 listed less than a year ago and
    2 without usable prices (Monte dei Paschi, Piraeus: price indices of 0.01-0.04, below the 0.20 floor)."""
    c = universe.stock_counts(*ALL)
    assert c["listed"] == len(data.stocks()) == 1108
    assert c["investable"] == 1102 and c["recent"] == 4 and c["unusable"] == 2
    assert c["listed"] == c["investable"] + c["recent"] + c["unusable"]
    assert c["excluded_esg"] == 0 and c["kept"] == c["investable"]
    assert c == {k: sum(universe.stock_counts((r,), *ALL[1:])[k] for r in data.regions()) for k in c}


def test_recent_stocks_have_less_than_a_year_of_history():
    """(1) "Recent" stocks have no return before the last estimation window (full history, not only the tail),
    and their window is complete from their first return on."""
    for region in data.regions():
        tail = data.sleeve_tail(region)
        full = data.sleeve_returns(region)
        started = full.apply(lambda s: s.first_valid_index())
        new = started[started > tail.index[0]].index
        complete = [c for c in new if tail[c].loc[started[c]:].notna().all() and tail[c].notna().iloc[-1]]
        assert len(complete) == universe.stock_counts((region,), *ALL[1:])["recent"], region


@pytest.mark.parametrize("region", ["US", "Eurozone", "Pacific", "EM EMEA"])
def test_esg_off_excludes_nothing(region):
    """(2) ESG Off: no stock excluded at any rebalancing (also in precomputed/level1/<region>__Off), and the
    stocks without an ESG score are kept and held."""
    assert store.available()
    stored = store.load_level1(region, NO_SCREEN)
    assert all(len(excluded) == 0 for _, excluded in stored["screen"].values())
    candidates = stored["screen"][max(stored["screen"])][0]
    unscored = candidates[data.stocks()["esg_score"].reindex(candidates).isna()]
    assert (stored["weights"].iloc[-1][unscored] > 0).all()
    assert len(universe.worst_esg(candidates, NO_SCREEN)) == 0
    assert universe.stock_counts((region,), *ALL[1:])["excluded_esg"] == 0


def test_unscored_stocks_rank_as_the_worst():
    """(2) Low / Medium / High: a stock without a score is excluded before any scored stock."""
    stocks = data.stocks()
    for region in data.regions():
        candidates = universe.investable(universe.last_window(region, ALL[1]))
        unscored = candidates[stocks["esg_score"].reindex(candidates).isna()]
        for esg in list(cfg.ESG_LEVELS)[1:]:
            worst = universe.worst_esg(candidates, esg)
            assert set(worst[:len(unscored)]) == set(unscored[:len(worst)]), (region, esg)


def test_every_page_shows_the_same_number(built):
    """(3) Who we are, Universe explorer, the journey (3a region cards) and the holdings on 3f show the numbers
    of universe.stock_counts, in the same phrase."""
    counts = universe.stock_counts(*ALL)
    line = blocks.stock_line(counts)
    assert line == (f"{counts['listed']:,} stocks in our universe · {counts['investable']:,} investable today "
                    f"({counts['recent']} listed less than a year ago, {counts['unusable']} without usable prices)")
    who = app()
    assert f"<b>{escape(line)}</b>" in _html(who)
    universe_page = app()
    universe_page.switch_page(cfg.PAGES["universe"]).run()
    assert any(c.value.startswith(line) for c in universe_page.caption)
    journey = app()
    journey.switch_page(cfg.PAGES["journey"]).run()
    shown = [c.value for c in journey.caption]
    for r in data.regions():
        short = blocks.stock_line(universe.stock_counts((r,), *ALL[1:]), short=True)
        assert any(s.startswith(short) for s in shown), r
    on_3f = walk(baseline())
    html = _html(on_3f)
    assert report.holdings_count(built["baseline"]) == {"stocks": counts["kept"], **universe.index_counts()}
    assert f'aria-label="{counts["kept"]:,}"' in html and "<span>stocks</span>" in html
    assert "<span>bond index</span>" in html and "<span>commodity indices</span>" in html
    method = "\n".join(m.value for m in on_3f.markdown)
    values = blocks.universe_values()
    for key in ("recent_names", "unusable_names", "listed", "investable", "indices"):
        assert values[key] in method, key


def test_counters_show_thousands_separators():
    """The animated figures show 1,102 like the text: a plain comma between animated groups of 3 digits."""
    html = blocks.count_up(1102)
    assert 'aria-label="1,102"' in html and '--to:1"></span>,<span class="count pad3" style="--to:102"' in html
    assert 'aria-label="1,002"' in blocks.count_up(1002) and 'aria-label="60%"' in blocks.count_up(60, 0, "%")
    assert "pad3" in (cfg.APP_DIR / "assets" / "style.css").read_text(encoding="utf-8")


def test_method_and_faq_explain_the_exclusions():
    """The method box and the FAQ name the stocks left out, with computed numbers only (no digit in the text)."""
    regions, sectors = ALL[:2]
    assert len(universe.stock_names(regions, sectors, "recent")) == universe.stock_counts(*ALL)["recent"]
    assert universe.stock_names(regions, sectors, "unusable") == ["BANCA MONTE DEI PASCHI", "PIRAEUS BANK"]
    new_text = [*content.METHOD[1][2:], content.FAQ[-1][1]]
    assert not any(re.search(r"\d", t) for t in new_text)
    values = blocks.universe_values()
    assert values["floor"] == "0.20" and values["tick"] == "5%"
    who = app()
    answers = "\n".join(m.value for m in who.markdown)
    assert values["recent_names"] in answers and values["unusable_names"] in answers


def test_holdings_are_the_stocks_the_portfolio_holds(built):
    """(3) The stock number of the holdings equals the stocks with a positive weight in the backtest."""
    for name, result in built.items():
        w = stock_weights(result)
        stocks = w[w.index.str.split(cfg.ASSET_ID_SEP).str[0].isin(data.regions())]
        assert report.holdings_count(result).get("stocks", 0) == int((stocks > 0).sum()), name


def test_who_we_are_counts_stocks_only():
    """(4) The Who we are figure is stocks only; the bond and commodity indices are named apart, never added,
    and every {placeholder} of the page text is filled."""
    counts, indices = universe.stock_counts(*ALL), universe.index_counts()
    assert indices == {"Bonds": 1, "Commodities": 3}
    html = _html(app())
    assert f"plus <b>{blocks.index_line(indices)}</b>" in html and blocks.index_line(indices) == \
        "1 bond index and 3 commodity indices"
    assert f"{counts['listed'] + sum(indices.values()):,}" not in html
    assert f"{counts['investable'] + sum(indices.values()):,}" not in html
    names = set(re.findall(r"{(\w+)}", content.WHO_INTRO + " ".join(p for _, ps in content.WHO for p in ps)))
    assert names == {"n_sleeves", "stocks", "indices", "years", "year", "low", "high"}
    assert not re.search(r"{\w+}", html)


OLD_LEVEL_WORD = "".join(["ag", "gress"])  # spelled in two parts so that this file does not contain it


def test_level_5_is_fully_invested():
    """(5) Level 5 (α = 100%) is the fully invested ERC, without leverage: the old level-5 word appears nowhere,
    in content.py or any other file of the app."""
    assert content.LEVEL_NAMES[max(cfg.ALPHAS)] == "Fully invested" and cfg.ALPHAS[max(cfg.ALPHAS)] == 1.0
    for path in [cfg.APP_DIR / "content.py", *cfg.APP_DIR.glob("*/*.py"), *cfg.APP_DIR.glob("*.py")]:
        assert OLD_LEVEL_WORD not in path.read_text(encoding="utf-8").lower(), path.name


def test_erc_risk_contributions_equal_the_budgets(built):
    """(6) Baseline at the last rebalancing: each sleeve carries 1/6 of the risk, and inside each sleeve every
    asset carries 1/N of the sleeve's risk."""
    result = built["baseline"]
    sleeves = composition.sleeves(result)
    assert np.allclose(sleeves["rc"], 1 / len(sleeves), atol=cfg.RC_TOLERANCE)
    for sleeve in sleeves.index:
        inner = composition.inner(result, sleeve)
        assert np.allclose(inner["rc"], 1 / len(inner), atol=cfg.RC_TOLERANCE), sleeve
