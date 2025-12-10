#!/bin/bash
# Migration script to change image_url column from VARCHAR(255) to TEXT
# This fixes the "Data too long for column 'image_url'" error

echo "🔧 Migrating image_url column from VARCHAR(255) to TEXT..."
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run this from the backend directory."
    exit 1
fi

# Source .env to get database credentials
source .env

# Check if required variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Database credentials not found in .env file"
    echo "Required: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
    exit 1
fi

echo "📋 Database: $DB_NAME on $DB_HOST"
echo ""

# Run the migration
echo "🔄 Running ALTER TABLE command..."
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" << EOF
ALTER TABLE content MODIFY COLUMN image_url TEXT NULL;
SELECT 'Migration completed successfully!' AS status;
DESCRIBE content;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo "The image_url column is now TEXT and can store long DALL·E URLs."
else
    echo ""
    echo "❌ Migration failed. Please check the error above."
    exit 1
fi

