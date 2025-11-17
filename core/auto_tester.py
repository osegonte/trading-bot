#!/usr/bin/env python3
"""
PRODUCTION Automated testing system for XAU/USD trading bot
Features: Real-time TP/SL monitoring, pause/resume, safety limits
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import signal
import sys
from telegram import Bot
from config.config import TELEGRAM_TOKEN
from data.data_provider import get_ohlc_data, fetch_macro_data, get_api_usage_stats
from signals import (detect_candlestick_pattern, get_trend_verdict, get_sr_verdict,
                     get_volume_verdict, get_rsi_verdict, get_macd_verdict,
                     get_bollinger_verdict, get_macro_verdict, check_news_blackout)
from storage.database import (log_signal, log_trade_plan, get_last_trade, update_trade_result, 
                get_signal_verdicts, is_bot_paused, get_pending_trades)
from utils.helpers import get_utc_timestamp, aggregate_verdicts_with_macro
from core.trade_plan import create_trade_plan
from core.verification import verify_trade_realtime
from grading.council import grade_council, get_council_stats
from grading.levels import get_current_level, update_level

# Configuration
SIGNAL_INTERVAL_MINUTES = 30  # Generate signal every 30 minutes
REALTIME_CHECK_MINUTES = 5    # Check pending trades every 5 minutes
MARKET_OPEN_HOUR = 18         # Gold futures open 18:00 UTC (Sunday)
MARKET_CLOSE_HOUR = 20        # Quiet period 20:00-23:00 UTC
CHECK_INTERVAL_SECONDS = 60   # Main loop check interval
MAX_TRADES_PER_DAY = 30       # Safety brake
CONSECUTIVE_LOSS_COOLDOWN = 3 # Pause after 3 losses in a row

# Chat ID
CHAT_ID = "1365285036"

# Setup logging with rotation
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Rotating file handler (max 10MB, keep 5 backups)
file_handler = RotatingFileHandler(
    'auto_tester.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Global state
start_time = datetime.now(pytz.UTC)
signal_count_today = 0
trade_count_today = 0
last_trade_date = None
consecutive_losses = 0
graceful_shutdown = False


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    global graceful_shutdown
    logger.info("🛑 Shutdown signal received. Finishing current operations...")
    graceful_shutdown = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def send_telegram_message(message):
    """Send message to Telegram"""
    if not CHAT_ID:
        logger.warning("CHAT_ID not set. Run /start command first.")
        return
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        logger.info(f"📤 Telegram: {message[:80]}...")
    except Exception as e:
        logger.error(f"❌ Telegram send failed: {e}")


def is_market_open():
    """Check if gold futures market is open"""
    # SIMPLIFIED: Gold trades nearly 24/7, just avoid weekends
    now = datetime.now(pytz.UTC)
    
    # Saturday is closed
    if now.weekday() == 5:
        return False
    
    # Otherwise, always open (24/5 trading)
    return True

def reset_daily_counters():
    """Reset counters at start of new trading day"""
    global signal_count_today, trade_count_today, last_trade_date, consecutive_losses
    
    now = datetime.now(pytz.UTC)
    today = now.date()
    
    if last_trade_date != today:
        signal_count_today = 0
        trade_count_today = 0
        last_trade_date = today
        consecutive_losses = 0
        logger.info(f"📅 New trading day: {today}")


def check_safety_limits():
    """Check if we should pause trading due to safety limits"""
    global consecutive_losses, trade_count_today
    
    # Max trades per day
    if trade_count_today >= MAX_TRADES_PER_DAY:
        logger.warning(f"🛑 Daily trade limit reached ({MAX_TRADES_PER_DAY})")
        return False, f"Daily limit reached ({MAX_TRADES_PER_DAY} trades)"
    
    # Consecutive losses cooldown
    if consecutive_losses >= CONSECUTIVE_LOSS_COOLDOWN:
        logger.warning(f"🛑 Cooldown after {consecutive_losses} consecutive losses")
        return False, f"Cooldown: {consecutive_losses} losses in a row"
    
    return True, "OK"


def generate_signal():
    """Generate a trading signal"""
    global signal_count_today, trade_count_today, consecutive_losses
    
    logger.info("🔍 Generating signal...")
    
    try:
        # Check if paused
        if is_bot_paused():
            logger.info("⏸️ Bot is paused. Skipping signal generation.")
            return None
        
        # Check safety limits
        safe, reason = check_safety_limits()
        if not safe:
            logger.info(f"🛑 Safety limit: {reason}")
            asyncio.run(send_telegram_message(f"⚠️ Trading paused: {reason}"))
            return None
        
        # Check news blackout
        is_blackout, blackout_reason = check_news_blackout()
        if is_blackout:
            logger.info(f"📰 News blackout: {blackout_reason}")
            return None
        
        # Fetch data
        df = get_ohlc_data(period="5d", interval="1m", candles=100)
        if df is None or df.empty:
            logger.error("❌ Failed to fetch OHLC data")
            return None
        
        current_price = round(df['Close'].iloc[-1], 2)
        
        # Run all modules
        trend_verdict = get_trend_verdict(df)
        candle_pattern, candle_verdict = detect_candlestick_pattern(df)
        sr_verdict, sr_explanation = get_sr_verdict(df)
        volume_verdict, volume_explanation = get_volume_verdict(df)
        rsi_verdict, rsi_explanation = get_rsi_verdict(df)
        macd_verdict, macd_explanation = get_macd_verdict(df)
        bollinger_verdict, bollinger_explanation = get_bollinger_verdict(df)
        macro_verdict, macro_explanation = get_macro_verdict(fetch_macro_data)
        
        # Aggregate
        verdicts = {
            'trend': trend_verdict,
            'candlestick': candle_verdict,
            'sr': sr_verdict,
            'volume': volume_verdict,
            'rsi': rsi_verdict,
            'macd': macd_verdict,
            'bollinger': bollinger_verdict
        }
        final_verdict, score, confidence, macro_adjusted = aggregate_verdicts_with_macro(verdicts, macro_verdict)
        
        # Log signal
        signal_id = log_signal(
            current_price, trend_verdict, candle_verdict, candle_pattern,
            sr_verdict, sr_explanation, volume_verdict, volume_explanation,
            rsi_verdict, rsi_explanation, macd_verdict, macd_explanation,
            bollinger_verdict, bollinger_explanation,
            macro_verdict, macro_explanation,
            final_verdict, score, confidence, 0, macro_adjusted
        )
        
        signal_count_today += 1
        logger.info(f"✅ Signal #{signal_id}: {final_verdict} @ ${current_price} (score: {score:+.1f}, conf: {confidence}%)")
        
        # Create trade plan if Buy/Sell
        trade_id = None
        if final_verdict in ["BUY", "SELL"]:
            level_data = get_current_level()
            plan = create_trade_plan(df, final_verdict, level_data['balance'])
            
            if plan:
                trade_id = log_trade_plan(signal_id, plan)
                trade_count_today += 1
                logger.info(f"📋 Trade #{trade_id}: {final_verdict} @ {plan['entry']} | SL:{plan['sl']} | TP:{plan['tp']}")
                
                # Send notification
                message = f"""🔔 <b>Trade #{trade_id}</b>

