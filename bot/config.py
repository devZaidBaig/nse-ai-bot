"""All tunable settings in one place. Edit these, not the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"          # paper portfolio lives here (committed by GitHub Actions)
DOCS_DIR = ROOT / "docs"            # dashboard (served by GitHub Pages)

# ---- Paper money ----
STARTING_CAPITAL = 10_000           # ₹10,000 dummy money

# ---- Universe: NIFTY 50 constituents (Yahoo tickers). Update when the index rebalances. ----
UNIVERSE = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "INDIGO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "MAXHEALTH", "INFY", "ITC", "JIOFIN",
    "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM",
    "TMPV", "TATASTEEL", "TCS", "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]
# Tickers that fail to download are skipped automatically, so a stale entry won't break a run.
BENCHMARK = "^NSEI"                 # NIFTY 50 index
HISTORY_YEARS = 8                   # price history to download (more history = more to learn from)

# ---- Strategy ----
TOP_N = 3                           # number of stocks to hold (small account → few, affordable picks)
REBALANCE_WEEKDAY = 4               # 0=Mon ... 4=Fri; re-rank & rebalance on this weekday
REBALANCE_DAYS = 28                 # rebalance every 4 weeks (weekly churned fees away — see state/research.md)
MODEL = "ml"                        # "ml" = AI ranker, "momentum" = plain 12-1 momentum (baseline)
HORIZON_DAYS = 21                   # model predicts which stocks beat their peers over the next month
TRAIN_YEARS = 3                     # rolling training window
STOP_LOSS = None                    # trailing stop off: in real-data tests an 8% or 20% stop cut returns
                                    # in every period (it sold on normal dips). Set e.g. 0.20 to re-enable.
INTRADAY_ALERT = 0.07               # message you if a holding is down 7%+ on the day (alert only, no selling)
MAX_POSITION_WEIGHT = 0.34          # max share of the account in one stock
REGIME_SMA = 200                    # NIFTY below its 200-day average = risk-off
RISK_OFF_EXPOSURE = 0.4             # invest only 40% of capital when risk-off
MIN_PROBA = 0.52                    # only buy stocks the model rates above this
HOLD_BUFFER = 12                    # keep a holding while it ranks in the top 12 (reduces churn & fees)

# ---- Indian equity delivery costs (approx., per side, as fraction of trade value) ----
BROKERAGE = 0.0                     # % brokerage (Zerodha/Groww-style delivery: 0)
FLAT_FEE_PER_ORDER = 0.0            # ₹ per order; set 20 if your broker charges ₹20
DP_CHARGE_PER_SELL = 15.34          # ₹ depository charge each time you sell a stock (CDSL + broker, incl. GST)
STT = 0.001                         # 0.1% on buy and sell for delivery
EXCHANGE_AND_GST = 0.00005
STAMP_DUTY_BUY = 0.00015            # 0.015% on buy side only
SLIPPAGE = 0.0005                   # 0.05% assumed slippage

# ---- News sentiment ----
NEWS_ENABLED = True
NEWS_LOOKBACK_DAYS = 3              # headlines from the last 3 days
NEWS_MAX_HEADLINES = 12             # per stock
NEWS_WEIGHT = 0.06                  # how much news nudges the model's score (sentiment is -1..+1)
NEWS_VETO = -0.45                   # don't buy a stock whose news is this negative (with >=3 headlines)
SENTIMENT_MODEL = "ProsusAI/finbert"  # falls back to a keyword scorer if unavailable

# ---- Messaging ----
WEEKLY_RECAP_WEEKDAY = 4            # Friday

# Company names used to search news
NAMES = {
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports", "APOLLOHOSP": "Apollo Hospitals",
    "ASIANPAINT": "Asian Paints", "AXISBANK": "Axis Bank", "BAJAJ-AUTO": "Bajaj Auto",
    "BAJFINANCE": "Bajaj Finance", "BAJAJFINSV": "Bajaj Finserv", "BEL": "Bharat Electronics",
    "BHARTIARTL": "Bharti Airtel", "CIPLA": "Cipla", "COALINDIA": "Coal India", "DRREDDY": "Dr Reddy's",
    "EICHERMOT": "Eicher Motors", "ETERNAL": "Eternal Zomato", "GRASIM": "Grasim Industries",
    "HCLTECH": "HCLTech", "HDFCBANK": "HDFC Bank", "HDFCLIFE": "HDFC Life", "INDIGO": "IndiGo InterGlobe",
    "HINDALCO": "Hindalco", "HINDUNILVR": "Hindustan Unilever", "ICICIBANK": "ICICI Bank",
    "MAXHEALTH": "Max Healthcare", "INFY": "Infosys", "ITC": "ITC Ltd", "JIOFIN": "Jio Financial",
    "JSWSTEEL": "JSW Steel", "KOTAKBANK": "Kotak Mahindra Bank", "LT": "Larsen & Toubro",
    "M&M": "Mahindra & Mahindra", "MARUTI": "Maruti Suzuki", "NESTLEIND": "Nestle India", "NTPC": "NTPC",
    "ONGC": "ONGC", "POWERGRID": "Power Grid", "RELIANCE": "Reliance Industries", "SBILIFE": "SBI Life",
    "SBIN": "State Bank of India", "SHRIRAMFIN": "Shriram Finance", "SUNPHARMA": "Sun Pharma",
    "TATACONSUM": "Tata Consumer", "TMPV": "Tata Motors Passenger Vehicles", "TATASTEEL": "Tata Steel", "TCS": "TCS",
    "TECHM": "Tech Mahindra", "TITAN": "Titan Company", "TRENT": "Trent", "ULTRACEMCO": "UltraTech Cement",
    "WIPRO": "Wipro",
}

# ---- World / macro market factors (Yahoo tickers) ----
MACRO = {
    "usdinr": "INR=X",        # rupee (up = weaker rupee: good for IT exporters, bad for importers)
    "brent": "BZ=F",          # crude oil (hurts oil importers/paint/aviation, helps ONGC)
    "us10y": "^TNX",          # US 10-year yield (global risk appetite / foreign flows)
    "spx": "^GSPC",           # S&P 500 (global equity mood)
    "indiavix": "^INDIAVIX",  # India fear gauge
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",        # US dollar index
}

# ---- Sectors (for sector momentum and peer comparison) ----
SECTORS = {
    "Banks": ["AXISBANK", "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN"],
    "Finance": ["BAJFINANCE", "BAJAJFINSV", "SHRIRAMFIN", "JIOFIN", "HDFCLIFE", "SBILIFE"],
    "IT": ["INFY", "TCS", "HCLTECH", "WIPRO", "TECHM"],
    "Auto": ["MARUTI", "M&M", "BAJAJ-AUTO", "EICHERMOT", "TMPV"],
    "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "COALINDIA"],
    "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
    "Consumer": ["HINDUNILVR", "ITC", "NESTLEIND", "TATACONSUM", "ASIANPAINT", "TITAN", "TRENT", "ETERNAL"],
    "Pharma/Health": ["SUNPHARMA", "CIPLA", "DRREDDY", "APOLLOHOSP", "MAXHEALTH"],
    "Industrials": ["LT", "BEL", "ADANIENT", "ADANIPORTS", "GRASIM", "ULTRACEMCO", "INDIGO", "BHARTIARTL"],
}

MODEL_CONFIG = STATE_DIR / "model_config.json"   # written by training; read by the live bot
