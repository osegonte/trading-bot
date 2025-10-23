#!/bin/bash
# PRODUCTION Deployment Script for ThinkPad
# Pulls changes, configures, and starts bot with health checks

set -e  # Exit on any error

echo "🚀 XAU/USD Trading Bot - ThinkPad Setup"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Navigate to project directory
cd ~/Desktop/trading-bot || {
    echo -e "${RED}❌ Project directory not found${NC}"
    exit 1
}

echo "📁 Current directory: $(pwd)"
echo ""

# Kill any existing bot process
echo "🛑 Checking for existing bot processes..."
if pgrep -f auto_tester.py > /dev/null; then
    echo -e "${YELLOW}⚠️  Killing existing bot process${NC}"
    pkill -f auto_tester.py
    sleep 2
fi
echo -e "${GREEN}✅ No conflicting processes${NC}"
echo ""

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main || {
    echo -e "${RED}❌ Git pull failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Successfully pulled latest code${NC}"
echo ""

# Check if data_twelve.py exists
if [ ! -f "data_twelve.py" ]; then
    echo -e "${RED}❌ data_twelve.py not found after pull${NC}"
    echo -e "${YELLOW}Make sure it was pushed from Mac Mini${NC}"
    exit 1
fi
echo -e "${GREEN}✅ data_twelve.py exists${NC}"
echo ""

# Check if API key is in config
echo "🔑 Checking API configuration..."
if grep -q "TWELVE_DATA_API_KEY" config.py; then
    echo -e "${GREEN}✅ API key found in config.py${NC}"
else
    echo -e "${YELLOW}⚠️  API key not found in config.py${NC}"
    echo ""
    echo "Adding API key to config.py..."
    
    # Backup config
    cp config.py config.py.backup
    
    # Add API key after TELEGRAM_TOKEN line
    sed -i '/TELEGRAM_TOKEN/a TWELVE_DATA_API_KEY = "4d84b9c11a8c4bceba24c5eecd21dd00"' config.py
    
    if grep -q "TWELVE_DATA_API_KEY" config.py; then
        echo -e "${GREEN}✅ API key added successfully${NC}"
    else
        echo -e "${RED}❌ Failed to add API key${NC}"
        echo "Please add manually:"
        echo "nano config.py"
        echo "Add: TWELVE_DATA_API_KEY = \"4d84b9c11a8c4bceba24c5eecd21dd00\""
        exit 1
    fi
fi
echo ""

# Activate virtual environment
echo "🐍 Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi
echo ""

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Health check - Test API connection
echo "🏥 Running health check..."
python3 -c "
from data_twelve import health_check
success, message = health_check()
print(message)
exit(0 if success else 1)
" || {
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Check your API key and internet connection"
    exit 1
}
echo -e "${GREEN}✅ Health check passed${NC}"
echo ""

# Ask to start bot
echo "🤖 Ready to start bot!"
read -p "Start auto_tester.py now? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  Bot not started. To start manually:${NC}"
    echo "source venv/bin/activate"
    echo "nohup python auto_tester.py > auto.log 2>&1 &"
    exit 0
fi

# Start bot
echo ""
echo "🚀 Starting bot..."
nohup python auto_tester.py > auto.log 2>&1 &
BOT_PID=$!
sleep 3

# Verify bot is running
if ps -p $BOT_PID > /dev/null; then
    echo -e "${GREEN}✅ Bot started successfully (PID: $BOT_PID)${NC}"
    echo ""
    echo "📊 Recent log output:"
    tail -10 auto.log
    echo ""
    echo "📱 Monitoring commands:"
    echo "  • View logs: tail -f auto.log"
    echo "  • Check status: ps aux | grep auto_tester"
    echo "  • Stop bot: pkill -f auto_tester"
    echo ""
    echo "🎉 Deployment complete! Check Telegram for startup message."
else
    echo -e "${RED}❌ Bot failed to start${NC}"
    echo "Check logs: tail -50 auto.log"
    exit 1
fi