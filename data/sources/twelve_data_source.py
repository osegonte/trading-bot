"""
Twelve Data Source - Clean wrapper for Twelve Data API
"""
import requests
import pandas as pd
from datetime import datetime
import pytz
import logging
import time
from config.config import TWELVE_DATA_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com"

# Track API usage
_api_call_count = 0
_last_reset_date = None
MAX_DAILY_CALLS = 750
WARNING_THRESHOLD = 600


class TwelveDataSource:
    """Wrapper for Twelve Data API"""
    
    def __init__(self):
        self.api_key = TWELVE_DATA_API_KEY
        self.base_url = BASE_URL
    
    def _check_quota(self) -> bool:
        """Check if quota allows request"""
        global _api_call_count, _last_reset_date
        
        now = datetime.now(pytz.UTC)
        today = now.date()
        
        if _last_reset_date != today:
            _api_call_count = 0
            _last_reset_date = today
        
        _api_call_count += 1
        
        if _api_call_count == WARNING_THRESHOLD:
            logger.warning(f"⚠️ API usage at {_api_call_count}/{MAX_DAILY_CALLS}")
        
        if _api_call_count >= MAX_DAILY_CALLS:
            logger.error(f"❌ Daily API limit reached")
            return False
        
        return True
    
    def _request(self, url: str, params: dict, timeout: int = 10, max_retries: int = 3):
        """Make API request with retry logic"""
        if not self._check_quota():
            return None
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                
                if response.status_code == 429:
                    wait = (2 ** attempt) * 2
                    logger.warning(f"Rate limited, waiting {wait}s")
                    time.sleep(wait)
                    continue
                
                if response.status_code != 200:
                    logger.error(f"API error {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return None
                
                data = response.json()
                
                if 'status' in data and data['status'] == 'error':
                    logger.error(f"API error: {data.get('message')}")
                    return None
                
                return data
            
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return None
    
    def get_price(self) -> float:
        """Get current XAU/USD price"""
        url = f"{self.base_url}/price"
        params = {'symbol': 'XAU/USD', 'apikey': self.api_key}
        
        data = self._request(url, params)
        
        if data and 'price' in data:
            return round(float(data['price']), 2)
        
        return None
    
    def get_ohlc(self, period: str = "5d", interval: str = "1min", outputsize: int = 100) -> pd.DataFrame:
        """Get OHLC data"""
        url = f"{self.base_url}/time_series"
        params = {
            'symbol': 'XAU/USD',
            'interval': '1min',
            'outputsize': min(outputsize + 20, 5000),
            'apikey': self.api_key
        }
        
        data = self._request(url, params, timeout=15)
        
        if data and 'values' in data and len(data['values']) > 0:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime').sort_index()
            
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            else:
                df['volume'] = 0
            
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            return df.tail(outputsize)
        
        return None
    
    def get_macro_data(self) -> dict:
        """Get macro indicators"""
        result = {
            'dxy_signal': 0,
            'yield_signal': 0,
            'risk_signal': 0,
            'dxy_explanation': 'Macro: neutral',
            'yield_explanation': 'Yields: neutral',
            'risk_explanation': 'Risk: neutral'
        }
        
        try:
            url = f"{self.base_url}/time_series"
            params = {
                'symbol': 'USD/EUR',
                'interval': '15min',
                'outputsize': 10,
                'apikey': self.api_key
            }
            
            data = self._request(url, params)
            
            if data and 'values' in data and len(data['values']) >= 5:
                closes = [float(v['close']) for v in data['values'][:5]]
                
                if closes[0] > closes[-1]:
                    result['dxy_signal'] = 1
                    result['dxy_explanation'] = "USD weakening (bullish)"
                elif closes[0] < closes[-1]:
                    result['dxy_signal'] = -1
                    result['dxy_explanation'] = "USD strengthening (bearish)"
            
            time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Macro data error: {e}")
        
        return result
    
    def health_check(self) -> tuple:
        """Check API health"""
        try:
            url = f"{self.base_url}/price"
            params = {'symbol': 'XAU/USD', 'apikey': self.api_key}
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 401:
                return (False, "❌ Invalid API key")
            
            if response.status_code == 429:
                return (False, "⚠️ Rate limited")
            
            if response.status_code != 200:
                return (False, f"❌ API error: {response.status_code}")
            
            data = response.json()
            
            if 'price' in data:
                return (True, f"✅ Twelve Data connected - XAU/USD @ ${float(data['price']):.2f}")
            else:
                return (False, f"⚠️ Unexpected response")
        
        except Exception as e:
            return (False, f"❌ Connection failed: {e}")
    
    def get_usage_stats(self) -> dict:
        """Get API usage stats"""
        global _api_call_count, _last_reset_date
        
        return {
            'calls_today': _api_call_count,
            'limit': MAX_DAILY_CALLS,
            'remaining': MAX_DAILY_CALLS - _api_call_count,
            'percentage': round((_api_call_count / MAX_DAILY_CALLS) * 100, 1),
            'date': _last_reset_date
        }
