#!/bin/bash
# Add is_admin column to user table
# Follows EMERGENCY_NET.md patterns - uses mysql command directly, loads from .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🔧 Adding is_admin column to user table..."
echo ""

# Load environment variables (following fix_database_schema.sh pattern)
if [ -f .env ]; then
    source <(grep -E '^DB_' .env | sed 's/^/export /')
    echo "✅ Loaded database credentials from .env"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Check required variables
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Missing database credentials in .env file"
    echo "   Required: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    exit 1
fi

echo "📋 Database: $DB_NAME @ $DB_HOST"
echo ""

# Check if column already exists and add it if it doesn't
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
-- Check and add is_admin column
SET @dbname = DATABASE();
SET @tablename = 'user';
SET @columnname = 'is_admin';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' BOOLEAN DEFAULT FALSE NOT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Verify the changes
DESCRIBE user;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ is_admin column added successfully!"
    echo "   All existing users have is_admin = FALSE by default"
    echo ""
    echo "💡 To set admin users, run:"
    echo "   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e \"UPDATE user SET is_admin = TRUE WHERE email = 'admin@example.com';\""
else
    echo ""
    echo "❌ Failed to add is_admin column"
    exit 1
fi

