# Council member grading and tracking
import sqlite3
from storage.database import DB_PATH

def init_council():
    """Initialize council members table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS council (
            member TEXT PRIMARY KEY,
            correct INTEGER DEFAULT 0,
            incorrect INTEGER DEFAULT 0,
            neutral INTEGER DEFAULT 0,
            total_r REAL DEFAULT 0,
            trade_count INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            expectancy REAL DEFAULT 0,
            weight REAL DEFAULT 1.0
        )
    ''')
    
    # Initialize members
    members = ['trend', 'candlestick', 'sr', 'volume', 'rsi', 'macd', 'bollinger', 'macro']
    
    for member in members:
        cursor.execute('''
            INSERT OR IGNORE INTO council (member) VALUES (?)
        ''', (member,))
    
    conn.commit()
    conn.close()

def grade_council(module_verdicts, trade_direction, trade_result, rr_realized):
    """
    Grade each council member based on trade outcome
    Args:
        module_verdicts: dict of {module: verdict}
        trade_direction: "BUY" or "SELL"
        trade_result: "WIN", "LOSS", or "EXPIRED"
        rr_realized: actual R achieved
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for module, verdict in module_verdicts.items():
        if verdict == "NEUTRAL":
            # Increment neutral counter
            cursor.execute('''
                UPDATE council 
                SET neutral = neutral + 1
                WHERE member = ?
            ''', (module,))
            continue
        
        # Check if module aligned with trade direction
        aligned = (verdict == trade_direction)
        
        if not aligned:
            # Module voted opposite - skip grading
            continue
        
        # Module aligned with trade
        if trade_result == "WIN":
            cursor.execute('''
                UPDATE council 
                SET correct = correct + 1,
                    total_r = total_r + ?,
                    trade_count = trade_count + 1
                WHERE member = ?
            ''', (rr_realized, module))
        
        elif trade_result == "LOSS":
            cursor.execute('''
                UPDATE council 
                SET incorrect = incorrect + 1,
                    total_r = total_r + ?,
                    trade_count = trade_count + 1
                WHERE member = ?
            ''', (rr_realized, module))
        
        # EXPIRED doesn't count toward correct/incorrect
    
    # Recalculate accuracy and expectancy for all members
    cursor.execute('SELECT member, correct, incorrect, total_r, trade_count FROM council')
    for row in cursor.fetchall():
        member, correct, incorrect, total_r, trade_count = row
        
        total_graded = correct + incorrect
        accuracy = (correct / total_graded * 100) if total_graded > 0 else 0
        expectancy = (total_r / trade_count) if trade_count > 0 else 0
        
        cursor.execute('''
            UPDATE council 
            SET accuracy = ?, expectancy = ?
            WHERE member = ?
        ''', (round(accuracy, 1), round(expectancy, 2), member))
    
    conn.commit()
    conn.close()

def get_council_stats():
    """Get council statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT member, correct, incorrect, neutral, accuracy, expectancy, trade_count
        FROM council
        ORDER BY accuracy DESC
    ''')
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

init_council()