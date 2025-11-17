# Support & Resistance detection
import pandas as pd
import numpy as np

def find_swing_highs_lows(df, window=5):
    """
    Find swing highs and lows in price data
    Args:
        df: DataFrame with OHLC data
        window: lookback window for swing detection
    Returns: tuple of (swing_highs, swing_lows)
    """
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(df) - window):
        # Check if current high is highest in window
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            swing_highs.append(df['High'].iloc[i])
        
        # Check if current low is lowest in window
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            swing_lows.append(df['Low'].iloc[i])
    
    return swing_highs, swing_lows

def get_nearest_sr_levels(df, num_levels=3):
    """
    Find nearest support and resistance levels
    Args:
        df: DataFrame with OHLC data
        num_levels: number of S/R levels to identify
    Returns: tuple of (support_levels, resistance_levels)
    """
    current_price = df['Close'].iloc[-1]
    
    swing_highs, swing_lows = find_swing_highs_lows(df)
    
    # Find resistance levels (above current price)
    resistances = [h for h in swing_highs if h > current_price]
    resistances = sorted(set(resistances))[:num_levels] if resistances else []
    
    # Find support levels (below current price)
    supports = [l for l in swing_lows if l < current_price]
    supports = sorted(set(supports), reverse=True)[:num_levels] if supports else []
    
    return supports, resistances

def get_sr_verdict(df, proximity_threshold=0.005):
    """
    Determine S/R verdict based on price position relative to levels
    Args:
        df: DataFrame with OHLC data
        proximity_threshold: % threshold to consider "near" a level (0.5%)
    Returns: tuple (verdict, explanation)
    """
    if len(df) < 20:
        return ("NEUTRAL", "Insufficient data")
    
    current_price = df['Close'].iloc[-1]
    supports, resistances = get_nearest_sr_levels(df)
    
    # Check proximity to support
    if supports:
        nearest_support = supports[0]
        distance_to_support = abs(current_price - nearest_support) / current_price
        
        if distance_to_support < proximity_threshold:
            return ("BUY", f"Near support at {round(nearest_support, 2)}")
    
    # Check proximity to resistance
    if resistances:
        nearest_resistance = resistances[0]
        distance_to_resistance = abs(current_price - nearest_resistance) / current_price
        
        if distance_to_resistance < proximity_threshold:
            return ("SELL", f"Near resistance at {round(nearest_resistance, 2)}")
    
    # Mid-zone between levels
    return ("NEUTRAL", "Mid-zone between levels")