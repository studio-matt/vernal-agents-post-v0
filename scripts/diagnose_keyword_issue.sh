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
echo "📋 Step 3: Check recent backend logs for keyword usage..."
echo "---"
sudo journalctl -u vernal-agents --since "2 hours ago" | \
  grep -E "$CAMPAIGN_ID|CRITICAL.*Keywords|keywords received|keywords being used|First keyword|Searching DuckDuckGo" | \
  tail -30

echo ""
echo "📋 Step 4: Check if 'pug' or 'looking' appears in logs..."
echo "---"
sudo journalctl -u vernal-agents --since "2 hours ago" | \
  grep -iE "pug|looking" | \
  grep -E "$CAMPAIGN_ID|keywords|CRITICAL" | \
  tail -20

echo ""
echo "✅ Diagnostic complete!"
echo ""
echo "What to look for:"
echo "1. Database keywords: Should show 'pug' - if it shows 'looking', that's the problem"
echo "2. Scraped URLs: Check if URLs are about 'looking' (TV series) vs 'pug' (dogs)"
echo "3. Logs: Should show 'Keywords received: [\"pug\"]' - if it shows 'looking', trace backwards"
echo "4. First keyword in logs: Should be 'pug'"

