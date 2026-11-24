"""Every page in dark and light mode, and the client journey for the three profiles (Streamlit AppTest)."""

import pytest
from conftest import profiles
from streamlit.testing.v1 import AppTest

import config as cfg
from logic import data, journey
from logic.portfolio import client_sleeves

TIMEOUT = 600


def app(theme: str = "dark") -> AppTest:
    """The full app (navbar, CSS, footer) on its landing page."""
    at = AppTest.from_file(str(cfg.APP_DIR / "app.py"), default_timeout=TIMEOUT)
    at.session_state["theme"] = theme
    return at.run()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("page", list(cfg.PAGES.values()))
def test_every_page_loads(page, theme):
    """No exception on any page, in both modes."""
    at = app(theme)
    at.switch_page(page).run()
    assert not at.exception, [e.value for e in at.exception]


def click_next(at: AppTest) -> AppTest:
    """Press Next, which must be enabled."""
    assert not at.button(key="next").disabled
    return at.button(key="next").click().run()


def walk(choices) -> AppTest:
    """Click through 3a-3f like a client and return the app on 3f."""
    at = app()
    at.switch_page(cfg.PAGES["journey"]).run()
    assert at.button(key="next").disabled  # no region yet
    for region in choices.regions:
        at.button(key=f"regions_{data.regions().index(region)}").click().run()
    click_next(at)
    for cls in choices.classes:
        at.button(key=f"classes_{data.asset_classes().index(cls)}").click().run()
    click_next(at)
    at.multiselect(key="w_sectors").set_value(list(choices.sectors)).run()
    click_next(at)
    at.select_slider(key="w_esg").set_value(choices.esg).run()
    click_next(at)
    at.select_slider(key="w_level").set_value(choices.level).run()
    click_next(at)
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_journey_builds_the_chosen_portfolio(name):
    """Each profile reaches 3f, and the session holds exactly the profile's choices."""
    expected = profiles()[name]
    at = walk(expected)
    values = {k: at.session_state[k] for k in ("regions", "classes", "sectors", "esg", "level")}
    got = journey.to_choices(values)
    assert at.session_state["step"] == "portfolio"
    assert set(got.regions) == set(expected.regions) and got.esg == expected.esg and got.level == expected.level
    assert client_sleeves(got) == client_sleeves(expected)


def test_next_is_blocked_with_a_single_sleeve():
    """One region with equities only is a single sleeve: Next stays disabled with a message."""
    at = app()
    at.switch_page(cfg.PAGES["journey"]).run()
    at.button(key="regions_0").click().run()
    click_next(at)
    at.button(key=f"classes_{data.asset_classes().index(cfg.EQUITIES)}").click().run()
    assert at.button(key="next").disabled and at.warning


def test_next_is_blocked_when_the_esg_screen_leaves_too_few_stocks():
    """Eurozone Health Care passes 3c, but the High screen leaves fewer than the minimum: 3d blocks Next."""
    at = app()
    at.switch_page(cfg.PAGES["journey"]).run()
    at.button(key=f"regions_{data.regions().index('Eurozone')}").click().run()
    click_next(at)
    for i, _ in enumerate(data.asset_classes()):
        at.button(key=f"classes_{i}").click().run()
    click_next(at)
    at.multiselect(key="w_sectors").set_value(["Health Care"]).run()
    click_next(at)
    at.select_slider(key="w_esg").set_value(list(cfg.ESG_LEVELS)[-1]).run()
    assert at.button(key="next").disabled and at.warning
