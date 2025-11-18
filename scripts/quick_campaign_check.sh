#!/bin/bash
# Quick inline campaign diagnostic - can be run directly without git pull
# Usage: bash quick_campaign_check.sh <campaign_id>

CAMPAIGN_ID="$1"
if [ -z "$CAMPAIGN_ID" ]; then
    echo "❌ Usage: bash quick_campaign_check.sh <campaign_id>"
    exit 1
fi

echo "🔍 Quick Diagnostic for Campaign: $CAMPAIGN_ID"
echo "=============================================="
echo ""

# Load environment
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# 1. Campaign info
echo "📊 1. CAMPAIGN INFO"
echo "-------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    campaign_id,
    campaign_name,
    type,
    status,
    site_base_url,
    created_at,
    updated_at
FROM campaigns 
WHERE campaign_id = '$CAMPAIGN_ID';
EOF
echo ""

# 2. Raw data summary
echo "📊 2. RAW DATA SUMMARY"
echo "----------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN source_url LIKE 'error:%' THEN 1 ELSE 0 END) as error_rows,
    SUM(CASE WHEN source_url LIKE 'placeholder:%' THEN 1 ELSE 0 END) as placeholder_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' THEN 1 ELSE 0 END) as valid_rows,
    SUM(CASE WHEN extracted_text IS NOT NULL AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_texts
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID';
EOF
echo ""

# 3. Error rows
echo "📊 3. ERROR ROWS (first 5)"
echo "--------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    source_url,
    LEFT(extracted_text, 300) as error_message,
    fetched_at
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID' 
  AND (source_url LIKE 'error:%' OR source_url LIKE 'placeholder:%')
ORDER BY fetched_at DESC
LIMIT 5;
EOF
echo ""

# 4. Recent logs
echo "📋 4. RECENT LOGS (last 30 lines)"
echo "----------------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID|a3811d41" | \
    tail -30
echo ""

# 5. Sitemap parsing logs
echo "📋 5. SITEMAP PARSING LOGS"
echo "---------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*sitemap|sitemap.*$CAMPAIGN_ID|Site Builder.*$CAMPAIGN_ID|🏗️.*$CAMPAIGN_ID" | \
    tail -20
echo ""

# 6. Error logs
echo "📋 6. ERROR LOGS"
echo "----------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*[Ee]rror|❌.*$CAMPAIGN_ID|Failed.*$CAMPAIGN_ID" | \
    tail -20
echo ""

echo "✅ Quick diagnostic complete"

