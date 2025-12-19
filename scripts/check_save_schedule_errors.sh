#!/bin/bash
echo "🔍 Checking recent save-content-item and schedule-content errors..."
echo "=========================================="
echo ""
echo "📋 Recent save-content-item errors:"
sudo journalctl -u vernal-agents -n 100 --no-pager | grep -A 10 -B 5 "save-content-item\|save_content_item" | tail -30
echo ""
echo "📋 Recent schedule-content errors:"
sudo journalctl -u vernal-agents -n 100 --no-pager | grep -A 10 -B 5 "schedule-content\|schedule_campaign_content" | tail -30
echo ""
echo "📋 Recent 500 errors:"
sudo journalctl -u vernal-agents -n 100 --no-pager | grep -A 5 "500\|ERROR\|Traceback" | tail -40
