"""Client journey steps 3a-3e: regions, asset classes, sectors, ESG, risk profile."""

import pandas as pd
import streamlit as st

import config as cfg
import content
from logic import data, performance, profile, universe
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
    """3c: sectors applied to every chosen region, with the stocks left in each."""
    blocks.section(*J["sectors"])
    st.multiselect(J["sectors"][0], data.sectors(), default=values["sectors"], key="w_sectors",
                   on_change=_save, args=("sectors", "w_sectors"), label_visibility="collapsed")
    counts = universe.stock_counts(values["regions"], tuple(st.session_state["sectors"]), "off")
    blocks.figures([(blocks.count_up(n), T["stocks_left"].format(region=r)) for r, n in counts.items()])


def esg(values: dict) -> None:
    """3d: ESG off / screen / screen + ESG risk budgets, with the ESG score it buys."""
    blocks.section(*J["esg"], lecture="LN 6")
    options = list(cfg.ESG_MODES)
    st.radio(J["esg"][0], options, index=options.index(values["esg"]), format_func=content.ESG_LABELS.get,
             captions=[content.ESG_HELP[o] for o in options], key="w_esg", on_change=_save, args=("esg", "w_esg"),
             label_visibility="collapsed")
    mode, sec = st.session_state["esg"], tuple(values["sectors"])
    screened, everyone = (universe.average_esg(values["regions"], sec, m) for m in (mode, "off"))
    st.info(T["esg_score"].format(screened=f"{screened:.1f}", all=f"{everyone:.1f}"), icon=":material/eco:")


def _save_answer(key: str, options: list[str]) -> None:
    """Store the position of the chosen option (0 = most cautious)."""
    st.session_state["answers"][key] = options.index(st.session_state[f"w_{key}"])


def profile_step(values: dict) -> None:
    """3e: six questions -> score -> risk level -> target volatility σ*."""
    blocks.section(J["profile"][0], J["profile"][1].format(n=len(content.QUESTIONS)))
    answers, columns = values["answers"], st.columns(2)
    for i, (key, question, options) in enumerate(content.QUESTIONS):
        columns[i % 2].radio(question, options, index=answers.get(key), key=f"w_{key}", on_change=_save_answer,
                             args=(key, options))
    if profile.is_complete(answers):
        lvl = profile.level(profile.score(answers))
        st.success(T["level_result"].format(level=lvl, name=content.LEVEL_NAMES[lvl],
                                            target=blocks.pct(cfg.TARGET_VOLS[lvl])), icon=":material/target:")
    with st.expander(T["mapping"]):
        st.write(T["mapping_body"].format(n=profile.max_points()))
        st.table({f"{k} · {content.LEVEL_NAMES[k]}": blocks.pct(v) for k, v in cfg.TARGET_VOLS.items()})