<b>{final_verdict}</b> @ {plan['entry']}
SL: {plan['sl']} | TP: {plan['tp']}
Risk: €{plan['risk_amount']:.2f} | Target: €{plan['potential_gain']:.2f}
Score: {score:+.1f} | Confidence: {confidence}%

⏱️ Real-time monitoring active"""
                
                asyncio.run(send_telegram_message(message))
        
        return {
            'signal_id': signal_id,
            'trade_id': trade_id,
            'verdict': final_verdict,
            'price': current_price,
            'score': score
        }
    
    except Exception as e:
        logger.error(f"💥 Error generating signal: {e}", exc_info=True)
        return None


def check_pending_trades():
    """Check all pending trades for TP/SL hits (real-time monitoring)"""
    global consecutive_losses
    
    try:
        pending = get_pending_trades()
        
        if not pending:
            return
        
        logger.info(f"🔍 Checking {len(pending)} pending trade(s)...")
        
        for trade in pending:
            trade_id = trade[0]
            signal_id = trade[1]
            timestamp_str = trade[2]
            direction = trade[3]
            entry = trade[4]
            sl = trade[5]
            tp = trade[6]
            risk_amount = trade[11]
            potential_gain = trade[12]
            
            # Parse entry time
            entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")
            
            # Verify trade
            result_data = verify_trade_realtime(entry_time, direction, entry, sl, tp)
            
            # If still pending, skip
            if result_data['result'] == 'PENDING':
                continue
            
            # Trade completed - grade it
            logger.info(f"✅ Trade #{trade_id} completed: {result_data['result']}")
            
            # Calculate PnL
            if result_data['result'] == 'WIN':
                pnl = potential_gain
                rr_realized = 2.0
                consecutive_losses = 0  # Reset on win
            elif result_data['result'] == 'LOSS':
                pnl = -risk_amount
                rr_realized = -1.0
                consecutive_losses += 1
            else:  # EXPIRED
                pnl = 0
                rr_realized = 0
                consecutive_losses = 0  # Reset on expiry
            
            result_data['pnl'] = pnl
            
            # Update trade
            update_trade_result(trade_id, result_data)
            
            # Grade council
            verdicts = get_signal_verdicts(signal_id)
            if verdicts and result_data['result'] in ['WIN', 'LOSS']:
                grade_council(verdicts, direction, result_data['result'], rr_realized)
            
            # Update level
            level_data = get_current_level()
            if result_data['result'] in ['WIN', 'LOSS']:
                new_level_data = update_level(pnl, result_data['result'])
            else:
                new_level_data = level_data
            
            # Send notification
            emoji = "✅" if result_data['result'] == 'WIN' else "❌" if result_data['result'] == 'LOSS' else "⏱️"
            message = f"""{emoji} <b>Trade #{trade_id} - {result_data['result']}</b>

