"""All page text in one place (no numbers: every figure is computed from the data)."""

APP_NAME = "Léman Wealth Management"  # same brand as streamlit/web_util.APP_NAME
COURSE = "QARM II · HEC Lausanne"
DISCLAIMER = "Academic project, not investment advice. Past performance does not predict future results."
PHOTO_CREDIT = "Photo: Lavaux and Lake Geneva by Rundvald, Wikimedia Commons, CC BY-SA 4.0."
NOT_A_GUARANTEE = "Projection, not a guarantee."

NAV = {
    "who": ("Who we are", ":material/groups:"),
    "strategy": ("Our strategy", ":material/insights:"),
    "journey": ("Client journey", ":material/route:"),
    "implementation": ("How we implement it", ":material/account_tree:"),
    "goals": ("Our goals", ":material/flag:"),
}
THEME_BUTTON = {"dark": ":material/light_mode:", "light": ":material/dark_mode:"}

HERO = {
    "who": ("Balance every risk.", "A multi-asset pension fund mandate built on risk budgeting.", "Build my portfolio"),
    "strategy": ("Risk, shared fairly.", "Why we budget risk instead of forecasting returns.", "Find my portfolio"),
    "journey": ("Build it together.", "A few short steps from your preferences to your portfolio.", None),
    "implementation": ("From data, decisions.", "Every step from raw prices to the monthly rebalancing.", None),
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
    ("LN 5", "Risk, not capital", "Every building block contributes the same share of risk (Equal Risk "
     "Contribution), so no single market dominates the pension."),
    ("LN 3", "Robust estimates", "Covariances are shrunk towards a constant-correlation target (Ledoit-Wolf), "
     "and no expected return is needed to build the weights."),
    ("LN 2", "Your risk level", "We mix the risk-budgeted portfolio with the risk-free asset to reach the "
     "volatility your profile calls for."),
]
MANDATE = ("Our mandate", "A multi-asset pension fund: global equities in regional sleeves, US bonds and "
           "commodities, allocated by equal risk contribution or ESG risk budgets, rebalanced every month.")

WHY_RB = [
    ("LN 5", "No return forecast", "ERC only needs the covariance matrix Σ: the weights do not depend on "
     "expected returns, the most error-prone input."),
    ("LN 3", "Stable weights", "Mean-variance weights jump with small changes in μ (estimation error). "
     "Risk-budgeting weights move slowly and keep turnover low."),
    ("LN 6", "ESG as a risk budget", "With the ESG option, each stock's risk budget b_i grows with its ESG "
     "score: better-rated companies carry more of the risk."),
    ("LN 2", "Volatility targeting", "The share α = σ*/σ̂(x) goes to the risk-budgeted portfolio and 1 − α "
     "to the risk-free asset. Same Sharpe ratio, your volatility."),
]

FAQ = [
    ("What is Equal Risk Contribution?", "A portfolio where each component adds the same amount to total "
     "volatility: volatile assets get less capital, calm ones more."),
    ("Why add a risk-free asset?", "It scales risk without changing the mix: σ(y) = α·σ(x) and the Sharpe "
     "ratio stays the same."),
    ("Is the backtest realistic?", "Weights only use past data and are held from the next day; costs are "
     "deducted, but the stock lists are today's index members (survivorship bias)."),
    ("Can I lose money?", "Yes. Your portfolio page shows drawdowns, crisis losses, VaR and ES."),
]

