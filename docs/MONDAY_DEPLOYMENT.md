# Monday Deployment Checklist

## On ThinkPad (Monday Morning)

### 1. Pull Latest Code
```bash
ssh osegonte@192.168.10.145
cd ~/Desktop/trading-bot
git pull origin main
```

### 2. Verify New Structure
```bash
ls -la
# Should see: core/, data/, storage/, grading/, signals/, etc.
```

### 3. Update Config
```bash
# Make sure config/config.py has correct API keys
grep "TWELVE_DATA_API_KEY" config/config.py
# Should show: 4d84b9c11a8c4bceba24c5eecd21dd00
```

### 4. Test Imports
```bash
source venv/bin/activate
python -c "from core.verification import verify_trade_realtime; print('✅ OK')"
python -c "from storage.database import init_db; print('✅ OK')"
python -c "from data.twelve_data import get_xauusd_price; print('✅ OK')"
```

### 5. Restart Bot
```bash
pkill -f auto_tester
sleep 3
cd core
nohup python auto_tester.py > ../auto.log 2>&1 &
cd ..
```

### 6. Monitor First 30 Minutes
```bash
tail -f auto.log
# Watch for:
# - "Bot is starting..."
# - "Health check: ✅"
# - "Signal #XXX" within 30 minutes
```

### 7. Telegram Verification
```
/status  → Should show "🟢 RUNNING"
/quota   → Should show API usage
/pending → Should show any pending trades
```

## Stage 1 Begins

- Let bot run for 7 days
- Monitor daily via Telegram
- Track in spreadsheet
- Collect 50-100 trades
- Analyze module performance

## MT5 Integration

- NOT YET - Wait for Stage 6 (Week 8)
- Will install MT5 on ThinkPad then
- For now: Simulation mode only
