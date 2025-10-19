# Macro sentiment analysis
import pandas as pd
from datetime import datetime, timedelta

# Simple cache to avoid rate limits
_macro_cache = {}
_cache_timestamp = None

def get_macro_verdict(data_fetcher, cache_seconds=60):
    """
    Analyze macro sentiment from DXY, yields, and risk tone
    Args:
        data_fetcher: function that fetches macro data
        cache_seconds: how long to cache results
    Returns: tuple (verdict, explanation_dict)
    """
    global _macro_cache, _cache_timestamp
    
    # Check cache
    now = datetime.utcnow()
    if _cache_timestamp and (now - _cache_timestamp).seconds < cache_seconds:
        if _macro_cache:
            return _macro_cache.get('verdict'), _macro_cache.get('explanation')
    
    try:
        # Fetch macro data
        macro_data = data_fetcher()
        
        if not macro_data:
            return ("NEUTRAL", {"error": "No macro data available"})
        
        dxy_signal = macro_data.get('dxy_signal', 0)
        yield_signal = macro_data.get('yield_signal', 0)
        risk_signal = macro_data.get('risk_signal', 0)
        
        # Calculate macro score
        macro_score = dxy_signal + yield_signal + risk_signal
        
        # Determine verdict
        if macro_score >= 1:
            verdict = "BUY"
        elif macro_score <= -1:
            verdict = "SELL"
        else:
            verdict = "NEUTRAL"
        
        explanation = {
            'dxy': macro_data.get('dxy_explanation', 'N/A'),
            'yield': macro_data.get('yield_explanation', 'N/A'),
            'risk': macro_data.get('risk_explanation', 'N/A'),
            'score': macro_score
        }
        
        # Update cache
        _macro_cache = {'verdict': verdict, 'explanation': explanation}
        _cache_timestamp = now
        
        return verdict, explanation
    
    except Exception as e:
        return ("NEUTRAL", {"error": f"Macro analysis failed: {str(e)}"})

def analyze_trend(prices, lookback=3):
    """
    Simple trend analysis: compare recent prices to older prices
    Returns: 1 (rising), -1 (falling), 0 (flat)
    """
    if len(prices) < lookback * 2:
        return 0
    
    recent = prices[-lookback:].mean()
    older = prices[-lookback*2:-lookback].mean()
    
    if recent > older * 1.002:  # Rising by 0.2%+
        return 1
    elif recent < older * 0.998:  # Falling by 0.2%+
        return -1
    else:
        return 0