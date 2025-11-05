#!/bin/bash
# Add settings columns to campaigns table

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Load database credentials from .env
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

source .env

# Check required variables
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Missing database credentials in .env file"
    exit 1
fi

echo "🔧 Adding settings columns to campaigns table..."
echo "📋 Database: $DB_NAME @ $DB_HOST"

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE campaigns 
ADD COLUMN IF NOT EXISTS extraction_settings_json TEXT NULL,
ADD COLUMN IF NOT EXISTS preprocessing_settings_json TEXT NULL,
ADD COLUMN IF NOT EXISTS entity_settings_json TEXT NULL,
ADD COLUMN IF NOT EXISTS modeling_settings_json TEXT NULL;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Settings columns added successfully!"
    echo ""
    echo "Columns added:"
    echo "  - extraction_settings_json"
    echo "  - preprocessing_settings_json"
    echo "  - entity_settings_json"
    echo "  - modeling_settings_json"
else
    echo "❌ Failed to add settings columns"
    exit 1
fi

