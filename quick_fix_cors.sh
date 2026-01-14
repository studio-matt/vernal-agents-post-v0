#!/bin/bash
# Quick CORS fix - restart service and verify it's working
# Run this on the server

set -e

echo "=== QUICK CORS FIX ==="
echo ""

# 1. Stop service
echo "1. Stopping service..."
sudo systemctl stop vernal-agents
sleep 2

# 2. Kill any stuck processes
echo "2. Killing any stuck processes..."
sudo pkill -f "python.*main.py" || true
sudo pkill -f "uvicorn" || true
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true
sleep 2

# 3. Verify port is free
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use, forcing cleanup..."
    sudo fuser -k 8000/tcp || true
    sleep 2
fi

# 4. Pull latest code
echo "3. Pulling latest code..."
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main

# 5. Verify .env exists
echo "4. Verifying .env file..."
if [ ! -f .env ]; then
    echo "❌ CRITICAL: .env file missing!"
    echo "   Restore from backup: cp /home/ubuntu/.env.backup .env"
    exit 1
fi
echo "✅ .env file exists"

# 6. Quick syntax check
echo "5. Checking for syntax errors..."
if python3 -c "import main" 2>&1 | grep -q "SyntaxError\|IndentationError"; then
    echo "❌ Syntax error found!"
    python3 -c "import main" 2>&1 | head -20
    exit 1
fi
echo "✅ No syntax errors"

# 7. Start service
echo "6. Starting service..."
sudo systemctl start vernal-agents
sleep 5

# 8. Wait for service to initialize (can take 30-60 seconds)
echo "7. Waiting for service to initialize (this can take 30-60 seconds)..."
for i in {1..12}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ Service is responding!"
        break
    else
        echo "   Waiting... ($i/12)"
        sleep 5
    fi
done

# 9. Verify service is running
echo "8. Verifying service status..."
if systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is ACTIVE"
else
    echo "❌ Service is NOT active"
    echo "   Checking logs..."
    sudo journalctl -u vernal-agents --since "1 minute ago" --no-pager | tail -30
    exit 1
fi

# 10. Test CORS
echo "9. Testing CORS..."
OPTIONS_TEST=$(curl -s -X OPTIONS http://127.0.0.1:8000/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -i 2>&1)

if echo "$OPTIONS_TEST" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS is working!"
    echo "$OPTIONS_TEST" | grep -i "access-control" | head -3
else
    echo "❌ CORS is NOT working"
    echo "   Response:"
    echo "$OPTIONS_TEST" | head -15
    echo ""
    echo "   Run full diagnostic: bash verify_service_running.sh"
    exit 1
fi

# 11. Test through nginx
echo "10. Testing through nginx..."
NGINX_TEST=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -i 2>&1)

HTTP_CODE=$(echo "$NGINX_TEST" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}')
if [ "$HTTP_CODE" = "502" ]; then
    echo "⚠️  502 Bad Gateway through nginx"
    echo "   Service works locally but nginx can't reach it"
    echo "   Check nginx configuration"
elif echo "$NGINX_TEST" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS working through nginx!"
else
    echo "⚠️  CORS not working through nginx"
    echo "   Check nginx configuration for CORS header interference"
fi

echo ""
echo "=== FIX COMPLETE ==="
echo ""
echo "If browser still shows CORS errors:"
echo "1. Clear browser cache (Ctrl+Shift+Delete)"
echo "2. Try incognito/private mode"
echo "3. Hard refresh (Ctrl+F5)"
echo ""
echo "To verify everything: bash verify_service_running.sh"

