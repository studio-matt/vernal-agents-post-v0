#!/bin/bash
# Check the most recent campaign created after the fix

echo "🔍 Checking most recent campaign activity..."
echo ""

# Find the most recent POST /analyze request
echo "📋 Most recent campaign creation:"
sudo journalctl -u vernal-agents --since "30 minutes ago" | \
    grep -E "POST.*analyze|📥 INCOMING REQUEST.*POST.*analyze" | \
    tail -1
echo ""

# Get the timestamp of the most recent campaign
LATEST_TIME=$(sudo journalctl -u vernal-agents --since "30 minutes ago" | \
    grep -E "POST.*analyze" | tail -1 | awk '{print $1, $2, $3}')

if [ -z "$LATEST_TIME" ]; then
    echo "❌ No recent campaign found"
    exit 1
fi

echo "📋 Campaign created around: $LATEST_TIME"
echo ""

# Check for scraping activity after that time
echo "📋 Scraping activity after campaign creation:"
sudo journalctl -u vernal-agents --since "$LATEST_TIME" | \
    grep -E "🚀 Starting web scraping|✅ Web scraping completed|📊 Summary|💾.*saving|💾.*Finished saving" | \
    tail -20
echo ""

# Check for errors after that time
echo "📋 Errors after campaign creation:"
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "$LATEST_TIME" | \
    grep -iE "❌|CRITICAL|ERROR.*json|cannot access local variable.*json" | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT errors:"
    sudo journalctl -u vernal-agents --since "$LATEST_TIME" | \
        grep -iE "❌|CRITICAL|ERROR.*json|cannot access local variable.*json" | \
        tail -10
else
    echo "✅ No errors found!"
fi
echo ""

# Check for database saving activity
echo "📋 Database saving activity:"
sudo journalctl -u vernal-agents --since "$LATEST_TIME" | \
    grep -E "💾.*saving|💾.*Finished saving|Committing.*rows|Successfully committed" | \
    tail -10
echo ""

# Check for campaign completion
echo "📋 Campaign completion status:"
sudo journalctl -u vernal-agents --since "$LATEST_TIME" | \
    grep -E "READY_TO_ACTIVATE|INCOMPLETE|100%|95%|Campaign.*marked as" | \
    tail -10
echo ""

echo "✅ Check complete!"
echo ""
echo "If you see '✅ Web scraping completed' and '💾 Finished saving' without json errors, the fix worked!"

