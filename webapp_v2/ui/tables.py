"""Formatted tables: percentages by default, plain numbers for ratios and counts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

PLAIN_COLUMNS = {"sharpe", "information_ratio", "DR"}  # ratios, not percentages


def show(table: pd.DataFrame, labels: dict | None = None, plain: set[str] = frozenset()) -> None:
    """Dataframe with percent formatting, except ratio columns shown with two decimals."""
    labels = labels or {}
    config = {}
    for col in table.columns:
        is_plain = col in PLAIN_COLUMNS or col in plain or str(col).startswith(("I*", "H*", "Gini"))
        config[col] = st.column_config.NumberColumn(labels.get(col, str(col)),
                                                    format="%.2f" if is_plain else "percent")
    st.dataframe(table, column_config=config, width="stretch")
