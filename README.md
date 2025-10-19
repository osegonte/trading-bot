# XAU/USD Trading Bot

Automated trading signal generator and testing system for gold futures.

## Features

- 8-module technical analysis system
- Macro sentiment filtering
- Automated trade verification
- Council member grading
- Level progression system (€20 → €1M challenge)

## Setup

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/xauusd-trading-bot.git
cd xauusd-trading-bot
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure
```bash
cp config.example.py config.py
nano config.py  # Add your Telegram bot token
```

### 5. Run Bot
```bash
# Manual mode
python bot.py

# Automated testing mode
python auto_tester.py
```

## Telegram Commands

- `/start` - Check bot status
- `/price` - Current XAU/USD price
- `/signal` - Generate analysis + trade plan
- `/macro` - Macro sentiment snapshot
- `/plan` - View latest trade plan
- `/grade` - Verify & grade last trade
- `/level` - Level progress
- `/council` - Module performance stats
- `/stats` - Overall performance

## Architecture

- **Phases 1-6**: Complete signal generation and verification
- **Phase 7**: Automated testing system
- **Data Source**: Yahoo Finance (yfinance)
- **Storage**: SQLite database
- **Monitoring**: Telegram bot interface

## Module System

1. **Trend** (EMA20/50) - Weight: 1.0
2. **Candlestick** patterns - Weight: 1.0
3. **Support/Resistance** - Weight: 1.0
4. **Volume** analysis - Weight: 1.0
5. **RSI** (14) - Weight: 0.5
6. **MACD** (12/26/9) - Weight: 0.5
7. **Bollinger Bands** - Weight: 0.5
8. **Macro** sentiment (DXY, yields, risk) - Gate filter

## License

Private project - All rights reserved
