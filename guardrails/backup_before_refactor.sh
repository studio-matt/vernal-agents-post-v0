#!/bin/bash
# Backup utility for refactoring - saves original files before changes
# Usage: bash guardrails/backup_before_refactor.sh [file1] [file2] ...

set -e

BACKUP_DIR=".refactor_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_DIR="${BACKUP_DIR}/${TIMESTAMP}"

# Create backup directory structure
mkdir -p "$SESSION_DIR"

echo "📦 Creating refactoring backup..."
echo "   Backup directory: $SESSION_DIR"
echo ""

# If files provided as arguments, backup those
if [ $# -gt 0 ]; then
    for file in "$@"; do
        if [ -f "$file" ]; then
            # Create directory structure in backup
            dir=$(dirname "$file")
            mkdir -p "$SESSION_DIR/$dir"
            
            # Copy file with full path preserved
            cp "$file" "$SESSION_DIR/$file"
            echo "✅ Backed up: $file"
        else
            echo "⚠️  File not found: $file"
        fi
    done
else
    # Default: backup main.py and all route files
    echo "📋 Backing up default files (main.py and app/routes/*.py)..."
    
    if [ -f "main.py" ]; then
        cp "main.py" "$SESSION_DIR/main.py"
        echo "✅ Backed up: main.py"
    fi
    
    if [ -d "app/routes" ]; then
        mkdir -p "$SESSION_DIR/app/routes"
        find app/routes -name "*.py" -type f | while read -r file; do
            cp "$file" "$SESSION_DIR/$file"
            echo "✅ Backed up: $file"
        done
    fi
fi

# Create metadata file
cat > "$SESSION_DIR/BACKUP_METADATA.txt" << EOF
Refactoring Backup Metadata
============================
Timestamp: $(date)
Session: $TIMESTAMP
Backup Directory: $SESSION_DIR

Files Backed Up:
$(find "$SESSION_DIR" -type f -name "*.py" | sed 's|^'"$SESSION_DIR"'/||' | sort)

To compare with current version:
  bash guardrails/compare_refactor.sh $TIMESTAMP

To restore from backup:
  bash guardrails/restore_from_backup.sh $TIMESTAMP
EOF

echo ""
echo "📝 Metadata saved: $SESSION_DIR/BACKUP_METADATA.txt"
echo ""
echo "✅ Backup complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Make your refactoring changes"
echo "   2. Compare: bash guardrails/compare_refactor.sh $TIMESTAMP"
echo "   3. If issues found, restore: bash guardrails/restore_from_backup.sh $TIMESTAMP"

