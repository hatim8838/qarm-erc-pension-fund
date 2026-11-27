"""Client journey steps 1-5: regions, asset classes, sectors, ESG screen, risk level."""

import pandas as pd
import streamlit as st

import config as cfg
import content
import services
from logic import data, journey, performance, portfolio, universe
from ui import blocks, charts, tables

T, J, B = content.TEXT, content.JOURNEY, content.NAV_BUTTONS


def _toggle(key: str, item: str) -> None:
    """Add or remove an item from a list choice."""
    chosen = st.session_state[key]
    if item in chosen:
        chosen.remove(item)
    else:
        chosen.append(item)


def _pick_cards(key: str, items: list[str], facts: dict[str, str], chosen: list[str]) -> None:
    """Clickable cards, one per item, that add or remove it from the choice ``key``."""
    for col, (i, item) in zip(st.columns(len(items)), enumerate(items)):
        on = item in chosen
        with col.container(key=f"pick_{key}_{i}{'_on' if on else ''}"):
            st.markdown(f"### {item}")
            st.caption(facts[item])
            st.button(B["selected"] if on else B["select"], key=f"{key}_{i}", on_click=_toggle, args=(key, item),
                      type="primary" if on else "secondary", width="stretch")


def _index_chart(returns: pd.DataFrame, key: str, note: str) -> None:
    """Annual return and volatility of official indices (no survivorship bias), one pair of bars each."""
    table = performance.metrics_table(returns)[["ann_return", "ann_volatility"]]
    charts.bars(table.rename(columns=content.METRIC_LABELS), key=key)
    st.caption(T[note].format(start=returns.index[0].year))


def regions(values: dict) -> None:
    """Step 1: regional equity sleeves as clickable cards."""
    blocks.section(*J["regions"])
    table = data.stocks()
    facts = {}
    for r in data.regions():
        n_countries = table.loc[table["zone"] == r, "country"].nunique()
        counts = universe.stock_counts((r,), tuple(data.sectors()), next(iter(cfg.ESG_LEVELS)))
        facts[r] = T["region_facts"].format(stocks=blocks.stock_line(counts, short=True), c=n_countries,
                                            countries="country" if n_countries == 1 else "countries")
    _pick_cards("regions", data.regions(), facts, values["regions"])
    names = {cfg.INDEX_LABELS[r]: f"{r} ({cfg.INDEX_LABELS[r]})" for r in data.regions()}
    _index_chart(data.index_returns()[list(names)].rename(columns=names), key="region_hist", note="index_note")


def classes(values: dict) -> None:
    """Step 2: asset classes with what they contain, their role and their history."""
    blocks.section(*J["classes"])
    facts = {c: content.CLASS_ROLES[c] for c in data.asset_classes()}
    _pick_cards("classes", data.asset_classes(), facts, values["classes"])
    idx = data.index_returns()
    chosen = values["regions"] or data.regions()  # equities = the regions picked in step 1, equal weights
    bonds, commodities = data.other_classes()
    classes_ = pd.DataFrame({
        f"{cfg.EQUITIES} ({', '.join(chosen)})": idx[[cfg.INDEX_LABELS[r] for r in chosen]].mean(axis=1),
        f"{bonds} ({cfg.BOND_INDEX})": idx[cfg.BOND_INDEX],
        # our commodity sleeve is built from 3 S&P GSCI sector indices (no survivorship bias), so we show it directly
        f"{commodities} (S&P GSCI energy, precious metals, agriculture)":
            data.portfolio_returns()[f"{cfg.CORE_SLEEVE_PREFIX}{commodities}"].loc[idx.index[0]:]})
    _index_chart(classes_.dropna(), key="class_hist", note="class_note")


def _save(key: str, widget: str) -> None:
    """Copy a widget value into the journey choice ``key``."""
    st.session_state[key] = st.session_state[widget]


