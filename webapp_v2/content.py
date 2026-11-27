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
    "who": ("Balance every risk.", "A multi-asset pension fund mandate built on Equal Risk Contribution.", "Build my portfolio"),
    "strategy": ("Risk, shared fairly.", "Why we budget risk instead of forecasting returns.", "Find my portfolio"),
    "universe": ("Know what you own.", "Every stock we can invest in, by region, industry and ESG score.", None),
    "journey": ("Build it together.", "A few short steps from your preferences to your portfolio.", None),
    "goals": ("Built for decades.", "What we aim for and what we commit to.", "Start the journey"),
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

# "Who we are": editorial sections (heading, paragraphs). {placeholders} are filled with computed figures.
WHO_INTRO = ("Léman Wealth Management manages the assets of pension funds around one idea: no single market should "
             "decide whether a fund can pay its pensions. Our portfolio combines {n_sleeves} building blocks: {stocks}, plus "
             "{indices}. We have tested it on {years} years of markets, from {year} to today, rebalancing it every "
             "month.")
WHO = [
    ("Our mandate", [
        "We run a multi-asset pension fund. Equities are held in regional sleeves, alongside US investment-grade "
        "bonds and a basket of commodities. Every month we rebuild the portfolio from the latest data and trade "
        "back to the new weights.",
        "Each fund can add an ESG screen that removes the worst-rated stocks of each region before the portfolio "
        "is built, and sets the level of risk it can bear. Everything else follows the same rules for every fund.",
    ]),
    ("How we invest", [
        "Our method starts from risk instead of money. With Equal Risk Contribution, every building block of the "
        "portfolio, each equity region, bonds and commodities, adds the same share to its overall risk. Volatile "
        "assets receive less money and calmer ones receive more, so no single market dominates.",
    ]),
    ("Your fund's level of risk", [
        "Sharing risk equally says nothing about how much risk the fund takes overall. That decision belongs to "
        "your investment committee: it picks one of five risk levels, which sets the share of the assets invested "
        "in the ERC portfolio, from {low} to {high}. The rest earns the risk-free rate.",
    ]),
    ("Working with us", [
        "Building your fund's portfolio takes a few minutes in the Client journey. You tell us which regions, "
        "asset classes and sectors the fund should hold, whether to apply an ESG screen, and its risk level.",
        "We then budget the risk and show you the result straight away: the allocation, each holding's share of "
        "risk, past performance against a benchmark, and a projection of where the fund's assets could go. Change any "
        "choice and the portfolio updates in front of you.",
    ]),
]
TEAM_INTRO = "Six people, each responsible for one part of the investment process."

WHY_RB = [
    ("No expected returns needed", "The ERC portfolio is independent of expected asset returns: it only uses the "
     "covariance of the assets."),
    ("Robust to its inputs", "Mean-variance portfolios are very sensitive to their input parameters, whereas "
     "risk-budgeting portfolios like ERC are more robust."),
    ("The least concentrated risk", "Among all portfolios, ERC is the one whose risk contributions are the least "
     "concentrated."),
]

BUILD_STEPS = [
    ("1 · Inside each sleeve", "In each region, every stock adds the same amount of risk to its sleeve. Bonds and "
     "commodities are their own sleeves."),
    ("2 · Across the sleeves", "The six sleeves (four equity regions, bonds, commodities) each carry one sixth of the "
     "portfolio's risk."),
    ("3 · The fund's level of risk", "The investment committee sets the share invested in this portfolio; the rest "
     "stays in the risk-free asset."),
]

