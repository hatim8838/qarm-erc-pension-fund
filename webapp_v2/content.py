"""All page text in one place (no numbers: every figure is computed from the data)."""

APP_NAME = "Léman Wealth Management"  # same brand as streamlit/web_util.APP_NAME
DISCLAIMER = "Academic project, not investment advice. Past performance does not predict future results."
PHOTO_CREDIT = "Photo: Lavaux and Lake Geneva by Rundvald, Wikimedia Commons, CC BY-SA 4.0."
NOT_A_GUARANTEE = "Projection, not a guarantee."

NAV = {
    "who": ("Who we are", ":material/groups:"),
    "strategy": ("Our strategy", ":material/insights:"),
    "universe": ("Universe explorer", ":material/public:"),
    "journey": ("Client journey", ":material/route:"),
    "goals": ("Our goals", ":material/flag:"),
}
THEME_BUTTON = {"dark": ":material/light_mode:", "light": ":material/dark_mode:"}

HERO = {
    "who": ("Balance every risk.", "A multi-asset pension fund mandate built on risk budgeting.", "Build my portfolio"),
    "strategy": ("Risk, shared fairly.", "Why we budget risk instead of forecasting returns.", "Find my portfolio"),
    "universe": ("Know what you own.", "Every stock we can invest in, by region, industry and ESG score.", None),
    "journey": ("Build it together.", "A few short steps from your preferences to your portfolio.", None),
    "goals": ("Built for decades.", "What we aim for, what we commit to, and what comes next.", "Start the journey"),
}

TEAM = [
    {"name": "Sami", "role": "Founder & CEO", "tags": ["Strategy", "Governance"],
     "bio": "Defines the firm's vision and investment philosophy, and leads the relationship with our investors."},
    {"name": "Hatim", "role": "CIO · Quantitative Research", "tags": ["Portfolio construction", "Risk budgeting"],
     "bio": "Leads portfolio construction and the quantitative research behind our risk-based allocation."},
    {"name": "Yazid", "role": "Head of Data", "tags": ["Market data", "Data quality"],
     "bio": "Oversees our data infrastructure, ensuring reliable and consistent market data across all strategies."},
    {"name": "Elvedin", "role": "Head of Risk & ESG", "tags": ["Risk management", "ESG"],
     "bio": "Monitors portfolio risk and integrates ESG criteria into our investment process."},
    {"name": "Ishaq", "role": "Head of Platform", "tags": ["Digital platform", "Analytics"],
     "bio": "Builds and maintains the digital platform through which investors access our analytics."},
    {"name": "Mathieu", "role": "COO · Investor Relations", "tags": ["Operations", "Client relations"],
     "bio": "Manages operations and client communication, ensuring a transparent and responsive service."},
]

APPROACH = [
    ("Risk, not capital", "Every building block contributes the same share of risk (Equal Risk "
     "Contribution), so no single market dominates the pension."),
    ("Robust estimates", "Covariances are shrunk towards a constant-correlation target (Ledoit-Wolf), "
     "and no expected return is needed to build the weights."),
    ("Your risk level", "You choose α, the share invested in the ERC portfolio; the rest earns the "
     "risk-free rate. Same Sharpe ratio, your level of risk."),
]
MANDATE = ("Our mandate", "A multi-asset pension fund: global equities in regional sleeves, US bonds and "
           "commodities, allocated by equal risk contribution, with an optional ESG screen, rebalanced every month.")

WHY_RB = [
    ("No return forecast", "ERC only needs the covariance matrix Σ: the weights do not depend on "
     "expected returns, the most error-prone input."),
    ("Stable weights", "Mean-variance weights jump with small changes in μ (estimation error). "
     "Risk-budgeting weights move slowly and keep turnover low."),
    ("A simple ESG screen", "At each rebalancing, the worst-rated stocks of each region are excluded "
     "(10, 30 or 50%); ERC then runs on the stocks that remain."),
    ("Your risk level", "A share α goes to the ERC portfolio and 1 − α to the risk-free asset: "
     "σ(y) = α·σ(x) and the Sharpe ratio stays the same."),
]

FAQ = [
    ("What is Equal Risk Contribution?", "A portfolio where each component adds the same amount to total "
     "volatility: volatile assets get less capital, calm ones more."),
    ("Why add a risk-free asset?", "It scales risk without changing the mix: σ(y) = α·σ(x) and the Sharpe "
     "ratio stays the same."),
    ("Is the backtest realistic?", "Weights only use past data and are held from the next day; costs are "
     "deducted, but the stock lists are today's index members (survivorship bias)."),
    ("Can I lose money?", "Yes. The Performance tab shows the largest past drawdown of your portfolio, and the "
     "Projection tab the range of outcomes over your horizon."),
]

