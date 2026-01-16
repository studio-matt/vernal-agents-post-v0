#!/bin/bash
# Compare refactored code with original backup
# Usage: bash guardrails/compare_refactor.sh [backup_timestamp]
#   If timestamp not provided, uses most recent backup

set -e

BACKUP_DIR=".refactor_backups"

if [ -z "$1" ]; then
    # Find most recent backup
    LATEST=$(ls -t "$BACKUP_DIR" 2>/dev/null | head -1)
    if [ -z "$LATEST" ]; then
        echo "❌ No backups found in $BACKUP_DIR"
        echo "   Create a backup first: bash guardrails/backup_before_refactor.sh"
        exit 1
    fi
    BACKUP_SESSION="$LATEST"
    echo "📋 Using most recent backup: $BACKUP_SESSION"
else
    BACKUP_SESSION="$1"
fi

BACKUP_PATH="$BACKUP_DIR/$BACKUP_SESSION"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup not found: $BACKUP_PATH"
    echo "   Available backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null || echo "   (none)"
    exit 1
fi

echo "🔍 Comparing refactored code with backup: $BACKUP_SESSION"
echo "=========================================================="
echo ""

# Find all Python files in backup
BACKUP_FILES=$(find "$BACKUP_PATH" -name "*.py" -type f | sed "s|^$BACKUP_PATH/||" | sort)

if [ -z "$BACKUP_FILES" ]; then
    echo "⚠️  No Python files found in backup"
    exit 0
fi

DIFF_COUNT=0
MISSING_COUNT=0
NEW_COUNT=0

echo "📊 File Comparison Summary"
echo "---------------------------"
echo ""

for backup_file in $BACKUP_FILES; do
    current_file="$backup_file"
    backup_full="$BACKUP_PATH/$backup_file"
    
    if [ ! -f "$current_file" ]; then
        echo "❌ MISSING: $current_file (was in backup, now deleted)"
        ((MISSING_COUNT++))
        continue
    fi
    
    # Check if files are identical
    if diff -q "$backup_full" "$current_file" >/dev/null 2>&1; then
        echo "✅ UNCHANGED: $current_file"
    else
        echo "🔀 MODIFIED: $current_file"
        ((DIFF_COUNT++))
        
        # Show diff stats
        LINES_ADDED=$(diff "$backup_full" "$current_file" | grep -c "^>" || echo "0")
        LINES_REMOVED=$(diff "$backup_full" "$current_file" | grep -c "^<" || echo "0")
        echo "   +$LINES_ADDED lines, -$LINES_REMOVED lines"
    fi
done

# Check for new files (in current but not in backup)
echo ""
echo "📋 Checking for new files..."
for current_file in $(find app/routes -name "*.py" -type f 2>/dev/null | sort); do
    backup_file="$BACKUP_PATH/$current_file"
    if [ ! -f "$backup_file" ]; then
        echo "✨ NEW: $current_file (not in backup)"
        ((NEW_COUNT++))
    fi
done

echo ""
echo "=========================================================="
echo "📊 Comparison Summary"
echo "=========================================================="
echo "✅ Unchanged files: $(( $(echo "$BACKUP_FILES" | wc -l) - DIFF_COUNT - MISSING_COUNT ))"
echo "🔀 Modified files: $DIFF_COUNT"
echo "❌ Missing files: $MISSING_COUNT"
echo "✨ New files: $NEW_COUNT"
echo ""

if [ "$DIFF_COUNT" -gt 0 ]; then
    echo "💡 To see detailed diffs:"
    echo "   diff -u $BACKUP_PATH/main.py main.py"
    echo "   diff -u $BACKUP_PATH/app/routes/admin.py app/routes/admin.py"
    echo ""
    echo "💡 To see side-by-side comparison:"
    echo "   diff -y $BACKUP_PATH/main.py main.py | less"
    echo ""
    echo "💡 To find what broke:"
    echo "   1. Compare function definitions: grep -E '^(def |async def )' $BACKUP_PATH/main.py main.py"
    echo "   2. Compare imports: grep '^import\|^from' $BACKUP_PATH/main.py main.py"
    echo "   3. Compare router includes: grep 'include_router' $BACKUP_PATH/main.py main.py"
fi

if [ "$MISSING_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: Files were deleted during refactoring!"
    echo "   Review missing files to ensure functionality wasn't lost"
fi

echo ""
echo "📚 Backup location: $BACKUP_PATH"
echo "📝 Metadata: $BACKUP_PATH/BACKUP_METADATA.txt"

