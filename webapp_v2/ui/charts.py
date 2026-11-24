"""Interactive Plotly figures that follow the dark / light mode and animate their transitions."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config as cfg
from ui import theme


def _color(name: str, i: int = 0) -> str:
    """Fixed colour for known series, palette otherwise."""
    return cfg.SERIES_COLORS.get(str(name), cfg.PALETTE[i % len(cfg.PALETTE)])


def show(fig: go.Figure, height: int = 360, percent_y: bool = False, key: str | None = None) -> None:
    """Apply the current theme, hover, legend toggles and animated transitions, then render."""
    c = theme.colors()
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=24, b=8), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(color=c["textColor"], family="Inter, sans-serif"),
        legend=dict(orientation="h", y=-0.2), hovermode="x unified",
        transition=dict(duration=cfg.CHART_TRANSITION_MS, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor=c["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=c["grid"], zeroline=False, tickformat=".0%" if percent_y else None)
    st.plotly_chart(fig, key=key, config={"displaylogo": False})


def lines(df: pd.DataFrame, log_y: bool = False, percent_y: bool = False, height: int = 380, key=None) -> None:
    """Time series with a date-range slider (zoom), one line per column."""
    fig = go.Figure([go.Scatter(x=df.index, y=df[c], name=str(c), mode="lines",
                                line=dict(color=_color(c, i), width=2)) for i, c in enumerate(df)])
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
    if log_y:
        fig.update_yaxes(type="log")
    show(fig, height, percent_y, key)


def donut(weights: pd.Series, height: int = 300, key=None) -> None:
    """Donut of weights."""
    colors = [_color(n, i) for i, n in enumerate(weights.index)]
    fig = go.Figure(go.Pie(labels=weights.index, values=weights.to_numpy(), hole=0.64, sort=False,
                           marker=dict(colors=colors), textinfo="percent"))
    fig.update_layout(hovermode=False)
    show(fig, height, key=key)


def bars(df: pd.DataFrame, horizontal: bool = False, percent: bool = True, height: int = 320, key=None) -> None:
    """Grouped bars: one trace per column, categories on the index."""
    fig = go.Figure()
    for i, c in enumerate(df):
        x, y = (df[c], df.index) if horizontal else (df.index, df[c])
        fig.add_bar(x=x, y=y, name=str(c), orientation="h" if horizontal else "v", marker_color=_color(c, i))
    fig.update_layout(barmode="group", hovermode="closest")
    if horizontal and percent:
        fig.update_xaxes(tickformat=".0%")
    show(fig, height, percent_y=percent and not horizontal, key=key)


def stacked_area(weights: pd.DataFrame, height: int = 340, key=None) -> None:
    """Weights over time, stacked to 100%, with a date-range slider."""
    fig = go.Figure([go.Scatter(x=weights.index, y=weights[c], name=str(c), stackgroup="w", mode="lines",
                                line=dict(width=0.5, color=_color(c, i))) for i, c in enumerate(weights)])
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
    show(fig, height, percent_y=True, key=key)


def fan(percentiles: pd.DataFrame, height: int = 380, key=None) -> None:
    """Projection fan: 5–95% and 25–75% bands around the median (columns are the percentiles)."""
    p = percentiles
    lo, q1, mid, q3, hi = (p[c] for c in p.columns)
    fig = go.Figure()
    for low, high, name, alpha in ((lo, hi, "5–95%", 0.15), (q1, q3, "25–75%", 0.3)):
        fig.add_scatter(x=p.index, y=high, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=p.index, y=low, mode="lines", line=dict(width=0), fill="tonexty", name=name,
                        fillcolor=f"rgba(124,196,255,{alpha})")
    fig.add_scatter(x=p.index, y=mid, mode="lines", name="Median", line=dict(color=cfg.PALETTE[0], width=3))
    fig.update_xaxes(title="Years")
    show(fig, height, key=key)
