#!/bin/bash
# diagnose_research_agent.sh - Diagnose research agent prompt/response mismatch
# Usage: ./diagnose_research_agent.sh {campaign_id} {agent_type}
# Example: ./diagnose_research_agent.sh fad936de-8696-47c6-94ca-cf54da1813c2 keyword

set -e

CAMPAIGN_ID=$1
AGENT_TYPE=$2

if [ -z "$CAMPAIGN_ID" ] || [ -z "$AGENT_TYPE" ]; then
    echo "Usage: $0 {campaign_id} {agent_type}"
    echo "Example: $0 fad936de-8696-47c6-94ca-cf54da1813c2 keyword"
    exit 1
fi

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
source .env 2>/dev/null || true

if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Database credentials not found in .env file"
    exit 1
fi

echo "=========================================="
echo "Research Agent Diagnostic: ${AGENT_TYPE}"
echo "Campaign ID: ${CAMPAIGN_ID}"
echo "=========================================="
echo ""

echo "=== 1. DATABASE PROMPT ==="
echo "Checking prompt stored in system_settings table..."
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT 
    setting_key,
    LEFT(setting_value, 1000) as prompt_preview,
    LENGTH(setting_value) as prompt_length,
    updated_at
  FROM system_settings
  WHERE setting_key = 'research_agent_${AGENT_TYPE}_prompt';
" 2>/dev/null || echo "❌ Failed to query database"

echo ""
echo "=== 2. BACKEND LOGS (last 10 minutes) ==="
echo "Searching for ${AGENT_TYPE} agent logs..."
sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | \
  grep -E "research.*${AGENT_TYPE}|${AGENT_TYPE}.*agent|prompt.*${AGENT_TYPE}|LLM.*${AGENT_TYPE}|Using prompt for ${AGENT_TYPE}|Formatted prompt|LLM response" | \
  tail -30 || echo "⚠️  No recent logs found (try triggering the agent from frontend)"

echo ""
echo "=== 3. CACHED INSIGHTS ==="
echo "Checking cached insights in database..."
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT 
    campaign_id,
    agent_type,
    LEFT(insights_text, 2000) as insights_preview,
    LENGTH(insights_text) as length,
    created_at,
    updated_at
  FROM campaign_research_insights
  WHERE campaign_id = '${CAMPAIGN_ID}' AND agent_type = '${AGENT_TYPE}';
" 2>/dev/null || echo "⚠️  No cached insights found (agent may not have run yet)"

echo ""
echo "=== 4. CAMPAIGN DATA ==="
echo "Checking if campaign has scraped data..."
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT 
    campaign_id,
    campaign_name,
    status,
    keywords,
    query,
    topics
  FROM campaign
  WHERE campaign_id = '${CAMPAIGN_ID}';
" 2>/dev/null || echo "❌ Campaign not found"

echo ""
echo "=== 5. RECOMMENDATIONS ==="
echo "To see full diagnostic:"
echo "1. Open browser DevTools (F12) → Console"
echo "2. Trigger ${AGENT_TYPE} agent from frontend"
echo "3. Watch for logs starting with: 🔍, 📊, 📝, ✅"
echo "4. Compare 'Raw response' with backend 'LLM response' log"
echo ""
echo "To watch backend logs in real-time:"
echo "  sudo journalctl -u vernal-agents -f | grep -E '${AGENT_TYPE}|prompt|LLM'"
echo ""
echo "=========================================="

