# SQLite logging for trade signals, trades, council, and levels
import sqlite3
from datetime import datetime

DB_PATH = "trading_signals.db"

def init_db():
    """Initialize all database tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Signals table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            price REAL NOT NULL,
            trend_verdict TEXT,
            candle_verdict TEXT,
            candle_pattern TEXT,
            sr_verdict TEXT,
            sr_explanation TEXT,
            volume_verdict TEXT,
            volume_explanation TEXT,
            rsi_verdict TEXT,
            rsi_explanation TEXT,
            macd_verdict TEXT,
            macd_explanation TEXT,
            bollinger_verdict TEXT,
            bollinger_explanation TEXT,
            macro_verdict TEXT,
            macro_explanation TEXT,
            final_verdict TEXT NOT NULL,
            score REAL,
            confidence INTEGER,
            blackout_flag INTEGER DEFAULT 0,
            macro_adjusted INTEGER DEFAULT 0
        )
    ''')
    
    # Trades table (extended for Phase 6)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            signal_id INTEGER,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            lots REAL NOT NULL,
            stop_pips INTEGER,
            tp_pips INTEGER,
            rr REAL,
            risk_amount REAL,
            potential_gain REAL,
            atr REAL,
            result TEXT,
            exit_price REAL,
            bars_to_hit INTEGER,
            pnl REAL,
            notes TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def log_signal(price, trend_verdict, candle_verdict, candle_pattern,
               sr_verdict, sr_explanation, volume_verdict, volume_explanation,
               rsi_verdict, rsi_explanation, macd_verdict, macd_explanation,
               bollinger_verdict, bollinger_explanation,
               macro_verdict, macro_explanation,
               final_verdict, score, confidence, blackout_flag=0, macro_adjusted=0):
    """Log a signal to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    cursor.execute('''
        INSERT INTO signals (
            timestamp, price, trend_verdict, candle_verdict, candle_pattern,
            sr_verdict, sr_explanation, volume_verdict, volume_explanation,
            rsi_verdict, rsi_explanation, macd_verdict, macd_explanation,
            bollinger_verdict, bollinger_explanation,
            macro_verdict, macro_explanation,
            final_verdict, score, confidence, blackout_flag, macro_adjusted
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, price, trend_verdict, candle_verdict, candle_pattern,
          sr_verdict, sr_explanation, volume_verdict, volume_explanation,
          rsi_verdict, rsi_explanation, macd_verdict, macd_explanation,
          bollinger_verdict, bollinger_explanation,
          macro_verdict, str(macro_explanation),
          final_verdict, score, confidence, blackout_flag, macro_adjusted))
    
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return row_id

def log_trade_plan(signal_id, plan):
    """Log a trade plan"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    cursor.execute('''
        INSERT INTO trades (
            timestamp, signal_id, direction, entry, stop_loss, take_profit,
            lots, stop_pips, tp_pips, rr, risk_amount, potential_gain, atr
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, signal_id, plan['direction'], plan['entry'], 
          plan['sl'], plan['tp'], plan['lots'], plan['stop_pips'],
          plan['tp_pips'], plan['rr'], plan['risk_amount'], 
          plan['potential_gain'], plan['atr']))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return trade_id

def update_trade_result(trade_id, result_data):
    """Update trade with verification result"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE trades
        SET result = ?, exit_price = ?, bars_to_hit = ?, pnl = ?
        WHERE id = ?
    ''', (result_data['result'], result_data.get('exit_price'), 
          result_data.get('bars'), result_data.get('pnl'), trade_id))
    
    conn.commit()
    conn.close()

def get_last_trade():
    """Get the most recent trade"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, signal_id, timestamp, direction, entry, stop_loss, 
               take_profit, lots, stop_pips, rr, result
        FROM trades
        ORDER BY id DESC
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def get_trade_by_id(trade_id):
    """Get trade by ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, signal_id, timestamp, direction, entry, stop_loss, 
               take_profit, lots, stop_pips, tp_pips, rr, risk_amount,
               potential_gain, result, exit_price, bars_to_hit, pnl
        FROM trades
        WHERE id = ?
    ''', (trade_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def get_signal_verdicts(signal_id):
    """Get all module verdicts for a signal"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT trend_verdict, candle_verdict, sr_verdict, volume_verdict,
               rsi_verdict, macd_verdict, bollinger_verdict, macro_verdict
        FROM signals
        WHERE id = ?
    ''', (signal_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'trend': result[0],
            'candlestick': result[1],
            'sr': result[2],
            'volume': result[3],
            'rsi': result[4],
            'macd': result[5],
            'bollinger': result[6],
            'macro': result[7]
        }
    return None

def get_stats():
    """Get comprehensive statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Signal stats
    cursor.execute('SELECT COUNT(*) FROM signals')
    total_signals = cursor.fetchone()[0]
    
    if total_signals == 0:
        conn.close()
        return {'total_signals': 0, 'total_trades': 0}
    
    cursor.execute('SELECT final_verdict, COUNT(*) FROM signals GROUP BY final_verdict')
    verdict_counts = dict(cursor.fetchall())
    
    cursor.execute('SELECT AVG(confidence) FROM signals WHERE final_verdict != "NEUTRAL"')
    avg_confidence = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM signals WHERE macro_adjusted = 1')
    macro_saves = cursor.fetchone()[0]
    
    # Trade stats
    cursor.execute('SELECT COUNT(*) FROM trades WHERE result IS NOT NULL')
    total_trades = cursor.fetchone()[0]
    
    win_rate = 0
    avg_rr = 0
    
    if total_trades > 0:
        cursor.execute('SELECT COUNT(*) FROM trades WHERE result = "WIN"')
        wins = cursor.fetchone()[0]
        win_rate = round((wins / total_trades) * 100, 1)
        
        cursor.execute('SELECT AVG(pnl) FROM trades WHERE result = "WIN"')
        avg_win = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(pnl) FROM trades WHERE result = "LOSS"')
        avg_loss = cursor.fetchone()[0] or 0
        
        if avg_loss != 0:
            avg_rr = abs(avg_win / avg_loss)
    
    conn.close()
    
    return {
        'total_signals': total_signals,
        'verdict_counts': verdict_counts,
        'avg_confidence': round(avg_confidence, 1),
        'macro_saves': macro_saves,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_rr': round(avg_rr, 2)
    }

init_db()