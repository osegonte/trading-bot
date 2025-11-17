#!/bin/bash
# Update all imports to use new unified structure

echo "🔄 Updating imports..."

# Update imports in core/
find core/ -name "*.py" -type f -exec sed -i '' \
    's/from data\.twelve_data import/from data.data_provider import/g' {} \;

# Update imports in telegram_bot/
find telegram_bot/ -name "*.py" -type f -exec sed -i '' \
    's/from data\.twelve_data import/from data.data_provider import/g' {} \;

# Update imports in grading/
find grading/ -name "*.py" -type f -exec sed -i '' \
    's/from data\.twelve_data import/from data.data_provider import/g' {} \;

echo "✅ Imports updated"
