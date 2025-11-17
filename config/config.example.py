# API keys and configuration
TELEGRAM_TOKEN = "7623552805:AAHGKcE4k2vpUDyy0Im79xrZ1lrUHonbjAA"

# Symbol configuration
SYMBOL_DEFAULT = "GC=F"  # Gold Futures
CANDLE_TIMEFRAME = "1m"

# Trading parameters
PIP_SIZE = 0.01  # Gold pip size
PIP_VALUE_PER_LOT = 1.00  # Approximate for gold
BROKER_MIN_LOT = 0.01
BROKER_LOT_STEP = 0.01
BROKER_MAX_LOT = 50.0

# Risk management
RISK_MODE = "SAFER"  # Options: "LEVEL_STRICT" or "SAFER"
RISK_PER_TRADE = 0.01  # 1% risk per trade (SAFER mode)
RR_TARGET = 2.0  # Risk:Reward target
SL_METHOD = "ATR"  # Options: "ATR" or "STRUCTURE"
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5

# Verification
VERIFICATION_WINDOW_BARS = 120  # 2 hours of 1m bars
ASSUMED_SPREAD = 0.05  # Price units
TIMEZONE = "UTC"

# Initial balance for level game
INITIAL_BALANCE = 20.0  # Starting balance in €

# Macro sentiment tickers
MACRO_TICKERS = {
    'DXY': 'DX-Y.NYB',
    'US10Y': '^TNX',
    'SPX': '^GSPC',
    'VIX': '^VIX'
}

MACRO_LOOKBACK_MIN = 15
MACRO_CACHE_SECONDS = 60

# News blackout
NEWS_BLACKOUT_MINUTES = 15
UPCOMING_EVENTS = []

# Aggregator weights
WEIGHTS = {
    'trend': 1.0,
    'candlestick': 1.0,
    'sr': 1.0,
    'volume': 1.0,
    'rsi': 0.5,
    'macd': 0.5,
    'bollinger': 0.5
}

BUY_SELL_THRESHOLDS = {
    'buy': 2.0,
    'sell': -2.0
}

CONFIDENCE = {
    'base': 50,
    'full_weight': 10,
    'half_weight': 5,
    'macro_align': 10,
    'macro_contra': -10,
    'cap': 90
}