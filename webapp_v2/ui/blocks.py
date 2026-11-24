"""Reusable page blocks: hero, count-up figures, bento cards, steps, FAQ, CTA, insight box, method box, footer."""

from __future__ import annotations

import base64
import math
from functools import lru_cache
from html import escape

import streamlit as st

import config as cfg
import content


def pct(value: float, decimals: int = 1) -> str:
    """Percentage text, e.g. 0.0746 -> "7.5%"."""
    return "—" if math.isnan(value) else f"{value:.{decimals}%}"


def count_up(value: float, decimals: int = 0, suffix: str = "") -> str:
    """HTML of a number that counts up from 0 (CSS-only: one animated counter per digit group)."""
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.{decimals}f}".partition(".")[::2]
    html = f'{sign}<span class="count" style="--to:{int(whole)}"></span>'
    if decimals:
        zeros = len(frac) - len(frac.lstrip("0"))  # leading zeros of the decimals are written out
        tail = f'<span class="count" style="--to:{int(frac)}"></span>' if frac.strip("0") else ""
        html += "." + "0" * zeros + tail
    label = f"{sign}{whole}{'.' + frac if decimals else ''}{suffix}"
    return f'<span class="figure-value" aria-label="{label}">{html}{escape(suffix)}</span>'


def figures(items: list[tuple[str, str]]) -> None:
    """Row of key figures: (value HTML, label)."""
    cells = "".join(f'<div class="figure rise" style="--i:{i}">{value}<span>{escape(label)}</span></div>'
                    for i, (value, label) in enumerate(items))
    st.html(f'<div class="figures cols-{len(items)}">{cells}</div>')


@lru_cache(maxsize=1)
def _photo_uri() -> str:
    """The hero photo as a data URI (no static file server needed)."""
    return "data:image/jpeg;base64," + base64.b64encode(cfg.HERO_PHOTO.read_bytes()).decode()


def hero(key: str, cta_page: str | None = None, photo: bool = False) -> None:
    """Page hero: eyebrow, 3-word tagline, one-line subtext, optional photo and call to action."""
    tagline, subtext, cta = content.HERO[key]
    style = f' style="background-image:url({_photo_uri()})"' if photo else ""
    st.html(f'<section class="hero rise{" photo" if photo else ""}"{style}><p class="eyebrow">'
            f"{escape(content.APP_NAME)}</p><h1>{escape(tagline)}</h1><p class='lead'>{escape(subtext)}</p></section>")
    if cta and cta_page:
        st.page_link(cta_page, label=cta, icon=":material/arrow_forward:")


def section(title: str, subtitle: str = "") -> None:
    """Section title with an optional subtitle."""
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.html(f'<div class="section rise"><h2>{escape(title)}</h2>{sub}</div>')


def cards(items: list[dict], columns: int = 3) -> None:
    """Bento grid of cards: title, body, and optional kicker / avatar / tags / list."""
    st.html(f'<div class="bento cols-{columns}">{"".join(_card(i, item) for i, item in enumerate(items))}</div>')


def _card(index: int, item: dict) -> str:
    """HTML of one card (staggered entrance through --i)."""
    parts = [f'<div class="avatar">{escape(item["avatar"])}</div>' if item.get("avatar") else "",
             f'<p class="kicker">{escape(item["kicker"])}</p>' if item.get("kicker") else "",
             f'<h3>{escape(item["title"])}</h3><p>{escape(item.get("body", ""))}</p>']
    if item.get("list"):
        parts.append("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in item["list"]) + "</ul>")
    if item.get("tags"):
        parts.append('<div class="tags">' + "".join(f'<span class="tag">{escape(t)}</span>' for t in item["tags"]) + "</div>")
    return f'<article class="card rise" style="--i:{index}">{"".join(parts)}</article>'


def steps(items: list[tuple[str, str]]) -> None:
    """Numbered "3 steps" block."""
    html = "".join(f'<div class="step rise" style="--i:{i}"><span class="num">{i + 1}</span>'
                   f"<h3>{escape(t)}</h3><p>{escape(b)}</p></div>" for i, (t, b) in enumerate(items))
    st.html(f'<div class="steps">{html}</div>')


def faq(items: list[tuple[str, str]]) -> None:
    """FAQ accordion (native expanders, styled in CSS)."""
    for question, answer in items:
        with st.expander(question):
            st.write(answer)


def cta_band(title: str, label: str, page: str) -> None:
    """Closing call-to-action band."""
    with st.container(key="cta_band"):
        st.html(f'<h2 class="band-title">{escape(title)}</h2>')
        st.page_link(page, label=label, icon=":material/arrow_forward:")


def loader(text: str) -> str:
    """Animated loading state (three pulsing dots), shown while a portfolio is computed."""
    return f'<div class="loader"><span></span><span></span><span></span><p>{escape(text)}</p></div>'


def insight(html: str) -> None:
    """Highlighted insight box; ``html`` comes from content.py templates filled with computed numbers."""
    st.html(f'<div class="insight rise">{html}</div>')


def method_box() -> None:
    """Shared "Method and limitations" expander, filled from config (window, α range, ESG levels)."""
    title, items = content.METHOD
    alphas, levels = cfg.ALPHAS.values(), [v for v in cfg.ESG_LEVELS.values() if v > 0]
    values = {"n": cfg.ESTIMATION_WINDOW, "low": pct(min(alphas), 0), "high": pct(max(alphas), 0),
              "levels": "/".join(f"{100 * v:.0f}" for v in levels) + "%"}
    with st.expander(title, icon=":material/info:"):
        st.markdown("\n".join(f"- {item.format(**values)}" for item in items))


def footer() -> None:
    """Footer: brand, team, disclaimer and photo credit."""
    team = " · ".join(m["name"] for m in content.TEAM)
    st.html(f'<footer class="site-footer"><strong>{escape(content.APP_NAME)}</strong><span>{escape(team)}</span>'
            f"<small>{escape(content.DISCLAIMER)}</small>"
            f"<small>{escape(content.PHOTO_CREDIT)}</small></footer>")