CLASS_ROLES = {
    "Equities": "Growth engine: the stocks of the regions you picked, ERC inside each region.",
    "Bonds": "Stabiliser: US investment-grade bonds (iShares AGG ETF, tracking the Bloomberg US Aggregate).",
    "Commodities": "Inflation hedge: energy, precious metals and agriculture (S&P GSCI sectors).",
}
METRIC_LABELS = {
    "ann_return": "Annual return", "ann_volatility": "Volatility", "sharpe": "Sharpe ratio",
    "max_drawdown": "Max drawdown", "tracking_error": "Tracking error vs benchmark",
    "information_ratio": "Information ratio",
}
LEVEL_NAMES = {1: "Cautious", 2: "Moderate", 3: "Balanced", 4: "Dynamic", 5: "Aggressive"}
ESG_HELP = "Share of the worst-ESG stocks excluded from each region, at every monthly rebalancing."

JOURNEY = {
    "regions": ("3a · Where do you want to invest?", "Pick one or more regional equity sleeves."),
    "classes": ("3b · Which asset classes?", "Each class is a sleeve of its own. Hold at least two sleeves."),
    "sectors": ("3c · Which sectors?", "Applied to the stocks of every region you picked."),
    "esg": ("3d · ESG preference", "Exclude the worst ESG-rated stocks of each region before ERC runs: the ESG "
                                    "screen decides what you own, ERC how the risk is spread."),
    "profile": ("3e · Your risk level", "Choose α, the share invested in the ERC portfolio; the rest earns the "
                                        "risk-free rate. This scales risk (σ = α·σ_ERC) without changing the "
                                        "mix, so the Sharpe ratio stays the same."),
    "portfolio": ("3f · Your portfolio", "{level} · α = {alpha} in ERC · ESG screen {esg} · {n} sleeves"),
}
STEP_NAMES = {"regions": "Regions", "classes": "Asset classes", "sectors": "Sectors", "esg": "ESG",
              "profile": "Risk level", "portfolio": "Your portfolio"}
PROBLEMS = {
    "no_region": "Pick at least one region.",
    "two_sleeves": "Hold at least two sleeves (for example equities and bonds).",
    "no_sector": "Pick at least one sector.",
    "thin_sleeve": "Too few stocks left in {regions} (minimum {n}): add sectors or lower the ESG screen.",
}
NAV_BUTTONS = {"back": "Back", "next": "Next", "select": "Select", "selected": "Selected ✓"}

TEXT = {
    "region_facts": "{n} stocks · {c} {countries}",
    "index_note": "Annual return and volatility of the official indices since {start}.",
    "class_note": "Annual return and volatility since {start}: official indices for equities and bonds, our sleeve of "
                  "three S&P GSCI sector indices for commodities.",
    "stocks_left": "stocks left in {region}",
    "team": "The team", "approach": "Our approach", "steps": "Three steps to your portfolio", "faq": "Questions",
    "who_figures": ["assets across {n} sleeves", "years of monthly rebalancing since {year}",
                    "Sharpe ratio of our ERC portfolio"],
    "closing_cta": "Ready to see your portfolio?",
    "three_steps": [("Tell us about you", "Regions, classes, sectors, an ESG screen and your risk level."),
                    ("We budget the risk", "Two-level ERC on shrunk covariances, mixed with the risk-free asset."),
                    ("See your portfolio", "Allocation, performance and projection, updated as you adjust.")],
    "why_rb": "Why risk budgeting", "lab": "EW vs ERC on our sleeves today",
    "lab_sub": "Risk contributions RC*_i of equal weights and of ERC on the same Ledoit-Wolf Σ̂ ({date}).",
    "theorem": "σ(x_mv) ≤ σ(x_erc) ≤ σ(x_ew) held at {share} of our {n} monthly rebalancings.",
    "excluded": "stocks excluded at the latest rebalancing", "kept": "stocks kept", "esg_now": "Portfolio ESG score",
    "esg_delta": "{delta:+.1f} vs Off", "esg_level": "ESG screen",
    "level_slider": "Risk level", "level_format": "{level} · {name} · α {alpha}",
    "level_line": "Level {level} · {alpha} in the ERC portfolio · {rf} risk-free",
    "adjust": "Adjust my choices",
    "cost_note": "Trading costs are set at {bps} bps of the amount traded at each rebalancing, a typical level for "
                 "an institutional investor in liquid markets. They reduce the annual return by {drag}.",
    "computed": "Recomputed in {s:.1f} s.", "cached": "Loaded from cache (first computed in {s:.1f} s).",
    "loading": "Budgeting the risk of your portfolio…",
    "tabs": ["Allocation", "Risk contribution", "Performance", "Projection"],
    "alpha": "ERC share α", "rf_share": "Risk-free 1 − α", "holdings": "Holdings", "esg_vs": "ESG score vs Off",
    "by_class": "By asset class", "by_sector": "Equities by sector",
    "benchmark": "Benchmark b", "gross_net": "Gross vs net of costs", "turnover": "Turnover at each rebalancing",
    "turnover_note": "Each bar is the share of the portfolio traded at a monthly rebalancing. It usually stays at a "
                     "few percent and spikes only when volatility changes sharply: in the 2008 crisis, in March "
                     "2020, and in 2021 when the Covid crash left the one-year estimation window.",
    "weights_time": "Weights at each monthly rebalancing", "expected": "Expected annual return",
    "expected_vol": "Expected volatility",
    "bench_title": "{b} with your α = {alpha}",
    "bench_note": "Fair comparison: the benchmark gets the same choice as you, α = {alpha} in the benchmark and "
                  "{rf} in the risk-free asset. 60/40 = 60% S&P 500 + 40% US bonds (AGG); 1/N = equal weights on "
                  "the six sleeve indices; both rebalanced monthly. Judge on the Sharpe ratio and the max drawdown: "
                  "a riskier benchmark can end higher in a strong equity market.",
    "ci_note": "± {margin} is the 95% interval of the estimated mean, μ ± 1.96·σ/√T, over T = {years:.0f} years "
               "of backtest: "
               "the estimation error of the mean, not the range of future returns.",
    "horizon": "Horizon (years)", "fan": "Value of {start} invested (median, 25–75% and 5–95% bands)",
    "mission": "Mission", "commitments": "Our commitments", "next": "Next steps",
}

