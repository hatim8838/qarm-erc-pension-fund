# Project structure

Multi-asset portfolio for a pension fund, built with Equal Risk Contributions (ERC) and extended with ESG-based risk budgeting.

> **Web app:** ESG is not used by the Streamlit app. The ESG parts described below belong to the
> computation pipeline only.

## Folder tree

```
Qarm-ERC-22/
├── .streamlit/
│   └── config.toml             # Streamlit theme (light base, amber accent)
├── data/
│   ├── raw/                    # Datastream files (input, never modified)
│   └── processed/              # results written by compute_erc.py (read by the app)
├── core/                       # computation code (no Streamlit)
│   ├── config.py               # paths, asset universe, backtest and ESG parameters
│   ├── importation_data.py     # loading and cleaning of the Datastream files
│   ├── utilities.py            # returns, risk budgeting (ERC), backtest, performance metrics
│   ├── erc_portfolio.py        # two-level ERC portfolio built from the investor's universe
│   └── esg.py                  # ESG risk budgets and investor screening
├── compute_erc.py              # runs the full pipeline: data/raw/ -> data/processed/
├── streamlit/                  # web app (only reads data/processed/)
│   ├── streamlit_app.py        # entry point: page config, navbar, light/dark mode, footer
│   ├── web_util.py             # design system: palette, CSS, navbar, cards, chart styling
│   ├── services.py             # cached data access and screening logic for the pages
│   ├── home_page.py            # Home
│   ├── investor_preferences.py # Investors > Investor Preferences
│   ├── universe_explorer.py    # Investors > Universe Explorer
│   ├── portfolio.py            # Portfolio (ERC Portfolio)
│   ├── methodology.py          # Methodology
│   ├── team.py                 # About Us
│   └── assets/                 # logo, mountain icon, banner (team photos go in assets/team/)
├── tests/                      # pytest tests (web app services, ERC portfolio)
├── requirements.txt
├── README.md
└── STRUCTURE.md
```

## Data

Daily Datastream series from 31/12/1999 to 16/11/2026, in USD, as total return indices. The processed outputs start on 01/01/2004 (one estimation window before the first rebalancing on 01/01/2005; AGG only starts on 26/09/2003).

| Asset class | Files |
|---|---|
| US equities | `LS&PCOMP.xlsx` (S&P 500 constituents) |
| Eurozone equities | `LMSEMUID.xlsx` (MSCI EMU constituents) |
| Pacific equities | `LMSPACFD.xlsx` (MSCI Pacific constituents) |
| EM EMEA equities | `LMSEMAFD.xlsx` (MSCI EM EMEA constituents) |
| Bonds | `UAGG.xlsx` (US Aggregate: sovereign, corporate, MBS) |
| Commodities | `GSENTOT.xlsx`, `GSPMTOT.xlsx`, `GSAGTOT.xlsx` (S&P GSCI Energy, Precious Metals, Agriculture) |
| Risk-free rate | `TRUS1MT.xlsx` (US 1-month T-bill yield, % p.a.) |
| Benchmarks | `S&PCOMP.xlsx`, `MSEMUI$.xlsx`, `MSPACF$.xlsx`, `MSEMAF$.xlsx`, `GSCITOT.xlsx` |
| Sectors and ESG | `*-ICB-ESG.xlsx` (ICB sector and ESG score per stock) |

`AUSGVAL.xlsx` (US Treasuries) is downloaded but not used: Treasuries are already about 40% of AGG.

### Cleaning rules (`clean_prices`)
1. Prices below 1.0 are removed (Datastream gives 2 decimals, so very low index levels create fake returns).
2. Weekends and dates without any data are dropped.
3. Stale prices at the start or end of a series (10+ identical values) are removed.
4. Temporary spikes (+50% or -33% reversed within 5 days) are removed as data errors.
5. Holes of at most 5 days are filled with the last price.

## Portfolio construction

- Six sleeves: four equity sleeves (US, Eurozone, Pacific, EM EMEA), bonds (AGG) and commodities (three GSCI sectors).
- Two-level ERC: ERC within each sleeve, then ERC across the six sleeves.
- Monthly rebalancing; covariance estimated on the past 252 business days only (Ledoit-Wolf shrinkage for sleeves with 30+ stocks); weights held from the next day and drifting with returns.
- A stock is eligible only if it has a complete 1-year return history.
- ESG portfolio: within the equity sleeves, risk budgets proportional to the ESG score; stocks without a score are excluded.
- Benchmarks: sleeve indices, 60/40 (S&P 500 / AGG) and 1/N (equal weight on the six sleeve indices), rebalanced monthly.

## Outputs (`data/processed/`)

| File | Content |
|---|---|
| `prices_*`, `simple_returns_daily_*`, `simple_returns_monthly_*`, `volatility_*` | data per asset class |
| `rf.parquet` | daily risk-free rate |
| `esg_universe.parquet` | stock table: sector, ESG score, eligibility at the start |
| `portfolio_returns.parquet` | daily returns of ERC, ESG, ERC per sleeve, 60/40, 1/N and the indices |
| `weights_erc/esg.parquet`, `sleeve_weights_erc/esg.parquet` | weights at each rebalancing |
| `turnover_erc/esg.parquet` | turnover at each rebalancing |
| `performance_metrics.csv` | return, volatility, Sharpe, max drawdown, VaR, ES |
| `crisis_performance.csv` | returns during 2008, 2020 and 2022 |
| `data_quality_report.csv` | cleaning report |

## Workflow

```bash
pip install -r requirements.txt
python compute_erc.py              # about 2 minutes
python -m streamlit run streamlit/streamlit_app.py
```

Run the commands from the project root (`Qarm-ERC-22/`), so that `.streamlit/config.toml` is picked up.

## Known limitations

- Survivorship bias: the stock lists are today's index members, which flatters the equity sleeves against their indices.
- A single (latest) ESG score is applied over the whole period (look-ahead bias).
- ICB sectors are static.
