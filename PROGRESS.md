# Progress log

One dated entry per working session. Newest at the bottom.

---

## 2026-11-24

**Covers:** commits on `main` since the last session (2026-11-18, after `9ec8130`), up to `799ec47`, plus the unmerged branch `origin/remove-esg-webapp`. Working tree was clean (no uncommitted changes).

### What changed

**Core / quant (Hatim, `98d6102`, 18 Nov)**
- Back to **4 equity sleeves** (US, Eurozone, Pacific, EM EMEA), dropping the 6-zone country split; bonds = AGG only (AUSGVAL dropped); commodities = 3 GSCI sectors. MSCI Pacific benchmark added.
- New cleaning rules: price < 1.0 removed, spikes (+50% / -33% reversed within 5 days) removed, stale ends, ffill ≤ 5 days.
- Calendar moved: data from 2004-01-01, portfolio from **2005-01-01**, monthly rebalancing, full 252-day window required (`MIN_WINDOW_COVERAGE = 1.0`).
- Implemented in `core/utilities.py`: `covariance_matrix` (Ledoit-Wolf for 30+ assets), `risk_contributions`, `risk_budget_weights`, `erc_weights`, `two_level_weights`, `backtest`, `drawdown`, `performance_metrics` (incl. VaR/ES), `period_performance` (2008, 2020, 2022).
- `core/esg.py`: `esg_risk_budgets` (budgets ∝ ESG score, missing scores excluded).
- `compute_erc.py`: backtests ERC, ESG, ERC per sleeve, 60/40, 1/N → `portfolio_returns.parquet`, `weights_*`, `sleeve_weights_*`, `turnover_*`, `performance_metrics.csv`, `crisis_performance.csv`.
- **`tests/test_core.py` was deleted.**
- Results 2005–2026: ERC 7.5% return / 6.4% vol / Sharpe 0.89 / MDD −27%; ESG 7.3% / 6.4% / 0.86; 60/40 7.5% / 11.2% / 0.55; 1/N 5.7% / 12.6% / 0.36.

**Web app (root `streamlit/`)**
- 19 Nov (Mathieu): Universe Explorer implemented (metrics, region/industry bars, ESG histogram, search + region filter, CSV download); Home banner image; `config.py` debug constant.
- 19–21 Nov (Elvedin, PR #2): new **ERC Portfolio** page (`portfolio.py`, `core/erc_portfolio.py`) with a live two-level ERC on the screened universe: ERC vs ESG-tilted budgets, tabs Allocation / Risk contributions / ERC vs Equal Weight (+ Min-Variance) / Holdings / Historical backtest. New **Methodology** content, **About us** team page, logo, top navigation replacing the sidebar.

**Redesigned copy `Qarm-ERC-22/` (Sami `3c9a86e`, Elvedin `799ec47`, 22 Nov)**
- A full second copy of the project (data, raw files, core, app, tests; 214 MB) with an "Amber" design: custom navbar with an Investors dropdown, light/dark switch, footer, new Home.
- New feature: **commodities optional** (Preferences step "Asset classes"); ERC then runs on 5 sleeves; pipeline adds "ex Commodities" backtests; `tests/test_erc_portfolio.py`.

**Unmerged: `origin/remove-esg-webapp` (Sami, 23 Nov)**: new Home design, reworked Preferences, **ESG removed from the web app**, nicer Universe Explorer table (all in `Qarm-ERC-22/`).

### Checks run today
- `pip install -r requirements.txt`: OK.
- Both apps run with no exceptions on any page: root on http://localhost:8501, `Qarm-ERC-22` on http://localhost:8502. Default flow: 396 stocks selected → ERC with 398 assets, volatility 5.1%, risk-contribution check "Verified".
- `pytest`: root **6 failed / 9 passed**; Qarm-ERC-22 **6 failed / 16 passed**. The failures are all in `test_webapp.py`, which still expects the old 6 zones and "MSCI Pacific = Planned".
- Lint (pyflakes, close to what VS Code/Pylance flags; I couldn't read the Problems panel itself): unused imports `TRADING_DAYS` (core/erc_portfolio.py:23), `Path` (core/importation_data.py:10), `APP_NAME` and `page_header` (streamlit/home_page.py:17), the same two core ones in `Qarm-ERC-22/`.
- Created `app_overview.html` (app map) and `PROGRESS.md`. Recreated `.claude/launch.json` (local preview config, two servers). No app code changed, nothing committed.

### Half-finished / inconsistencies found
- **Two copies of the app on `main`** (`streamlit/` and `Qarm-ERC-22/`), about 420 MB of data in total. Which one does Streamlit Cloud deploy?
- **ESG direction unclear:** `main` keeps ESG screening and ESG budgets; the unmerged branch removes ESG from the app.
- Stale text written before the ERC existed: Home roadmap ("In development · ERC & backtesting", "no portfolio weights shown"), Preferences caption ("Six investor zones… Asia and Oceania"), Explorer ("portfolio weights have not yet been calculated"), eligibility caption, `universe_explorer.py` docstring ("next step").
- `STRUCTURE.md` (root) describes the new pipeline, but `README.md` is one line.
- `portfolio.py` loads `crisis_performance.csv` and `sleeve_weights_erc.parquet` but shows neither; turnover is computed but never shown; an `if True:` block remains; the `erc_portfolio.py` docstring mentions a missing `core.shrinkage` module.
- The backtest tab is the full-universe portfolio only ("Not recomputed for your selection").
- No tests for `core/` in the root copy.

### What's left to do
**Strategy content**
- [ ] Decide on ESG (keep as risk budgeting vs remove) and make the app, Methodology and report consistent.
- [ ] Show crisis performance (2008 / 2020 / 2022), sleeve weights over time and turnover; add VaR/ES to the metrics table.
- [ ] Robustness: quarterly rebalancing, transaction costs, sample vs Ledoit-Wolf covariance.
- [ ] Clearly state limitations (survivorship bias, static ESG snapshot, static ICB) in the app.

**Presentation clarity**
- [ ] Remove the stale "in development" text across pages; align captions with 4 sleeves and 100% eligibility.
- [ ] Write a proper README (what, how to run, deployed URL).

**Web app: design, interactivity, completeness**
- [ ] Choose one app (root vs `Qarm-ERC-22`), merge the wanted features (commodities toggle, navbar, Explorer table), and delete the other copy.
- [ ] Let the user pick the rebalancing date / see weights over time, and recompute or approximate the backtest for the user's selection.

**No technical issues**
- [ ] Update `tests/test_webapp.py` to 4 zones; restore core tests (returns, ERC risk contributions = budgets, backtest).
- [ ] Clean unused imports and dead code.
- [ ] Check the Streamlit Cloud deployment points at the right entry file and that the data size fits.
