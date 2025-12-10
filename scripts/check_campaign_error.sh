#!/bin/bash
# Script to check actual backend error for campaigns endpoint

echo "🔍 Checking backend logs for campaign endpoint errors..."
echo ""

# Get recent errors
echo "📋 Recent errors from /campaigns endpoints:"
sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -A 30 -E "campaigns|ERROR|❌|Traceback|AttributeError|KeyError|TypeError" | tail -100

echo ""
echo "📋 Testing /campaigns endpoint directly:"
curl -v http://127.0.0.1:8000/campaigns 2>&1 | head -50

echo ""
echo "📋 Full error traceback (if any):"
sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -B 5 -A 50 "Traceback" | tail -100

