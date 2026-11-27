"""Pipeline: data/raw/ -> data/processed/  (run from the repo root: python compute_erc.py)

1. Load and clean the Datastream files; save the daily returns and the risk-free rate.
2. Backtest the portfolios (monthly rebalancing, 1-year estimation window):
   - ERC: two-level ERC (within each sleeve, then across the 6 sleeves)
   - ERC on the commodity sleeve alone (shown next to the official indices in the app)
   - ERC indices: the same two-level ERC on the official equity indices (survivorship check)
   - benchmarks: 60/40 (S&P 500 / AGG) and 1/N (equal weight on the 6 sleeve indices)
3. Save the daily returns of these portfolios and the ERC sleeve weights.
The web app only reads the files written here.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from core.config import (
    ASSET_ID_SEP,
    BENCHMARK_6040,
    DATA_START,
    EQUITY_ASSET_CLASS,
    PORTFOLIO_START,
    PROCESSED_DIR,
    PROCESSED_FILES,
    ZONES,
)
from core.importation_data import load_all
from core.utilities import (
    backtest,
    covariance_matrix,
    eligible_assets,
    erc_weights,
    performance_metrics,
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
    """Save the daily returns of every asset class (from DATA_START) and the risk-free rate.
    Returns the daily returns, keyed by asset class."""
    prices = {EQUITY_ASSET_CLASS[z]: px for z, px in data["equities"].items()}
    prices.update({"bonds": data["bonds"], "commodities": data["commodities"], "benchmarks": data["benchmarks"]})
    returns = {}
    for ac, px in prices.items():
        returns[ac] = simple_returns(px).loc[DATA_START:]
        save(returns[ac], PROCESSED_FILES["returns_daily"].format(ac=ac))
    save(data["rf"].loc[DATA_START:], "rf")
    data["quality"].to_csv(PROCESSED_DIR / "data_quality_report.csv", index=False)
    return returns


# --------------------------------------------------------------------------- #
# 2. Portfolios
# --------------------------------------------------------------------------- #
def asset_returns(returns: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """All assets in one frame (columns ``"<sleeve>|<asset>"``) and the sleeves."""
    frames = {zone: returns[EQUITY_ASSET_CLASS[zone]] for zone in ZONES}
    frames["Bonds"] = returns["bonds"]
    frames["Commodities"] = returns["commodities"]
    frames = {s: df.add_prefix(s + ASSET_ID_SEP) for s, df in frames.items()}
    return pd.concat(frames.values(), axis=1).sort_index(), {s: list(df.columns) for s, df in frames.items()}


def benchmark_returns(returns: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """60/40 and 1/N, rebalanced monthly like the portfolios."""
    bench = returns["benchmarks"]
    indices = pd.concat([bench[["US", "Eurozone", "Pacific", "EM EMEA"]], returns["bonds"],
                         bench[["Commodities"]]], axis=1)
    w_6040 = pd.Series(BENCHMARK_6040)
    w_1n = pd.Series(1 / indices.shape[1], index=indices.columns)
    return pd.DataFrame({
        "60/40": backtest(indices[w_6040.index], lambda W: w_6040, PORTFOLIO_START)["returns"],
        "1/N": backtest(indices, lambda W: w_1n, PORTFOLIO_START)["returns"],
    })


def erc_on_indices(returns: dict[str, pd.DataFrame]) -> pd.Series:
    """Robustness check for survivorship bias: the same two-level ERC, but each equity sleeve is its official
    index (S&P 500, MSCI EMU, MSCI Pacific, MSCI EM EMEA) instead of today's index members."""
    bench = returns["benchmarks"]
    frames = {zone: bench[[zone]] for zone in ZONES}
    frames["Bonds"], frames["Commodities"] = returns["bonds"], returns["commodities"]
    frames = {s: df.add_prefix(s + ASSET_ID_SEP) for s, df in frames.items()}
    R = pd.concat(frames.values(), axis=1).sort_index()
    sleeves = {s: list(df.columns) for s, df in frames.items()}
    return backtest(R, lambda W: two_level_weights(W, sleeves), PORTFOLIO_START)["returns"]


def run_portfolios(data: dict, returns: dict[str, pd.DataFrame]) -> None:
    R, sleeves = asset_returns(returns)
    rf = data["rf"]["rf_daily"]

    # Stock table (sector, ESG score) with eligibility at the portfolio start
    esg = data["esg"].copy()
    first_day = R.index[R.index < pd.Timestamp(PORTFOLIO_START)][-1]
    esg["eligible_at_start"] = eligible_assets(R, first_day).reindex(esg.index).fillna(False)
    save(esg, "esg_universe")

    logger.info("Backtest: two-level ERC")
    erc = backtest(R, lambda W: two_level_weights(W, sleeves), PORTFOLIO_START)
    port = pd.DataFrame({"ERC": erc["returns"]})
    logger.info("Backtest: ERC within Commodities")
    port["ERC Commodities"] = backtest(R[sleeves["Commodities"]], lambda W: erc_weights(covariance_matrix(W)),
                                       PORTFOLIO_START)["returns"]
    logger.info("Backtest: ERC on the official indices (survivorship robustness check)")
    port["ERC indices"] = erc_on_indices(returns)
    port = port.join(benchmark_returns(returns))

    save(port, "portfolio_returns")
    save(erc["sleeve_weights"], "sleeve_weights_erc")

    metrics = pd.DataFrame({c: performance_metrics(port[c], rf) for c in port.columns}).T

    print("\nPerformance 2005-2026")
    print(metrics[["ann_return", "ann_volatility", "sharpe", "max_drawdown", "ES_95"]].round(3).to_string())
    print("\nSleeve weights (ERC), average over the backtest")
    print(erc["sleeve_weights"].mean().round(3).to_string())


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
