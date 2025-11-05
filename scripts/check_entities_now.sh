#!/bin/bash
# Quick diagnostic to check entity extraction for a campaign

CAMPAIGN_ID="$1"
if [ -z "$CAMPAIGN_ID" ]; then
    echo "Usage: $0 <campaign_id>"
    exit 1
fi

echo "🔍 Checking entity extraction for campaign: $CAMPAIGN_ID"
echo ""

# Load environment
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# Check database for raw data
echo "📊 Checking database for raw data..."
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT source_url) as unique_urls,
    SUM(CASE WHEN extracted_text IS NOT NULL AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_texts,
    AVG(LENGTH(extracted_text)) as avg_text_length,
    MAX(LENGTH(extracted_text)) as max_text_length
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID';
EOF

echo ""
echo "🔍 Testing research endpoint directly..."
curl -s "http://127.0.0.1:8000/campaigns/${CAMPAIGN_ID}/research?limit=5" | jq '{
    status: .status,
    total_raw: .total_raw,
    entities: {
        persons: .entities.persons | length,
        organizations: .entities.organizations | length,
        locations: .entities.locations | length,
        dates: .entities.dates | length
    },
    sample_entities: {
        persons: .entities.persons[0:3],
        organizations: .entities.organizations[0:3],
        locations: .entities.locations[0:3],
        dates: .entities.dates[0:3]
    },
    diagnostics: .diagnostics
}'

echo ""
echo "📋 Checking backend logs for entity extraction errors..."
sudo journalctl -u vernal-agents --since "30 minutes ago" | \
    grep -E "${CAMPAIGN_ID}|extract_entities|Error extracting entities|text_processing" | \
    tail -20

echo ""
echo "✅ Diagnostic complete"

