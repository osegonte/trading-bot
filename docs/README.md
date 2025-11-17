# XAU/USD Automated Trading Bot

**Version:** 2.0 (Weekend Cleanup - November 2025)  
**Goal:** €20 → €1 Million through systematic algorithmic trading

## 🎯 Project Overview

Sophisticated council-based trading system for XAU/USD (Gold) using 8+ technical analysis modules that vote on trades. Executes only when aggregate confidence score reaches ±2.0 threshold.

**Current Status:**
- ✅ Stage 0: Emergency Stabilization (Timezone fix deployed)
- 🔄 Stage 1: Data Collection (Starting Week 1)
- ⏸️ Stage 2-7: Planned improvements

## 🏗️ Architecture

```
Development Flow:
Mac Mini (VS Code) → GitHub → ThinkPad (Auto-pull) → Production Bot (24/7)
```

### System Components

**Decision Council (8 Modules):**
1. **Trend** - EMA20/50 analysis (Weight: 1.0)
2. **Candlestick** - Pattern detection (Weight: 1.0)
3. **Support/Resistance** - Key level identification (Weight: 1.0)
4. **Volume** - Strength confirmation (Weight: 1.0)
5. **RSI** - Momentum (14 period) (Weight: 0.5)
6. **MACD** - Trend momentum (12/26/9) (Weight: 0.5)
7. **Bollinger Bands** - Volatility (Weight: 0.5)
8. **Macro Sentiment** - DXY/Yields/Risk (Gate filter)

**Execution System:**
- Signal generation: Every 30 minutes
- Trade monitoring: Every 5 minutes (real-time TP/SL tracking)
- Risk per trade: 1% of balance
- Risk/Reward target: 2:1
- Market: 24/5 (Monday-Friday)

## 📊 Performance Tracking

**Level System:**
- Start: L1 @ €20.00
- Target: L2 @ €24.00 (+20%)
- Goal: L50+ @ €1M+

**Module Grading:**
- Each module earns accuracy % and expectancy (R)
- Tracked per trade outcome
- Used for weight optimization

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Twelve Data API key (free tier: 800 calls/day)
- Telegram bot token
- Git configured

### Installation

```bash
# Clone repository
git clone https://github.com/osegonte/trading-bot.git
cd trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.py config.py
nano config.py  # Add your API keys
```

### Configuration

Edit `config.py`:
```python
TELEGRAM_TOKEN = "your_telegram_bot_token"
TWELVE_DATA_API_KEY = "your_twelve_data_key"
RISK_MODE = "SAFER"  # or "LEVEL_STRICT"
```

### Running

```bash
# Telegram bot only (manual signals)
python bot.py

# Automated trading bot (production)
python auto_tester.py

# Background mode (ThinkPad)
nohup python auto_tester.py > auto.log 2>&1 &
```

## 📱 Telegram Commands

### Control Commands
- `/start` - Bot overview and command list
- `/status` - Health check and statistics
- `/pause` - Pause auto-trading
- `/resume` - Resume auto-trading
- `/quota` - API usage details

### Market Commands
- `/price` - Current XAU/USD price
- `/signal` - Generate full analysis + trade plan
- `/macro` - Macro sentiment snapshot
- `/pending` - View pending trades

### Trading Commands
- `/plan` - View latest trade plan
- `/grade [id]` - Verify and grade trade
- `/level` - Level progression status
- `/council` - Module performance stats
- `/stats` - Overall performance summary

## 🔧 Development Workflow

### On Mac Mini (Development)

```bash
# Make changes
nano verification.py

# Test locally (optional)
python bot.py

# Commit and push
git add .
git commit -m "Fix: timezone handling in verification"
git push origin main
```

### On ThinkPad (Production)

Bot auto-pulls from GitHub on SSH connection, or manual:

```bash
ssh osegonte@192.168.10.145
cd ~/Desktop/trading-bot
git pull origin main
botrestart  # Alias for restart
```

**ThinkPad Aliases:**
```bash
botrestart   # Kill and restart bot
botlogs      # tail -f auto.log
botstatus    # ps aux | grep auto_tester
```

## 📁 Project Structure

