# Level system tracking
import sqlite3
from storage.database import DB_PATH
from config.config import INITIAL_BALANCE, RISK_MODE

def init_levels():
    """Initialize levels table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level INTEGER NOT NULL,
            balance REAL NOT NULL,
            target REAL NOT NULL,
            result TEXT,
            mode TEXT
        )
    ''')
    
    # Check if we have a starting level
    cursor.execute('SELECT COUNT(*) FROM levels')
    if cursor.fetchone()[0] == 0:
        # Initialize level 1
        from datetime import datetime
        cursor.execute('''
            INSERT INTO levels (timestamp, level, balance, target, result, mode)
            VALUES (?, 1, ?, ?, 'START', ?)
        ''', (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), 
              INITIAL_BALANCE, INITIAL_BALANCE * 1.2, RISK_MODE))
    
    conn.commit()
    conn.close()

def get_current_level():
    """Get current level and balance"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT level, balance, target FROM levels 
        ORDER BY id DESC LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {'level': result[0], 'balance': result[1], 'target': result[2]}
    else:
        return {'level': 1, 'balance': INITIAL_BALANCE, 'target': INITIAL_BALANCE * 1.2}

def update_level(pnl, result):
    """
    Update level based on trade result
    Args:
        pnl: profit/loss amount
        result: "WIN" or "LOSS"
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    from datetime import datetime
    
    current = get_current_level()
    new_balance = current['balance'] + pnl
    
    if RISK_MODE == "LEVEL_STRICT":
        # Challenge mode: +1 level on win, -1 on loss
        if result == "WIN":
            new_level = current['level'] + 1
            new_balance = current['balance'] * 1.2
        else:
            new_level = max(1, current['level'] - 1)
            new_balance = current['balance'] / 1.2
        
        new_target = new_balance * 1.2
    
    else:  # SAFER mode
        # Milestone-based
        new_level = current['level']
        
        # Check if we crossed +20% milestone
        if new_balance >= current['target']:
            new_level += 1
            new_target = new_balance * 1.2
        # Check if we dropped below -20% from level start
        elif new_balance <= current['balance'] / 1.2:
            new_level = max(1, new_level - 1)
            new_target = new_balance * 1.2
        else:
            new_target = current['target']
    
    # Log level change
    cursor.execute('''
        INSERT INTO levels (timestamp, level, balance, target, result, mode)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
          new_level, round(new_balance, 2), round(new_target, 2), result, RISK_MODE))
    
    conn.commit()
    conn.close()
    
    return {'level': new_level, 'balance': round(new_balance, 2), 'target': round(new_target, 2)}

init_levels()