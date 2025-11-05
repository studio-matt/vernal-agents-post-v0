#!/bin/bash
# Create system_settings table and insert default topic extraction prompt

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

echo "🔧 Creating system_settings table..."
echo "📋 Database: $DB_NAME @ $DB_HOST"

# Execute SQL script
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$SCRIPT_DIR/add_system_settings_table.sql"

if [ $? -eq 0 ]; then
    echo "✅ system_settings table created successfully!"
    echo "✅ Default topic extraction prompt inserted"
else
    echo "❌ Failed to create system_settings table"
    exit 1
fi

