#!/bin/bash
# Diagnose keyword issue for a specific campaign
# Shows where keywords might have changed from "pug" to "looking"

CAMPAIGN_ID="${1:-a298b592-411c-4a48-9ea3-10d397d3d84c}"

echo "🔍 Diagnosing keyword issue for campaign: $CAMPAIGN_ID"
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Load environment variables
if [ -f .env ]; then
    source <(grep -E '^DB_' .env | sed 's/^/export /')
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "📋 Step 1: Check keywords stored in database..."
echo "---"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SELECT 
    campaign_id,
    campaign_name,
    keywords,
    type,
    description,
    status,
    topics
FROM campaigns
WHERE campaign_id = '$CAMPAIGN_ID';
EOF

echo ""
echo "📋 Step 2: Check what URLs were actually scraped..."
echo "---"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SELECT 
    source_url,
    LEFT(extracted_text, 100) as text_sample,
    LENGTH(extracted_text) as text_length,
    fetched_at
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID'
ORDER BY fetched_at DESC
LIMIT 10;
EOF

echo ""
echo "📋 Step 3: Check ALL logs for this campaign (including older ones)..."
echo "---"
echo "Searching for when this campaign was built..."
sudo journalctl -u vernal-agents | \
  grep -E "$CAMPAIGN_ID.*analyze|$CAMPAIGN_ID.*Starting web scraping|$CAMPAIGN_ID.*Keywords" | \
  tail -20

echo ""
echo "📋 Step 4: Check what keywords were actually used when scraping..."
echo "---"
sudo journalctl -u vernal-agents | \
  grep -E "$CAMPAIGN_ID.*CRITICAL.*Keywords|$CAMPAIGN_ID.*Searching DuckDuckGo|$CAMPAIGN_ID.*DuckDuckGo returned" | \
  tail -20

echo ""
echo "📋 Step 5: Check scraped URLs to infer what was searched..."
echo "---"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SELECT 
    source_url,
    CASE 
        WHEN source_url LIKE '%looking%' OR source_url LIKE '%Looking%' THEN 'LOOKING (TV series)'
        WHEN source_url LIKE '%pug%' OR source_url LIKE '%Pug%' THEN 'PUG (dog)'
        ELSE 'OTHER'
    END as content_type,
    fetched_at
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID'
ORDER BY fetched_at DESC;
EOF

echo ""
echo "✅ Diagnostic complete!"
echo ""
echo "What to look for:"
echo "1. Database keywords: Should show 'pug' - if it shows 'looking', that's the problem"
echo "2. Scraped URLs: Check if URLs are about 'looking' (TV series) vs 'pug' (dogs)"
echo "3. Logs: Should show 'Keywords received: [\"pug\"]' - if it shows 'looking', trace backwards"
echo "4. First keyword in logs: Should be 'pug'"

