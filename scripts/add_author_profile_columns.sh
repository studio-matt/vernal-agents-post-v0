#!/bin/bash
# Add profile_json, liwc_scores, trait_scores columns to author_personalities table
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

echo "🔧 Adding author profile columns to author_personalities table..."
echo "📋 Database: $DB_NAME @ $DB_HOST"
echo ""

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SET @dbname = DATABASE();
SET @tablename = 'author_personalities';

-- Add profile_json column
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = 'profile_json')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN profile_json TEXT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add liwc_scores column
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = 'liwc_scores')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN liwc_scores TEXT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add trait_scores column
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = 'trait_scores')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN trait_scores TEXT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Author profile columns added (or already exist)"
    echo "   - profile_json: Full AuthorProfile JSON"
    echo "   - liwc_scores: Quick access to LIWC category scores"
    echo "   - trait_scores: MBTI/OCEAN/HEXACO trait scores"
else
    echo "❌ Failed to add author profile columns"
    exit 1
fi

