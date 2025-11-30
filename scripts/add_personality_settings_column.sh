#!/bin/bash
# Add personality_settings_json column to campaigns table
# Idempotent script - safe to run multiple times

set -e

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

echo "🔧 Adding personality_settings_json column to campaigns table..."
echo "📋 Database: $DB_NAME @ $DB_HOST"
echo ""

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SET @dbname = DATABASE();
SET @tablename = 'campaigns';
SET @columnname = 'personality_settings_json';

-- Check and add personality_settings_json column
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
EOF

if [ $? -eq 0 ]; then
    echo "✅ personality_settings_json column added (or already exists)"
else
    echo "❌ Failed to add personality_settings_json column"
    exit 1
fi

