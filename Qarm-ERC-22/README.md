# Qarm-ERC-22 — Léman Wealth Management

ERC multi-asset portfolio for a pension fund, with ESG screening and ESG-based risk budgeting.
QARM II project, HEC Lausanne.

This folder is a complete, self-contained project: data, computation code, web app and tests.
It is the redesigned version of the original `qarm-erc-pension-fund` app. Pages, data and
computations are the same; only the design changed.

## What the app does

| Page | Content |
|---|---|
| **Home** | Mandate, how to use the app, data coverage, roadmap |
| **Investors › Investor Preferences** | Choose regions, industries, ESG ambition, commodities; run the screening |
| **Investors › Universe Explorer** | Screened stocks by region, industry and ESG score; downloadable list |
| **Portfolio** | Two-level Equal Risk Contribution portfolio: allocation, risk contributions, ERC vs equal weight, holdings, historical backtest |
| **Methodology** | The method in plain language, data, ESG screen, limitations |
| **About Us** | The team |

## Quick start

```bash
cd Qarm-ERC-22
pip install -r requirements.txt
python -m streamlit run streamlit/streamlit_app.py
```

Run from this folder, so that `.streamlit/config.toml` (the theme) is used. The processed data is
already included in `data/processed/`, so the app works right away.

To rebuild the processed data from the raw Datastream files (about 2 minutes):

```bash
python compute_erc.py
```

To run the tests:

```bash
python -m pytest tests
```

## Design

Inspired by the "Amber Quant" Streamlit app: Inter font, custom top navbar (with an "Investors"
dropdown), peach `#FFCC99` and amber `#CC6600` accents, navy section bars, white cards with soft
shadows, call-to-action boxes and a centred footer. Charts use a blue / gold / amber / navy palette.

A **light / dark mode** button (moon / sun) sits at the right of the navbar. The choice is kept while
the browser tab stays open and resets to light on a full page refresh. Streamlit's theme is a
server-wide setting, so this switch is meant for one user at a time (local use or a demo).

All design code lives in `streamlit/web_util.py` (palette, CSS, navbar, cards, chart styling).

## Project structure

See [STRUCTURE.md](STRUCTURE.md) for the folder tree, the data sources, the cleaning rules, the
portfolio construction and the output files.

## Disclaimer

Educational project. Historical data, not live quotes. Not investment advice.
