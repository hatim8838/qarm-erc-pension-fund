"""ERC Portfolio: two-level Equal Risk Contribution allocation of the investor's screened universe.

Method (QARM II, LN 5 / Lab 5): minimise 1/2 y'Sigma y - sum b_i ln(y_i), then w = y / sum(y).
Covariance: the team estimator of core.utilities (Ledoit-Wolf shrinkage for large blocks).
All numbers come from ``data/processed/``; nothing is invented.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import ASSET_ID_SEP, EQUITY_ASSET_CLASS, ESTIMATION_WINDOW, PORTFOLIO_START, ZONES
from core.erc_portfolio import build_erc_portfolio, estimation_window
from core.importation_data import read_processed
from core.utilities import drawdown, rebalancing_dates
from services import DataUnavailableError, ScreeningParams, cached_screening
from web_util import NAVY, PAGES, RESULT_KEY, SLATE, ESG_GREEN, fmt_date, fmt_pct, page_header, style_figure

# --------------------------------------------------------------------------- #
# Look & feel (same restrained palette as the rest of the app)
# --------------------------------------------------------------------------- #
CHARCOAL = "#2B2F36"
LIGHT = "#C9D0DA"
GOLD = "#C08A3E"
SLEEVE_COLORS = {
    "US": NAVY,
    "Eurozone": "#3E6FA8",
    "Pacific": "#7A9CC6",
    "EM EMEA": "#B7C4D6",
    "Bonds": SLATE,
    "Commodities": GOLD,
}
SERIES_COLORS = {"ERC": NAVY, "ESG": ESG_GREEN, "60/40": "#7C8591", "1/N": "#B3BAC4", "S&P 500": GOLD, "AGG": "#9AA6B5"}

st.markdown(
    """