QUESTIONS = [
    ("horizon", "When will you need this money?",
     ["In less than 3 years", "In 3 to 7 years", "In 7 to 15 years", "In more than 15 years"]),
    ("drop", "Your portfolio falls by 20% in a few weeks. You…",
     ["Sell everything", "Sell part of it", "Do nothing", "Buy more"]),
    ("income", "How stable is your income?", ["Unstable", "Somewhat stable", "Stable", "Very stable, with savings"]),
    ("experience", "Your investment experience?",
     ["None", "Savings accounts and funds", "Stocks and ETFs", "Active investor for years"]),
    ("max_loss", "The largest loss you accept over one year?", ["5%", "10%", "20%", "30% or more"]),
    ("goal", "Your main goal?", ["Preserve capital", "Regular income", "Balanced growth", "Maximum growth"]),
]
CLASS_ROLES = {
    "Equities": "Growth engine: the stocks of the regions you picked, ERC inside each region.",
    "Bonds": "Stabiliser: US investment-grade bonds (Bloomberg US Aggregate).",
    "Commodities": "Inflation hedge: energy, precious metals and agriculture (S&P GSCI sectors).",
}
METRIC_LABELS = {
    "ann_return": "Annual return", "ann_volatility": "Volatility", "sharpe": "Sharpe ratio SR(x | r)",
    "max_drawdown": "Max drawdown", "VaR_95": "Hist. VaR 95%", "ES_95": "Hist. ES 95%", "VaR_99": "Hist. VaR 99%",
    "ES_99": "Hist. ES 99%", "tracking_error": "Tracking error σ(x | b)", "information_ratio": "IR(x | b)",
}
LEVEL_NAMES = {1: "Cautious", 2: "Moderate", 3: "Balanced", 4: "Dynamic", 5: "Aggressive"}
ESG_LABELS = {"off": "Off", "screen": "ESG screen", "screen_rb": "ESG screen + ESG risk budgets"}
ESG_HELP = {"off": "Every stock of your sectors, equal risk contributions.",
            "screen": "The worst-rated stocks of each region and sector are excluded.",
            "screen_rb": "Screen, then risk budgets proportional to the ESG score (LN 6 risk budgeting)."}

JOURNEY = {
    "regions": ("3a · Where do you want to invest?", "Pick one or more regional equity sleeves."),
    "classes": ("3b · Which asset classes?", "Each class is a sleeve of its own. Hold at least two sleeves."),
    "sectors": ("3c · Which sectors?", "Applied to the stocks of every region you picked."),
    "esg": ("3d · ESG preference", "Screen out the worst ESG scores, and optionally budget risk by ESG score."),
    "profile": ("3e · Your risk profile", "{n} questions set your target volatility σ*."),
    "portfolio": ("3f · Your portfolio", "{level} profile · target σ* = {target} · {n} sleeves"),
}
STEP_NAMES = {"regions": "Regions", "classes": "Asset classes", "sectors": "Sectors", "esg": "ESG",
              "profile": "Risk profile", "portfolio": "Your portfolio"}
PROBLEMS = {
    "no_region": "Pick at least one region.",
    "two_sleeves": "Hold at least two sleeves (for example equities and bonds).",
    "no_sector": "Pick at least one sector.",
    "thin_sleeve": "Too few stocks left in {regions} (minimum {n}): add sectors or relax the ESG option.",
    "questionnaire": "Answer every question to continue.",
}
NAV_BUTTONS = {"back": "Back", "next": "Next", "select": "Select", "selected": "Selected ✓"}

