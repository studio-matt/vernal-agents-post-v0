#!/bin/bash
# Find actual campaign analysis logs (not just status polling)

# Get campaign ID from user or use the one from logs
CAMPAIGN_ID="${1:-798641df-4ed8-4779-9712-03e5f6082444}"
TASK_ID="${2:-ba5f9485-7627-4237-875d-ebe185a20269}"

echo "🔍 Finding campaign analysis logs..."
echo "Campaign ID: $CAMPAIGN_ID"
echo "Task ID: $TASK_ID"
echo ""

# 1. Check for POST /analyze request
echo "📋 1. CAMPAIGN CREATION REQUEST (POST /analyze)"
echo "-----------------------------------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "POST.*analyze|📥 INCOMING REQUEST.*POST.*analyze" | \
    grep -A 5 -B 5 "$CAMPAIGN_ID\|$TASK_ID" | \
    tail -30
echo ""

# 2. Check for actual scraping activity
echo "📋 2. SCRAPING ACTIVITY"
echo "-----------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "$CAMPAIGN_ID.*scrap|scrap.*$CAMPAIGN_ID|🚀 Starting web scraping|✅ Web scraping completed|❌ CRITICAL.*Scraping|📊 Summary" | \
    tail -30
echo ""

# 3. Check for errors
echo "📋 3. ERRORS AND WARNINGS"
echo "-------------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "$CAMPAIGN_ID.*[Ee]rror|❌.*$CAMPAIGN_ID|⚠️.*$CAMPAIGN_ID|Failed.*$CAMPAIGN_ID|CRITICAL.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 4. Check for task progress updates
echo "📋 4. TASK PROGRESS UPDATES"
echo "--------------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "$TASK_ID|$CAMPAIGN_ID.*progress|set_task|📊.*progress" | \
    tail -30
echo ""

# 5. Check for database operations
echo "📋 5. DATABASE OPERATIONS"
echo "-------------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "$CAMPAIGN_ID.*💾|💾.*$CAMPAIGN_ID|Committing.*$CAMPAIGN_ID|Database.*$CAMPAIGN_ID" | \
    tail -30
echo ""

# 6. Check for any activity with this campaign
echo "📋 6. ALL ACTIVITY FOR THIS CAMPAIGN"
echo "------------------------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "$CAMPAIGN_ID|$TASK_ID" | \
    grep -v "GET.*analyze/status" | \
    tail -50
echo ""

# 7. Check if campaign was actually created
echo "📋 7. CAMPAIGN CREATION"
echo "-----------------------"
sudo journalctl -u vernal-agents --since "1 hour ago" | \
    grep -E "Creating campaign|Campaign created|campaign_id.*$CAMPAIGN_ID" | \
    tail -20
echo ""

echo "✅ Diagnostic complete!"
echo ""
echo "If you see NO logs for POST /analyze:"
echo "  - Campaign creation request never reached the backend"
echo "  - Check frontend is calling the correct URL"
echo "  - Check nginx is proxying requests correctly"
echo ""
echo "If you see POST /analyze but no scraping logs:"
echo "  - Campaign was created but scraping never started"
echo "  - Check for errors in the logs above"
echo "  - Check if web_scraping module is available"
echo ""
echo "If you see scraping logs but no results:"
echo "  - Scraping ran but returned 0 results"
echo "  - Check Playwright/DuckDuckGo availability"
echo "  - Check network connectivity"

