# Volume analysis for confirmation
import pandas as pd

def calculate_volume_ma(df, period=20):
    """Calculate Volume Moving Average"""
    return df['Volume'].rolling(window=period).mean()

def get_volume_verdict(df, strong_threshold=1.2, weak_threshold=0.7):
    """
    Analyze volume strength compared to average
    Args:
        df: DataFrame with OHLCV data
        strong_threshold: multiplier for strong volume (1.2 = 120% of avg)
        weak_threshold: multiplier for weak volume (0.7 = 70% of avg)
    Returns: tuple (verdict, explanation)
    """
    if len(df) < 20:
        return ("NEUTRAL", "Insufficient data")
    
    # Calculate volume MA
    volume_ma = calculate_volume_ma(df, 20)
    
    current_volume = df['Volume'].iloc[-1]
    avg_volume = volume_ma.iloc[-1]
    
    if avg_volume == 0:
        return ("NEUTRAL", "No volume data")
    
    volume_ratio = current_volume / avg_volume
    
    if volume_ratio > strong_threshold:
        return ("BUY", f"Strong volume ({round(volume_ratio, 2)}x avg)")
    elif volume_ratio < weak_threshold:
        return ("SELL", f"Weak volume ({round(volume_ratio, 2)}x avg)")
    else:
        return ("NEUTRAL", f"Normal volume ({round(volume_ratio, 2)}x avg)")