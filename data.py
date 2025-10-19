# Price/OHLC fetcher
import yfinance as yf
from config import MACRO_TICKERS, MACRO_LOOKBACK_MIN
from signals.macro import analyze_trend

def get_xauusd_price():
    """Fetches the latest XAU/USD price"""
    tickers_to_try = ["GC=F", "XAUUSD=X", "GLD"]
    
    for ticker_symbol in tickers_to_try:
        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period="5d", interval="1m")
            
            if not data.empty:
                return round(data['Close'].iloc[-1], 2)
        except Exception:
            continue
    
    return None

def get_ohlc_data(period="5d", interval="1m", candles=100):
    """Fetches OHLC data for XAU/USD"""
    tickers_to_try = ["GC=F", "XAUUSD=X"]
    
    for ticker_symbol in tickers_to_try:
        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period=period, interval=interval)
            
            if not data.empty:
                return data.tail(candles)
        except Exception as e:
            print(f"Failed to fetch OHLC from {ticker_symbol}: {e}")
            continue
    
    return None

def fetch_macro_data():
    """
    Fetch macro sentiment data (DXY, yields, risk tone)
    Returns: dict with signals and explanations
    """
    result = {
        'dxy_signal': 0,
        'yield_signal': 0,
        'risk_signal': 0,
        'dxy_explanation': 'N/A',
        'yield_explanation': 'N/A',
        'risk_explanation': 'N/A'
    }
    
    try:
        # Fetch DXY (Dollar Index)
        dxy_ticker = yf.Ticker(MACRO_TICKERS['DXY'])
        dxy_data = dxy_ticker.history(period="1d", interval="15m")
        
        if not dxy_data.empty and len(dxy_data) >= 6:
            dxy_trend = analyze_trend(dxy_data['Close'])
            if dxy_trend > 0:
                result['dxy_signal'] = -1  # DXY up = bearish for gold
                result['dxy_explanation'] = "DXY rising (bearish)"
            elif dxy_trend < 0:
                result['dxy_signal'] = 1   # DXY down = bullish for gold
                result['dxy_explanation'] = "DXY falling (bullish)"
            else:
                result['dxy_explanation'] = "DXY flat"
    except Exception as e:
        result['dxy_explanation'] = f"DXY error: {str(e)[:30]}"
    
    try:
        # Fetch US 10Y Yield
        yield_ticker = yf.Ticker(MACRO_TICKERS['US10Y'])
        yield_data = yield_ticker.history(period="1d", interval="15m")
        
        if not yield_data.empty and len(yield_data) >= 6:
            yield_trend = analyze_trend(yield_data['Close'])
            if yield_trend > 0:
                result['yield_signal'] = -1  # Yields up = bearish for gold
                result['yield_explanation'] = "Yields rising (bearish)"
            elif yield_trend < 0:
                result['yield_signal'] = 1   # Yields down = bullish for gold
                result['yield_explanation'] = "Yields falling (bullish)"
            else:
                result['yield_explanation'] = "Yields flat"
    except Exception as e:
        result['yield_explanation'] = f"Yield error: {str(e)[:30]}"
    
    try:
        # Fetch risk tone (S&P 500 or VIX)
        spx_ticker = yf.Ticker(MACRO_TICKERS['SPX'])
        spx_data = spx_ticker.history(period="1d", interval="15m")
        
        if not spx_data.empty and len(spx_data) >= 6:
            spx_trend = analyze_trend(spx_data['Close'])
            if spx_trend < 0:
                result['risk_signal'] = 1  # Stocks down = risk-off = bullish for gold
                result['risk_explanation'] = "Risk-off (stocks down, bullish)"
            elif spx_trend > 0:
                result['risk_signal'] = -1  # Stocks up = risk-on = bearish for gold
                result['risk_explanation'] = "Risk-on (stocks up, bearish)"
            else:
                result['risk_explanation'] = "Risk neutral"
    except Exception as e:
        result['risk_explanation'] = f"Risk error: {str(e)[:30]}"
    
    return result