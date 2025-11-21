#!/bin/bash
# Check the campaign created after the fix (9d270f97-743f-4f50-8faa-f4ac8ad8c321)

CAMPAIGN_ID="9d270f97-743f-4f50-8faa-f4ac8ad8c321"

echo "🔍 Checking campaign $CAMPAIGN_ID (created after fix)..."
echo ""

# 1. Check for scraping completion
echo "📋 1. Scraping Activity:"
sudo journalctl -u vernal-agents --since "18:51:00" | \
    grep -E "$CAMPAIGN_ID.*scrap|scrap.*$CAMPAIGN_ID|🚀|✅.*Web scraping|📊 Summary" | \
    tail -10
echo ""

# 2. Check for database saving
echo "📋 2. Database Saving Activity:"
sudo journalctl -u vernal-agents --since "18:51:00" | \
    grep -E "$CAMPAIGN_ID.*💾|💾.*$CAMPAIGN_ID|Committing.*$CAMPAIGN_ID|Successfully committed.*$CAMPAIGN_ID|Finished saving.*$CAMPAIGN_ID" | \
    tail -10
echo ""

# 3. Check for errors
echo "📋 3. Errors (should be NONE):"
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "18:51:00" | \
    grep -E "$CAMPAIGN_ID.*json|cannot access local variable.*json|❌.*$CAMPAIGN_ID" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No json errors found for this campaign!"
else
    echo "❌ Found $ERROR_COUNT errors:"
    sudo journalctl -u vernal-agents --since "18:51:00" | \
        grep -E "$CAMPAIGN_ID.*json|cannot access local variable.*json|❌.*$CAMPAIGN_ID" | \
        tail -10
fi
echo ""

# 4. Check for campaign completion status
echo "📋 4. Campaign Completion Status:"
sudo journalctl -u vernal-agents --since "18:51:00" | \
    grep -E "$CAMPAIGN_ID.*READY|READY.*$CAMPAIGN_ID|Campaign.*$CAMPAIGN_ID.*marked|100%|95%" | \
    tail -10
echo ""

# 5. Check database for saved data
echo "📋 5. Database Check (if you have DB access):"
echo "Run this SQL query to check if data was saved:"
echo ""
echo "SELECT COUNT(*) as total_rows,"
echo "  SUM(CASE WHEN source_url LIKE 'error:%' THEN 1 ELSE 0 END) as error_rows,"
echo "  SUM(CASE WHEN source_url NOT LIKE 'error:%' AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_rows"
echo "FROM campaign_raw_data"
echo "WHERE campaign_id = '$CAMPAIGN_ID';"
echo ""

echo "✅ Check complete!"
echo ""
echo "If you see '💾 Finished saving' and no json errors, the fix worked! 🎉"

