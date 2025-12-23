#!/bin/bash
# Check if backend is logging requests
# Run this while making a request from the frontend

echo "🔍 CHECKING BACKEND LOGS FOR ADMIN SETTINGS REQUESTS"
echo "===================================================="
echo ""
echo "Watch for 'INCOMING REQUEST' or 'admin/settings' in backend logs"
echo "Make a request from the frontend now..."
echo ""

# Watch backend logs
sudo journalctl -u vernal-agents -f --since "1 minute ago" | grep --line-buffered -E "INCOMING|admin/settings|linkedin|PUT|GET" | while read line; do
    echo "📥 $line"
done

