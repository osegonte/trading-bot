#!/usr/bin/env python3
"""
Automated testing system for XAU/USD trading bot
Runs signals, grades trades, and reports performance
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from telegram import Bot
from config import TELEGRAM_TOKEN
from data_twelve import get_ohlc_data, fetch_macro_data
from signals import (detect_candlestick_pattern, get_trend_verdict, get_sr_verdict,
                     get_volume_verdict, get_rsi_verdict, get_macd_verdict,
                     get_bollinger_verdict, get_macro_verdict, check_news_blackout)
from db import log_signal, log_trade_plan, get_last_trade, update_trade_result, get_signal_verdicts
from utils import get_utc_timestamp, aggregate_verdicts_with_macro
from trade_plan import create_trade_plan
from verification import verify_trade
from council import grade_council, get_council_stats
from levels import get_current_level, update_level

# Configuration
SIGNAL_INTERVAL_MINUTES = 30  # Generate signal every 30 minutes
AUTO_GRADE_DELAY_HOURS = 2    # Grade trades after 2 hours
MARKET_OPEN_HOUR = 13         # Gold futures open 13:30 UTC (Sunday evening)
MARKET_CLOSE_HOUR = 20        # Gold futures close 20:00 UTC
CHECK_INTERVAL_SECONDS = 60   # Check every minute

# Your Telegram chat ID (get from @userinfobot)
CHAT_ID = "1365285036"  # Will be set from first message or command

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_tester.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Track pending trades for auto-grading
pending_trades = []


def is_market_open():
    """Check if gold futures market is open"""
    now = datetime.now(pytz.UTC)
    
    # Weekend check (Saturday is closed, Sunday opens evening)
    if now.weekday() == 5:  # Saturday
        return False
    
    # Gold futures trade nearly 24 hours, but we'll focus on active hours
    # Sunday 18:00 UTC - Friday 17:00 UTC (with daily breaks)
    
    # Simple check: open Mon-Fri during core hours
    if now.weekday() < 5:  # Monday-Friday
        if MARKET_OPEN_HOUR <= now.hour < MARKET_CLOSE_HOUR:
            return True
    
    # Sunday evening opening
    if now.weekday() == 6 and now.hour >= 18:  # Sunday 18:00+ UTC
        return True
    
    return False


async def send_telegram_message(message):
    """Send message to Telegram"""
    global CHAT_ID
    
    if not CHAT_ID:
        logger.warning("CHAT_ID not set. Run /start command first.")
        return
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message)
        logger.info(f"Sent Telegram message: {message[:50]}...")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


def generate_signal():
    """Generate a trading signal"""
    logger.info("Generating signal...")
    
    try:
        # Check news blackout
        is_blackout, blackout_reason = check_news_blackout()
        if is_blackout:
            logger.info(f"Skipping signal: {blackout_reason}")
            return None
        
        # Fetch data
        df = get_ohlc_data(period="5d", interval="1m", candles=100)
        if df is None or df.empty:
            logger.error("Failed to fetch OHLC data")
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
        
        logger.info(f"Signal #{signal_id}: {final_verdict} @ {current_price} (score: {score})")
        
        # Create trade plan if Buy/Sell
        trade_id = None
        if final_verdict in ["BUY", "SELL"]:
            level_data = get_current_level()
            plan = create_trade_plan(df, final_verdict, level_data['balance'])
            
            if plan:
                trade_id = log_trade_plan(signal_id, plan)
                logger.info(f"Trade #{trade_id} created: {final_verdict} @ {plan['entry']} SL:{plan['sl']} TP:{plan['tp']}")
                
                # Add to pending trades for auto-grading
                grade_time = datetime.now(pytz.UTC) + timedelta(hours=AUTO_GRADE_DELAY_HOURS)
                pending_trades.append({
                    'trade_id': trade_id,
                    'signal_id': signal_id,
                    'grade_time': grade_time,
                    'direction': final_verdict
                })
                
                # Send notification
                message = f"""🔔 New Trade #{trade_id}

Direction: {final_verdict}
Entry: {plan['entry']} | SL: {plan['sl']} | TP: {plan['tp']}
Risk: €{plan['risk_amount']} | Target: €{plan['potential_gain']}
Score: {score:+.1f} | Confidence: {confidence}%

