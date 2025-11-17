#!/bin/bash
# Clean database - remove old ERROR trades

echo "🗑️ Cleaning database..."

sqlite3 trading_signals.db << 'SQL'
-- Delete old ERROR trades (before Nov 17)
DELETE FROM trades WHERE result = 'ERROR' AND timestamp < '2025-11-17';

-- Delete corresponding signals
DELETE FROM signals WHERE id NOT IN (SELECT signal_id FROM trades);

-- Reset auto-increment
DELETE FROM sqlite_sequence WHERE name='trades';
DELETE FROM sqlite_sequence WHERE name='signals';

-- Show what's left
SELECT 'Remaining trades:', COUNT(*) FROM trades;
SELECT 'Remaining signals:', COUNT(*) FROM signals;
SQL

echo "✅ Database cleaned!"