FAQ = [
    ("What is Equal Risk Contribution?", "A portfolio where each component adds the same amount to total "
     "volatility: volatile assets get less capital, calm ones more."),
    ("Why add a risk-free asset?", "It sets the level of risk without changing the mix: holding less in the ERC "
     "portfolio lowers risk in proportion, and the return per unit of risk stays the same."),
    ("Is the backtest realistic?", "Weights only use past data and are held from the next day, and trading costs "
     "are deducted. Two biases remain. Our stock lists are today's index members, so companies that left the "
     "indices are missing (survivorship bias): to measure it, we rebuilt the same ERC on the official indices, "
     "which have no such bias. Its Sharpe ratio falls from {erc_sharpe} to {idx_sharpe}, close to the 60/40 "
     "({b_sharpe}), with {vol_cut} less volatility and a smaller worst loss ({idx_dd} against {b_dd}). And ESG "
     "scores are today's, applied to the whole history (look-ahead bias)."),
    ("Can I lose money?", "Yes. The Performance tab shows the largest past drawdown of your portfolio, and the "
     "Projection tab the range of outcomes over your horizon."),
    ("Why can the portfolio hold fewer stocks than the universe lists?", "Our universe is today's {listed} members "
     "of the {indices}, and {investable} of them are investable today. A stock needs a full year of prices before "
     "we can estimate its risk, so the {recent} listed less than a year ago wait ({recent_names}). Prices below "
     "{floor} are left out, because a one-cent step would be more than {tick} of the price, and so are stocks "
     "whose price did not move on more than {zero_share} of the days: this excludes {unusable_names}. Using today's members also means that companies which left these indices are missing "
     "from the backtest (survivorship bias)."),
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
LEVEL_NAMES = {1: "Cautious", 2: "Moderate", 3: "Balanced", 4: "Dynamic", 5: "Fully invested"}
# Stock counts: the same phrase wherever the size of the universe appears (logic.universe.stock_counts)
STOCK_LINE = "{investable} stocks"  # one number everywhere: the stocks investable today
STOCK_LINE_SHORT = "{investable} stocks"
STOCK_NAMES = ("stock", "stocks")
INDEX_NAMES = {"Bonds": ("bond index", "bond indices"), "Commodities": ("commodity index", "commodity indices")}
ESG_HELP = "Share of the worst-ESG stocks excluded from each region, at every monthly rebalancing."

JOURNEY = {
    "regions": ("Step 1 · Where do you want to invest?", "Pick one or more regional equity sleeves."),
    "classes": ("Step 2 · Which asset classes?", "Each class is a sleeve of its own. Hold at least two sleeves."),
    "sectors": ("Step 3 · Which sectors?", "Applied to the stocks of every region you picked."),
    "esg": ("Step 4 · ESG preference", "Exclude the worst ESG-rated stocks of each region before ERC runs: the ESG "
                                    "screen decides what you own, ERC how the risk is spread."),
    "profile": ("Step 5 · Your risk level", "Choose the share of the fund invested in the ERC portfolio; the rest "
                                        "earns the risk-free rate. A lower level means less risk, with the same "
                                        "diversification."),
    "portfolio": ("Step 6 · Your portfolio", "{level} · α = {alpha} in ERC · ESG screen {esg} · {n} sleeves"),
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
    "region_facts": "{stocks} · {c} {countries}",
    "index_note": "Annual return and volatility of the official indices since {start}.",
    "class_note": "Annual return and volatility since {start}: official indices for equities and bonds, our sleeve of "
                  "three S&P GSCI sector indices for commodities.",
    "stocks_left": "stocks left in {region}",
    "team": "The team", "faq": "Questions",
    "closing_cta": "Ready to see your portfolio?",
    "problem": "The problem: money is not risk",
    "problem_sub": "A classic 60/40 portfolio looks balanced. But stocks are far more volatile than bonds, so they "
                   "carry almost all of its risk: when stocks fall, the whole portfolio falls.",
    "problem_note": "60% S&P 500 and 40% US bonds (AGG), {start}–{end}: stocks are {money} of the money and {risk} "
                    "of the risk.",
    "answer": "Our answer: share the risk equally",
    "answer_sub": "Equal Risk Contribution (ERC) gives each sleeve the same share of the total risk: calm assets "
                  "get more money, volatile ones less.",
    "answer_note": "Our portfolio with every sleeve, at the last rebalancing ({date}).",
    "money": "Share of the money", "risk": "Share of the risk",
    "build": "How we build the portfolio",
    "why_rb": "Why ERC", "lab": "Equal money is not equal risk",
    "lab_sub": "Putting the same amount in each sleeve (1/N) does not spread the risk: the most volatile sleeves "
               "cause most of the ups and downs. ERC adjusts the amounts so that each sleeve causes the same share.",
    "lab_vol": "Volatility with {name}",
    "lab_note": "Each bar is a sleeve's share of the portfolio's risk on {date}. With 1/N, the Eurozone causes "
                "{euro} of the risk and bonds {bonds}; with ERC, every sleeve causes one sixth.",
    "theorem": "ERC was also less risky than 1/N at {share} of our {n} monthly rebalancings.",
    "excluded": "stocks excluded at the latest rebalancing", "kept": "stocks kept", "esg_now": "Portfolio ESG score",
    "esg_delta": "{delta:+.1f} vs Off", "esg_level": "ESG screen",
    "level_slider": "Risk level", "level_format": "{level} · {name} · α {alpha}",
    "level_line": "Level {level} · {alpha} in the ERC portfolio · {rf} risk-free",
    "step": "Step {n}",
    "no_equities": "This step only applies to equities. You did not select equities in step 2: click Next.",
    "levels_title": "What each level would have meant", "levels_invested": "Invested in ERC",
    "levels_yours": " (your choice)",
    "levels_note": "Backtest {start}–{end} of the portfolio built in the previous steps, after trading costs. "
                   "A higher level brings more return and deeper losses: the committee chooses the level of risk "
                   "the fund can bear.",
    "adjust": "Adjust my choices",
    "cost_note": "Trading costs are set at {bps} bps of the amount traded at each rebalancing, a typical level for "
                 "an institutional investor in liquid markets. They reduce the annual return by {drag}.",
    "computed": "Recomputed in {s:.1f} s.", "cached": "Loaded from cache (first computed in {s:.1f} s).",
    "loading": "Budgeting the risk of your portfolio…",
    "tabs": ["Allocation", "Risk contribution", "Performance", "Projection"],
    "alpha": "ERC share α", "rf_share": "Risk-free 1 − α", "esg_vs": "ESG score vs Off",
    "by_class": "By asset class", "by_sector": "Equities by sector",
    "benchmark": "Benchmark b", "gross_net": "Gross vs net of costs", "turnover": "Turnover at each rebalancing",
    "turnover_note": "Each bar is the share of the portfolio traded at a monthly rebalancing. It usually stays at a "
                     "few percent and spikes only when volatility changes sharply: in the 2008 crisis, in March "
                     "2020, and in 2021 when the Covid crash left the one-year estimation window.",
    "weights_time": "Weights at each monthly rebalancing", "expected": "Expected annual return",
    "expected_vol": "Expected volatility",
    "bench_title": "{b} with the same cash share ({rf})",
    "bench_note": "The benchmark holds the same {rf} in the risk-free asset as your portfolio. 60/40: 60% S&P 500 "
                  "and 40% US bonds (AGG). 1/N: equal weights on the six sleeve indices. Both rebalanced monthly.",
    "ci_note": "± {margin} is the 95% confidence interval of the average return, estimated over {years:.0f} years "
               "of backtest: it measures the uncertainty of the average, not the range of future returns.",
    "horizon": "Horizon (years)", "fan": "Value of {start} invested (median, 25–75% and 5–95% bands)",
}

UNIVERSE = {
    "breakdown": "Investment universe breakdown", "geo": "Geographical breakdown", "industry": "Industry breakdown",
    "stocks": "Number of stocks", "counts_caption": "Breakdowns are based on stock counts, not portfolio weights.",
    "held_note": "{line}. A stock enters the portfolio only with a complete {n}-day return history and a moving "
                 "price.",
    "esg": "ESG analysis", "esg_mean": "Average ESG score", "esg_median": "Median ESG score",
    "esg_coverage": "ESG score coverage", "esg_hist": "ESG score distribution", "esg_axis": "ESG score",
    "companies": "Selected companies", "search": "Search for a company", "region_filter": "Filter by region",
    "displayed": "{n} companies displayed.", "empty": "No company matches these filters.",
}
UNIVERSE_COLUMNS = {"name": "Company", "zone": "Region", "country": "Country", "industry": "Industry",
                    "sector": "Sector", "esg_score": "ESG Score", "isin": "ISIN"}

COMPOSITION = {
    "inside": "Inside the ERC portfolio ({alpha} of the fund)", "total": "Show as % of the whole fund",
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
    "business days with Ledoit-Wolf shrinkage. Long-only. A share of the fund ({low} to {high}, set by its "
    "risk level) is invested in the ERC portfolio, the rest in the risk-free asset.",
    "**ESG option**: exclusion of the worst {levels} ESG-scored equities in each region, at every rebalancing.",
    "**Investable stocks**: a stock enters the portfolio only with a full year of prices ({n} business days), the "
    "window on which its risk is estimated. Of the {listed} stocks in our universe, {investable} are investable "
    "today. {recent} were listed less than a year ago and will enter once they have a full year: {recent_names}.",
    "**Prices too low to record real moves**: our data rounds prices to the cent, so below {floor} a one-cent step "
    "is more than {tick} of the price and the daily moves become rounding noise. These prices are left out, and so "
    "are stocks whose price did not move on more than {zero_share} of the days of the year (stale prices), which "
    "leaves {unusable} stocks without a usable price over the last year: {unusable_names}.",
    "**Limits**: estimates are historical and do not guarantee future risk. The stock lists are today's members "
    "of the {indices}: companies that left these indices in the past are missing from the "
    "backtest, a survivorship bias that makes past returns look better. Rebuilt on the official indices, the ERC "
    "portfolio has a Sharpe ratio of {idx_sharpe} instead of {erc_sharpe} ({b_name}: {b_sharpe}). ESG scores are "
    "today's, applied to the whole history: a look-ahead bias. "
    "Educational project, not investment advice.",
])

