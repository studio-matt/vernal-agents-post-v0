#!/bin/bash
# Check what keywords are stored in the database for a campaign

CAMPAIGN_ID="${1}"

if [ -z "$CAMPAIGN_ID" ]; then
    echo "Usage: $0 <campaign_id>"
    echo "Example: $0 a298b592-411c-4a48-9ea3-10d397d3d84c"
    exit 1
fi

cd /home/ubuntu/vernal-agents-post-v0

# Load environment variables
if [ -f .env ]; then
    source <(grep -E '^DB_' .env | sed 's/^/export /')
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "🔍 Checking keywords for campaign: $CAMPAIGN_ID"
echo ""

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
SELECT 
    campaign_id,
    campaign_name,
    keywords,
    type,
    description,
    status
FROM campaigns
WHERE campaign_id = '$CAMPAIGN_ID';
EOF

