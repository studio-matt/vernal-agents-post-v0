#!/bin/bash
# clear_research_cache.sh - Clear cached research agent insights
# Usage: ./clear_research_cache.sh [campaign_id] [agent_type]
# Examples:
#   ./clear_research_cache.sh 53a427d4-fa5a-4838-91a0-699837f601e1 topical-map
#   ./clear_research_cache.sh 53a427d4-fa5a-4838-91a0-699837f601e1  # Clear all agents for campaign
#   ./clear_research_cache.sh  # Clear all cached insights (use with caution!)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
source .env 2>/dev/null || true

if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Database credentials not found in .env file"
    exit 1
fi

CAMPAIGN_ID=$1
AGENT_TYPE=$2

if [ -z "$CAMPAIGN_ID" ] && [ -z "$AGENT_TYPE" ]; then
    echo "⚠️  WARNING: This will clear ALL cached research insights!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
    mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "DELETE FROM campaign_research_insights;"
    echo "✅ Cleared all cached research insights"
elif [ -z "$AGENT_TYPE" ]; then
    echo "Clearing all cached insights for campaign: $CAMPAIGN_ID"
    mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "DELETE FROM campaign_research_insights WHERE campaign_id = '${CAMPAIGN_ID}';"
    echo "✅ Cleared cached insights for campaign $CAMPAIGN_ID"
else
    echo "Clearing cached insights for campaign: $CAMPAIGN_ID, agent: $AGENT_TYPE"
    mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "DELETE FROM campaign_research_insights WHERE campaign_id = '${CAMPAIGN_ID}' AND agent_type = '${AGENT_TYPE}';"
    echo "✅ Cleared cached insights for campaign $CAMPAIGN_ID, agent $AGENT_TYPE"
fi

