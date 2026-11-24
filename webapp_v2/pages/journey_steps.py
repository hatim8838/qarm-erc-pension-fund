"""Client journey steps 3a-3e: regions, asset classes, sectors, ESG screen, risk level."""

import pandas as pd
import streamlit as st

import config as cfg
import content
from logic import data, journey, performance, portfolio, universe
from ui import blocks, charts

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


def _sleeve_history() -> pd.DataFrame:
    """Annual return and volatility of core's level-1 ERC portfolio of each sleeve."""
    cols = {f"{cfg.CORE_SLEEVE_PREFIX}{s}": s for s in data.sleeves()}
    return performance.metrics_table(data.portfolio_returns()[list(cols)].rename(columns=cols))


def regions(values: dict) -> None:
    """3a: regional equity sleeves as clickable cards."""
    blocks.section(*J["regions"])
    table, history = data.stocks(), _sleeve_history()
    facts = {r: T["region_facts"].format(n=(table["zone"] == r).sum(), c=table.loc[table["zone"] == r, "country"]
                                         .nunique(), ret=blocks.pct(history.loc[r, "ann_return"]),
                                         vol=blocks.pct(history.loc[r, "ann_volatility"])) for r in data.regions()}
    _pick_cards("regions", data.regions(), facts, values["regions"])


def classes(values: dict) -> None:
    """3b: asset classes with what they contain, their role and their history."""
    blocks.section(*J["classes"])
    facts = {c: content.CLASS_ROLES[c] for c in data.asset_classes()}
    _pick_cards("classes", data.asset_classes(), facts, values["classes"])
    history = _sleeve_history()
    st.caption(T["class_history"].format(start=data.portfolio_returns().index[0].year))
    charts.bars(history[["ann_return", "ann_volatility"]].rename(columns=content.METRIC_LABELS), key="class_hist")


def _save(key: str, widget: str) -> None:
    """Copy a widget value into the journey choice ``key``."""
    st.session_state[key] = st.session_state[widget]


def sectors(values: dict) -> None:
    """3c: sectors applied to every chosen region, with the investable stocks left in each."""
    blocks.section(*J["sectors"])
    st.multiselect(J["sectors"][0], data.sectors(), default=values["sectors"], key="w_sectors",
                   on_change=_save, args=("sectors", "w_sectors"), label_visibility="collapsed")
    sec = tuple(st.session_state["sectors"])
    blocks.figures([(blocks.count_up(universe.counts(r, sec, values["esg"])["kept"]),
                     T["stocks_left"].format(region=r)) for r in values["regions"]])


def esg_label(level: str) -> str:
    """Slider label of an ESG level, e.g. "Medium (30%)"."""
    return f"{level} ({blocks.pct(cfg.ESG_LEVELS[level], 0)})"


def esg(values: dict) -> None:
    """3d: ESG screen slider, with the stocks excluded today and the ESG score it buys, live."""
    blocks.section(*J["esg"])
    st.select_slider(T["esg_level"], list(cfg.ESG_LEVELS), value=values["esg"], format_func=esg_label,
                     key="w_esg", on_change=_save, args=("esg", "w_esg"), help=content.ESG_HELP)
    counts = [universe.counts(r, tuple(values["sectors"]), values["esg"]) for r in values["regions"]]
    items = [(blocks.count_up(sum(c["excluded"] for c in counts)), T["excluded"]),
             (blocks.count_up(sum(c["kept"] for c in counts)), T["kept"])]
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
    """3e: one slider sets α, with the resulting split on one live line."""
    blocks.section(*J["profile"])
    st.select_slider(T["level_slider"], list(cfg.ALPHAS), value=values["level"], format_func=level_label,
                     key="w_level", on_change=_save, args=("level", "w_level"))
    alpha = cfg.ALPHAS[st.session_state["level"]]
    st.markdown(T["level_line"].format(level=st.session_state["level"], alpha=blocks.pct(alpha, 0),
                                       rf=blocks.pct(1 - alpha, 0)))
