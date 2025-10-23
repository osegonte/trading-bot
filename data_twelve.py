"""
Twelve Data source - 800 requests/day free tier
PRODUCTION VERSION with rate limiting, retries, and comprehensive error handling
"""
import requests
import pandas as pd
from config import TWELVE_DATA_API_KEY
import time
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com"

# Track daily API usage (resets at midnight UTC)
_api_call_count = 0
_last_reset_date = None
MAX_DAILY_CALLS = 750  # Set to 750 to leave buffer
WARNING_THRESHOLD = 600

def _check_daily_quota():
    """Check if we're approaching daily API limit"""
    global _api_call_count, _last_reset_date
    
    now = datetime.now(pytz.UTC)
    today = now.date()
    
    # Reset counter at midnight UTC
    if _last_reset_date != today:
        _api_call_count = 0
        _last_reset_date = today
        logger.info(f"✅ API quota reset for {today}")
    
    _api_call_count += 1
    
    # Warn if approaching limit
    if _api_call_count == WARNING_THRESHOLD:
        logger.warning(f"⚠️ API usage at {_api_call_count}/{MAX_DAILY_CALLS} - approaching daily limit!")
    
    # Hard stop if at limit
    if _api_call_count >= MAX_DAILY_CALLS:
        logger.error(f"❌ Daily API limit reached ({MAX_DAILY_CALLS} calls)")
        return False
    
    return True

def _make_request(url, params, timeout=10, max_retries=3):
    """
    Make API request with retry logic and rate limit handling
    Args:
        url: API endpoint
        params: Query parameters
        timeout: Request timeout
        max_retries: Number of retry attempts
    Returns: Response data or None
    """
    if not _check_daily_quota():
        logger.error("Daily quota exceeded, skipping request")
        return None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                logger.warning(f"⏳ Rate limited (429), waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                time.sleep(wait_time)
                continue
            
            # Handle other errors
            if response.status_code != 200:
                logger.error(f"❌ API error {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
            
            data = response.json()
            
            # Check for API error messages
            if 'status' in data and data['status'] == 'error':
                logger.error(f"❌ API returned error: {data.get('message', 'Unknown error')}")
                return None
            
            return data
        
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Request timeout (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
        
        except requests.exceptions.RequestException as e:
            logger.error(f"🔌 Request failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
        
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
            return None
    
    logger.error(f"❌ All {max_retries} attempts failed")
    return None

def get_xauusd_price():
    """Get current gold price with retry logic"""
    try:
        url = f"{BASE_URL}/price"
        params = {
            'symbol': 'XAU/USD',
            'apikey': TWELVE_DATA_API_KEY
        }
        
        data = _make_request(url, params)
        
        if data and 'price' in data:
            price = float(data['price'])
            logger.info(f"✅ Got price: ${price:.2f}")
            return round(price, 2)
        else:
            logger.warning(f"⚠️ Price data invalid or missing")
    
    except Exception as e:
        logger.error(f"❌ Price fetch error: {e}")
    
    return None


def get_ohlc_data(period="5d", interval="1min", candles=100):
    """Get OHLC data for XAU/USD with retry logic"""
    try:
        url = f"{BASE_URL}/time_series"
        params = {
            'symbol': 'XAU/USD',
            'interval': '1min',
            'outputsize': min(candles + 20, 5000),
            'apikey': TWELVE_DATA_API_KEY
        }
        
        data = _make_request(url, params, timeout=15)
        
        if data and 'values' in data and len(data['values']) > 0:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            df = df.sort_index()
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            result = df.tail(candles)
            logger.info(f"✅ Got {len(result)} candles (from {result.index[0]} to {result.index[-1]})")
            return result
        else:
            logger.warning(f"⚠️ OHLC data invalid or missing")
    
    except Exception as e:
        logger.error(f"❌ OHLC fetch error: {e}")
    
    return None


def fetch_macro_data():
    """
    Fetch macro indicators with Twelve Data
    Simplified version - returns neutral data if unavailable
    """
    result = {
        'dxy_signal': 0,
        'yield_signal': 0,
        'risk_signal': 0,
        'dxy_explanation': 'Macro data: neutral',
        'yield_explanation': 'Yields: neutral',
        'risk_explanation': 'Risk: neutral'
    }
    
    try:
        url = f"{BASE_URL}/time_series"
        params = {
            'symbol': 'USD/EUR',
            'interval': '15min',
            'outputsize': 10,
            'apikey': TWELVE_DATA_API_KEY
        }
        
        data = _make_request(url, params)
        
        if data and 'values' in data and len(data['values']) >= 5:
            closes = [float(v['close']) for v in data['values'][:5]]
            
            if closes[0] > closes[-1]:
                result['dxy_signal'] = 1
                result['dxy_explanation'] = "USD weakening (bullish)"
            elif closes[0] < closes[-1]:
                result['dxy_signal'] = -1
                result['dxy_explanation'] = "USD strengthening (bearish)"
            else:
                result['dxy_explanation'] = "USD flat"
        
        time.sleep(0.5)  # Rate limit protection between calls
    
    except Exception as e:
        logger.error(f"⚠️ Macro data error: {e}")
        result['dxy_explanation'] = "Data unavailable"
    
    return result


def get_api_usage_stats():
    """Get current API usage statistics"""
    return {
        'calls_today': _api_call_count,
        'limit': MAX_DAILY_CALLS,
        'remaining': MAX_DAILY_CALLS - _api_call_count,
        'percentage': round((_api_call_count / MAX_DAILY_CALLS) * 100, 1) if MAX_DAILY_CALLS > 0 else 0,
        'date': _last_reset_date
    }


def health_check():
    """
    Verify API connection and key validity
    Returns: tuple (success: bool, message: str)
    """
    try:
        # Test with a simple price query
        url = f"{BASE_URL}/price"
        params = {
            'symbol': 'XAU/USD',
            'apikey': TWELVE_DATA_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 401:
            return (False, "❌ Invalid API key")
        
        if response.status_code == 429:
            return (False, "⚠️ Rate limited - too many requests")
        
        if response.status_code != 200:
            return (False, f"❌ API error: {response.status_code}")
        
        data = response.json()
        
        if 'price' in data:
            return (True, f"✅ API connected - XAU/USD @ ${float(data['price']):.2f}")
        else:
            return (False, f"⚠️ Unexpected response: {data}")
    
    except Exception as e:
        return (False, f"❌ Connection failed: {e}")