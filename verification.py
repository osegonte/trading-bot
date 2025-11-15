"""
PRODUCTION Trade verification with real-time monitoring
FIXED: Proper timezone handling for pandas DataFrame comparison
"""
from datetime import datetime, timedelta
import pytz
import logging
from data_twelve import get_ohlc_data
from config import VERIFICATION_WINDOW_BARS

logger = logging.getLogger(__name__)

def verify_trade_realtime(entry_time, direction, entry_price, sl_price, tp_price):
    """
    Verify trade outcome by checking which level hit first (REAL-TIME)
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
        now = datetime.now(pytz.UTC)
        
        # Ensure entry_time is timezone-aware
        if entry_time.tzinfo is None:
            entry_time_utc = pytz.UTC.localize(entry_time)
        else:
            entry_time_utc = entry_time
        
        # Check if trade is too old (expired after 2 hours)
        time_since_entry = (now - entry_time_utc).total_seconds() / 60  # minutes
        
        if time_since_entry > VERIFICATION_WINDOW_BARS:
            logger.info(f"Trade expired ({time_since_entry:.0f} minutes > {VERIFICATION_WINDOW_BARS})")
            return {
                'result': 'EXPIRED',
                'exit_price': None,
                'bars': VERIFICATION_WINDOW_BARS,
                'rr': 0
            }
        
        # Fetch data from entry time to now
        df = get_ohlc_data(period="5d", interval="1m", candles=200)
        
        if df is None or df.empty:
            logger.warning("Could not fetch data for verification")
            return {
                'result': 'PENDING',
                'exit_price': None,
                'bars': 0,
                'rr': 0
            }
        
        # CRITICAL FIX: Ensure DataFrame index is timezone-aware for comparison
        # This prevents the "Invalid comparison between dtype=datetime64[ns] and datetime" error
        if df.index.tz is None:
            # DataFrame has naive timestamps - make them UTC-aware
            df.index = df.index.tz_localize('UTC')
        elif str(df.index.tz) != 'UTC':
            # DataFrame has different timezone - convert to UTC
            df.index = df.index.tz_convert('UTC')
        
        # Now both are timezone-aware UTC - comparison will work
        df_after_entry = df[df.index > entry_time_utc]
        
        if df_after_entry.empty:
            logger.info("No data yet after entry time - trade still pending")
            return {
                'result': 'PENDING',
                'exit_price': None,
                'bars': 0,
                'rr': 0
            }
        
        # Check each candle
        for i, (idx, candle) in enumerate(df_after_entry.iterrows()):
            if direction == "BUY":
                # Check if SL hit first (low <= sl)
                if candle['Low'] <= sl_price:
                    # Check if same candle also hit TP
                    if candle['High'] >= tp_price:
                        # Same bar ambiguity - assume worst case (SL first)
                        logger.info(f"BUY: Both levels hit in same bar - assuming SL")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                    else:
                        logger.info(f"BUY: SL hit at {sl_price} in {i+1} bars")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                
                # Check if TP hit (high >= tp)
                if candle['High'] >= tp_price:
                    logger.info(f"BUY: TP hit at {tp_price} in {i+1} bars")
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': i + 1,
                        'rr': 2.0
                    }
            
            else:  # SELL
                # Check if SL hit first (high >= sl)
                if candle['High'] >= sl_price:
                    if candle['Low'] <= tp_price:
                        # Same bar ambiguity - worst case
                        logger.info(f"SELL: Both levels hit in same bar - assuming SL")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                    else:
                        logger.info(f"SELL: SL hit at {sl_price} in {i+1} bars")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': i + 1,
                            'rr': -1.0
                        }
                
                # Check if TP hit (low <= tp)
                if candle['Low'] <= tp_price:
                    logger.info(f"SELL: TP hit at {tp_price} in {i+1} bars")
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': i + 1,
                        'rr': 2.0
                    }
        
        # Neither hit yet - still pending
        bars_elapsed = len(df_after_entry)
        logger.info(f"Trade still pending ({bars_elapsed} bars elapsed)")
        return {
            'result': 'PENDING',
            'exit_price': None,
            'bars': bars_elapsed,
            'rr': 0
        }
    
    except Exception as e:
        logger.error(f"Verification error: {e}", exc_info=True)
        return {
            'result': 'ERROR',
            'exit_price': None,
            'bars': 0,
            'rr': 0
        }


# Keep old function for backward compatibility
def verify_trade(entry_time, direction, entry_price, sl_price, tp_price):
    """Legacy function - redirects to real-time version"""
    return verify_trade_realtime(entry_time, direction, entry_price, sl_price, tp_price)