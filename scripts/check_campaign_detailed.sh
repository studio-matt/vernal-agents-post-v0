#!/bin/bash
# Comprehensive campaign diagnostic script
# Usage: ./check_campaign_detailed.sh <campaign_id>

CAMPAIGN_ID="$1"
if [ -z "$CAMPAIGN_ID" ]; then
    echo "❌ Usage: $0 <campaign_id>"
    exit 1
fi

echo "🔍 Comprehensive Diagnostic for Campaign: $CAMPAIGN_ID"
echo "=================================================="
echo ""

# Load environment
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# 1. Check campaign in database
echo "📊 1. CAMPAIGN DATABASE INFO"
echo "----------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
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

# 2. Check raw data rows
echo "📊 2. RAW DATA ROWS"
echo "-------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
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

# 3. Show error rows details
echo "📊 3. ERROR ROWS DETAILS"
echo "-------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
SELECT 
    source_url,
    LEFT(extracted_text, 200) as error_message,
    fetched_at,
    meta_json
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID' 
  AND (source_url LIKE 'error:%' OR source_url LIKE 'placeholder:%')
ORDER BY fetched_at DESC
LIMIT 10;
EOF
echo ""

# 4. Show valid rows sample
echo "📊 4. VALID ROWS SAMPLE (first 5)"
echo "---------------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
SELECT 
    source_url,
    LENGTH(extracted_text) as text_length,
    fetched_at
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID' 
  AND source_url NOT LIKE 'error:%' 
  AND source_url NOT LIKE 'placeholder:%'
ORDER BY fetched_at DESC
LIMIT 5;
EOF
echo ""

# 5. Check backend logs for this campaign
echo "📋 5. BACKEND LOGS - RECENT ACTIVITY"
echo "-------------------------------------"
echo "Searching logs for campaign ID: $CAMPAIGN_ID"
echo ""
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID|a3811d41" | \
    tail -50
echo ""

# 6. Check for sitemap parsing logs
echo "📋 6. SITEMAP PARSING LOGS"
echo "--------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*sitemap|sitemap.*$CAMPAIGN_ID|Site Builder.*$CAMPAIGN_ID|🏗️.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 7. Check for scraping logs
echo "📋 7. SCRAPING LOGS"
echo "-------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*scrap|scrap.*$CAMPAIGN_ID|Scraping.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 8. Check for errors
echo "📋 8. ERROR LOGS"
echo "----------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*[Ee]rror|❌.*$CAMPAIGN_ID|Failed.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 9. Check analysis task status
echo "📋 9. ANALYSIS TASK STATUS"
echo "--------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*task|Task.*$CAMPAIGN_ID|📊.*$CAMPAIGN_ID|progress.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 10. Check research endpoint response
echo "📋 10. RESEARCH ENDPOINT TEST"
echo "-----------------------------"
echo "Testing /campaigns/$CAMPAIGN_ID/research endpoint..."
curl -s "http://127.0.0.1:8000/campaigns/${CAMPAIGN_ID}/research?limit=5" | jq '{
    status: .status,
    total_raw: .total_raw,
    diagnostics: {
        total_rows: .diagnostics.total_rows,
        valid_urls: .diagnostics.valid_urls,
        valid_texts: .diagnostics.valid_texts,
        has_errors: .diagnostics.has_errors,
        errors_count: (.diagnostics.errors | length),
        errors: .diagnostics.errors[0:3]
    }
}' 2>/dev/null || echo "❌ Failed to call research endpoint"
echo ""

echo "✅ Diagnostic complete"
echo ""
echo "💡 Next steps:"
echo "   - If you see error rows, check the error_message column"
echo "   - If sitemap parsing failed, check the sitemap_parsing logs"
echo "   - If scraping failed, check the scraping logs"
echo "   - If campaign status is INCOMPLETE, try 'Reset Status' and rebuild"

