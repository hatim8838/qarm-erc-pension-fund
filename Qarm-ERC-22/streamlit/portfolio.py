"""ERC Portfolio (Amber design): two-level Equal Risk Contribution allocation of the investor's screened universe.

Method (QARM II, LN 5 / Lab 5): minimise 1/2 y'Sigma y - sum b_i ln(y_i), then w = y / sum(y).
Covariance: the team estimator of core.utilities (Ledoit-Wolf shrinkage for large blocks).
All numbers come from ``data/processed/``; nothing is invented.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import (
    ASSET_ID_SEP,
    BOND_SLEEVE,
    COMMODITY_SLEEVE,
    EQUITY_ASSET_CLASS,
    ESTIMATION_WINDOW,
    EX_COMMODITIES_SUFFIX,
    NON_EQUITY_SLEEVES,
    PORTFOLIO_START,
    ZONES,
)
from core.erc_portfolio import build_erc_portfolio, estimation_window
from core.importation_data import read_processed
from core.utilities import drawdown, rebalancing_dates
from services import DataUnavailableError, ScreeningParams, cached_screening
from web_util import (
    AMBER,
    CHART_BLUE,
    CHART_GOLD,
    PAGES,
    PEACH,
    RESULT_KEY,
    SERIES_COLORS,
    SERIES_DASH,
    SLATE,
    SLEEVE_COLORS,
    chart_colors,
    fmt_date,
    fmt_pct,
    page_header,
    style_figure,
    sub_title,
)

# --------------------------------------------------------------------------- #
# Look & feel: Amber palette from web_util (peach = capital, blue = risk, amber = target)
# --------------------------------------------------------------------------- #
LIGHT = PEACH          # capital-weight bars
RISK = CHART_BLUE      # risk-contribution bars


def _base(series: str) -> str:
    """Series name without the " ex Commodities" suffix (same colour and line style)."""
    return series.removesuffix(EX_COMMODITIES_SUFFIX)


def add_target_line(fig: go.Figure, y: float, label: str) -> go.Figure:
    """Risk-budget target: a thin dotted guide line across the bars, with a small
    amber tag in the right margin (outside the bars, so it never covers them)."""
    fig.add_hline(y=y, line_dash="dot", line_width=1.5, line_color=AMBER)
    fig.add_annotation(
        x=1, xref="paper", xanchor="left", xshift=8,
        y=y, yref="y", yanchor="middle",
        text=f"{label}<br><b>{y:.1f}%</b>",
        showarrow=False, align="left",
        font=dict(size=11, color="white"),
        bgcolor=AMBER, borderpad=5,
    )
    fig.update_layout(margin=dict(r=90))
    return fig

page_header(
    "ERC Portfolio",
    "Every building block of the portfolio contributes <b>the same share of risk</b>, "
    "not the same share of capital. The allocation below is computed from your screened universe, "
    "inside each region, then across regions, bonds and (if you keep them) commodities.",
    eyebrow="Léman Wealth Management · Step 3",
)


# --------------------------------------------------------------------------- #
# Data access (cached, read-only)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading return series…")
def load_returns(stocks: tuple[tuple[str, str], ...], include_commodities: bool = True) -> pd.DataFrame:
    """Daily returns of the selected stocks, plus the bond sleeve and (optionally) the commodity sleeve.

    Columns are ``"<sleeve>|<asset>"`` (stocks are given as ``(zone, name)``). The sleeves found in
    the columns are exactly the sleeves of the ERC portfolio, so leaving commodities out here makes
    the across-sleeve ERC run on one sleeve less (risk budget 1/N with the new N).
    """
    frames = []
    for zone in ZONES:
        names = [n for z, n in stocks if z == zone]
        if names:
            df = read_processed("returns_daily", EQUITY_ASSET_CLASS[zone], columns=names)
            df.columns = [f"{zone}{ASSET_ID_SEP}{c}" for c in df.columns]
            frames.append(df)
    bonds = read_processed("returns_daily", "bonds")
    bonds.columns = [f"{BOND_SLEEVE}{ASSET_ID_SEP}{c}" for c in bonds.columns]
    frames.append(bonds)
    if include_commodities:
        comm = read_processed("returns_daily", "commodities")
        comm.columns = [f"{COMMODITY_SLEEVE}{ASSET_ID_SEP}{c}" for c in comm.columns]
        frames.append(comm)
    return pd.concat(frames, axis=1).sort_index()


@st.cache_data(show_spinner="Estimating covariance and solving the ERC problem…", max_entries=48)
def compute_portfolio(stocks, as_of, include_commodities: bool = True):
    """Equal risk budgets everywhere (no ESG input)."""
    returns = load_returns(stocks, include_commodities)
    window, dropped = estimation_window(returns, pd.Timestamp(as_of), ESTIMATION_WINDOW)
    return build_erc_portfolio(window, esg_scores=None, dropped=dropped)


@st.cache_data(show_spinner=False)
def reference_backtest() -> dict | None:
    """Pre-computed backtest written by ``compute_erc.py`` (None if the files are missing)."""
    try:
        from core.config import PROCESSED_DIR

        return {
            "returns": pd.read_parquet(PROCESSED_DIR / "portfolio_returns.parquet"),
            "metrics": pd.read_csv(PROCESSED_DIR / "performance_metrics.csv", index_col=0),
            "crisis": pd.read_csv(PROCESSED_DIR / "crisis_performance.csv", index_col=0),
            "sleeves": pd.read_parquet(PROCESSED_DIR / "sleeve_weights_erc.parquet"),
        }
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def rebalancing_calendar() -> list[pd.Timestamp]:
    idx = read_processed("returns_daily", "bonds").dropna(how="all").index
    return list(rebalancing_dates(idx, PORTFOLIO_START))[::-1]  # most recent first


# --------------------------------------------------------------------------- #
# Universe coming from the investor preferences
# --------------------------------------------------------------------------- #
result = st.session_state.get(RESULT_KEY)
using_default = result is None
if using_default:
    try:
        result = cached_screening(ScreeningParams(tuple(ZONES), None, "None", True))
    except DataUnavailableError as exc:
        st.error(str(exc))
        st.stop()
selected = result["selected"]
params = result["params"]

if using_default:
    st.markdown(
        '<div class="amber-callout">No investor preferences applied yet: the portfolio below uses the default '
        "universe (all regions, all industries).</div>",
        unsafe_allow_html=True,
    )
    st.page_link(PAGES["preferences"], label="Set your investor preferences", icon=":material/tune:")
else:
    regions_txt = ", ".join(params.regions)
    industries_txt = "all industries" if params.sectors is None else f"{len(params.sectors)} industries"
    st.markdown(
        f'<span class="amber-tag">Regions · {regions_txt}</span>'
        f'<span class="amber-tag">{industries_txt}</span>'
        f'<span class="amber-tag">Commodities · {"included" if params.include_commodities else "excluded"}</span>'
        f'<span class="amber-tag">{len(selected)} selected stocks</span>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
as_of = rebalancing_calendar()[0]  # most recent monthly rebalancing date

st.caption(
    f"Risk estimated on the last {ESTIMATION_WINDOW} business days, as of {fmt_date(as_of)} · "
    "long-only · fully invested."
)

stocks = tuple(sorted((str(r.zone), str(r["name"])) for _, r in selected.iterrows()))
include_commodities = params.include_commodities
if selected.empty:
    st.warning(
        "Your screening selected no equity: the portfolio only contains "
        + ("bonds and commodities." if include_commodities else "bonds, which is not enough for an ERC portfolio.")
    )

try:
    port = compute_portfolio(stocks, as_of.strftime("%Y-%m-%d"), include_commodities)
except (ValueError, FileNotFoundError) as exc:
    st.error(f"The portfolio could not be computed: {exc}")
    st.stop()

if port.dropped:
    st.caption(
        f"{len(port.dropped)} selected asset(s) are left out on this date: they do not have a complete "
        f"{ESTIMATION_WINDOW}-day return history."
    )

sleeves = list(port.sleeve_weights.index)
n_sleeves = len(sleeves)
w = port.weights
equity_share = float(port.sleeve_weights.drop(list(NON_EQUITY_SLEEVES), errors="ignore").sum())
non_equity_txt = " and ".join(s.lower() for s in sleeves if s in NON_EQUITY_SLEEVES)

# --------------------------------------------------------------------------- #
# Headline numbers
# --------------------------------------------------------------------------- #
k1, k2, k3, k4 = st.columns(4)
k1.metric("Portfolio volatility", fmt_pct(port.volatility), help="Annualised, estimated on the window with the chosen covariance.")
k2.metric("Assets held", f"{int((w > 1e-6).sum()):,}", help=f"Across {n_sleeves} sleeves.")
k3.metric("Equity share of capital", fmt_pct(equity_share), help=f"Total capital weight of the equity regions; the rest is in {non_equity_txt}.")
ok = port.max_rc_gap < 1e-4
k4.metric(
    "Risk-contribution check",
    "Verified" if ok else "Check solver",
    help=f"Largest gap between a relative risk contribution and its budget, at both levels: {port.max_rc_gap:.2e}.",
)

st.write("")
tab_alloc, tab_risk, tab_ew, tab_hold, tab_bt = st.tabs(
    ["Allocation", "Risk contributions", "ERC vs Equal Weight", "Holdings", "Historical backtest"]
)

# --------------------------------------------------------------------------- #
# Allocation
# --------------------------------------------------------------------------- #
with tab_alloc:
    left, right = st.columns([5, 5], gap="large")
    with left:
        sub_title("Capital allocation by sleeve")
        fig = go.Figure(
            go.Pie(
                labels=sleeves,
                values=port.sleeve_weights.to_numpy(),
                hole=0.55,
                sort=False,
                direction="clockwise",
                rotation=90,
                marker=dict(colors=[SLEEVE_COLORS.get(s, SLATE) for s in sleeves], line=dict(color=chart_colors()["sep"], width=2)),
                textposition="outside",   # sleeve names on the chart: the shades are close
                texttemplate="%{label}<br><b>%{percent:.1%}</b>",
                outsidetextfont=dict(size=13, color=chart_colors()["text"]),
                automargin=True,          # grow the margins so no outside label is cut off
                hovertemplate="%{label}: %{percent}<extra></extra>",
            )
        )
        fig = style_figure(fig, height=420)
        fig.update_layout(showlegend=False, margin=dict(l=70, r=70, t=50, b=50))
        st.plotly_chart(fig)
    with right:
        sub_title("Sleeves")
        table = pd.DataFrame(
            {
                "Sleeve": sleeves,
                "Assets": [len(port.inner_weights[s]) for s in sleeves],
                "Capital weight": (100 * port.sleeve_weights).to_numpy(),
                "Risk contribution": (100 * port.sleeve_rc).to_numpy(),
                "Stand-alone volatility": (100 * port.sleeve_vol).to_numpy(),
            }
        )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Capital weight": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Risk contribution": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Stand-alone volatility": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        top_cap = port.sleeve_weights.idxmax()
        low_cap = port.sleeve_weights.idxmin()
        st.markdown(
            f'<div class="amber-callout">The portfolio holds <b>{fmt_pct(port.sleeve_weights[top_cap])}</b> of its capital in '
            f"<b>{top_cap}</b> and only <b>{fmt_pct(port.sleeve_weights[low_cap])}</b> in <b>{low_cap}</b>, "
            f"yet each sleeve contributes <b>{fmt_pct(1 / n_sleeves)}</b> of the total risk. Low-volatility sleeves "
            "receive more capital, high-volatility sleeves less.</div>",
            unsafe_allow_html=True,
        )

    sub_title("Largest positions")
    top = w.sort_values(ascending=False).head(15)[::-1]
    labels = [f"{i.split(ASSET_ID_SEP, 1)[1]}  ·  {i.split(ASSET_ID_SEP, 1)[0]}" for i in top.index]
    fig = go.Figure(
        go.Bar(
            x=100 * top.to_numpy(),
            y=labels,
            orientation="h",
            marker_color=[SLEEVE_COLORS.get(i.split(ASSET_ID_SEP, 1)[0], SLATE) for i in top.index],
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Capital weight (%)", showlegend=False)
    fig = style_figure(fig, height=420)
    st.plotly_chart(fig)

# --------------------------------------------------------------------------- #
# Risk contributions
# --------------------------------------------------------------------------- #
with tab_risk:
    sub_title("Capital weights vs risk contributions, across sleeves")
    fig = go.Figure()
    fig.add_bar(name="Capital weight", x=sleeves, y=100 * port.sleeve_weights.to_numpy(), marker_color=LIGHT)
    fig.add_bar(name="Risk contribution", x=sleeves, y=100 * port.sleeve_rc.to_numpy(), marker_color=RISK)
    fig.update_layout(barmode="group", yaxis_title="% of portfolio")
    fig = style_figure(fig, height=360)
    add_target_line(fig, 100 / n_sleeves, f"Target 1/{n_sleeves}")
    st.plotly_chart(fig)
    st.caption(
        "Equal risk contribution does not mean equal capital: the blue bars are all equal to the target, the peach bars are not."
    )

    st.write("")
    sub_title("Inside a sleeve")
    sleeve = st.selectbox("Sleeve", sleeves, key="sleeve_pick")
    inner_w = port.inner_weights[sleeve]
    inner_rc = port.inner_rc[sleeve]
    budget = port.inner_budgets[sleeve]
    if len(inner_w) == 1:
        st.info(f"{sleeve} contains a single asset: it carries 100% of the sleeve.")
    else:
        order = inner_w.sort_values(ascending=False).head(25).index
        names = [i.split(ASSET_ID_SEP, 1)[1] for i in order]
        if True:
            st.markdown(f"Top {len(order)} of {len(inner_w)} assets" if len(inner_w) > 25 else "All assets")
            fig = go.Figure()
            fig.add_bar(name="Weight inside sleeve", x=names, y=100 * inner_w[order].to_numpy(), marker_color=LIGHT)
            fig.add_bar(name="Risk contribution", x=names, y=100 * inner_rc[order].to_numpy(), marker_color=RISK)
            fig.update_layout(barmode="group", yaxis_title="% of the sleeve", xaxis_tickangle=-45)
            fig = style_figure(fig, height=420)
            add_target_line(fig, 100 / len(inner_w), f"Target 1/{len(inner_w)}")  # equal budgets
            st.plotly_chart(fig)

# --------------------------------------------------------------------------- #
# ERC vs Equal Weight vs Minimum Variance (LN 5)
# --------------------------------------------------------------------------- #
with tab_ew:
    cmp_ = port.comparison
    rcs = cmp_.attrs["risk_contributions"]
    st.markdown(
        "For the same sleeves, the risk of the ERC portfolio sits between the minimum-variance and the "
        "equal-weight portfolios.",
        unsafe_allow_html=True,
    )
    v = cmp_["volatility"]
    holds = v["Minimum Variance"] <= v["ERC"] + 1e-9 <= v["Equal Weight"] + 2e-9
    show = pd.DataFrame(
        {
            "Portfolio": cmp_.index,
            "Volatility": 100 * cmp_["volatility"].to_numpy(),
            "Largest risk contribution": 100 * cmp_["max_risk_contribution"].to_numpy(),
        }
    )
    st.dataframe(
        show,
        hide_index=True,
        width="stretch",
        column_config={
            "Volatility": st.column_config.NumberColumn(format="%.2f%%"),
            "Largest risk contribution": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    (st.success if holds else st.warning)(
        "ERC risk lies between minimum variance and equal weight." if holds else "The ordering is not met numerically on this date."
    )
    pal = {"Equal Weight": "#BDBDBD", "ERC": CHART_BLUE, "Minimum Variance": CHART_GOLD}
    sub_title("Risk contributions by sleeve")
    fig = go.Figure([go.Bar(name=c, x=sleeves, y=100 * rcs.loc[sleeves, c], marker_color=pal[c]) for c in rcs])
    fig.update_layout(barmode="group", yaxis_title="% of risk")
    st.plotly_chart(style_figure(fig, height=340))
    st.caption(
        "Equal Weight spreads capital evenly but lets the most volatile sleeves dominate the risk. Minimum Variance "
        "minimises risk but concentrates it in one or two sleeves. ERC balances the risk itself."
    )

# --------------------------------------------------------------------------- #
# Holdings
# --------------------------------------------------------------------------- #
with tab_hold:
    hold = pd.DataFrame(
        {
            "Sleeve": [i.split(ASSET_ID_SEP, 1)[0] for i in w.index],
            "Asset": [i.split(ASSET_ID_SEP, 1)[1] for i in w.index],
            "Capital weight (%)": 100 * w.to_numpy(),
            "Share of total risk (%)": 100 * port.risk_share.reindex(w.index).to_numpy(),
            "Stand-alone volatility (%)": 100 * port.asset_vol.reindex(w.index).to_numpy(),
        }
    ).sort_values("Capital weight (%)", ascending=False)
    with st.container(key="card_hold_filters"):
        f1, f2 = st.columns([3, 2], gap="medium")
        chosen = f1.multiselect("Sleeves", sleeves, default=sleeves)
        query = f2.text_input("Search an asset")
    view = hold[hold["Sleeve"].isin(chosen)]
    if query:
        view = view[view["Asset"].str.contains(query, case=False, na=False)]
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        height=460,
        column_config={
            "Capital weight (%)": st.column_config.NumberColumn(format="%.3f"),
            "Share of total risk (%)": st.column_config.NumberColumn(format="%.3f"),
            "Stand-alone volatility (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    cap_col, dl_col = st.columns([3, 1], vertical_alignment="center")
    cap_col.caption(f"{len(view):,} of {len(hold):,} assets. Weights as of {fmt_date(port.as_of)}.")
    dl_col.download_button(
        "Download holdings (CSV)",
        hold.to_csv(index=False).encode("utf-8"),
        file_name=f"erc_holdings_{port.as_of:%Y-%m-%d}.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

# --------------------------------------------------------------------------- #
# Reference backtest (pre-computed by compute_erc.py)
# --------------------------------------------------------------------------- #
with tab_bt:
    ref = reference_backtest()
    if ref is None:
        st.info("The pre-computed backtest files were not found in data/processed/.")
    else:
        st.caption(
            f"Historical simulation of the full-universe portfolio, monthly rebalancing since {PORTFOLIO_START[:4]}, "
            "before costs. Past performance is not a forecast. Not recomputed for your selection."
        )
        rets = ref["returns"]
        base = ["ERC", "60/40", "1/N"]
        # Without commodities, show the ex-commodities backtests (ERC on 5 sleeves) when compute_erc.py
        # has produced them; 60/40 holds no commodities, so it is the same in both cases.
        ex_cols = {b: f"{b}{EX_COMMODITIES_SUFFIX}" for b in ("ERC", "1/N")}
        has_ex = all(c in rets.columns for c in ex_cols.values())
        if not include_commodities and has_ex:
            base = [ex_cols.get(b, b) for b in base]
        elif not include_commodities:
            st.warning(
                "The historical simulation below still includes commodities: the backtest without commodities "
                "has not been computed yet. Run `python compute_erc.py` once to add it."
            )
        pick = [c for c in base if c in rets.columns]
        if pick:
            wealth = 100 * (1 + rets[pick].fillna(0)).cumprod()
            fig = go.Figure(
                [
                    go.Scatter(
                        x=wealth.index,
                        y=wealth[c],
                        name=c,
                        line=dict(color=SERIES_COLORS.get(_base(c)), dash=SERIES_DASH.get(_base(c), "solid"),
                                  width=3 if _base(c) == "ERC" else 1.8),
                    )
                    for c in pick
                ]
            )
            fig.update_layout(yaxis_title="Value of 100 invested (log scale)", yaxis_type="log")
            st.plotly_chart(style_figure(fig, height=400))

            dd = pd.DataFrame({c: 100 * drawdown(rets[c]) for c in pick})
            fig = go.Figure(
                [
                    go.Scatter(x=dd.index, y=dd[c], name=c, line=dict(color=SERIES_COLORS.get(_base(c)), dash=SERIES_DASH.get(_base(c), "solid"),
                                                    width=2 if _base(c) == "ERC" else 1.3))
                    for c in pick
                ]
            )
            fig.update_layout(yaxis_title="Drawdown (%)")
            sub_title("Drawdowns")
            st.plotly_chart(style_figure(fig, height=300))

        m = ref["metrics"].loc[[c for c in pick if c in ref["metrics"].index]] if pick else ref["metrics"].iloc[:0]
        if not m.empty:
            sub_title("Performance and risk metrics")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Annualised return": 100 * m["ann_return"],
                        "Volatility": 100 * m["ann_volatility"],
                        "Sharpe ratio": m["sharpe"],
                        "Max drawdown": 100 * m["max_drawdown"],
                    }
                ),
                width="stretch",
                column_config={
                    "Annualised return": st.column_config.NumberColumn(format="%.1f%%"),
                    "Volatility": st.column_config.NumberColumn(format="%.1f%%"),
                    "Sharpe ratio": st.column_config.NumberColumn(format="%.2f"),
                    "Max drawdown": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

# --------------------------------------------------------------------------- #
# Method and limitations
# --------------------------------------------------------------------------- #
st.write("")
with st.expander("Method and limitations"):
    st.markdown(
        "- **Method**: each region, then bonds and commodities, is built so that every component contributes the same "
        "share of risk (Equal Risk Contribution). Risk is estimated on the last 252 business days with Ledoit-Wolf "
        "shrinkage. Long-only, fully invested.\n"
        "- **Commodities are optional**: without them the across-sleeve ERC runs on one sleeve less, so each "
        "remaining sleeve carries 1/N of the risk with the new N (e.g. 1/5 instead of 1/6). The freed capital is "
        "spread over the remaining sleeves, bonds (the calmest) taking the largest part; the weights inside each "
        "sleeve do not change.\n"
        "- **Limits**: estimates are historical and do not guarantee future risk. Stock lists are today's index "
        "constituents. Educational project, not investment advice."
    )
