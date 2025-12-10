#!/bin/bash
# Script to check actual backend error for campaigns endpoint

echo "🔍 Checking backend logs for campaign endpoint errors..."
echo ""

# Get recent errors
echo "📋 Recent errors from /campaigns endpoints:"
sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -A 30 -E "campaigns|ERROR|❌|Traceback|AttributeError|KeyError|TypeError|500|Internal Server Error" | tail -100

echo ""
echo "📋 All recent requests to /campaigns endpoints:"
sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -E "campaigns|GET.*campaigns|POST.*campaigns" | tail -50

echo ""
echo "📋 Full error traceback (if any):"
sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -B 5 -A 50 "Traceback\|Exception\|Error fetching campaign" | tail -150

echo ""
echo "💡 To test with authentication, get a JWT token from the frontend and run:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' http://127.0.0.1:8000/campaigns"
