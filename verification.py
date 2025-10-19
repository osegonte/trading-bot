# Trade verification from OHLC data
import yfinance as yf
from datetime import datetime, timedelta
from config import VERIFICATION_WINDOW_BARS, SYMBOL_DEFAULT

def verify_trade(entry_time, direction, entry_price, sl_price, tp_price):
    """
    Verify trade outcome by checking which level hit first
    Args:
        entry_time: datetime of entry
        direction: "BUY" or "SELL"
        entry_price: entry price
        sl_price: stop loss price
        tp_price: take profit price
    Returns: dict with result, exit_price, bars_to_hit
    """
    try:
        # Fetch OHLC from entry time forward
        ticker = yf.Ticker(SYMBOL_DEFAULT)
        
        # Get data for verification window
        start_time = entry_time
        end_time = entry_time + timedelta(minutes=VERIFICATION_WINDOW_BARS)
        
        data = ticker.history(start=start_time, end=end_time, interval="1m")
        
        if data.empty:
            return {'result': 'EXPIRED', 'exit_price': None, 'bars': 0, 'rr': 0}
        
        # Check each candle
        for i, (idx, candle) in enumerate(data.iterrows()):
            if direction == "BUY":
                # Check if SL hit first (low <= sl)
                if candle['Low'] <= sl_price:
                    # Check if same candle also hit TP
                    if candle['High'] >= tp_price:
                        # Same bar ambiguity - assume worst case (SL first)
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                    else:
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                
                # Check if TP hit (high >= tp)
                if candle['High'] >= tp_price:
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': i + 1,
                        'rr': 2.0  # Based on RR_TARGET
                    }
            
            else:  # SELL
                # Check if SL hit first (high >= sl)
                if candle['High'] >= sl_price:
                    if candle['Low'] <= tp_price:
                        # Same bar ambiguity - worst case
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                    else:
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                
                # Check if TP hit (low <= tp)
                if candle['Low'] <= tp_price:
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': i + 1,
                        'rr': 2.0
                    }
        
        # Neither hit within window
        return {'result': 'EXPIRED', 'exit_price': None, 'bars': VERIFICATION_WINDOW_BARS, 'rr': 0}
    
    except Exception as e:
        print(f"Verification error: {e}")
        return {'result': 'ERROR', 'exit_price': None, 'bars': 0, 'rr': 0}