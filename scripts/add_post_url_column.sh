#!/bin/bash

# =====================================================
# Migration: Add post_url column to content table
# =====================================================
# This column stores the published URL for content posted to any platform
# (WordPress permalink, LinkedIn post URL, Facebook post URL, etc.)

set -e  # Exit on any error

echo "🔧 Adding post_url column to content table..."

# Load database credentials from .env file
if [ -f .env ]; then
    # Source DB_* variables from .env
    source <(grep -E '^DB_' .env | sed 's/^/export /')
    echo "✅ Loaded database credentials from .env"
else
    echo "❌ .env file not found. Please create one with DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME"
    exit 1
fi

# Validate required environment variables
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Missing required database credentials in .env file"
    echo "   Required: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    exit 1
fi

echo "📋 Database: $DB_NAME @ $DB_HOST"

# Check if column already exists
COLUMN_EXISTS=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -sN -e "
SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '$DB_NAME'
  AND TABLE_NAME = 'content'
  AND COLUMN_NAME = 'post_url';
")

if [ "$COLUMN_EXISTS" -gt 0 ]; then
    echo "✅ Column post_url already exists in content table. Skipping migration."
    exit 0
fi

# Add the column
echo "📝 Adding post_url column..."
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE content 
ADD COLUMN post_url VARCHAR(500) NULL 
COMMENT 'Published URL for any platform (WordPress permalink, LinkedIn post URL, etc.)';
EOF

if [ $? -eq 0 ]; then
    echo "✅ post_url column added successfully!"
    echo "   All existing content items will have post_url = NULL by default"
    echo ""
    echo "💡 The column will be populated automatically when content is posted to platforms."
else
    echo "❌ Failed to add post_url column"
    exit 1
fi

