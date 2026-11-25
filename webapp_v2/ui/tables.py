"""Formatted tables: percentages by default, plain numbers for ratios and counts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

PLAIN_COLUMNS = {"sharpe", "information_ratio"}  # ratios, not percentages


def show(table: pd.DataFrame, labels: dict | None = None, plain: set[str] = frozenset()) -> None:
    """Dataframe with percent formatting, except ratio columns shown with two decimals."""
    labels = labels or {}
    shown = table.copy().astype(object)
    for col in table.columns:
        fmt = "{:.2f}" if col in PLAIN_COLUMNS or col in plain else "{:.2%}"
        # a missing value (e.g. tracking error of the benchmark against itself) is shown as a dash, not "None"
        shown[col] = [("–" if pd.isna(v) else fmt.format(v)) for v in table[col]]
    st.dataframe(shown.rename(columns=labels), width="stretch")


def progress(table: pd.DataFrame, labels: dict, bars: set[str], counts: set[str]) -> None:
    """Table in percent with progress bars on the ``bars`` columns and integers on ``counts``."""
    config = {}
    for col in table.columns:
        if col in counts:
            config[col] = st.column_config.NumberColumn(labels.get(col, col), format="%d")
        elif col in bars:
            config[col] = st.column_config.ProgressColumn(labels.get(col, col), format="%.1f%%", min_value=0,
                                                          max_value=100)
        else:
            config[col] = st.column_config.NumberColumn(labels.get(col, col), format="%.1f%%")
    shown = table.astype(float).mul([1 if c in counts else 100 for c in table.columns])
    st.dataframe(shown, column_config=config, width="stretch")
