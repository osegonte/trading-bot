# Candlestick pattern detection
import pandas as pd

def is_doji(candle, threshold=0.1):
    """Detect Doji pattern"""
    body = abs(candle['Close'] - candle['Open'])
    range_size = candle['High'] - candle['Low']
    
    if range_size == 0:
        return False
    
    return (body / range_size) < threshold

def is_hammer(candle):
    """Detect Hammer pattern (bullish)"""
    body = abs(candle['Close'] - candle['Open'])
    lower_shadow = min(candle['Open'], candle['Close']) - candle['Low']
    upper_shadow = candle['High'] - max(candle['Open'], candle['Close'])
    
    if body == 0:
        return False
    
    return (lower_shadow > 2 * body) and (upper_shadow < body * 0.5)

def is_bullish_engulfing(curr, prev):
    """Detect Bullish Engulfing pattern"""
    prev_bearish = prev['Close'] < prev['Open']
    curr_bullish = curr['Close'] > curr['Open']
    engulfs = (curr['Open'] < prev['Close']) and (curr['Close'] > prev['Open'])
    
    return prev_bearish and curr_bullish and engulfs

def is_bearish_engulfing(curr, prev):
    """Detect Bearish Engulfing pattern"""
    prev_bullish = prev['Close'] > prev['Open']
    curr_bearish = curr['Close'] < curr['Open']
    engulfs = (curr['Open'] > prev['Close']) and (curr['Close'] < prev['Open'])
    
    return prev_bullish and curr_bearish and engulfs

def detect_candlestick_pattern(df):
    """
    Detect candlestick patterns in the latest candles
    Returns: tuple (pattern_name, verdict)
    """
    if len(df) < 2:
        return ("No Pattern", "NEUTRAL")
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    if is_bullish_engulfing(curr, prev):
        return ("Bullish Engulfing", "BUY")
    
    if is_bearish_engulfing(curr, prev):
        return ("Bearish Engulfing", "SELL")
    
    if is_hammer(curr):
        return ("Hammer", "BUY")
    
    if is_doji(curr):
        return ("Doji", "NEUTRAL")
    
    return ("No Clear Pattern", "NEUTRAL")