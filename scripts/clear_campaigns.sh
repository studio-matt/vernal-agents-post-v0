#!/bin/bash
# Clear all campaigns from database
# Usage: ./clear_campaigns.sh

set -e

echo "🗑️  Clearing all campaigns from database..."

# Load database credentials from .env file
if [ -f .env ]; then
    source <(grep -E '^DB_|^MYSQL_' .env | sed 's/^/export /')
fi

# Default values if not in .env
DB_HOST=${DB_HOST:-"50.6.198.220"}
DB_USER=${DB_USER:-"vernalcontentum_vernaluse"}
DB_PASSWORD=${DB_PASSWORD:-""}
DB_NAME=${DB_NAME:-"vernalcontentum_contentMachine"}

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ DB_PASSWORD not set in .env file"
    exit 1
fi

echo "📊 Checking current campaign count..."
CURRENT_COUNT=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -N -e "SELECT COUNT(*) FROM campaigns;" 2>/dev/null || echo "0")
echo "   Current campaigns: $CURRENT_COUNT"

if [ "$CURRENT_COUNT" -eq 0 ]; then
    echo "✅ Database already empty - no campaigns to delete"
    exit 0
fi

echo "⚠️  About to delete $CURRENT_COUNT campaigns..."
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Deleting all campaigns..."
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
DELETE FROM campaigns;
EOF

# Verify deletion
FINAL_COUNT=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -N -e "SELECT COUNT(*) FROM campaigns;" 2>/dev/null || echo "0")

if [ "$FINAL_COUNT" -eq 0 ]; then
    echo "✅ Successfully deleted all campaigns"
else
    echo "⚠️  Warning: Still $FINAL_COUNT campaigns remaining"
fi

echo "✅ Done!"

