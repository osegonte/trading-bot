# Price/OHLC fetcher with better error handling
import yfinance as yf
import pandas as pd
import time

def get_xauusd_price():
    """Fetches the latest XAU/USD price"""
    tickers_to_try = [
        ("GC=F", "Gold Futures"),
        ("XAUUSD=X", "Gold Spot"),
        ("GLD", "Gold ETF")
    ]
    
    for ticker_symbol, name in tickers_to_try:
        for attempt in range(3):  # Try 3 times
            try:
                print(f"Trying {name} ({ticker_symbol}), attempt {attempt + 1}...")
                ticker = yf.Ticker(ticker_symbol)
                
                # Try different periods
                for period in ["1d", "5d", "1mo"]:
                    try:
                        data = ticker.history(period=period, interval="1m")
                        
                        if not data.empty:
                            price = round(data['Close'].iloc[-1], 2)
                            print(f"✅ Got price from {name}: {price}")
                            return price
                    except:
                        continue
                
                time.sleep(2)  # Wait before retry
            
            except Exception as e:
                print(f"⚠️ {name} attempt {attempt + 1} failed: {e}")
                time.sleep(2)
                continue
    
    return None


def get_ohlc_data(period="5d", interval="1m", candles=100):
    """Fetches OHLC data with retry logic"""
    tickers_to_try = [
        ("GC=F", "Gold Futures"),
        ("XAUUSD=X", "Gold Spot")
    ]
    
    for ticker_symbol, name in tickers_to_try:
        for attempt in range(3):
            try:
                print(f"Fetching OHLC from {name} ({ticker_symbol}), attempt {attempt + 1}...")
                ticker = yf.Ticker(ticker_symbol)
                
                # Try different periods
                for p in [period, "1d", "5d"]:
                    try:
                        data = ticker.history(period=p, interval=interval)
                        
                        if not data.empty and len(data) >= 20:
                            print(f"✅ Got {len(data)} candles from {name}")
                            return data.tail(candles)
                    except:
                        continue
                
                time.sleep(2)
            
            except Exception as e:
                print(f"⚠️ {name} OHLC attempt {attempt + 1} failed: {e}")
                time.sleep(2)
                continue
    
    return None


def fetch_macro_data():
    """Fetch macro data with error handling"""
    from config import MACRO_TICKERS
    from signals.macro import analyze_trend
    
    result = {
        'dxy_signal': 0,
        'yield_signal': 0,
        'risk_signal': 0,
        'dxy_explanation': 'N/A',
        'yield_explanation': 'N/A',
        'risk_explanation': 'N/A'
    }
    
    # Try DXY with retries
    for attempt in range(2):
        try:
            dxy_ticker = yf.Ticker(MACRO_TICKERS['DXY'])
            dxy_data = dxy_ticker.history(period="1d", interval="15m")
            
            if not dxy_data.empty and len(dxy_data) >= 6:
                dxy_trend = analyze_trend(dxy_data['Close'])
                if dxy_trend > 0:
                    result['dxy_signal'] = -1
                    result['dxy_explanation'] = "DXY rising (bearish)"
                elif dxy_trend < 0:
                    result['dxy_signal'] = 1
                    result['dxy_explanation'] = "DXY falling (bullish)"
                else:
                    result['dxy_explanation'] = "DXY flat"
                break
        except:
            if attempt == 0:
                time.sleep(2)
            else:
                result['dxy_explanation'] = "DXY unavailable"
    
    # Similar for yields and risk (simplified for space)
    return result