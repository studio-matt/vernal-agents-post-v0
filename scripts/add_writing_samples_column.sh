#!/bin/bash
# Migration script to add writing_samples_json column to author_personalities table
# Idempotent - safe to run multiple times

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Database connection details
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-vernalcontentum_contentMachine}"

echo "🔧 Adding writing_samples_json column to author_personalities table..."

# Check if column already exists
COLUMN_EXISTS=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -sN -e "
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = '$DB_NAME' 
    AND TABLE_NAME = 'author_personalities' 
    AND COLUMN_NAME = 'writing_samples_json';
" 2>/dev/null || echo "0")

if [ "$COLUMN_EXISTS" = "1" ]; then
    echo "✅ Column writing_samples_json already exists. Skipping migration."
    exit 0
fi

# Add the column
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE author_personalities 
ADD COLUMN writing_samples_json TEXT NULL 
COMMENT 'Original writing samples used for extraction (JSON array)';
EOF

if [ $? -eq 0 ]; then
    echo "✅ Successfully added writing_samples_json column to author_personalities table"
else
    echo "❌ Failed to add writing_samples_json column"
    exit 1
fi

