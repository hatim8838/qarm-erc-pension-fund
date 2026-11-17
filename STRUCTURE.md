# Project structure

Multi-asset portfolio for a pension fund, built with Equal Risk Contributions (ERC) and extended with ESG-based risk budgeting.

## Folder tree

```
qarm-erc-pension-fund/
├── data/
│   ├── raw/                    # Datastream files
│   └── processed/              # computed results
├── core/                       # computation code
│   ├── importation_data.py     # loading and cleaning of Datastream files
│   ├── utilities.py            # returns, risk budgeting, backtest, performance and risk metrics
│   └── esg.py                  # ESG scores and risk budgets
├── compute_erc.py              # runs the full pipeline and writes results to data/processed/
├── streamlit/                  # web app
│   ├── streamlit_app.py        # app entry point and page navigation
│   ├── home_page.py            # global multi-asset portfolio
│   ├── risk_preference.py      # risk-profile questionnaire
│   ├── ERC_portfolio.py        # results by asset class
│   ├── ESG_portfolio.py        # ERC vs ESG risk budgeting
│   ├── methodology.py          # data and methodology
│   ├── team.py
│   ├── web_util.py             # layout helpers
│   └── pictures/
├── requirements.txt
└── README.md
```

## Data

Daily Datastream series from 31/12/1999 to 16/11/2026, in USD, as total return indices.

| Asset class | Files |
|---|---|
| US equities | `LS&PCOMP.xlsx` (S&P 500 constituents) |
| Eurozone equities | `LMSEMUID.xlsx` (MSCI EMU constituents) |
| EM EMEA equities | `LMSEMAFD.xlsx` (MSCI EM EMEA constituents) |
| Pacific equities | `LMSPACFD.xlsx` (MSCI Pacific constituents) |
| Bonds | `UAGG.xlsx` (US Aggregate), `AUSGVAL.xlsx` (US Government) |
| Commodities | `GSENTOT.xlsx`, `GSPMTOT.xlsx`, `GSAGTOT.xlsx` (S&P GSCI Energy, Precious Metals, Agriculture) |
| Risk-free rate | `TRUS1MT.xlsx` (US 1-month T-bill yield) |
| Benchmarks | `S&PCOMP.xlsx`, `MSEMUI$.xlsx`, `MSEMAF$.xlsx`, `GSCITOT.xlsx` |
| Sectors and ESG | `*-ICB-ESG.xlsx` (ICB sector and ESG score per stock) |

## Workflow

1. `core/importation_data.py` loads and cleans the raw files.
2. `compute_erc.py` computes daily returns, ERC weights within each asset class and across asset classes, ESG risk budgets, the backtest (monthly rebalancing, 1-year rolling estimation window) and performance and risk metrics against the benchmarks.
3. The Streamlit pages only read the results from `data/processed/`.

```bash
pip install -r requirements.txt
python compute_erc.py
streamlit run streamlit/streamlit_app.py
```
