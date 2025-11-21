#!/bin/bash
# Comprehensive diagnostic for campaign df3b03fa-45fe-4644-98bb-77e8e7a52281

CAMPAIGN_ID="df3b03fa-45fe-4644-98bb-77e8e7a52281"

echo "🔍 Comprehensive Diagnostic for Campaign: $CAMPAIGN_ID"
echo "=================================================="
echo ""

# 1. Check campaign in database
echo "📋 1. CAMPAIGN DATABASE RECORD"
echo "-------------------------------"
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    campaign_id,
    campaign_name,
    type,
    status,
    site_base_url,
    keywords,
    urls,
    created_at,
    updated_at
FROM campaigns
WHERE campaign_id = '$CAMPAIGN_ID';
EOF
echo ""

# 2. Check scraped data
echo "📋 2. SCRAPED DATA IN DATABASE"
echo "-------------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN source_url LIKE 'error:%' THEN 1 ELSE 0 END) as error_rows,
    SUM(CASE WHEN source_url LIKE 'placeholder:%' THEN 1 ELSE 0 END) as placeholder_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' THEN 1 ELSE 0 END) as valid_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_with_text
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID';
EOF
echo ""

# 3. Show sample rows
echo "📋 3. SAMPLE DATA ROWS (first 10)"
echo "----------------------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    id,
    source_url,
    CASE 
        WHEN source_url LIKE 'error:%' THEN 'ERROR'
        WHEN source_url LIKE 'placeholder:%' THEN 'PLACEHOLDER'
        ELSE 'VALID'
    END as row_type,
    LENGTH(extracted_text) as text_length,
    LEFT(extracted_text, 100) as text_sample,
    fetched_at
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID'
ORDER BY fetched_at DESC
LIMIT 10;
EOF
echo ""

# 4. Check backend logs for this campaign
echo "📋 4. BACKEND LOGS - CAMPAIGN CREATION"
echo "--------------------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*POST.*analyze|POST.*analyze.*$CAMPAIGN_ID|Creating campaign.*$CAMPAIGN_ID" | \
    tail -10
echo ""

# 5. Check scraping activity
echo "📋 5. SCRAPING ACTIVITY"
echo "-----------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*scrap|scrap.*$CAMPAIGN_ID|🚀.*$CAMPAIGN_ID|✅.*Web scraping.*$CAMPAIGN_ID|📊 Summary.*$CAMPAIGN_ID" | \
    tail -20
echo ""

# 6. Check database saving
echo "📋 6. DATABASE SAVING"
echo "---------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*💾|💾.*$CAMPAIGN_ID|Finished saving.*$CAMPAIGN_ID|Successfully committed.*$CAMPAIGN_ID" | \
    tail -10
echo ""

# 7. Check for errors
echo "📋 7. ERRORS"
echo "-------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*ERROR|$CAMPAIGN_ID.*CRITICAL|$CAMPAIGN_ID.*❌|json.*$CAMPAIGN_ID|cannot access.*$CAMPAIGN_ID" | \
    tail -20
echo ""

# 8. Check campaign status updates
echo "📋 8. CAMPAIGN STATUS UPDATES"
echo "-----------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*READY|$CAMPAIGN_ID.*INCOMPLETE|$CAMPAIGN_ID.*PROCESSING|Campaign.*$CAMPAIGN_ID.*marked|valid_data_count.*$CAMPAIGN_ID" | \
    tail -15
echo ""

# 9. Check sitemap parsing (for site builder)
echo "📋 9. SITEMAP PARSING (if site builder)"
echo "----------------------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*sitemap|sitemap.*$CAMPAIGN_ID|Site Builder.*$CAMPAIGN_ID|🏗️.*$CAMPAIGN_ID|Found.*URLs.*$CAMPAIGN_ID" | \
    tail -15
echo ""

# 10. Check research endpoint response
echo "📋 10. RESEARCH ENDPOINT TEST"
echo "-----------------------------"
echo "Testing /campaigns/$CAMPAIGN_ID/research endpoint..."
curl -s -H "Authorization: Bearer $(grep -o 'Bearer [^"]*' ~/.config/cursor/settings.json 2>/dev/null || echo 'YOUR_TOKEN')" \
    "https://themachine.vernalcontentum.com/campaigns/$CAMPAIGN_ID/research" | \
    jq '.total_rows, .valid_texts, .valid_urls, .has_data' 2>/dev/null || echo "Could not fetch research data"
echo ""

echo "✅ Diagnostic complete!"
echo ""
echo "Key things to check:"
echo "  - Campaign status should be READY_TO_ACTIVATE if successful"
echo "  - valid_rows should be > 0 for data to be available"
echo "  - Check errors section for any issues during scraping/saving"
echo "  - For site builder: Check sitemap parsing section for URL extraction"

