#!/usr/bin/env python3
"""
PRODUCTION Telegram bot handler with enhanced commands
New: /status, /pause, /resume, /quota
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import pytz

from config.config import TELEGRAM_TOKEN, RISK_MODE
from data.data_provider import get_xauusd_price, get_ohlc_data, fetch_macro_data, get_api_usage_stats, health_check
from signals import (detect_candlestick_pattern, get_trend_verdict, get_sr_verdict, 
                     get_volume_verdict, get_rsi_verdict, get_macd_verdict, 
                     get_bollinger_verdict, get_macro_verdict, check_news_blackout)
from storage.database import (log_signal, log_trade_plan, update_trade_result, get_last_trade, 
                get_trade_by_id, get_signal_verdicts, get_stats, set_bot_paused,
                is_bot_paused, get_pending_trades, get_bot_start_time)
from utils.helpers import get_utc_timestamp, format_verdict, calculate_percentage, aggregate_verdicts_with_macro
from core.trade_plan import create_trade_plan
from core.verification import verify_trade_realtime
from grading.council import grade_council, get_council_stats
from grading.levels import get_current_level, update_level

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    await update.message.reply_text(
        "🤖 <b>XAU/USD Trading Bot - PRODUCTION</b>\n\n"
        "<b>Market Commands:</b>\n"
        "/price - Current XAU/USD price\n"
        "/signal - Generate analysis + trade plan\n"
        "/macro - Macro sentiment snapshot\n\n"
        "<b>Trading Commands:</b>\n"
        "/plan - View latest trade plan\n"
        "/grade - Verify & grade last trade\n"
        "/pending - View pending trades\n\n"
        "<b>Control Commands:</b>\n"
        "/status - Bot health & statistics\n"
        "/pause - Pause auto-trading\n"
        "/resume - Resume auto-trading\n"
        "/quota - API usage details\n\n"
        "<b>Stats Commands:</b>\n"
        "/level - Level progress\n"
        "/council - Module performance\n"
        "/stats - Overall performance\n\n"
        "Real-time monitoring active 🟢",
        parse_mode='HTML'
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status command - bot health and stats"""
    try:
        # Bot status
        paused = is_bot_paused()
        status_emoji = "⏸️" if paused else "🟢"
        status_text = "PAUSED" if paused else "RUNNING"
        
        # Uptime
        start_time = get_bot_start_time()
        if start_time:
            uptime = datetime.now(pytz.UTC) - start_time
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            uptime_text = f"{hours}h {minutes}m"
        else:
            uptime_text = "Unknown"
        
        # API usage
        api_stats = get_api_usage_stats()
        
        # Pending trades
        pending = get_pending_trades()
        pending_count = len(pending) if pending else 0
        
        # Current level
        level_data = get_current_level()
        
        # Health check
        health_ok, health_msg = health_check()
        health_emoji = "✅" if health_ok else "❌"
        
        response = f"""🤖 <b>Bot Status</b>

<b>System</b>
Status: {status_emoji} {status_text}
Uptime: {uptime_text}
API: {health_emoji} {api_stats['calls_today']}/{api_stats['limit']} calls

<b>Trading</b>
Level: L{level_data['level']} | Balance: €{level_data['balance']:.2f}
Pending Trades: {pending_count}

<b>Health Check</b>
{health_msg}"""
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Error in /status: {e}")
        await update.message.reply_text(f"❌ Error fetching status: {e}")


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /pause command"""
    try:
        if is_bot_paused():
            await update.message.reply_text("⏸️ Bot is already paused")
            return
        
        set_bot_paused(True)
        logger.info("Bot paused via /pause command")
        await update.message.reply_text(
            "⏸️ <b>Auto-trading PAUSED</b>\n\n"
            "No new signals will be generated.\n"
            "Pending trades will still be monitored.\n\n"
            "Use /resume to restart.",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Error in /pause: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /resume command"""
    try:
        if not is_bot_paused():
            await update.message.reply_text("🟢 Bot is already running")
            return
        
        set_bot_paused(False)
        logger.info("Bot resumed via /resume command")
        await update.message.reply_text(
            "🟢 <b>Auto-trading RESUMED</b>\n\n"
            "Signal generation restarted.\n"
            "Next signal in ~30 minutes.",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Error in /resume: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /quota command - API usage details"""
    try:
        api_stats = get_api_usage_stats()
        
        # Calculate remaining hours
        now = datetime.now(pytz.UTC)
        midnight = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=pytz.UTC)
        remaining_hours = (midnight - now).seconds // 3600
        
        response = f"""📊 <b>API Quota Status</b>

<b>Today's Usage</b>
Used: {api_stats['calls_today']} / {api_stats['limit']}
Remaining: {api_stats['remaining']}
Percentage: {api_stats['percentage']:.1f}%

<b>Rate</b>
Calls/hour: {api_stats['calls_today'] // max(1, 24-remaining_hours)}
Hours until reset: {remaining_hours}h

<b>Status</b>"""
        
        if api_stats['percentage'] < 75:
            response += "\n✅ Healthy - plenty of quota"
        elif api_stats['percentage'] < 90:
            response += "\n⚠️ Caution - approaching limit"
        else:
            response += "\n🛑 Critical - near daily limit"
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Error in /quota: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /pending command - view pending trades"""
    try:
        pending_trades = get_pending_trades()
        
        if not pending_trades:
            await update.message.reply_text("✅ No pending trades")
            return
        
        response = f"📋 <b>Pending Trades ({len(pending_trades)})</b>\n\n"
        
        for trade in pending_trades[:5]:  # Show max 5
            trade_id = trade[0]
            direction = trade[3]
            entry = trade[4]
            sl = trade[5]
            tp = trade[6]
            
            response += f"<b>Trade #{trade_id}</b> - {direction}\n"
            response += f"Entry: {entry} | SL: {sl} | TP: {tp}\n\n"
        
        if len(pending_trades) > 5:
            response += f"... and {len(pending_trades) - 5} more"
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Error in /pending: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /price command"""
    await update.message.reply_text("Fetching XAU/USD price...")
    
    current_price = get_xauusd_price()
    
    if current_price:
        await update.message.reply_text(f"💰 <b>XAU/USD</b> = ${current_price:.2f}", parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Could not fetch price. Check logs.")


async def macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /macro command - macro snapshot"""
    await update.message.reply_text("Fetching macro snapshot...")
    
    macro_verdict, macro_explanation = get_macro_verdict(fetch_macro_data)
    
    if 'error' in macro_explanation:
        await update.message.reply_text(f"❌ {macro_explanation['error']}")
        return
    
    response = f"""🌍 <b>Macro Snapshot</b> (15m basis)

<b>DXY:</b> {macro_explanation['dxy']}
<b>US10Y:</b> {macro_explanation['yield']}
<b>Risk Tone:</b> {macro_explanation['risk']}

<b>Macro Verdict:</b> {format_verdict(macro_verdict)} (score: {macro_explanation['score']:+d})"""
    
    await update.message.reply_text(response, parse_mode='HTML')


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /signal command - full analysis with trade plan"""
    await update.message.reply_text("🔍 Analyzing market...")
    
    # Check if paused
    if is_bot_paused():
        await update.message.reply_text("⏸️ Bot is paused. Use /resume first.")
        return
    
    # Check news blackout
    is_blackout, blackout_reason = check_news_blackout()
    
    if is_blackout:
        response = f"""🚫 <b>NO TRADE</b> - High-impact news window

Reason: {blackout_reason}

Wait for the event to pass before trading."""
        await update.message.reply_text(response, parse_mode='HTML')
        return
    
    # Fetch data
    df = get_ohlc_data(period="5d", interval="1m", candles=100)
    
    if df is None or df.empty:
        await update.message.reply_text("❌ Could not fetch market data")
        return
    
    current_price = round(df['Close'].iloc[-1], 2)
    
    # All modules
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
    
    # Create trade plan if Buy/Sell
    trade_plan_msg = ""
    if final_verdict in ["BUY", "SELL"]:
        level_data = get_current_level()
        plan = create_trade_plan(df, final_verdict, level_data['balance'])
        
        if plan:
            trade_id = log_trade_plan(signal_id, plan)
            trade_plan_msg = f"""
<b>Trade Plan #{trade_id}:</b>
Entry: {plan['entry']} | SL: {plan['sl']} | TP: {plan['tp']}
Lots: {plan['lots']} | Stop: {plan['stop_pips']} pips | R:R {plan['rr']}
Risk: €{plan['risk_amount']} | Target: €{plan['potential_gain']}
"""
    
    # Format response
    macro_note = ""
    if macro_adjusted:
        macro_note = f"\n⚠️ Macro conflict: signal downgraded to Neutral"
    
    response = f"""💰 <b>XAU/USD</b> = ${current_price:.2f}

<b>Modules:</b>
• Trend: {format_verdict(trend_verdict)}
• Candlestick: {candle_pattern} {format_verdict(candle_verdict)}
• S/R: {sr_explanation} {format_verdict(sr_verdict)}
• Volume: {volume_explanation} {format_verdict(volume_verdict)}
• RSI: {rsi_explanation} {format_verdict(rsi_verdict)}
• MACD: {macd_explanation} {format_verdict(macd_verdict)}
• Bollinger: {bollinger_explanation} {format_verdict(bollinger_verdict)}
• Macro: {macro_explanation.get('dxy', 'N/A')} {format_verdict(macro_verdict)}

<b>Final:</b> {format_verdict(final_verdict)} (score: {score:+.1f})
<b>Confidence:</b> {confidence}%{macro_note}{trade_plan_msg}
Signal #{signal_id} | {get_utc_timestamp()}"""
    
    await update.message.reply_text(response, parse_mode='HTML')


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /plan command - show latest trade plan"""
    trade_data = get_last_trade()
    
    if not trade_data:
        await update.message.reply_text("❌ No trade plan available. Run /signal first.")
        return
    
    trade_id = trade_data[0]
    signal_id = trade_data[1]
    timestamp = trade_data[2]
    direction = trade_data[3]
    entry = trade_data[4]
    sl = trade_data[5]
    tp = trade_data[6]
    lots = trade_data[7]
    stop_pips = trade_data[8]
    rr = trade_data[10]
    result = trade_data[13] if len(trade_data) > 13 else None
    
    if result:
        await update.message.reply_text(f"✅ Latest trade (#{trade_id}) completed: {result}")
        return
    
    response = f"""📋 <b>Trade Plan #{trade_id}</b> (XAU/USD 1m)

<b>Direction:</b> {direction} (signal #{signal_id})
<b>Entry:</b> {entry} | <b>SL:</b> {sl} | <b>TP:</b> {tp}
<b>Lots:</b> {lots} | <b>Stop:</b> {stop_pips} pips | <b>R:R</b> {rr}
<b>Mode:</b> {RISK_MODE}

⏱️ Real-time monitoring active"""
    
    await update.message.reply_text(response, parse_mode='HTML')


async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /grade command - verify and grade last trade"""
    args = context.args
    
    # Get trade to grade
    if args and args[0].isdigit():
        trade_id = int(args[0])
        trade_data = get_trade_by_id(trade_id)
    else:
        trade_data = get_last_trade()
    
    if not trade_data:
        await update.message.reply_text("❌ No trade to grade. Run /signal first.")
        return
    
    trade_id = trade_data[0]
    signal_id = trade_data[1]
    timestamp_str = trade_data[2]
    direction = trade_data[3]
    entry = trade_data[4]
    sl = trade_data[5]
    tp = trade_data[6]
    lots = trade_data[7]
    stop_pips = trade_data[8]
    tp_pips = trade_data[9]
    rr_target = trade_data[10]
    risk_amount = trade_data[11]
    potential_gain = trade_data[12]
    result = trade_data[13] if len(trade_data) > 13 else None
    
    # Check if already graded
    if result:
        await update.message.reply_text(f"✅ Trade #{trade_id} already graded: {result}")
        return
    
    await update.message.reply_text(f"🔍 Verifying trade #{trade_id}...")
    
    # Parse timestamp
    entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")
    
    # Verify trade
    result_data = verify_trade_realtime(entry_time, direction, entry, sl, tp)
    
    if result_data['result'] == 'PENDING':
        await update.message.reply_text(f"⏱️ Trade #{trade_id} still pending (no level hit yet)")
        return
    
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
    
    # Update trade in DB
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
    
    # Format response
    if result_data['result'] == 'WIN':
        outcome = f"✅ TP hit in {result_data['bars']} bars"
    elif result_data['result'] == 'LOSS':
        outcome = f"❌ SL hit in {result_data['bars']} bars"
    else:
        outcome = "⏱️ Expired (no level hit)"
    
    # Council summary
    council_summary = []
    for module, verdict in verdicts.items():
        if verdict == direction:
            icon = "✅" if result_data['result'] == 'WIN' else "❌"
        elif verdict == "NEUTRAL":
            icon = "➖"
        else:
            icon = "❌"
        council_summary.append(f"{module.title()}{icon}")
    
    response = f"""📊 <b>Trade #{trade_id} Result</b>

{outcome}
<b>PnL:</b> {rr_realized:+.1f}R | {pnl:+.2f}€

<b>Council:</b>
{' '.join(council_summary)}

<b>Level:</b> {level_data['level']} → {new_level_data['level']}
<b>Balance:</b> €{level_data['balance']:.2f} → €{new_level_data['balance']:.2f}
<b>Next Target:</b> €{new_level_data['target']:.2f}"""
    
    await update.message.reply_text(response, parse_mode='HTML')


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /level command - show level progress"""
    level_data = get_current_level()
    
    progress = ((level_data['balance'] - (level_data['target'] / 1.2)) / 
                (level_data['target'] - (level_data['target'] / 1.2)) * 100)
    progress = max(0, min(100, progress))
    
    # Progress bar
    filled = int(progress // 10)
    bar = "▓" * filled + "░" * (10 - filled)
    
    response = f"""📊 <b>Level Progress</b>

<b>Current:</b> L{level_data['level']} | Balance: €{level_data['balance']:.2f}
<b>Next Target (+20%):</b> €{level_data['target']:.2f}
<b>Progress:</b> {progress:.0f}%

{bar}

<b>Mode:</b> {RISK_MODE}"""
    
    await update.message.reply_text(response, parse_mode='HTML')


async def council_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /council command - show council statistics"""
    stats = get_council_stats()
    
    if not stats:
        await update.message.reply_text("❌ No council data yet. Complete some trades first.")
        return
    
    response = "🏛️ <b>Council Performance</b>\n\n"
    
    for member, correct, incorrect, neutral, accuracy, expectancy, trade_count in stats:
        response += f"<b>{member.title()}:</b> {accuracy:.0f}% acc | {expectancy:+.2f}R exp\n"
        response += f"  ✅{correct} ❌{incorrect} ➖{neutral}\n\n"
    
    await update.message.reply_text(response, parse_mode='HTML')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command - comprehensive performance"""
    await update.message.reply_text("📊 Calculating stats...")
    
    stats_data = get_stats()
    
    if stats_data['total_signals'] == 0 and stats_data['total_trades'] == 0:
        await update.message.reply_text("❌ No data yet. Use /signal to start!")
        return
    
    total_signals = stats_data['total_signals']
    total_trades = stats_data['total_trades']
    verdict_counts = stats_data.get('verdict_counts', {})
    avg_confidence = stats_data.get('avg_confidence', 0)
    macro_saves = stats_data.get('macro_saves', 0)
    win_rate = stats_data.get('win_rate', 0)
    avg_rr = stats_data.get('avg_rr', 0)
    
    buy_count = verdict_counts.get('BUY', 0)
    sell_count = verdict_counts.get('SELL', 0)
    neutral_count = verdict_counts.get('NEUTRAL', 0)
    
    macro_save_rate = round((macro_saves / total_signals) * 100, 1) if total_signals > 0 else 0
    
    response = f"""📊 <b>Performance Summary</b>

<b>Signals (last {total_signals}):</b>
• Buy: {buy_count} ({calculate_percentage(buy_count, total_signals)}%)
• Sell: {sell_count} ({calculate_percentage(sell_count, total_signals)}%)
• Neutral: {neutral_count} ({calculate_percentage(neutral_count, total_signals)}%)
• Avg Confidence: {avg_confidence}%

<b>Macro Gate:</b>
• Interventions: {macro_saves} ({macro_save_rate}%)

<b>Trades (last {total_trades}):</b>
• Win Rate: {win_rate}%
• Avg R:R: {avg_rr}

Higher neutral count = more cautious, quality signals!"""
    
    await update.message.reply_text(response, parse_mode='HTML')


def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Control commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("quota", quota))
    application.add_handler(CommandHandler("pending", pending))
    
    # Market commands
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("signal", signal))
    application.add_handler(CommandHandler("macro", macro))
    
    # Trading commands
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("grade", grade))
    
    # Stats commands
    application.add_handler(CommandHandler("level", level))
    application.add_handler(CommandHandler("council", council_stats))
    application.add_handler(CommandHandler("stats", stats))
    
    logger.info("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()