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
echo "📋 Step 3: Find when this campaign was last scraped (from database)..."
echo "---"
SCRAPE_TIME=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -Nse \
  "SELECT MAX(fetched_at) FROM campaign_raw_data WHERE campaign_id = '$CAMPAIGN_ID';")

if [ -n "$SCRAPE_TIME" ] && [ "$SCRAPE_TIME" != "NULL" ]; then
    echo "✅ Last scraped: $SCRAPE_TIME"
    # Convert to format for journalctl (YYYY-MM-DD HH:MM:SS)
    SCRAPE_DATE=$(echo "$SCRAPE_TIME" | cut -d' ' -f1)
    echo "   Searching logs around: $SCRAPE_DATE"
    TIME_WINDOW="--since \"$SCRAPE_DATE\""
else
    echo "⚠️ No scrape time found, searching last 24 hours"
    TIME_WINDOW="--since \"24 hours ago\""
fi

echo ""
echo "📋 Step 4: Check what keywords were used for THIS campaign..."
echo "---"
sudo journalctl -u vernal-agents $TIME_WINDOW 2>/dev/null | \
  grep -E "$CAMPAIGN_ID" | \
  grep -E "CRITICAL.*Keywords|keywords received|keywords being used|Searching DuckDuckGo|DuckDuckGo returned|Starting web scraping" | \
  tail -20

if [ $? -ne 0 ] || [ -z "$(sudo journalctl -u vernal-agents $TIME_WINDOW 2>/dev/null | grep -E "$CAMPAIGN_ID")" ]; then
    echo "⚠️ No logs found for this campaign in that time window"
    echo "   Trying last 7 days..."
    sudo journalctl -u vernal-agents --since "7 days ago" 2>/dev/null | \
      grep -E "$CAMPAIGN_ID" | \
      grep -E "CRITICAL.*Keywords|keywords received|keywords being used" | \
      tail -10
fi

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

