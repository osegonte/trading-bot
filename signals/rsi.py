# RSI momentum analysis
from utils.indicators import calculate_rsi
import pandas as pd  # ADD THIS LINE

def get_rsi_verdict(df, period=14):
    """
    Analyze RSI for momentum signals
    Args:
        df: DataFrame with OHLC data
        period: RSI period (default 14)
    Returns: tuple (verdict, explanation)
    """
    if len(df) < period + 5:
        return ("NEUTRAL", "Insufficient data")
    
    rsi = calculate_rsi(df['Close'], period)
    current_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    
    if pd.isna(current_rsi):
        return ("NEUTRAL", "RSI calculation error")
    
    # Oversold zone - potential buy
    if current_rsi < 30:
        return ("BUY", f"RSI {round(current_rsi, 1)} oversold")
    
    # Rising through 40-50 - bullish momentum
    if 40 <= current_rsi <= 50 and current_rsi > prev_rsi:
        return ("BUY", f"RSI {round(current_rsi, 1)} rising")
    
    # Overbought zone - potential sell
    if current_rsi > 70:
        return ("SELL", f"RSI {round(current_rsi, 1)} overbought")
    
    # Falling through 60-50 - bearish momentum
    if 50 <= current_rsi <= 60 and current_rsi < prev_rsi:
        return ("SELL", f"RSI {round(current_rsi, 1)} falling")
    
    # Neutral zone
    return ("NEUTRAL", f"RSI {round(current_rsi, 1)} neutral")