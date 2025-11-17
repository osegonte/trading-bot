"""
PRODUCTION Trade verification with real-time monitoring
VERSION 2.0 - Enhanced with comprehensive error handling and timezone fix
"""
from datetime import datetime, timedelta
import pytz
import logging
from data.data_provider import get_ohlc_data
from config.config import VERIFICATION_WINDOW_BARS

logger = logging.getLogger(__name__)

def verify_trade_realtime(entry_time, direction, entry_price, sl_price, tp_price):
    """
    Verify trade outcome by checking which level hit first (REAL-TIME)
    
    Args:
        entry_time: datetime of entry (can be naive or aware)
        direction: "BUY" or "SELL"
        entry_price: entry price
        sl_price: stop loss price
        tp_price: take profit price
    
    Returns: 
        dict with result, exit_price, bars_to_hit, rr
    """
    try:
        # Step 1: Ensure entry_time is timezone-aware UTC
        if entry_time.tzinfo is None:
            entry_time_utc = pytz.UTC.localize(entry_time)
            logger.debug(f"Localized naive entry_time to UTC: {entry_time_utc}")
        else:
            entry_time_utc = entry_time.astimezone(pytz.UTC)
            logger.debug(f"Converted entry_time to UTC: {entry_time_utc}")
        
        # Step 2: Check if trade is expired
        now = datetime.now(pytz.UTC)
        time_since_entry = (now - entry_time_utc).total_seconds() / 60  # minutes
        
        if time_since_entry > VERIFICATION_WINDOW_BARS:
            logger.info(f"Trade expired ({time_since_entry:.0f} minutes > {VERIFICATION_WINDOW_BARS})")
            return {
                'result': 'EXPIRED',
                'exit_price': None,
                'bars': VERIFICATION_WINDOW_BARS,
                'rr': 0
            }
        
        # Step 3: Fetch OHLC data
        df = get_ohlc_data(period="5d", interval="1m", candles=200)
        
        if df is None or df.empty:
            logger.warning("Could not fetch data for verification - marking as PENDING")
            return {
                'result': 'PENDING',
                'exit_price': None,
                'bars': 0,
                'rr': 0
            }
        
        # Step 4: CRITICAL FIX - Ensure DataFrame index is timezone-aware
        if df.index.tz is None:
            # DataFrame has naive timestamps - make them UTC-aware
            df.index = df.index.tz_localize('UTC')
            logger.debug("Localized DataFrame index to UTC")
        elif str(df.index.tz) != 'UTC':
            # DataFrame has different timezone - convert to UTC
            df.index = df.index.tz_convert('UTC')
            logger.debug(f"Converted DataFrame index from {df.index.tz} to UTC")
        
        # Step 5: Filter data after entry time
        df_after_entry = df[df.index > entry_time_utc]
        
        if df_after_entry.empty:
            logger.info("No data yet after entry time - trade still PENDING")
            return {
                'result': 'PENDING',
                'exit_price': None,
                'bars': 0,
                'rr': 0
            }
        
        # Step 6: Check each candle for TP/SL hits
        for i, (idx, candle) in enumerate(df_after_entry.iterrows()):
            bars_elapsed = i + 1
            
            if direction == "BUY":
                # Check SL first (conservative assumption if both hit)
                if candle['Low'] <= sl_price:
                    # Check if same candle also hit TP (ambiguous case)
                    if candle['High'] >= tp_price:
                        logger.info(f"BUY: Both levels hit in bar {bars_elapsed} - assuming SL hit first (worst case)")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': bars_elapsed,
                            'rr': -1.0
                        }
                    else:
                        logger.info(f"BUY: SL hit at {sl_price} in {bars_elapsed} bars")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': bars_elapsed,
                            'rr': -1.0
                        }
                
                # Check TP
                if candle['High'] >= tp_price:
                    logger.info(f"BUY: TP hit at {tp_price} in {bars_elapsed} bars")
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': bars_elapsed,
                        'rr': 2.0
                    }
            
            else:  # SELL
                # Check SL first
                if candle['High'] >= sl_price:
                    # Check if same candle also hit TP
                    if candle['Low'] <= tp_price:
                        logger.info(f"SELL: Both levels hit in bar {bars_elapsed} - assuming SL hit first (worst case)")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': bars_elapsed,
                            'rr': -1.0
                        }
                    else:
                        logger.info(f"SELL: SL hit at {sl_price} in {bars_elapsed} bars")
                        return {
                            'result': 'LOSS',
                            'exit_price': sl_price,
                            'bars': bars_elapsed,
                            'rr': -1.0
                        }
                
                # Check TP
                if candle['Low'] <= tp_price:
                    logger.info(f"SELL: TP hit at {tp_price} in {bars_elapsed} bars")
                    return {
                        'result': 'WIN',
                        'exit_price': tp_price,
                        'bars': bars_elapsed,
                        'rr': 2.0
                    }
        
        # Step 7: Neither level hit yet - still PENDING
        bars_elapsed = len(df_after_entry)
        logger.info(f"Trade still PENDING ({bars_elapsed} bars elapsed, {time_since_entry:.0f} min since entry)")
        return {
            'result': 'PENDING',
            'exit_price': None,
            'bars': bars_elapsed,
            'rr': 0
        }
    
    except Exception as e:
        logger.error(f"❌ Verification error: {e}", exc_info=True)
        return {
            'result': 'ERROR',
            'exit_price': None,
            'bars': 0,
            'rr': 0,
            'error': str(e)
        }


def verify_trade(entry_time, direction, entry_price, sl_price, tp_price):
    """
    Legacy function for backward compatibility
    Redirects to real-time version
    """
    return verify_trade_realtime(entry_time, direction, entry_price, sl_price, tp_price)