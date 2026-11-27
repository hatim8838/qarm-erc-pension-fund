# Léman Wealth: an ERC multi-asset portfolio for a pension fund

QARM project, HEC Lausanne (Prof. Divernois).

We manage the portfolio of a pension fund with **Equal Risk Contribution (ERC)**: each of our six sleeves
(US, Eurozone, Pacific and EM EMEA equities, bonds, commodities) contributes the same share of the total risk.
The client chooses the regions, asset classes, sectors, an ESG screen and a risk level in a web app, and gets the
portfolio, its risk decomposition and its backtest against a 60/40 and a 1/N benchmark.

## How it works

1. `compute_erc.py` reads the Datastream files in `data/raw/`, cleans the prices and writes the daily returns
   and the reference portfolios to `data/processed/`.
2. The web app (`webapp_v2/`) only reads `data/processed/`. It builds the client's portfolio with a two-level
   ERC (within each sleeve, then across sleeves), mixes it with the risk-free asset at the chosen level α and
   backtests it with monthly rebalancing on a one-year estimation window (2005 to 2026).

## Run it

```bash
pip install -r requirements.txt
cd webapp_v2 && python -m streamlit run app.py   # the app
python -m pytest -q                              # the tests (from webapp_v2/)
```

The processed data and the precomputed results are in the repository, so the app runs without
recomputing anything. To rebuild them from the raw files (from the repository root):

```bash
python compute_erc.py                                      # about 2 minutes
OMP_NUM_THREADS=1 python webapp_v2/scripts/precompute.py   # precomputed results of the app
```

See `STRUCTURE.md` for the folders, the data, the cleaning rules and the known limitations.
