 # Main entrypoint - Telegram bot handler with Phase 6 trade planning and verification
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

from config import TELEGRAM_TOKEN, RISK_MODE
from data import get_xauusd_price, get_ohlc_data, fetch_macro_data
from signals import (detect_candlestick_pattern, get_trend_verdict, get_sr_verdict, 
                     get_volume_verdict, get_rsi_verdict, get_macd_verdict, 
                     get_bollinger_verdict, get_macro_verdict, check_news_blackout)
from db import (log_signal, log_trade_plan, update_trade_result, get_last_trade, 
                get_trade_by_id, get_signal_verdicts, get_stats)
from utils import get_utc_timestamp, format_verdict, calculate_percentage, aggregate_verdicts_with_macro
from trade_plan import create_trade_plan
from verification import verify_trade
from council import grade_council, get_council_stats
from levels import get_current_level, update_level

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    await update.message.reply_text(
        "Bot is alive! Commands:\n"
        "/price - Current price\n"
        "/signal - Full analysis + trade plan\n"
        "/macro - Macro snapshot\n"
        "/plan - View latest trade plan\n"
        "/grade - Verify & grade last trade\n"
        "/level - Level progress\n"
        "/council - Council stats\n"
        "/stats - Performance summary"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /price command"""
    await update.message.reply_text("Fetching XAU/USD price...")
    
    current_price = get_xauusd_price()
    
    if current_price:
        await update.message.reply_text(f"XAU/USD = {current_price}")
    else:
        await update.message.reply_text("Could not fetch price. Try again later.")


async def macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /macro command - macro snapshot"""
    await update.message.reply_text("Fetching macro snapshot...")
    
    macro_verdict, macro_explanation = get_macro_verdict(fetch_macro_data)
    
    if 'error' in macro_explanation:
        await update.message.reply_text(f"{macro_explanation['error']}")
        return
    
    response = f"""Macro Snapshot (15m basis)

DXY: {macro_explanation['dxy']}
US10Y: {macro_explanation['yield']}
Risk Tone: {macro_explanation['risk']}

Macro Verdict: {format_verdict(macro_verdict)} (score: {macro_explanation['score']:+d})"""
    
    await update.message.reply_text(response)


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /signal command - full analysis with trade plan"""
    await update.message.reply_text("Analyzing market...")
    
    # Check news blackout
    is_blackout, blackout_reason = check_news_blackout()
    
    if is_blackout:
        response = f"""NO TRADE - High-impact news window
Reason: {blackout_reason}

Wait for the event to pass before trading."""
        await update.message.reply_text(response)
        return
    
    # Fetch data
    df = get_ohlc_data(period="5d", interval="1m", candles=100)
    
    if df is None or df.empty:
        await update.message.reply_text("Could not fetch market data.")
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
Trade Plan #{trade_id}:
Entry: {plan['entry']} | SL: {plan['sl']} | TP: {plan['tp']}
Lots: {plan['lots']} | Stop: {plan['stop_pips']} pips | R:R {plan['rr']}
Risk: €{plan['risk_amount']} | Target: €{plan['potential_gain']}
"""
    
    # Format response
    macro_note = ""
    if macro_adjusted:
        macro_note = f"\nMacro conflict: technical signal downgraded to Neutral."
    
    response = f"""XAU/USD = {current_price}

Modules:
- Trend: {format_verdict(trend_verdict)}
- Candlestick: {candle_pattern} {format_verdict(candle_verdict)}
- S/R: {sr_explanation} {format_verdict(sr_verdict)}
- Volume: {volume_explanation} {format_verdict(volume_verdict)}
- RSI: {rsi_explanation} {format_verdict(rsi_verdict)}
- MACD: {macd_explanation} {format_verdict(macd_verdict)}
- Bollinger: {bollinger_explanation} {format_verdict(bollinger_verdict)}
- Macro: {macro_explanation.get('dxy', 'N/A')} {format_verdict(macro_verdict)}

Final: {format_verdict(final_verdict)} (score: {score:+.1f})
Confidence: {confidence}%{macro_note}{trade_plan_msg}
Signal #{signal_id} | {get_utc_timestamp()}"""
    
    await update.message.reply_text(response)


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /plan command - show latest trade plan"""
    trade_data = get_last_trade()
    
    if not trade_data:
        await update.message.reply_text("No trade plan available. Run /signal first.")
        return
    
    trade_id, signal_id, timestamp, direction, entry, sl, tp, lots, stop_pips, rr, result = trade_data
    
    if result:
        await update.message.reply_text(f"Latest trade (#{trade_id}) already completed: {result}")
        return
    
    response = f"""Trade Plan (XAU/USD 1m)
Direction: {direction} (signal #{signal_id})
Entry: {entry} | SL: {sl} | TP: {tp}
Lots: {lots} | Stop: {stop_pips} pips | R:R {rr}
Mode: {RISK_MODE}
"""
    
    await update.message.reply_text(response)


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
        await update.message.reply_text("No trade to grade. Run /signal first.")
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
    
    # Check if already graded
    if trade_data[13]:  # result field
        await update.message.reply_text(f"Trade #{trade_id} already graded: {trade_data[13]}")
        return
    
    await update.message.reply_text(f"Verifying trade #{trade_id}...")
    
    # Parse timestamp
    entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S UTC")
    
    # Verify trade
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
        outcome = f"TP hit in {result_data['bars']} bars"
    elif result_data['result'] == 'LOSS':
        outcome = f"SL hit in {result_data['bars']} bars"
    else:
        outcome = "Expired (no level hit)"
    
    # Council summary
    council_summary = []
    for module, verdict in verdicts.items():
        if verdict == direction:
            icon = "+" if result_data['result'] == 'WIN' else "-"
        elif verdict == "NEUTRAL":
            icon = "0"
        else:
            icon = "x"
        council_summary.append(f"{module.title()}{icon}")
    
    response = f"""Result: {outcome}
PnL: {rr_realized:+.1f}R | {pnl:+.2f}€

Council: {' '.join(council_summary)}

Level: {level_data['level']} -> {new_level_data['level']}
Balance: €{level_data['balance']:.2f} -> €{new_level_data['balance']:.2f}
Next Target: €{new_level_data['target']:.2f}
"""
    
    await update.message.reply_text(response)


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /level command - show level progress"""
    level_data = get_current_level()
    
    progress = ((level_data['balance'] - (level_data['target'] / 1.2)) / 
                (level_data['target'] - (level_data['target'] / 1.2)) * 100)
    progress = max(0, min(100, progress))
    
    response = f"""Level Progress
Current: L{level_data['level']} | Balance: €{level_data['balance']:.2f}
Next Target (+20%): €{level_data['target']:.2f}
Progress: {progress:.0f}%
Mode: {RISK_MODE}
"""
    
    await update.message.reply_text(response)


async def council_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /council command - show council statistics"""
    stats = get_council_stats()
    
    if not stats:
        await update.message.reply_text("No council data yet. Complete some trades first.")
        return
    
    response = "Council Performance:\n\n"
    
    for member, correct, incorrect, neutral, accuracy, expectancy, trade_count in stats:
        response += f"{member.title()}: {accuracy:.1f}% acc | {expectancy:+.2f}R exp\n"
        response += f"  Correct:{correct} Wrong:{incorrect} Neutral:{neutral}\n\n"
    
    await update.message.reply_text(response)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command - comprehensive performance"""
    await update.message.reply_text("Calculating stats...")
    
    stats_data = get_stats()
    
    if stats_data['total_signals'] == 0 and stats_data['total_trades'] == 0:
        await update.message.reply_text("No data yet. Use /signal to start!")
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
    
    response = f"""Performance Summary

Signals (last {total_signals}):
- Buy: {buy_count} ({calculate_percentage(buy_count, total_signals)}%)
- Sell: {sell_count} ({calculate_percentage(sell_count, total_signals)}%)
- Neutral: {neutral_count} ({calculate_percentage(neutral_count, total_signals)}%)
- Avg Confidence: {avg_confidence}%

Macro Gate:
- Interventions: {macro_saves} ({macro_save_rate}% of signals)

Trades (last {total_trades}):
- Win Rate: {win_rate}%
- Avg R:R: {avg_rr}

Higher neutral count = more cautious, quality signals!"""
    
    await update.message.reply_text(response)


def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("signal", signal))
    application.add_handler(CommandHandler("macro", macro))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("grade", grade))
    application.add_handler(CommandHandler("level", level))
    application.add_handler(CommandHandler("council", council_stats))
    application.add_handler(CommandHandler("stats", stats))
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()