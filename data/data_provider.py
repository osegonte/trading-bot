"""
Unified Data Provider
Automatically switches between Twelve Data and cTrader based on config
"""
import logging
from typing import Optional, Tuple
import pandas as pd
from config.config import DATA_SOURCE

logger = logging.getLogger(__name__)


def get_xauusd_price() -> Optional[float]:
    """
    Get current XAU/USD price from configured source
    
    Returns:
        Current price or None if error
    """
    if DATA_SOURCE == 'ctrader':
        try:
            from data.sources.ctrader_source import CTraderSource
            source = CTraderSource()
            return source.get_price()
        except Exception as e:
            logger.warning(f"cTrader price fetch failed: {e}, falling back to Twelve Data")
    
    # Default: Twelve Data
    from data.sources.twelve_data_source import TwelveDataSource
    source = TwelveDataSource()
    return source.get_price()


def get_ohlc_data(period: str = "5d", interval: str = "1min", candles: int = 100) -> Optional[pd.DataFrame]:
    """
    Get OHLC data from configured source
    
    Args:
        period: Time period
        interval: Candle interval
        candles: Number of candles
    
    Returns:
        DataFrame with OHLC data or None
    """
    if DATA_SOURCE == 'ctrader':
        try:
            from data.sources.ctrader_source import CTraderSource
            source = CTraderSource()
            return source.get_ohlc(interval=interval, bars=candles)
        except Exception as e:
            logger.warning(f"cTrader OHLC fetch failed: {e}, falling back to Twelve Data")
    
    # Default: Twelve Data
    from data.sources.twelve_data_source import TwelveDataSource
    source = TwelveDataSource()
    return source.get_ohlc(period=period, interval=interval, outputsize=candles)


def fetch_macro_data() -> dict:
    """
    Fetch macro data (always from Twelve Data for now)
    
    Returns:
        Dict with macro indicators
    """
    from data.sources.twelve_data_source import TwelveDataSource
    source = TwelveDataSource()
    return source.get_macro_data()


def health_check() -> Tuple[bool, str]:
    """
    Check data source health
    
    Returns:
        Tuple of (success, message)
    """
    if DATA_SOURCE == 'ctrader':
        try:
            from data.sources.ctrader_source import CTraderSource
            source = CTraderSource()
            return source.health_check()
        except Exception as e:
            logger.warning(f"cTrader health check failed: {e}")
    
    # Default: Twelve Data
    from data.sources.twelve_data_source import TwelveDataSource
    source = TwelveDataSource()
    return source.health_check()


def get_api_usage_stats() -> dict:
    """
    Get API usage statistics
    
    Returns:
        Dict with usage stats
    """
    if DATA_SOURCE == 'ctrader':
        return {
            'calls_today': 0,
            'limit': 999999,
            'remaining': 999999,
            'percentage': 0,
            'date': None
        }
    
    # Default: Twelve Data
    from data.sources.twelve_data_source import TwelveDataSource
    source = TwelveDataSource()
    return source.get_usage_stats()
