#!/bin/bash
# Quick database check script for campaigns table
# Run: bash scripts/check_campaigns_db.sh

DB_USER="vernalcontentum_vernaluse"
DB_NAME="vernalcontentum_contentMachine"

echo "🔍 Checking campaigns database..."
echo "=================================="
echo ""

# Prompt for password
read -sp "Enter MySQL password for $DB_USER: " DB_PASS
echo ""

# Check if mysql command exists
if ! command -v mysql &> /dev/null; then
    echo "❌ mysql command not found. Install MySQL client first."
    exit 1
fi

echo "1️⃣ Counting campaigns..."
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT COUNT(*) as total_campaigns FROM campaigns;
"

echo ""
echo "2️⃣ Campaigns per user..."
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT user_id, COUNT(*) as count 
FROM campaigns 
GROUP BY user_id 
ORDER BY count DESC;
"

echo ""
echo "3️⃣ Checking indexes on campaigns table..."
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SHOW INDEXES FROM campaigns;
"

echo ""
echo "4️⃣ Checking table size..."
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
    table_rows
FROM information_schema.TABLES
WHERE table_schema = '$DB_NAME'
AND table_name = 'campaigns';
"

echo ""
echo "5️⃣ Testing query performance (EXPLAIN)..."
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
EXPLAIN SELECT * FROM campaigns WHERE user_id = 1 LIMIT 1;
"

echo ""
echo "6️⃣ Checking for missing indexes..."
mysql -u "$DB_USER" -p"$DB_NAME" -e "
SELECT 
    COLUMN_NAME,
    INDEX_NAME,
    NON_UNIQUE,
    SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE table_schema = '$DB_NAME'
AND table_name = 'campaigns'
AND COLUMN_NAME IN ('user_id', 'campaign_id', 'status')
ORDER BY COLUMN_NAME, SEQ_IN_INDEX;
"

echo ""
echo "✅ Database check complete!"
echo ""
echo "💡 If user_id doesn't have an index, create it with:"
echo "   CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);"
