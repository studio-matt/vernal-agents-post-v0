#!/bin/bash
# Check if database saving worked for the campaign

CAMPAIGN_ID="9d270f97-743f-4f50-8faa-f4ac8ad8c321"

echo "🔍 Checking database saving for campaign $CAMPAIGN_ID..."
echo ""

# Check all logs from 18:52:00 to 18:53:00 (around scraping completion)
echo "📋 All activity from 18:52:00 to 18:53:00:"
sudo journalctl -u vernal-agents --since "18:52:00" --until "18:53:00" | \
    grep -E "$CAMPAIGN_ID|💾|Finished|Committing|Successfully committed|json|ERROR|CRITICAL" | \
    tail -30
echo ""

# Check specifically for database operations
echo "📋 Database Operations:"
sudo journalctl -u vernal-agents --since "18:52:00" --until "18:53:00" | \
    grep -E "$CAMPAIGN_ID" | \
    grep -E "💾|Committing|committed|saving|database|INSERT|campaign_raw_data" | \
    tail -20
echo ""

# Check for any errors
echo "📋 Errors (should be NONE):"
sudo journalctl -u vernal-agents --since "18:52:00" --until "18:53:00" | \
    grep -E "$CAMPAIGN_ID.*ERROR|$CAMPAIGN_ID.*CRITICAL|$CAMPAIGN_ID.*json|cannot access" | \
    tail -10
if [ $? -ne 0 ]; then
    echo "✅ No errors found!"
fi
echo ""

# Check campaign status updates
echo "📋 Campaign Status Updates:"
sudo journalctl -u vernal-agents --since "18:52:00" | \
    grep -E "$CAMPAIGN_ID.*READY|$CAMPAIGN_ID.*INCOMPLETE|Campaign.*$CAMPAIGN_ID.*marked|valid_data_count" | \
    tail -10
echo ""

echo "✅ Check complete!"
echo ""
echo "If you see '💾 Finished saving' or 'Successfully committed' without errors, the fix worked!"

