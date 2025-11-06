#!/bin/bash
# Migration script wrapper - run this on the BACKEND server
# This populates system settings with hardcoded agent definitions

set -e

echo "🚀 Agent Migration Script"
echo "=========================="
echo ""
echo "This script will migrate hardcoded agent definitions from agents.py"
echo "to the system_settings table in the database."
echo ""
echo "⚠️  This must be run on the BACKEND server where the database is accessible."
echo ""

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$BACKEND_DIR" || {
    echo "❌ ERROR: Cannot find backend directory"
    exit 1
}

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📋 Activating virtual environment..."
    source venv/bin/activate
fi

# Run the migration script
echo "📋 Running migration script..."
python3 scripts/migrate_agents_to_settings.py

echo ""
echo "✅ Migration complete!"
echo ""
echo "📊 Next steps:"
echo "1. Verify agents appear in admin panel at /admin"
echo "2. All agent prompts/configs are now editable from admin panel"
echo "3. Changes in admin panel will be used immediately (no code changes needed)"

