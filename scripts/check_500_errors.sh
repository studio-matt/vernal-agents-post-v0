#!/bin/bash
echo "🔍 Checking 500 Errors for save-content-item and schedule-content"
echo "=========================================="
echo ""
echo "📋 Last 50 lines of service logs (most recent first):"
sudo journalctl -u vernal-agents -n 50 --no-pager | tail -50
echo ""
echo "=========================================="
echo "📋 Errors containing 'save-content-item' or 'save_content_item':"
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -A 20 -B 5 "save-content-item\|save_content_item\|Error saving content item" | tail -60
echo ""
echo "=========================================="
echo "📋 Errors containing 'schedule-content' or 'schedule_campaign_content':"
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -A 20 -B 5 "schedule-content\|schedule_campaign_content\|Error scheduling content" | tail -60
echo ""
echo "=========================================="
echo "📋 All ERROR and Traceback entries (last 100 lines):"
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -A 15 "ERROR\|Traceback\|Exception\|Error" | tail -100
echo ""
echo "=========================================="
echo "📋 Recent 500 status responses:"
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -A 10 -B 5 "500\|Internal Server Error" | tail -50
echo ""
echo "=========================================="
echo "✅ Diagnostic complete"

