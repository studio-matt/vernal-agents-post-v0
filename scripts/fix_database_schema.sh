#!/bin/bash
# Fix database schema - enlarge raw_html column to MEDIUMTEXT

set -e

echo "🔧 Fixing database schema for campaign_raw_data table..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Load environment variables
if [ -f .env ]; then
    source <(grep -E '^DB_' .env | sed 's/^/export /')
    echo "✅ Loaded database credentials from .env"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Check if all required variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Missing database credentials in .env file"
    echo "   Required: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    exit 1
fi

echo "📋 Database: $DB_NAME @ $DB_HOST"
echo ""

# Run the SQL command
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
-- Fix raw_html column (if not already fixed)
ALTER TABLE campaign_raw_data
MODIFY COLUMN raw_html MEDIUMTEXT;

-- Fix extracted_text column (also needs to be larger)
ALTER TABLE campaign_raw_data
MODIFY COLUMN extracted_text MEDIUMTEXT;

-- Verify the changes
DESCRIBE campaign_raw_data;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database schema updated successfully!"
    echo "   raw_html column is now MEDIUMTEXT (can store up to 16MB)"
    echo "   extracted_text column is now MEDIUMTEXT (can store up to 16MB)"
else
    echo ""
    echo "❌ Failed to update database schema"
    exit 1
fi

