#!/bin/bash
# Restore files from refactoring backup
# Usage: bash guardrails/restore_from_backup.sh [backup_timestamp] [file1] [file2] ...
#   If timestamp not provided, uses most recent backup
#   If files not provided, restores all files from backup

set -e

BACKUP_DIR=".refactor_backups"

if [ -z "$1" ]; then
    echo "❌ Error: Backup timestamp required"
    echo "   Usage: bash guardrails/restore_from_backup.sh [timestamp] [file1] [file2] ..."
    echo ""
    echo "   Available backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null | head -5 || echo "   (none)"
    exit 1
fi

BACKUP_SESSION="$1"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_SESSION"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup not found: $BACKUP_PATH"
    echo "   Available backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null || echo "   (none)"
    exit 1
fi

shift # Remove timestamp from arguments

echo "🔄 Restoring from backup: $BACKUP_SESSION"
echo "=========================================="
echo ""

# Create restore backup (backup current state before restoring)
RESTORE_BACKUP_DIR=".refactor_backups/restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESTORE_BACKUP_DIR"

if [ $# -eq 0 ]; then
    # Restore all files
    echo "📋 Restoring all files from backup..."
    
    find "$BACKUP_PATH" -name "*.py" -type f | while read -r backup_file; do
        relative_path=$(echo "$backup_file" | sed "s|^$BACKUP_PATH/||")
        current_file="$relative_path"
        
        if [ -f "$current_file" ]; then
            # Backup current file before restoring
            mkdir -p "$RESTORE_BACKUP_DIR/$(dirname "$current_file")"
            cp "$current_file" "$RESTORE_BACKUP_DIR/$current_file"
            echo "   Backed up current: $current_file"
        fi
        
        # Restore from backup
        mkdir -p "$(dirname "$current_file")"
        cp "$backup_file" "$current_file"
        echo "✅ Restored: $current_file"
    done
else
    # Restore specific files
    echo "📋 Restoring specific files..."
    
    for file in "$@"; do
        backup_file="$BACKUP_PATH/$file"
        
        if [ ! -f "$backup_file" ]; then
            echo "⚠️  File not in backup: $file"
            continue
        fi
        
        if [ -f "$file" ]; then
            # Backup current file before restoring
            mkdir -p "$RESTORE_BACKUP_DIR/$(dirname "$file")"
            cp "$file" "$RESTORE_BACKUP_DIR/$file"
            echo "   Backed up current: $file"
        fi
        
        # Restore from backup
        mkdir -p "$(dirname "$file")"
        cp "$backup_file" "$file"
        echo "✅ Restored: $file"
    done
fi

echo ""
echo "✅ Restore complete!"
echo ""
echo "💡 Current state backed up to: $RESTORE_BACKUP_DIR"
echo "💡 Restart service: sudo systemctl restart vernal-agents"
echo "💡 Verify: curl http://127.0.0.1:8000/health"

