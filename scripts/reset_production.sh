#!/bin/bash
echo "🔄 Resetting database for clean production run..."

# Backup first
cp trading_signals.db trading_signals.db.backup.$(date +%Y%m%d_%H%M%S)

# Clean database
sqlite3 trading_signals.db << 'SQL'
-- Remove all old ERROR trades
DELETE FROM trades WHERE result = 'ERROR';

-- Remove old signals from before today
DELETE FROM signals WHERE timestamp < '2025-11-17';

-- Reset levels to start fresh at €20
DELETE FROM levels;
INSERT INTO levels (timestamp, level, balance, target, result, mode) 
VALUES (datetime('now'), 1, 20.0, 24.0, 'FRESH_START', 'SAFER');

-- Clean up
VACUUM;

-- Show final state
.mode column
.headers on
SELECT 'Trades remaining:', COUNT(*) FROM trades;
SELECT 'Current level:', level, 'Balance:', balance FROM levels ORDER BY id DESC LIMIT 1;
SQL

echo ""
echo "✅ Database reset complete!"
