#!/bin/bash
# Cleanup Script - Remove unnecessary files before deployment

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              CLEANUP SCRIPT                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REMOVED=0

# Function to remove file/directory
remove_item() {
    local item=$1
    local description=$2
    
    if [ -e "$item" ]; then
        echo -n "Removing $description... "
        rm -rf "$item"
        echo -e "${GREEN}✓${NC}"
        REMOVED=$((REMOVED + 1))
    fi
}

echo "═══════════════════════════════════════════════════════════"
echo "1. REMOVING PYTHON CACHE"
echo "═══════════════════════════════════════════════════════════"

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.py[cod]" -delete 2>/dev/null || true

echo -e "${GREEN}✓ Python cache cleaned${NC}"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "2. REMOVING OLD/DEPRECATED FILES"
echo "═══════════════════════════════════════════════════════════"

# Archive folder (old files already moved)
remove_item "archive" "archive directory"

# Old data.py (Yahoo Finance - deprecated)
remove_item "data.py" "old Yahoo Finance data.py"

# Old signals.py (monolithic - refactored)
remove_item "signals.py" "old monolithic signals.py"

# Test files in root
remove_item "test_mt5_connection.py" "MT5 test script"
remove_item "reorganize.sh" "reorganization script (no longer needed)"

# Backup files
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*.backup" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "3. REMOVING MACOS SYSTEM FILES"
echo "═══════════════════════════════════════════════════════════"

find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "._*" -delete 2>/dev/null || true

echo -e "${GREEN}✓ macOS files cleaned${NC}"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "4. REMOVING LOG FILES (if any)"
echo "═══════════════════════════════════════════════════════════"

# Keep directory but remove old logs
if [ -f "auto.log" ]; then
    remove_item "auto.log" "old auto.log"
fi

if [ -f "auto_tester.log" ]; then
    remove_item "auto_tester.log" "old auto_tester.log"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "5. CHECKING FOR OTHER UNNECESSARY FILES"
echo "═══════════════════════════════════════════════════════════"

# List potentially unnecessary files
UNNECESSARY_PATTERNS=(
    "*.log"
    "*.tmp"
    "*.swp"
    ".pytest_cache"
    ".coverage"
    "htmlcov"
)

for pattern in "${UNNECESSARY_PATTERNS[@]}"; do
    found=$(find . -name "$pattern" -not -path "./venv/*" 2>/dev/null)
    if [ -n "$found" ]; then
        echo -e "${YELLOW}⚠ Found: $pattern${NC}"
        echo "$found"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "6. VERIFYING ESSENTIAL FILES REMAIN"
echo "═══════════════════════════════════════════════════════════"

ESSENTIAL_KEEP=(
    "requirements.txt"
    ".gitignore"
    "README.md"
    "config/config.py"
    "config/modules.yaml"
)

ALL_GOOD=true
for file in "${ESSENTIAL_KEEP[@]}"; do
    if [ ! -e "$file" ]; then
        echo -e "${RED}✗ Missing essential file: $file${NC}"
        ALL_GOOD=false
    fi
done

if $ALL_GOOD; then
    echo -e "${GREEN}✓ All essential files present${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  CLEANUP COMPLETE                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ $REMOVED -gt 0 ]; then
    echo -e "${GREEN}✓ Removed $REMOVED items${NC}"
else
    echo -e "${GREEN}✓ Nothing to remove - already clean!${NC}"
fi

echo ""
echo "Project is clean and ready for deployment!"
