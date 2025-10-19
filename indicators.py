# Indicator calculations
import pandas as pd
import numpy as np

def calculate_sma(data, period):
    """Calculate Simple Moving Average"""
    return data.rolling(window=period).mean()

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period=14):
    """
    Calculate Relative Strength Index
    Args:
        data: pandas Series of prices
        period: RSI period (default 14)
    Returns: pandas Series of RSI values
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """
    Calculate MACD (Moving Average Convergence Divergence)
    Args:
        data: pandas Series of prices
        fast: fast EMA period (default 12)
        slow: slow EMA period (default 26)
        signal: signal line period (default 9)
    Returns: tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """
    Calculate Bollinger Bands
    Args:
        data: pandas Series of prices
        period: moving average period (default 20)
        std_dev: number of standard deviations (default 2)
    Returns: tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = calculate_sma(data, period)
    std = data.rolling(window=period).std()
    
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return upper_band, middle_band, lower_band