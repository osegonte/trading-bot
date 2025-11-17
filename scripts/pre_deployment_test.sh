#!/bin/bash
# Pre-Deployment Test Suite
# Tests all critical components before deployment

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     PRE-DEPLOYMENT TEST SUITE                              ║"
echo "╔════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_component() {
    local name=$1
    local command=$2
    
    echo -n "Testing $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Warning function
warn_component() {
    local name=$1
    local message=$2
    
    echo -e "${YELLOW}⚠ WARNING${NC}: $name - $message"
    WARNINGS=$((WARNINGS + 1))
}

echo "═══════════════════════════════════════════════════════════"
echo "1. DIRECTORY STRUCTURE"
echo "═══════════════════════════════════════════════════════════"

for dir in core data storage grading signals telegram_bot utils config modules scripts docs; do
    test_component "$dir/" "[ -d $dir ]"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "2. CRITICAL FILES"
echo "═══════════════════════════════════════════════════════════"

CRITICAL_FILES=(
    "core/auto_tester.py"
    "core/verification.py"
    "telegram_bot/bot.py"
    "storage/database.py"
    "data/twelve_data.py"
    "config/config.py"
    "config/modules.yaml"
    "requirements.txt"
    ".gitignore"
)

for file in "${CRITICAL_FILES[@]}"; do
    test_component "$file" "[ -f $file ]"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "3. PYTHON IMPORTS"
echo "═══════════════════════════════════════════════════════════"

python << 'PYEOF'
import sys
sys.path.insert(0, '.')

tests = [
    ("storage.database", "init_db"),
    ("data.twelve_data", "get_xauusd_price"),
    ("core.verification", "verify_trade_realtime"),
    ("grading.council", "init_council"),
    ("grading.analytics", "calculate_module_metrics"),
    ("utils.helpers", "get_utc_timestamp"),
    ("utils.config_loader", "load_module_config"),
    ("modules.base_module", "TradingModule"),
]

errors = 0
for module, attr in tests:
    try:
        mod = __import__(module, fromlist=[attr])
        getattr(mod, attr)
        print(f"✓ {module}.{attr}")
    except Exception as e:
        print(f"✗ {module}.{attr}: {e}")
        errors += 1

sys.exit(errors)
PYEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All imports successful${NC}"
else
    echo -e "${RED}✗ Some imports failed${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "4. CONFIGURATION"
echo "═══════════════════════════════════════════════════════════"

# Check API keys
if grep -q "your_telegram_bot_token_here" config/config.py 2>/dev/null; then
    warn_component "Telegram Token" "Still using example token"
fi

if grep -q "your_twelve_data_api_key_here" config/config.py 2>/dev/null; then
    warn_component "Twelve Data Key" "Still using example key"
fi

# Check if real keys are present
if grep -q "TELEGRAM_TOKEN = \"7623552805" config/config.py 2>/dev/null; then
    echo -e "${GREEN}✓ Telegram token configured${NC}"
else
    warn_component "Telegram Token" "May not be configured"
fi

if grep -q "TWELVE_DATA_API_KEY = \"4d84b9c11a8c4bceba24c5eecd21dd00\"" config/config.py 2>/dev/null; then
    echo -e "${GREEN}✓ Twelve Data key configured${NC}"
else
    warn_component "Twelve Data Key" "May not be configured"
fi

# Check YAML config
test_component "modules.yaml valid" "python -c 'import yaml; yaml.safe_load(open(\"config/modules.yaml\"))'"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "5. DEPENDENCIES"
echo "═══════════════════════════════════════════════════════════"

REQUIRED_PACKAGES=(
    "pandas"
    "numpy"
    "pytz"
    "requests"
    "python-telegram-bot"
    "pyyaml"
)

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    test_component "$pkg" "pip show $pkg"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "6. GIT STATUS"
echo "═══════════════════════════════════════════════════════════"

if [ -d .git ]; then
    echo "Branch: $(git branch --show-current)"
    echo "Last commit: $(git log -1 --oneline)"
    echo ""
    
    UNCOMMITTED=$(git status --porcelain | wc -l)
    if [ $UNCOMMITTED -gt 0 ]; then
        warn_component "Git" "$UNCOMMITTED uncommitted changes"
        echo "Uncommitted files:"
        git status --short
    else
        echo -e "${GREEN}✓ All changes committed${NC}"
    fi
else
    warn_component "Git" "Not a git repository"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "7. FILE PERMISSIONS"
echo "═══════════════════════════════════════════════════════════"

test_component "scripts executable" "[ -x scripts/pre_deployment_test.sh ]"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ ALL TESTS PASSED ✓✓✓${NC}"
    echo ""
    echo "System is ready for deployment!"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ TESTS PASSED WITH WARNINGS ⚠${NC}"
    echo ""
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo ""
    echo "Review warnings above. System should work but check configs."
    exit 0
else
    echo -e "${RED}✗✗✗ TESTS FAILED ✗✗✗${NC}"
    echo ""
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo ""
    echo "Fix errors above before deployment!"
    exit 1
fi