TEXT = {
    "region_facts": "{n} stocks · {c} countries · history: {ret} a year, σ = {vol}",
    "class_history": "History of each sleeve since {start} (level-1 ERC portfolio of core).",
    "stocks_left": "stocks left in {region}",
    "team": "The team", "approach": "Our approach", "steps": "Three steps to your portfolio", "faq": "Questions",
    "who_figures": ["assets across {n} sleeves", "years of monthly rebalancing since {year}",
                    "Sharpe ratio of our ERC portfolio"],
    "closing_cta": "Ready to see your portfolio?",
    "three_steps": [("Tell us about you", "Regions, classes, sectors, ESG and a short risk questionnaire."),
                    ("We budget the risk", "Two-level ERC or ESG risk budgets, then volatility targeting."),
                    ("See your portfolio", "Allocation, risk, diversification, performance and projection.")],
    "why_rb": "Why risk budgeting", "lab": "EW vs ERC on our sleeves today",
    "lab_sub": "Risk contributions RC*_i of equal weights and of ERC on the same Ledoit-Wolf Σ̂ ({date}).",
    "theorem": "σ(x_mv) ≤ σ(x_erc) ≤ σ(x_ew) held at {share} of our {n} monthly rebalancings.",
    "backtest": "The real backtest", "backtest_sub": "All sleeves, fully invested, {start}–{end}, net of {bps} bps costs.",
    "esg_score": "ESG score of the stocks you keep: {screened} (without the screen: {all})",
    "level_result": "Risk level {level} · {name} · target volatility σ* = {target}",
    "mapping": "How your answers become σ*",
    "mapping_body": "Each answer scores its position (0 = most cautious). The total over {n} points gives s; "
                    "five equal bands of s give the risk level and its target volatility:",
    "unreachable": "Your target σ* = {target} is above the risk of the portfolio you chose (σ̂ = {sigma}): it stays "
                   "fully invested. To reach σ*, add equities or remove bonds.",
    "adjust": "Adjust my choices", "level": "Risk level", "cost": "Transaction cost (bps of traded value)",
    "computed": "Recomputed in {s:.1f} s.", "cached": "Loaded from cache (first computed in {s:.1f} s).",
    "loading": "Budgeting the risk of your portfolio…",
    "tabs": ["Allocation", "Risk", "Diversification", "Performance", "Projection"],
    "alpha": "Risky share α", "rf_share": "Risk-free 1 − α", "holdings": "Holdings", "esg_vs": "ESG score vs off",
    "by_class": "By asset class", "by_region": "By sleeve", "by_sector": "Equities by sector",
    "target_vs": "Target σ* vs realised σ", "ex_ante": "Ex-ante σ̂(y) = α·σ̂(x) at each rebalancing",
    "decomp": "Risk decomposition today (Euler: ΣRC_i = σ(y))", "var_es": "Daily VaR and ES, Gaussian vs historical",
    "crises": "Cumulative return during each crisis", "diversification": "Concentration on weights and on risk",
    "benchmark": "Benchmark b", "gross_net": "Gross vs net of costs", "turnover": "Turnover at each rebalancing",
    "weights_time": "Weights at each monthly rebalancing", "expected": "Expected annual return μ̂",
    "ci_note": "± {margin} is the 95% interval of the estimate μ̂ ± 1.96·σ̂/√T over T = {years:.0f} years: "
               "the estimation error of LN 3, not the range of future returns.",
    "horizon": "Horizon (years)", "fan": "Value of {start} invested (median, 25–75% and 5–95% bands, LN 6)",
    "formulas": "Each step, its lecture and its formula", "impl_window": "days in each estimation window",
    "impl_rebalancings": "monthly rebalancings, {start}–{end}", "impl_sleeves": "sleeves, each built by ERC",
    "mission": "Mission", "commitments": "Our commitments", "next": "Next steps",
}

PIPELINE = [  # (badge, step, formula in LaTeX)
    ("Data", "Datastream prices → simple returns", r"R_t = P_t / P_{t-1} - 1"),
    ("LN 3", "Ledoit-Wolf, constant-correlation target", r"\hat\Sigma = \delta F + (1-\delta) S"),
    ("LN 5", "Level 1: ERC inside each sleeve", r"y^* = \arg\min \tfrac12 y^\top\Sigma y \;\text{s.t.}\; \sum_i \ln y_i \ge c,"
                                                r"\quad x = y^*/\textstyle\sum_i y^*_i"),
    ("LN 6", "ESG option: risk budgets", r"RC_i = b_i\,\sigma(x),\quad b_i \propto \text{ESG}_i"),
    ("LN 5", "Level 2: ERC across sleeves", r"RC_i = x_i\frac{(\Sigma x)_i}{\sqrt{x^\top\Sigma x}} = \frac{\sigma(x)}{n}"),
    ("LN 2", "Volatility targeting", r"y = (1-\alpha)\,r + \alpha\,x,\quad \alpha = \min(1, \sigma^*/\hat\sigma(x))"),
    ("LN 3", "Monthly rebalancing and costs", r"R^{net} = R - c\sum_i |\Delta x_i|"),
    ("LN 6", "Risk measures", r"\mathrm{VaR}_\alpha = -x^\top\mu + \Phi^{-1}(\alpha)\sigma(x),\quad"
                              r"\mathrm{ES}_\alpha = -x^\top\mu + \sigma(x)\frac{\phi(\Phi^{-1}(\alpha))}{1-\alpha}"),
]

GOALS = {
    "mission": "Give every pension client a portfolio whose risk is spread evenly across markets and whose "
               "overall risk matches who they are.",
    "commitments": ["No look-ahead: decisions use past data only", "The same rules for every client",
                    "Course methods only (LN 2, 3, 5, 6), each one labelled", "Costs and limits shown openly"],
    "next": ["Quarterly rebalancing as a robustness check", "Turnover limits between rebalancings",
             "Dynamic ESG scores instead of today's snapshot", "Downloadable client reports"],
}
