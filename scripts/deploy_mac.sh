#!/bin/bash
# PRODUCTION Deployment Script for Mac Mini
# Pushes all changes to GitHub with health checks

set -e  # Exit on any error

echo "🚀 XAU/USD Trading Bot - Production Deployment"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Navigate to project directory
cd /Users/osegonte/trading-bot || {
    echo -e "${RED}❌ Project directory not found${NC}"
    exit 1
}

echo "📁 Current directory: $(pwd)"
echo ""

# Health checks
echo "🏥 Running health checks..."
echo ""

# 1. Check if config.py has API key
if grep -q "TWELVE_DATA_API_KEY" config.py; then
    echo -e "${GREEN}✅ Config has Twelve Data API key${NC}"
else
    echo -e "${RED}❌ Config missing TWELVE_DATA_API_KEY${NC}"
    exit 1
fi

# 2. Check if data_twelve.py exists
if [ -f "data_twelve.py" ]; then
    echo -e "${GREEN}✅ data_twelve.py exists${NC}"
else
    echo -e "${RED}❌ data_twelve.py not found${NC}"
    echo -e "${YELLOW}This file needs to be created first${NC}"
    exit 1
fi

# 3. Check critical files
CRITICAL_FILES=("auto_tester.py" "bot.py" "db.py" "verification.py" "requirements.txt")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file exists${NC}"
    else
        echo -e "${RED}❌ $file missing${NC}"
        exit 1
    fi
done

echo ""
echo "📊 Git status:"
git status --short
echo ""

# Ask for confirmation
read -p "🤔 Push these changes to GitHub? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  Deployment cancelled${NC}"
    exit 0
fi

# Git operations
echo ""
echo "📤 Pushing to GitHub..."
echo ""

# Add all changes
git add .

# Commit with timestamp
COMMIT_MSG="Production deployment - $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG" || {
    echo -e "${YELLOW}⚠️  No changes to commit${NC}"
}

# Push to GitHub
git push origin main || {
    echo -e "${RED}❌ Push failed${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. SSH into ThinkPad: ssh osegonte@192.168.10.145"
echo "2. Run: cd ~/Desktop/trading-bot && git pull"
echo "3. Add API key to config.py on ThinkPad"
echo "4. Start bot: nohup python auto_tester.py > auto.log 2>&1 &"
echo ""
echo "🎉 Deployment complete!"