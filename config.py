import os

HF_TOKEN = os.environ.get("HF_TOKEN", "")
DATA_REPO = "P2SAMAPA/fi-etf-macro-signal-master-data"
OUTPUT_REPO = "P2SAMAPA/p2-etf-brownian-bridge-results"

UNIVERSES = {
    "FI_COMMODITIES": ["TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV"],
    "EQUITY_SECTORS": [
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI", "IWM", "IWD", "IWO"
    ],
    "COMBINED": [
        "TLT", "VCIT", "LQD", "HYG", "VNQ", "GLD", "SLV",
        "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
        "XLP", "XLU", "GDX", "XME", "IWF", "XSD", "XBI", "IWM", "IWD", "IWO"
    ]
}

# Bridge type: "price" or "volatility"
BRIDGE_TYPE = "price"          # price target = month-end level, volatility = mean-reverting vol

# For price bridge: target is the ETF's own price at the last month-end (or can be a market index like SPY)
USE_MARKET_TARGET = False       # if True, target is SPY level (requires SPY in universe)
TARGET_INDEX = "SPY"

# For volatility bridge: target volatility (annualised) – compute historical mean
VOL_TARGET_WINDOW = 252         # days to compute mean volatility

# Rolling window for estimating drift (days)
ESTIMATION_WINDOW = 60          # use last 60 days to estimate volatility and drift

TOP_N = 3