<style>
.erc-lead {color:#4A4F57; font-size:1.02rem; line-height:1.6; max-width:60rem; margin:.2rem 0 1.2rem 0;}
.erc-callout {border-left:3px solid #1B365D; background:#F3F5F8; padding:.8rem 1rem; border-radius:4px;
              color:#1A1F2B; font-size:.95rem; line-height:1.55; margin:.4rem 0 1rem 0;}
.erc-tag {display:inline-block; padding:.1rem .55rem; border-radius:999px; font-size:.72rem; font-weight:600;
          margin-right:.35rem; background:#EEF1F5; color:#5B6B7F;}
.erc-tag-course {background:#E5F2EC; color:#2E7D5B;}
</style>
""",
    unsafe_allow_html=True,
)

page_header(
    "ERC Portfolio",
    None,
    eyebrow="Léman Wealth Management · Step 3",
)
st.markdown(
    '<p class="erc-lead">Every building block of the portfolio contributes <b>the same share of risk</b>, '
    "not the same share of capital. The allocation below is computed from your screened universe, "
    "inside each region, then across regions, bonds and commodities.</p>",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data access (cached, read-only)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading return series…")
def load_returns(stocks: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    """Daily returns of the selected stocks, plus the bond and commodity sleeves.

    Columns are ``"<sleeve>|<asset>"`` (stocks are given as ``(zone, name)``).
    """
    frames = []
    for zone in ZONES:
        names = [n for z, n in stocks if z == zone]
        if names:
            df = read_processed("returns_daily", EQUITY_ASSET_CLASS[zone], columns=names)
            df.columns = [f"{zone}{ASSET_ID_SEP}{c}" for c in df.columns]
            frames.append(df)
    bonds = read_processed("returns_daily", "bonds")
    bonds.columns = [f"Bonds{ASSET_ID_SEP}{c}" for c in bonds.columns]
    comm = read_processed("returns_daily", "commodities")
    comm.columns = [f"Commodities{ASSET_ID_SEP}{c}" for c in comm.columns]
    return pd.concat([*frames, bonds, comm], axis=1).sort_index()


@st.cache_data(show_spinner="Estimating covariance and solving the ERC problem…", max_entries=48)
def compute_portfolio(stocks, scores, as_of, esg_budgets: bool):
    returns = load_returns(stocks)
    window, dropped = estimation_window(returns, pd.Timestamp(as_of), ESTIMATION_WINDOW)
    esg = pd.Series(dict(scores), dtype=float) if esg_budgets else None
    return build_erc_portfolio(window, esg_scores=esg, dropped=dropped)


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
        result = cached_screening(ScreeningParams(tuple(ZONES), None, "Medium", True))
    except DataUnavailableError as exc:
        st.error(str(exc))
        st.stop()
selected = result["selected"]
params = result["params"]

if using_default:
    st.info(
        "No investor preferences applied yet: the portfolio below uses the default universe "
        "(all regions, all industries, ESG ambition Medium)."
    )
    st.page_link(PAGES["preferences"], label="Set your investor preferences", icon=":material/tune:")
else:
    regions_txt = ", ".join(params.regions)
    industries_txt = "all industries" if params.sectors is None else f"{len(params.sectors)} industries"
    st.markdown(
        f'<span class="erc-tag">Regions · {regions_txt}</span>'
        f'<span class="erc-tag">{industries_txt}</span>'
        f'<span class="erc-tag">ESG ambition · {params.esg_label}</span>'
        f'<span class="erc-tag">{len(selected)} selected stocks</span>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
as_of = rebalancing_calendar()[0]  # most recent monthly rebalancing date

with st.container(border=True):
    budget_label = st.radio(
        "Risk budgets inside the equity regions",
        ["Equal risk contribution (ERC)", "ESG-tilted risk budgets"],
        horizontal=True,
        help="ERC: every stock gets the same risk budget (LN 5). ESG-tilted: the risk budget of a stock is "
        "proportional to its ESG score (the team's extension of the risk-budgeting framework).",
    )
    st.caption(
        f"Risk estimated on the last {ESTIMATION_WINDOW} business days, as of {fmt_date(as_of)} · "
        "long-only · fully invested."
    )
esg_budgets = budget_label.startswith("ESG")

stocks = tuple(sorted((str(r.zone), str(r["name"])) for _, r in selected.iterrows()))
scores = tuple((i, float(v)) for i, v in selected["esg_score"].items() if pd.notna(v)) if esg_budgets else ()
if selected.empty:
    st.warning("Your screening selected no equity: the portfolio only contains bonds and commodities.")

try:
    port = compute_portfolio(stocks, scores, as_of.strftime("%Y-%m-%d"), esg_budgets)
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
equity_share = float(port.sleeve_weights.drop(["Bonds", "Commodities"], errors="ignore").sum())

# --------------------------------------------------------------------------- #
# Headline numbers
# --------------------------------------------------------------------------- #
k1, k2, k3, k4 = st.columns(4)
k1.metric("Portfolio volatility", fmt_pct(port.volatility), help="Annualised, estimated on the window with the chosen covariance.")
k2.metric("Assets held", f"{int((w > 1e-6).sum()):,}", help=f"Across {n_sleeves} sleeves.")
k3.metric("Equity share of capital", fmt_pct(equity_share), help="Total capital weight of the equity regions; the rest is in bonds and commodities.")
ok = port.max_rc_gap < 1e-4
k4.metric(
    "Risk-contribution check",
    "Verified" if ok else "Check solver",
    help=f"Largest gap between a relative risk contribution and its budget, at both levels: {port.max_rc_gap:.2e}.",
)

tab_alloc, tab_risk, tab_ew, tab_hold, tab_bt = st.tabs(
    ["Allocation", "Risk contributions", "ERC vs Equal Weight", "Holdings", "Historical backtest"]
)

# --------------------------------------------------------------------------- #
# Allocation
# --------------------------------------------------------------------------- #
with tab_alloc:
    left, right = st.columns([4, 6], gap="large")
    with left:
        st.markdown("**Capital allocation by sleeve**")
        fig = go.Figure(
            go.Pie(
                labels=sleeves,
                values=port.sleeve_weights.to_numpy(),
                hole=0.62,
                sort=False,
                marker=dict(colors=[SLEEVE_COLORS.get(s, SLATE) for s in sleeves], line=dict(color="white", width=2)),
                textinfo="percent",
                hovertemplate="%{label}: %{percent}<extra></extra>",
            )
        )
        fig.add_annotation(text=f"{n_sleeves}<br>sleeves", showarrow=False, font=dict(size=16, color=CHARCOAL))
        fig = style_figure(fig, height=330)
        fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"))
        st.plotly_chart(fig, width="stretch")
    with right:
        st.markdown("**Sleeves**")
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
            f'<div class="erc-callout">The portfolio holds <b>{fmt_pct(port.sleeve_weights[top_cap])}</b> of its capital in '
            f"<b>{top_cap}</b> and only <b>{fmt_pct(port.sleeve_weights[low_cap])}</b> in <b>{low_cap}</b>, "
            f"yet each sleeve contributes <b>{fmt_pct(1 / n_sleeves)}</b> of the total risk. Low-volatility sleeves "
            "receive more capital, high-volatility sleeves less.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("**Largest positions**")
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
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------------- #
# Risk contributions
# --------------------------------------------------------------------------- #
with tab_risk:
    st.markdown("**Capital weights vs risk contributions, across sleeves**")
    fig = go.Figure()
    fig.add_bar(name="Capital weight", x=sleeves, y=100 * port.sleeve_weights.to_numpy(), marker_color=LIGHT)
    fig.add_bar(name="Risk contribution", x=sleeves, y=100 * port.sleeve_rc.to_numpy(), marker_color=NAVY)
    fig.add_hline(
        y=100 / n_sleeves,
        line_dash="dash",
        line_color=CHARCOAL,
        annotation_text=f"Target: 1/{n_sleeves} = {100 / n_sleeves:.1f}%",
        annotation_position="top right",
    )
    fig.update_layout(barmode="group", yaxis_title="% of portfolio")
    st.plotly_chart(style_figure(fig, height=360), width="stretch")
    st.caption(
        "Equal risk contribution does not mean equal capital: the dark bars are all equal to the target, the light bars are not."
    )

    st.divider()
    st.markdown("**Inside a sleeve**")
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
            fig.add_bar(name="Risk contribution", x=names, y=100 * inner_rc[order].to_numpy(), marker_color=NAVY)
            if port.esg_budgets and sleeve in ZONES:
                fig.add_scatter(
                    name="Risk budget (ESG)",
                    x=names,
                    y=100 * budget[order].to_numpy(),
                    mode="markers",
                    marker=dict(symbol="line-ew-open", size=16, color=CHARCOAL, line=dict(width=2, color=CHARCOAL)),
                )
            else:
                fig.add_hline(
                    y=100 / len(inner_w),
                    line_dash="dash",
                    line_color=CHARCOAL,
                    annotation_text=f"Target 1/{len(inner_w)}",
                    annotation_position="top right",
                )
            fig.update_layout(barmode="group", yaxis_title="% of the sleeve", xaxis_tickangle=-45)
            st.plotly_chart(style_figure(fig, height=420), width="stretch")

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
    pal = {"Equal Weight": LIGHT, "ERC": NAVY, "Minimum Variance": GOLD}
    st.markdown("**Risk contributions by sleeve**")
    fig = go.Figure([go.Bar(name=c, x=sleeves, y=100 * rcs.loc[sleeves, c], marker_color=pal[c]) for c in rcs])
    fig.update_layout(barmode="group", yaxis_title="% of risk")
    st.plotly_chart(style_figure(fig, height=340), width="stretch")
    st.caption(
        "Equal Weight spreads capital evenly but lets the most volatile sleeves dominate the risk. Minimum Variance "
        "minimises risk but concentrates it in one or two sleeves. ERC balances the risk itself."
    )

# --------------------------------------------------------------------------- #
# Holdings
# --------------------------------------------------------------------------- #
with tab_hold:
    esg_map = selected["esg_score"].to_dict()
    hold = pd.DataFrame(
        {
            "Sleeve": [i.split(ASSET_ID_SEP, 1)[0] for i in w.index],
            "Asset": [i.split(ASSET_ID_SEP, 1)[1] for i in w.index],
            "ESG score": [f"{esg_map[i]:.1f}" if pd.notna(esg_map.get(i, np.nan)) else "–" for i in w.index],
            "Capital weight (%)": 100 * w.to_numpy(),
            "Share of total risk (%)": 100 * port.risk_share.reindex(w.index).to_numpy(),
            "Stand-alone volatility (%)": 100 * port.asset_vol.reindex(w.index).to_numpy(),
        }
    ).sort_values("Capital weight (%)", ascending=False)
    chosen = st.multiselect("Sleeves", sleeves, default=sleeves)
    query = st.text_input("Search an asset")
    view = hold[hold["Sleeve"].isin(chosen)]
    if query:
        view = view[view["Asset"].str.contains(query, case=False, na=False)]
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        height=460,
        column_config={
            "ESG score": st.column_config.TextColumn(),
            "Capital weight (%)": st.column_config.NumberColumn(format="%.3f"),
            "Share of total risk (%)": st.column_config.NumberColumn(format="%.3f"),
            "Stand-alone volatility (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.caption(f"{len(view):,} of {len(hold):,} assets. Weights as of {fmt_date(port.as_of)}.")
    st.download_button(
        "Download holdings (CSV)",
        hold.to_csv(index=False).encode("utf-8"),
        file_name=f"erc_holdings_{port.as_of:%Y-%m-%d}.csv",
        mime="text/csv",
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
        pick = [c for c in ["ERC", "ESG", "60/40", "1/N"] if c in rets.columns]
        if pick:
            wealth = 100 * (1 + rets[pick].fillna(0)).cumprod()
            fig = go.Figure(
                [
                    go.Scatter(
                        x=wealth.index,
                        y=wealth[c],
                        name=c,
                        line=dict(color=SERIES_COLORS.get(c), width=3 if c == "ERC" else 1.8),
                    )
                    for c in pick
                ]
            )
            fig.update_layout(yaxis_title="Value of 100 invested (log scale)", yaxis_type="log")
            st.plotly_chart(style_figure(fig, height=400), width="stretch")

            dd = pd.DataFrame({c: 100 * drawdown(rets[c]) for c in pick})
            fig = go.Figure(
                [
                    go.Scatter(x=dd.index, y=dd[c], name=c, line=dict(color=SERIES_COLORS.get(c), width=2 if c == "ERC" else 1.3))
                    for c in pick
                ]
            )
            fig.update_layout(yaxis_title="Drawdown (%)")
            st.markdown("**Drawdowns**")
            st.plotly_chart(style_figure(fig, height=300), width="stretch")

        m = ref["metrics"].loc[[c for c in pick if c in ref["metrics"].index]] if pick else ref["metrics"].iloc[:0]
        if not m.empty:
            st.markdown("**Performance and risk metrics**")
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
with st.expander("Method and limitations"):
    st.markdown(
        "- **Method**: each region, then bonds and commodities, is built so that every component contributes the same "
        "share of risk (Equal Risk Contribution). Risk is estimated on the last 252 business days with Ledoit-Wolf "
        "shrinkage. Long-only, fully invested.\n"
        "- **ESG option**: risk budgets proportional to ESG scores instead of equal budgets.\n"
        "- **Limits**: estimates are historical and do not guarantee future risk. Stock lists are today's index "
        "constituents and ESG scores are a recent snapshot. Educational project, not investment advice."
    )
