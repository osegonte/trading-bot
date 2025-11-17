# Bollinger Bands analysis
from utils.indicators import calculate_bollinger_bands
import pandas as pd

def get_bollinger_verdict(df, period=20, std_dev=2):
    """
    Analyze Bollinger Bands for reversal signals
    Args:
        df: DataFrame with OHLC data
        period: BB period (default 20)
        std_dev: standard deviation multiplier (default 2)
    Returns: tuple (verdict, explanation)
    """
    if len(df) < period + 5:
        return ("NEUTRAL", "Insufficient data")
    
    upper, middle, lower = calculate_bollinger_bands(df['Close'], period, std_dev)
    
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    
    current_upper = upper.iloc[-1]
    current_middle = middle.iloc[-1]
    current_lower = lower.iloc[-1]
    
    if pd.isna(current_upper) or pd.isna(current_lower):
        return ("NEUTRAL", "BB calculation error")
    
    # Calculate band width percentage
    band_width = (current_upper - current_lower) / current_middle * 100
    
    # Price touching/bouncing off lower band - potential buy
    if current_price <= current_lower * 1.005:  # Within 0.5% of lower band
        if current_price > prev_price:
            return ("BUY", f"Bounce off lower BB")
        return ("BUY", f"At lower BB")
    
    # Price touching/failing at upper band - potential sell
    if current_price >= current_upper * 0.995:  # Within 0.5% of upper band
        if current_price < prev_price:
            return ("SELL", f"Rejection at upper BB")
        return ("SELL", f"At upper BB")
    
    # Price near middle band - neutral
    middle_zone = abs(current_price - current_middle) / current_middle
    if middle_zone < 0.003:  # Within 0.3% of middle
        return ("NEUTRAL", "Near middle BB")
    
    # Inside bands, no edge
    return ("NEUTRAL", "Inside bands")