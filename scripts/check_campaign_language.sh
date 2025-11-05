#!/bin/bash
# Check campaign for language issues

CAMPAIGN_ID="$1"
if [ -z "$CAMPAIGN_ID" ]; then
    echo "Usage: $0 <campaign_id>"
    exit 1
fi

echo "🔍 Checking campaign language issues: $CAMPAIGN_ID"
echo ""

# Load environment
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# Check campaign keywords/query
echo "📊 Campaign keywords/query:"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
SELECT 
    campaign_name,
    query,
    keywords,
    type
FROM campaigns 
WHERE campaign_id = '$CAMPAIGN_ID';
EOF

echo ""
echo "📝 Sample of scraped text (first 500 chars):"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF 2>/dev/null | grep -v "^$"
SELECT 
    source_url,
    LEFT(extracted_text, 500) as text_sample
FROM campaign_raw_data 
WHERE campaign_id = '$CAMPAIGN_ID'
LIMIT 3;
EOF

echo ""
echo "✅ Check complete - Review the keywords/query above to see if they might trigger non-English results"