```
trading-bot/
├── auto_tester.py         # Main production loop
├── bot.py                 # Telegram interface
├── verification.py        # Trade verification (FIXED)
├── data_twelve.py         # Twelve Data API connector
├── db.py                  # SQLite operations
├── config.py              # Configuration (gitignored)
├── config.example.py      # Template
├── levels.py              # Level progression system
├── council.py             # Module grading
├── trade_plan.py          # Risk calculation
├── indicators.py          # Technical indicators
├── utils.py               # Helper functions
│
├── signals/               # Analysis modules
│   ├── __init__.py
│   ├── candles.py
│   ├── trend.py
│   ├── sr.py
│   ├── volume.py
│   ├── rsi.py
│   ├── macd.py
│   ├── bollinger.py
│   ├── macro.py
│   └── news.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 🐛 Troubleshooting

### Bot not trading
```bash
# Check if paused
sqlite3 trading_signals.db "SELECT paused FROM bot_control;"

# Resume if needed
# In Telegram: /resume
```

### ERROR trades
```bash
# Check recent logs
tail -100 auto.log | grep ERROR

# Common causes:
# - API rate limit hit
# - Data fetch failure
# - Timezone issues (should be fixed now)
```

### API quota exceeded
```bash
# Check usage
# In Telegram: /quota

# Reset at midnight UTC automatically
```

### Database issues
```bash
# Backup and reset
mv trading_signals.db trading_signals_backup.db
botrestart  # Creates fresh DB
```

## 📈 Staged Improvement Plan

### ✅ Stage 0: Emergency Stabilization (COMPLETE)
- Fixed timezone comparison bug
- Enhanced error handling
- Stable operation

### 🔄 Stage 1: Data Collection (Week 1)
- Collect 50-100 trades
- Analyze module performance
- Establish baseline metrics

### ⏸️ Stage 2: Intelligent Cleanup (Week 2)
- Reorganize file structure
- Create modular architecture
- Improve code quality

### ⏸️ Stage 3: Module Interface (Week 3)
- Implement base module class
- Refactor existing modules
- Add config system

### ⏸️ Stage 4: Analytics System (Week 4)
- Build performance dashboard
- Implement auto-optimizer
- Generate reports

### ⏸️ Stage 5: Module Expansion (Week 5+)
- Add 10+ new strategies
- Build module library
- Integrate expert strategies

### ⏸️ Stage 6: MT5 Integration (Week 8-9)
- Connect to MT5 demo
- Real execution testing
- Validation period

### ⏸️ Stage 7: Advanced Features (Month 3+)
- Machine learning integration
- Multi-asset support
- Advanced risk management

## 🔒 Security

**Never commit:**
- `config.py` (contains API keys)
- `*.db` (contains trading data)
- `*.log` (contains sensitive logs)

**Protected in .gitignore ✓**

## 📊 Key Metrics

**Target Performance:**
- Win rate: 50-60%
- Average R:R: 2.0+
- Expectancy: >0.5R
- Max consecutive losses: <5

**API Usage:**
- Limit: 800 calls/day (Twelve Data free tier)
- Average: 140-180 calls/day
- Buffer: 600-660 calls remaining

## 🤝 Contributing

This is a personal project, but improvements welcome:

1. Create feature branch
2. Test thoroughly
3. Update documentation
4. Submit for review

## 📝 Version History

**v2.0** (Nov 2025) - Weekend Cleanup
- Fixed timezone comparison bug
- Enhanced error handling
- Improved documentation
- Prepared for Stage 1

**v1.0** (Oct 2025) - Initial Production
- Basic council system
- 8 analysis modules
- Automated trading loop
- Telegram interface

## 📞 Support

Check logs first:
```bash
tail -100 auto.log
```

Common fixes in Troubleshooting section above.

## ⚠️ Disclaimer

**This is experimental trading software.**
- Use at your own risk
- Start with demo account
- Never risk more than you can afford to lose
- Past performance ≠ future results

## 📜 License

Private project - All rights reserved

---

**Current Goal:** Complete Stage 1 (Data Collection) - 50+ clean trades  
**Next Milestone:** Stage 2 (Code Cleanup) - Modular architecture  
**Ultimate Goal:** €20 → €1M systematic journey 🚀