#!/bin/bash
# Check actual data for campaign df3b03fa-45fe-4644-98bb-77e8e7a52281

CAMPAIGN_ID="df3b03fa-45fe-4644-98bb-77e8e7a52281"

echo "🔍 Checking actual data for campaign: $CAMPAIGN_ID"
echo ""

cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# Show all rows with details
echo "📋 ALL DATA ROWS:"
echo "----------------"
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
    LEFT(extracted_text, 500) as text_preview,
    fetched_at,
    LEFT(meta_json, 200) as meta_preview
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID'
ORDER BY fetched_at DESC;
EOF
echo ""

# Check if research data exists
echo "📋 RESEARCH DATA CACHE:"
echo "----------------------"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null
SELECT 
    campaign_id,
    word_cloud_json IS NOT NULL as has_wordcloud,
    topics_json IS NOT NULL as has_topics,
    entities_json IS NOT NULL as has_entities,
    hashtags_json IS NOT NULL as has_hashtags,
    LENGTH(word_cloud_json) as wordcloud_length,
    LENGTH(topics_json) as topics_length,
    LEFT(word_cloud_json, 200) as wordcloud_preview,
    LEFT(topics_json, 200) as topics_preview,
    created_at,
    updated_at
FROM campaign_research_data
WHERE campaign_id = '$CAMPAIGN_ID';
EOF
echo ""

# Check backend logs for scraping
echo "📋 SCRAPING LOGS:"
echo "-----------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID" | \
    grep -E "scrap|🚀|✅.*Web scraping|📊 Summary|💾|Finished saving|READY_TO_ACTIVATE|Research endpoint" | \
    tail -30
echo ""

# Check research endpoint logs
echo "📋 RESEARCH ENDPOINT LOGS:"
echo "---------------------------"
sudo journalctl -u vernal-agents --since "24 hours ago" | \
    grep -E "$CAMPAIGN_ID.*research|Research endpoint.*$CAMPAIGN_ID|extract_topics.*$CAMPAIGN_ID|wordCloud.*$CAMPAIGN_ID" | \
    tail -30
echo ""
