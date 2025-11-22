#!/bin/bash
# Migration script to add custom_keywords_json column to campaigns table
# This is idempotent - safe to run multiple times

set -e

echo "🚀 Adding custom_keywords_json column to campaigns table"
echo "========================================================="
echo ""

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$BACKEND_DIR" || {
    echo "❌ ERROR: Cannot find backend directory"
    exit 1
}

# Load database credentials from .env
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found in $BACKEND_DIR"
    exit 1
fi

echo "📋 Loading database credentials from .env..."
source .env

# Check if required variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ ERROR: Database credentials not found in .env"
    echo "Required: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    exit 1
fi

echo "✅ Database credentials loaded"
echo ""

# Check if column already exists (idempotent check)
echo "🔍 Checking if custom_keywords_json column already exists..."
COLUMN_EXISTS=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -sN -e "
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = '$DB_NAME' 
    AND TABLE_NAME = 'campaigns' 
    AND COLUMN_NAME = 'custom_keywords_json';
" 2>/dev/null || echo "0")

if [ "$COLUMN_EXISTS" = "1" ]; then
    echo "✅ Column custom_keywords_json already exists - skipping migration"
    exit 0
fi

echo "📋 Column does not exist - adding it now..."
echo ""

# Add the column
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE campaigns 
ADD COLUMN custom_keywords_json TEXT NULL;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Successfully added custom_keywords_json column to campaigns table"
    echo ""
    echo "📊 Verification:"
    mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
        DESCRIBE campaigns;
    " | grep custom_keywords_json || {
        echo "⚠️  WARNING: Column not found in DESCRIBE output (but migration may have succeeded)"
    }
    echo ""
    echo "✅ Migration complete!"
else
    echo "❌ ERROR: Failed to add column"
    exit 1
fi

