# Find and replace in config/config.py

# OLD:
BUY_SELL_THRESHOLDS = {
    'buy': 2.0,
    'sell': -2.0
}

# NEW (more aggressive):
BUY_SELL_THRESHOLDS = {
    'buy': 1.5,   # Lower = more trades
    'sell': -1.5
}