UNIVERSE = {
    "breakdown": "Investment universe breakdown", "geo": "Geographical breakdown", "industry": "Industry breakdown",
    "stocks": "Number of stocks", "counts_caption": "Breakdowns are based on stock counts, not portfolio weights.",
    "held_note": "The portfolio can hold {pairs} today: a stock enters only with a complete {n}-day return history "
                 "and a moving price.",
    "held_pair": "{held} of the {listed} {region} stocks",
    "esg": "ESG analysis", "esg_mean": "Average ESG score", "esg_median": "Median ESG score",
    "esg_coverage": "ESG score coverage", "esg_hist": "ESG score distribution", "esg_axis": "ESG score",
    "companies": "Selected companies", "search": "Search for a company", "region_filter": "Filter by region",
    "displayed": "{n} companies displayed.", "empty": "No company matches these filters.",
}
UNIVERSE_COLUMNS = {"name": "Company", "zone": "Region", "country": "Country", "industry": "Industry",
                    "sector": "Sector", "esg_score": "ESG Score", "isin": "ISIN"}

COMPOSITION = {
    "inside": "Inside your ERC portfolio (α = {alpha} of your money)", "total": "Show as % of my total money",
    "donut": "Capital allocation by sleeve", "n_sleeves": "{n} sleeves", "table": "Sleeves",
    "insight": "The portfolio holds <b>{top_w}</b> of its capital in <b>{top}</b> and only <b>{low_w}</b> in "
               "<b>{low}</b>, yet each sleeve contributes <b>{rc}</b> of the total risk. Low-volatility sleeves "
               "receive more capital, high-volatility sleeves less.",
    "positions": "Largest positions", "position": "{name} · {sleeve}", "weight_axis": "Capital weight (%)",
    "across": "Capital weights vs risk contributions, across sleeves", "portfolio_axis": "% of portfolio",
    "target_n": "Target: 1/{n} = {pct}", "across_caption": "Equal risk contribution does not mean equal capital: "
    "the dark bars are all equal to the target, the light bars are not.",
    "inside_sleeve": "Inside a sleeve", "sleeve": "Sleeve", "top_of": "Top {k} of {n} assets", "all": "All {n} assets",
    "target_inner": "Target 1/N", "sleeve_axis": "% of the sleeve", "single": "{sleeve} holds a single asset: it "
    "carries 100% of the sleeve's capital and risk.",
}
SLEEVE_COLUMNS = {"assets": "Assets", "weight": "Capital weight", "rc": "Risk contribution",
                  "vol": "Stand-alone volatility"}
BAR_NAMES = {"weight": "Capital weight", "rc": "Risk contribution", "inner_weight": "Weight inside the sleeve"}
METHOD = ("Method and limitations", [
    "**Method**: two-level Equal Risk Contribution: inside each region first, then across the regions, bonds and "
    "commodities, so that every component contributes the same share of risk. Risk is estimated on the last {n} "
    "business days with Ledoit-Wolf shrinkage. Long-only. A share α of your money ({low} to {high}, set by your "
    "risk level) is invested in the ERC portfolio and 1 − α in the risk-free asset.",
    "**ESG option**: exclusion of the worst {levels} ESG-scored equities in each region, at every rebalancing.",
    "**Limits**: estimates are historical and do not guarantee future risk. Stock lists are today's index "
    "constituents and ESG scores are a recent snapshot. Educational project, not investment advice.",
])

GOALS = {
    "mission": "Give every pension client a portfolio whose risk is spread evenly across markets and whose "
               "overall risk matches who they are.",
    "commitments": ["No look-ahead: decisions use past data only", "The same rules for every client",
                    "Transparent methods, explained on our strategy page", "Costs and limits shown openly"],
    "next": ["Quarterly rebalancing as a robustness check", "Turnover limits between rebalancings",
             "Dynamic ESG scores instead of today's snapshot", "Downloadable client reports"],
}