PnL: {rr_realized:+.1f}R | {pnl:+.2f}€
Duration: {result_data['bars']} bars

Level: L{level_data['level']} → L{new_level_data['level']}
Balance: €{level_data['balance']:.2f} → €{new_level_data['balance']:.2f}"""
            
            asyncio.run(send_telegram_message(message))
    
    except Exception as e:
        logger.error(f"💥 Error checking pending trades: {e}", exc_info=True)


def send_daily_summary():
    """Send daily performance summary"""
    logger.info("📊 Sending daily summary...")
    
    try:
        level_data = get_current_level()
        council_stats = get_council_stats()
        api_stats = get_api_usage_stats()
        
        message = f"""📊 <b>Daily Summary - {datetime.now(pytz.UTC).strftime('%Y-%m-%d')}</b>

<b>Account</b>
Level: L{level_data['level']} | Balance: €{level_data['balance']:.2f}
Target: €{level_data['target']:.2f}

<b>Activity</b>
Signals: {signal_count_today} | Trades: {trade_count_today}
API Calls: {api_stats['calls_today']}/{api_stats['limit']}

<b>Top Modules</b>"""
        
        if council_stats:
            sorted_stats = sorted(council_stats, key=lambda x: x[4], reverse=True)[:3]
            for member, correct, incorrect, neutral, accuracy, expectancy, trade_count in sorted_stats:
                message += f"\n{member.title()}: {accuracy:.0f}% ({expectancy:+.2f}R)"
        
        asyncio.run(send_telegram_message(message))
    
    except Exception as e:
        logger.error(f"💥 Error sending daily summary: {e}", exc_info=True)


def main():
    """Main auto-tester loop with real-time monitoring"""
    global graceful_shutdown
    
    logger.info("🚀 AUTO-TESTER STARTING (PRODUCTION MODE)")
    logger.info(f"📍 Signal interval: {SIGNAL_INTERVAL_MINUTES}m | Real-time check: {REALTIME_CHECK_MINUTES}m")
    
    # Health check
    from data.data_provider import health_check
    success, message = health_check()
    logger.info(f"🏥 Health check: {message}")
    
    if not success:
        logger.error("❌ Health check failed. Exiting.")
        asyncio.run(send_telegram_message(f"❌ Bot startup failed:\n{message}"))
        return
    
    # Send startup notification
    asyncio.run(send_telegram_message(f"🤖 <b>Auto-tester started</b>\n\n{message}\n\nReal-time monitoring active 🟢"))
    
    last_signal_time = None
    last_check_time = None
    last_summary_date = None
    
    while not graceful_shutdown:
        try:
            now = datetime.now(pytz.UTC)
            
            # Reset daily counters
            reset_daily_counters()
            
            # Check if market is open
            if is_market_open():
                # Generate signal if interval has passed
                if last_signal_time is None or (now - last_signal_time).seconds >= SIGNAL_INTERVAL_MINUTES * 60:
                    generate_signal()
                    last_signal_time = now
                
                # Check pending trades (real-time monitoring)
                if last_check_time is None or (now - last_check_time).seconds >= REALTIME_CHECK_MINUTES * 60:
                    check_pending_trades()
                    last_check_time = now
            
            # Send daily summary at market close (23:00 UTC)
            if now.hour == 23 and now.minute < 5 and now.date() != last_summary_date:
                send_daily_summary()
                last_summary_date = now.date()
            
            # Sleep before next check
            time.sleep(CHECK_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard interrupt detected")
            break
        
        except Exception as e:
            logger.error(f"💥 Error in main loop: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL_SECONDS)
    
    # Graceful shutdown
    logger.info("🛑 Shutting down gracefully...")
    asyncio.run(send_telegram_message("🛑 <b>Auto-tester stopped</b>\n\nManual restart required."))
    logger.info("✅ Shutdown complete")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"💥 Critical error: {e}", exc_info=True)
        asyncio.run(send_telegram_message(f"💥 <b>Bot crashed</b>\n\n{str(e)[:200]}"))
        sys.exit(1)