def sectors(values: dict) -> None:
    """Step 3: sectors applied to every chosen region, with the investable stocks left in each."""
    blocks.section(*J["sectors"])
    if cfg.EQUITIES not in values["classes"]:
        st.info(T["no_equities"], icon=":material/info:")
        return
    st.multiselect(J["sectors"][0], data.sectors(), default=values["sectors"], key="w_sectors",
                   on_change=_save, args=("sectors", "w_sectors"), label_visibility="collapsed")
    sec = tuple(st.session_state["sectors"])
    blocks.figures([(blocks.count_up(universe.stock_counts((r,), sec, values["esg"])["kept"]),
                     T["stocks_left"].format(region=r)) for r in values["regions"]])


def esg_label(level: str) -> str:
    """Slider label of an ESG level, e.g. "Medium (30%)"."""
    return f"{level} ({blocks.pct(cfg.ESG_LEVELS[level], 0)})"


def esg(values: dict) -> None:
    """Step 4: ESG screen slider, with the stocks excluded today and the ESG score it buys, live."""
    blocks.section(*J["esg"])
    if cfg.EQUITIES not in values["classes"]:
        st.info(T["no_equities"], icon=":material/info:")
        return
    st.select_slider(T["esg_level"], list(cfg.ESG_LEVELS), value=values["esg"], format_func=esg_label,
                     key="w_esg", on_change=_save, args=("esg", "w_esg"), help=content.ESG_HELP)
    counts = universe.stock_counts(tuple(values["regions"]), tuple(values["sectors"]), values["esg"])
    items = [(blocks.count_up(counts["excluded_esg"]), T["excluded"]), (blocks.count_up(counts["kept"]), T["kept"])]
    choices = journey.to_choices(values)
    if journey.problem("esg", values) is None:
        score, off = (universe.esg_score(portfolio.today(choices.but(esg=e, level=portfolio.FULL)))
                      for e in (choices.esg, portfolio.NO_SCREEN))
        items.append((blocks.count_up(score, 1), f'{T["esg_now"]} ({T["esg_delta"].format(delta=score - off)})'))
    blocks.figures(items)


def level_label(level: int) -> str:
    """Slider label of a risk level, e.g. "3 · Balanced · α 60%"."""
    alpha = blocks.pct(cfg.ALPHAS[level], 0)
    return T["level_format"].format(level=level, name=content.LEVEL_NAMES[level], alpha=alpha)


def profile_step(values: dict) -> None:
    """Step 5: one slider sets α, with the resulting split on one live line."""
    blocks.section(*J["profile"])
    st.select_slider(T["level_slider"], list(cfg.ALPHAS), value=values["level"], format_func=level_label,
                     key="w_level", on_change=_save, args=("level", "w_level"))
    alpha = cfg.ALPHAS[st.session_state["level"]]
    st.markdown(T["level_line"].format(level=st.session_state["level"], alpha=blocks.pct(alpha, 0),
                                       rf=blocks.pct(1 - alpha, 0)))
    if all(journey.problem(s, values) is None for s in ("regions", "classes", "sectors", "esg")):
        _levels_table(journey.to_choices(values), st.session_state["level"])


def _levels_table(choices: portfolio.Choices, chosen: int) -> None:
    """What each risk level would have meant for the portfolio built in steps 1-4 (backtest, net of costs):
    the information a pension fund's committee needs to choose, instead of a questionnaire."""
    series = {}
    for level in cfg.ALPHAS:
        result, _, _ = services.build_timed(choices.but(level=level))
        name = f"{level} · {content.LEVEL_NAMES[level]}" + (T["levels_yours"] if level == chosen else "")
        series[name] = portfolio.net_returns(result, cfg.TRANSACTION_COST_BPS)
    returns = pd.DataFrame(series)
    table = performance.metrics_table(returns)[["ann_return", "ann_volatility", "max_drawdown"]]
    table.insert(0, "invested", list(cfg.ALPHAS.values()))
    blocks.section(T["levels_title"])
    tables.show(table.rename(columns={**content.METRIC_LABELS, "invested": T["levels_invested"]}))
    st.caption(T["levels_note"].format(start=returns.index[0].year, end=returns.index[-1].year))