# "Our goals": opening paragraph, then editorial sections. A paragraph is a string, or (bold lead-in, text).
GOALS_INTRO = ("Our goal is simple to state and hard to achieve: give every pension fund a portfolio whose risk is "
               "spread evenly across markets, and whose overall risk matches what the fund can bear.")
GOALS = [
    ("What we aim for", [
        "A pension is built over decades, so the portfolio has to hold up in every kind of market, not only in the "
        "good years. Spreading risk evenly across regions, bonds and commodities means that no single market can "
        "decide the outcome on its own.",
        "The other half of the goal is specific to each fund. Two pension funds can bear very different levels of "
        "risk, depending on their reserves and on how many of their members already draw a pension. That is why "
        "each fund chooses its own risk level, and why we review and adjust the portfolio every month as markets "
        "change.",
    ]),
    ("How we measure success", [
        "Success, for a pension fund, is not beating the market every year. It is growing the assets steadily "
        "enough to pay every pension, without losses so deep that the fund has to cut benefits or ask for more "
        "contributions.",
        "So we judge ourselves on what matters to the fund: risk that stays close to the level it chose, smaller "
        "falls when markets are in trouble, and growth that builds up over the long run. We show these results "
        "openly in the portfolio, next to a classic portfolio, so the fund can judge for itself.",
    ]),
    ("Responsible investing", [
        "Each fund decides how much sustainability matters in its portfolio. With our ESG screen, the companies with the "
        "weakest environmental, social and governance ratings in each region are left out before the portfolio "
        "is built, and the fund chooses how strict the screen is.",
        "The portfolio stays diversified whatever the choice: risk is still spread evenly over the companies that "
        "remain, and the fund sees straight away how the screen changes its ESG score and what it costs.",
    ]),
    ("How we work with you", [
        "Managing a pension fund's assets is a long-term mandate built on trust. This is what your fund can expect "
        "from us.",
        ("A mandate built around your rules.", "Together we set the regions, asset classes and sectors your fund "
         "holds, the ESG screen and the level of risk it can bear. We then apply these choices the same way every "
         "month."),
        ("A disciplined process.", "Every decision follows the same written method, with no discretionary bets. "
         "Your portfolio stays predictable and easy to explain to your board and your members."),
        ("Full transparency.", "You see every holding, the share of risk each part of the portfolio carries, and "
         "performance after trading costs, next to a classic 60/40 portfolio."),
    ]),
]