Will auto-grade in {AUTO_GRADE_DELAY_HOURS} hours."""
                
                asyncio.run(send_telegram_message(message))
        
        return {
            'signal_id': signal_id,
            'trade_id': trade_id,
            'verdict': final_verdict,
            'price': current_price,
            'score': score
        }
    
    except Exception as e:
        logger.error(f"Error generating signal: {e}", exc_info=True)
        return None


def grade_trade(trade_info):
    """Grade a pending trade"""
    trade_id = trade_info['trade_id']
    signal_id = trade_info['signal_id']
    direction = trade_info['direction']
    
    logger.info(f"Grading trade #{trade_id}...")
    
    try:
        # Get trade data
        trade_data = get_last_trade()
        if not trade_data or trade_data[0] != trade_id:
            logger.error(f"Trade #{trade_id} not found")
            return
        
        timestamp_str = trade_data[2]
        entry = trade_data[4]
        sl = trade_data[5]
        tp = trade_data[6]
        lots = trade_data[7]
        stop_pips = trade_data[8]
        tp_pips = trade_data[9]
        rr_target = trade_data[10]
        risk_amount = trade_data[11]
        potential_gain = trade_data[12]
        
        # Check if already graded
        if trade_data[13]:
            logger.info(f"Trade #{trade_id} already graded: {trade_data[13]}")
            return
        
        # Verify trade
        entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")
        result_data = verify_trade(entry_time, direction, entry, sl, tp)
        
        # Calculate PnL
        if result_data['result'] == 'WIN':
            pnl = potential_gain
            rr_realized = rr_target
        elif result_data['result'] == 'LOSS':
            pnl = -risk_amount
            rr_realized = -1.0
        else:  # EXPIRED
            pnl = 0
            rr_realized = 0
        
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
        
        logger.info(f"Trade #{trade_id} graded: {result_data['result']} ({rr_realized:+.1f}R)")
        
        # Send notification
        emoji = "✅" if result_data['result'] == 'WIN' else "❌" if result_data['result'] == 'LOSS' else "⏱️"
        message = f"""{emoji} Trade #{trade_id} Result: {result_data['result']}

PnL: {rr_realized:+.1f}R | {pnl:+.2f}€
Hit in: {result_data['bars']} bars

Level: L{level_data['level']} → L{new_level_data['level']}
Balance: €{level_data['balance']:.2f} → €{new_level_data['balance']:.2f}
"""
        
        asyncio.run(send_telegram_message(message))
    
    except Exception as e:
        logger.error(f"Error grading trade #{trade_id}: {e}", exc_info=True)


def send_daily_summary():
    """Send daily performance summary"""
    logger.info("Sending daily summary...")
    
    try:
        level_data = get_current_level()
        council_stats = get_council_stats()
        
        message = f"""📊 Daily Summary - {datetime.now(pytz.UTC).strftime('%Y-%m-%d')}

Level: L{level_data['level']}
Balance: €{level_data['balance']:.2f}
Target: €{level_data['target']:.2f}

Top 3 Modules:
"""
        
        if council_stats:
            sorted_stats = sorted(council_stats, key=lambda x: x[4], reverse=True)[:3]
            for member, correct, incorrect, neutral, accuracy, expectancy, trade_count in sorted_stats:
                message += f"- {member.title()}: {accuracy:.1f}% ({expectancy:+.2f}R)\n"
        
        asyncio.run(send_telegram_message(message))
    
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}", exc_info=True)


def main():
    """Main auto-tester loop"""
    logger.info("🚀 Auto-tester starting...")
    
    # Send startup notification
    asyncio.run(send_telegram_message("🤖 Auto-tester started. Monitoring markets..."))
    
    last_signal_time = None
    last_summary_date = None
    
    while True:
        try:
            now = datetime.now(pytz.UTC)
            
            # Check if market is open
            if is_market_open():
                # Generate signal if interval has passed
                if last_signal_time is None or (now - last_signal_time).seconds >= SIGNAL_INTERVAL_MINUTES * 60:
                    generate_signal()
                    last_signal_time = now
                
                # Check for trades to grade
                for trade_info in pending_trades[:]:
                    if now >= trade_info['grade_time']:
                        grade_trade(trade_info)
                        pending_trades.remove(trade_info)
            
            # Send daily summary at market close
            if now.hour == MARKET_CLOSE_HOUR and now.date() != last_summary_date:
                send_daily_summary()
                last_summary_date = now.date()
            
            # Sleep before next check
            time.sleep(CHECK_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            asyncio.run(send_telegram_message("🛑 Auto-tester stopped."))
            break
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()