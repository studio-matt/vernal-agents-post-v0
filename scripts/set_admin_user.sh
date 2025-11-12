#!/bin/bash
# Set matt@envoydesign.com as admin user
# Follows EMERGENCY_NET.md patterns - uses mysql command directly, loads from .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🔧 Setting matt@envoydesign.com as admin user..."
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

# Set matt@envoydesign.com as admin
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
-- Set matt@envoydesign.com as admin
UPDATE user SET is_admin = TRUE WHERE email = 'matt@envoydesign.com';

-- Verify the change
SELECT id, username, email, is_admin, is_verified 
FROM user 
WHERE email = 'matt@envoydesign.com';
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ matt@envoydesign.com set as admin user!"
else
    echo ""
    echo "❌ Failed to set admin user"
    exit 1
fi

