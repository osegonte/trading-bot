# Trend analysis using EMAs
import pandas as pd

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def get_trend_verdict(df):
    """
    Determine trend based on EMA20 and EMA50
    Returns: str - "BUY", "SELL", or "NEUTRAL"
    """
    if len(df) < 50:
        return "NEUTRAL"
    
    df['EMA20'] = calculate_ema(df['Close'], 20)
    df['EMA50'] = calculate_ema(df['Close'], 50)
    
    current_price = df['Close'].iloc[-1]
    ema20 = df['EMA20'].iloc[-1]
    ema50 = df['EMA50'].iloc[-1]
    
    if current_price > ema20 and current_price > ema50:
        return "BUY"
    elif current_price < ema20 and current_price < ema50:
        return "SELL"
    else:
        return "NEUTRAL"