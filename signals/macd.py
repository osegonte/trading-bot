# MACD momentum analysis
from utils.indicators import calculate_macd
import pandas as pd

def get_macd_verdict(df):
    """
    Analyze MACD for trend and momentum signals
    Args:
        df: DataFrame with OHLC data
    Returns: tuple (verdict, explanation)
    """
    if len(df) < 35:  # Need at least 26 + 9 periods
        return ("NEUTRAL", "Insufficient data")
    
    macd_line, signal_line, histogram = calculate_macd(df['Close'])
    
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_hist = histogram.iloc[-1]
    prev_hist = histogram.iloc[-2]
    
    if pd.isna(current_macd) or pd.isna(current_signal):
        return ("NEUTRAL", "MACD calculation error")
    
    # Bullish crossover
    if current_macd > current_signal and prev_hist < 0 and current_hist > 0:
        return ("BUY", "Bullish crossover")
    
    # Strong bullish momentum
    if current_macd > current_signal and current_hist > prev_hist:
        return ("BUY", "MACD bullish")
    
    # Bearish crossover
    if current_macd < current_signal and prev_hist > 0 and current_hist < 0:
        return ("SELL", "Bearish crossover")
    
    # Strong bearish momentum
    if current_macd < current_signal and current_hist < prev_hist:
        return ("SELL", "MACD bearish")
    
    # Flat or unclear
    return ("NEUTRAL", "MACD flat")