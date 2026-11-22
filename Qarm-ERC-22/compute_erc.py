"""Pipeline: data/raw/ -> data/processed/  (run from the repo root: python compute_erc.py)

1. Load and clean the Datastream files; save prices, returns and volatility.
2. Backtest the portfolios (monthly rebalancing, 1-year estimation window):
   - ERC: two-level ERC (within each sleeve, then across the 6 sleeves)
   - ESG: same, with ESG risk budgets inside the equity sleeves
   - ERC / ESG ex Commodities: same without the commodity sleeve (optional for the
     investor): the across-sleeve ERC then runs on 5 sleeves, risk budget 1/5 each
   - one ERC portfolio per sleeve (results by asset class)
   - benchmarks: 60/40 (S&P 500 / AGG) and 1/N (equal weight on the 6 sleeve indices,
     or on 5 without commodities)
3. Save weights, returns, performance metrics and crisis returns.
The Streamlit app only reads the files written here.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from core.config import (
    ASSET_ID_SEP,
    BENCHMARK_6040,
    BOND_SLEEVE,
    COMMODITY_SLEEVE,
    DATA_START,
    EQUITY_ASSET_CLASS,
    ESG_PORTFOLIO_START,
    EX_COMMODITIES_SUFFIX,
    PORTFOLIO_START,
    PROCESSED_DIR,
    PROCESSED_FILES,
    ZONES,
)
from core.esg import esg_risk_budgets
from core.importation_data import load_all
from core.utilities import (
    backtest,
    covariance_matrix,
    eligible_assets,
    erc_weights,
    performance_metrics,
    period_performance,
    rolling_volatility,
    simple_returns,
    two_level_weights,
)

logger = logging.getLogger("compute_erc")


def save(df: pd.DataFrame | pd.Series, name: str) -> None:
    df = df.to_frame() if isinstance(df, pd.Series) else df
    df.to_parquet(PROCESSED_DIR / f"{name}.parquet")


# --------------------------------------------------------------------------- #
# 1. Data layer
# --------------------------------------------------------------------------- #
def build_data_layer(data: dict) -> dict[str, pd.DataFrame]:
    """Save prices / daily returns / monthly returns / volatility per asset class
    (from DATA_START). Returns the daily returns, keyed by asset class."""
    prices = {EQUITY_ASSET_CLASS[z]: px for z, px in data["equities"].items()}
    prices.update({"bonds": data["bonds"], "commodities": data["commodities"], "benchmarks": data["benchmarks"]})
    returns = {}
    for ac, px in prices.items():
        r = simple_returns(px)
        outputs = {
            "prices": px,
            "returns_daily": r,
            "returns_monthly": simple_returns(px, freq="M"),
            "volatility": rolling_volatility(r),
        }
        for kind, df in outputs.items():
            save(df.loc[DATA_START:], PROCESSED_FILES[kind].format(ac=ac))
        returns[ac] = r.loc[DATA_START:]
    save(data["rf"].loc[DATA_START:], "rf")
    data["quality"].to_csv(PROCESSED_DIR / "data_quality_report.csv", index=False)
    return returns


# --------------------------------------------------------------------------- #
# 2. Portfolios
# --------------------------------------------------------------------------- #
def asset_returns(returns: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """All assets in one frame (columns ``"<sleeve>|<asset>"``) and the sleeves."""
    frames = {zone: returns[EQUITY_ASSET_CLASS[zone]] for zone in ZONES}
    frames[BOND_SLEEVE] = returns["bonds"]
    frames[COMMODITY_SLEEVE] = returns["commodities"]
    frames = {s: df.add_prefix(s + ASSET_ID_SEP) for s, df in frames.items()}
    return pd.concat(frames.values(), axis=1).sort_index(), {s: list(df.columns) for s, df in frames.items()}


def esg_budgets(esg: pd.DataFrame) -> dict[str, pd.Series]:
    """ESG risk budgets of each equity sleeve, indexed like the return columns."""
    return {zone: esg_risk_budgets(esg.loc[esg["zone"] == zone, "esg_score"]) for zone in ZONES}


def benchmark_returns(returns: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """60/40, 1/N and 1/N without commodities, rebalanced monthly like the portfolios."""
    bench = returns["benchmarks"]
    indices = pd.concat([bench[["US", "Eurozone", "Pacific", "EM EMEA"]], returns["bonds"],
                         bench[["Commodities"]]], axis=1)
    w_6040 = pd.Series(BENCHMARK_6040)
    w_1n = pd.Series(1 / indices.shape[1], index=indices.columns)
    no_comm = indices.drop(columns="Commodities")
    w_1n_ex = pd.Series(1 / no_comm.shape[1], index=no_comm.columns)
    return pd.DataFrame({
        "60/40": backtest(indices[w_6040.index], lambda W: w_6040, PORTFOLIO_START)["returns"],
        "1/N": backtest(indices, lambda W: w_1n, PORTFOLIO_START)["returns"],
        f"1/N{EX_COMMODITIES_SUFFIX}": backtest(no_comm, lambda W: w_1n_ex, PORTFOLIO_START)["returns"],
    })


def run_portfolios(data: dict, returns: dict[str, pd.DataFrame]) -> None:
    R, sleeves = asset_returns(returns)
    rf = data["rf"]["rf_daily"]

    # ESG universe table with eligibility at the portfolio start
    esg = data["esg"].copy()
    first_day = R.index[R.index < pd.Timestamp(PORTFOLIO_START)][-1]
    esg["eligible_at_start"] = eligible_assets(R, first_day).reindex(esg.index).fillna(False)
    save(esg, "esg_universe")

    logger.info("Backtest: two-level ERC")
    erc = backtest(R, lambda W: two_level_weights(W, sleeves), PORTFOLIO_START)
    logger.info("Backtest: two-level ERC with ESG risk budgets")
    budgets = esg_budgets(esg)
    esg_bt = backtest(R, lambda W: two_level_weights(W, sleeves, budgets), ESG_PORTFOLIO_START)

    # Same portfolios without the commodity sleeve (investor option): ERC across 5 sleeves.
    ex = {s: c for s, c in sleeves.items() if s != COMMODITY_SLEEVE}
    R_ex = R[[c for cols in ex.values() for c in cols]]
    logger.info("Backtest: two-level ERC without commodities")
    erc_ex = backtest(R_ex, lambda W: two_level_weights(W, ex), PORTFOLIO_START)
    logger.info("Backtest: two-level ERC with ESG risk budgets, without commodities")
    esg_ex = backtest(R_ex, lambda W: two_level_weights(W, ex, budgets), ESG_PORTFOLIO_START)

    port = pd.DataFrame({
        "ERC": erc["returns"],
        "ESG": esg_bt["returns"],
        f"ERC{EX_COMMODITIES_SUFFIX}": erc_ex["returns"],
        f"ESG{EX_COMMODITIES_SUFFIX}": esg_ex["returns"],
    })
    for sleeve, cols in sleeves.items():
        logger.info("Backtest: ERC within %s", sleeve)
        port[f"ERC {sleeve}"] = backtest(R[cols], lambda W: erc_weights(covariance_matrix(W)),
                                         PORTFOLIO_START)["returns"]
    port = port.join(benchmark_returns(returns))
    index_names = {"US": "S&P 500", "Eurozone": "MSCI EMU", "Pacific": "MSCI Pacific",
                   "EM EMEA": "MSCI EM EMEA", "Commodities": "S&P GSCI"}
    port = port.join(returns["benchmarks"].rename(columns=index_names).loc[port.index])
    port = port.join(returns["bonds"].rename(columns={"US Aggregate": "AGG"}).loc[port.index])

    save(port, "portfolio_returns")
    for name, bt in (("erc", erc), ("esg", esg_bt), ("erc_ex_commodities", erc_ex), ("esg_ex_commodities", esg_ex)):
        save(bt["weights"], f"weights_{name}")
        save(bt["sleeve_weights"], f"sleeve_weights_{name}")
        save(bt["turnover"], f"turnover_{name}")

    metrics = pd.DataFrame({c: performance_metrics(port[c], rf) for c in port.columns}).T
    metrics.to_csv(PROCESSED_DIR / "performance_metrics.csv")
    period_performance(port).to_csv(PROCESSED_DIR / "crisis_performance.csv")

    print("\nPerformance 2005-2026")
    print(metrics[["ann_return", "ann_volatility", "sharpe", "max_drawdown", "ES_95"]].round(3).to_string())
    print("\nSleeve weights (ERC), average over the backtest")
    print(erc["sleeve_weights"].mean().round(3).to_string())
    print("\nSleeve weights (ERC ex Commodities), average over the backtest")
    print(erc_ex["sleeve_weights"].mean().round(3).to_string())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    t0 = time.time()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for f in PROCESSED_DIR.glob("*"):  # start from a clean folder (no old outputs)
        f.unlink()
    data = load_all()
    returns = build_data_layer(data)
    run_portfolios(data, returns)
    print(f"\nDone in {time.time() - t0:.0f}s, files in {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
