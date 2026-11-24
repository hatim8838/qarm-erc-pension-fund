"""Interactive Plotly figures that follow the dark / light mode and animate their transitions."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config as cfg
from logic import data
from ui import theme


def _color(name: str, i: int = 0) -> str:
    """Fixed colour for known series, palette otherwise."""
    return cfg.SERIES_COLORS.get(str(name), cfg.PALETTE[i % len(cfg.PALETTE)])


def show(fig: go.Figure, height: int = 360, percent_y: bool = False, key: str | None = None,
         legend_y: float = -0.2) -> None:
    """Apply the current theme, hover, legend toggles and animated transitions, then render."""
    c = theme.colors()
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=24, b=8), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(color=c["textColor"], family="Inter, sans-serif"),
        legend=dict(orientation="h", y=legend_y), hovermode="x unified",
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


def sleeve_colors() -> dict[str, str]:
    """One fixed colour per sleeve (data order) and for the risk-free asset, shared by every chart."""
    return {**{s: cfg.PALETTE[i % len(cfg.PALETTE)] for i, s in enumerate(data.sleeves())},
            cfg.RISK_FREE: cfg.SERIES_COLORS[cfg.RISK_FREE]}


def donut(weights: pd.Series, height: int = 300, center: str = "", colors: dict | None = None, key=None) -> None:
    """Donut of weights with % labels, an optional centre text and a legend."""
    marker = [(colors or {}).get(n) or _color(n, i) for i, n in enumerate(weights.index)]
    fig = go.Figure(go.Pie(labels=weights.index, values=weights.to_numpy(), hole=0.64, sort=False,
                           marker=dict(colors=marker), textinfo="percent"))
    if center:
        fig.add_annotation(text=center, showarrow=False, font=dict(size=16))
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



def counts(values: pd.Series, horizontal: bool = False, axis_title: str = "", height: int = 400, key=None) -> None:
    """Bars of counts with the value on each bar (horizontal: largest at the top)."""
    v = values[::-1] if horizontal else values
    x, y = (v.to_numpy(), v.index) if horizontal else (v.index, v.to_numpy())
    fig = go.Figure(go.Bar(x=x, y=y, orientation="h" if horizontal else "v", text=v.to_numpy(),
                           textposition="outside", cliponaxis=False, marker_color=cfg.PALETTE[0]))
    fig.update_layout(hovermode="closest", **{"xaxis_title" if horizontal else "yaxis_title": axis_title})
    show(fig, height, key=key)


def histogram(values: pd.Series, axis_title: str, bins: int, height: int = 320, key=None) -> None:
    """Distribution of the values in ``bins`` bins."""
    fig = go.Figure(go.Histogram(x=values.dropna(), nbinsx=bins, marker_color=cfg.PALETTE[3]))
    fig.update_layout(hovermode="closest", xaxis_title=axis_title, bargap=0.05)
    show(fig, height, key=key)


def ranked(values: pd.Series, colors: list[str], axis_title: str, height: int = 440, key=None) -> None:
    """Horizontal bars in % (index = labels), largest at the top, one colour per bar."""
    fig = go.Figure(go.Bar(x=100 * values[::-1].to_numpy(), y=values.index[::-1], orientation="h",
                           marker_color=colors[::-1], hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
    fig.update_layout(hovermode="closest", xaxis_title=axis_title, showlegend=False)
    show(fig, height, key=key)


def versus(df: pd.DataFrame, target: float, target_label: str, axis_title: str, tilt: bool = False,
           height: int = 380, key=None) -> None:
    """Light vs dark grouped bars in % (two columns) with a dashed target line."""
    c = theme.colors()
    fig = go.Figure([go.Bar(x=df.index, y=100 * df[col], name=str(col), marker_color=color)
                     for col, color in zip(df.columns, (c["weight"], c["risk"]))])
    fig.add_hline(y=100 * target, line_dash="dash", line_color=c["textColor"], annotation_text=target_label,
                  annotation_position="top right")
    fig.update_layout(barmode="group", hovermode="closest", yaxis_title=axis_title,
                      xaxis_tickangle=-45 if tilt else 0)
    show(fig, height, key=key, legend_y=1.12 if tilt else -0.2)  # rotated labels: legend on top
