#!/bin/bash
# Test if admin settings requests are reaching nginx/backend
# Run this while making a request from the frontend

echo "🔍 TESTING ADMIN SETTINGS REQUESTS"
echo "==================================="
echo ""
echo "This script will watch for admin settings requests."
echo "👉 NOW: Go to https://machine.vernalcontentum.com/admin"
echo "👉 Click 'Platform Keys' → Try to save LinkedIn settings"
echo ""
echo "Watching logs (press Ctrl+C to stop)..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Clear screen
clear

echo "📊 WATCHING FOR ADMIN SETTINGS REQUESTS"
echo "========================================"
echo ""
echo -e "${YELLOW}Terminal 1: Nginx Access Logs${NC}"
echo "----------------------------------------"
sudo tail -f /var/log/nginx/access.log 2>/dev/null | grep --line-buffered -E "admin/settings|linkedin" | while read line; do
    echo -e "${GREEN}✅ NGINX ACCESS:${NC} $line"
done &

NGINX_ACCESS_PID=$!

echo ""
echo -e "${YELLOW}Terminal 2: Nginx Error Logs${NC}"
echo "----------------------------------------"
sudo tail -f /var/log/nginx/error.log 2>/dev/null | grep --line-buffered -E "admin|linkedin|timeout|refused" | while read line; do
    echo -e "${RED}❌ NGINX ERROR:${NC} $line"
done &

NGINX_ERROR_PID=$!

echo ""
echo -e "${YELLOW}Terminal 3: Backend Logs${NC}"
echo "----------------------------------------"
sudo journalctl -u vernal-agents -f --no-pager 2>/dev/null | grep --line-buffered -E "admin/settings|linkedin|INCOMING|RESPONSE" | while read line; do
    echo -e "${GREEN}✅ BACKEND:${NC} $line"
done &

BACKEND_PID=$!

# Wait for Ctrl+C
trap "kill $NGINX_ACCESS_PID $NGINX_ERROR_PID $BACKEND_PID 2>/dev/null; exit" INT TERM

echo ""
echo -e "${GREEN}✅ All logs are being watched${NC}"
echo ""
echo "Make a request from the frontend now..."
echo "Press Ctrl+C to stop watching"
echo ""

wait

