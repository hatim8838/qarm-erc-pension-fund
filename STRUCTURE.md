# Project structure

Multi-asset portfolio for a pension fund, built with Equal Risk Contribution (ERC), with an ESG screen by
exclusion, delivered through a web app.

## Folder tree

```
qarm-erc-pension-fund/
├── data/
│   ├── raw/                     # Datastream files (input, never modified)
│   └── processed/               # written by compute_erc.py, read by the app
├── core/                        # data and ERC code shared by the pipeline and the app
│   ├── config.py                # paths, asset universe, backtest parameters
│   ├── importation_data.py      # loading and cleaning of the Datastream files
│   └── utilities.py             # returns, ERC weights, backtest, performance metrics
├── compute_erc.py               # pipeline: data/raw/ -> data/processed/
├── webapp_v2/                   # web app (Streamlit)
│   ├── app.py                   # entry point and navigation
│   ├── config.py, content.py    # app settings, and every text shown in the app
│   ├── pages/                   # Who we are, Our strategy, Universe explorer, Client journey, Our goals
│   ├── logic/                   # computations: universe, covariance, ERC, α mix, performance, projection
│   ├── ui/                      # charts, tables, page blocks, dark / light theme
│   ├── scripts/precompute.py    # writes precomputed/
│   ├── precomputed/             # stored results, used only while they match the code and the data
│   └── tests/                   # course examples, stock counts, pages, precomputed results
├── requirements.txt
└── README.md
```

## Data

Daily Datastream series from 31/12/1999 to 16/11/2026, in USD, as total return indices. The processed outputs
start on 01/01/2004: one estimation window before the first rebalancing on 01/01/2005 (AGG only starts on
26/09/2003).

| Asset class | Files |
|---|---|
| US equities | `LS&PCOMP.xlsx` (S&P 500 constituents) |
| Eurozone equities | `LMSEMUID.xlsx` (MSCI EMU constituents) |
| Pacific equities | `LMSPACFD.xlsx` (MSCI Pacific constituents) |
| EM EMEA equities | `LMSEMAFD.xlsx` (MSCI EM EMEA constituents) |
| Bonds | `UAGG.xlsx` (US Aggregate: sovereign, corporate, MBS) |
| Commodities | `GSENTOT.xlsx`, `GSPMTOT.xlsx`, `GSAGTOT.xlsx` (S&P GSCI Energy, Precious Metals, Agriculture) |
| Risk-free rate | `TRUS1MT.xlsx` (US 1-month T-bill yield, % p.a.) |
| Indices | `S&PCOMP.xlsx`, `MSEMUI$.xlsx`, `MSPACF$.xlsx`, `MSEMAF$.xlsx`, `GSCITOT.xlsx` |
| Sectors and ESG | `*-ICB-ESG.xlsx` (ICB sector and ESG score of each stock) |

### Cleaning rules (`clean_prices`)
1. Prices below 0.20 are removed (Datastream gives 2 decimals: below 0.20 one cent is more than 5% of the price,
   so the returns are rounding noise). Low but real levels above it are kept.
2. Weekends and dates without any data are dropped.
3. Stale prices at the start or end of a series (10+ identical values) are removed.
4. Temporary spikes (+50% or -33% reversed within 5 days) are removed as data errors.
5. Holes of at most 5 days are filled with the last price.

## Portfolio construction

- Six sleeves: four equity sleeves (US, Eurozone, Pacific, EM EMEA), bonds (AGG) and commodities
  (three GSCI sectors).
- Two-level ERC: ERC within each sleeve, then ERC across the sleeves the client holds.
- Monthly rebalancing; covariance estimated on the past 252 business days only, with Ledoit-Wolf shrinkage
  (LN 3); weights held from the next day and drifting with returns.
- A stock is investable at a rebalancing date only if it has a return on every day of the window and at most
  20% zero returns (more means stale prices). Today: 1,108 stocks listed, 1,093 investable.
- ESG screen: the worst-rated 10%, 30% or 50% of the investable stocks of each region are excluded before ERC runs.
- Risk level: the client invests α (20% to 100%) in the ERC portfolio and the rest at the risk-free rate.
- Transaction costs: 10 bps of the traded value at each rebalancing.
- Benchmarks: 60/40 (S&P 500 / AGG) and 1/N (equal weight on the six sleeve indices), rebalanced monthly and
  mixed with the risk-free asset at the client's α.

## Outputs (`data/processed/`)

| File | Content |
|---|---|
| `simple_returns_daily_*.parquet` | daily returns per asset class (stocks, bonds, commodities, indices) |
| `rf.parquet` | daily risk-free rate |
| `esg_universe.parquet` | stock table: zone, country, sector, ESG score |
| `portfolio_returns.parquet` | daily returns of ERC, ERC Commodities, ERC indices, 60/40 and 1/N |
| `sleeve_weights_erc.parquet` | ERC sleeve weights at each rebalancing (the app uses the sleeve order) |
| `data_quality_report.csv` | cleaning report: prices removed per series |

`ERC indices` is a robustness check for survivorship bias: the same two-level ERC with each equity sleeve
replaced by its official index.

## Workflow

```bash
pip install -r requirements.txt
python compute_erc.py                                      # about 2 minutes
OMP_NUM_THREADS=1 python webapp_v2/scripts/precompute.py   # needed after any change to core/, logic/ or the data
cd webapp_v2 && python -m streamlit run app.py
```

Run the first two commands from the repository root.

## Known limitations

- Survivorship bias: the stock lists are today's index members, which flatters the equity sleeves against their
  indices. The ERC on the official indices (Sharpe 0.53) still matches the 60/40 (0.56) with less volatility.
- A single (latest) ESG score is applied over the whole period (look-ahead bias).
- ICB sectors are static.
