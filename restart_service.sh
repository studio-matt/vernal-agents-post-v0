#!/bin/bash
# Restart backend service with verification
# Run this on the server: bash restart_service.sh

set -e

echo "=== RESTARTING BACKEND SERVICE ==="
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# 1. Pull latest code
echo "1. Pulling latest code..."
git fetch origin
git switch main
git pull --ff-only origin main
echo "✅ Code updated"
echo ""

# 2. Verify Python imports work
echo "2. Verifying Python imports..."
source venv/bin/activate
if python3 -c "import main" 2>&1 | grep -q "SyntaxError\|IndentationError\|ImportError\|NameError"; then
    echo "❌ Python import FAILED!"
    python3 -c "import main" 2>&1 | head -30
    exit 1
fi
echo "✅ Python imports successful"
echo ""

# 3. Stop service
echo "3. Stopping service..."
sudo systemctl stop vernal-agents || true
sleep 2
echo "✅ Service stopped"
echo ""

# 4. Kill any stuck processes
echo "4. Cleaning up stuck processes..."
sudo pkill -f "uvicorn main:app" || true
sleep 1
echo "✅ Cleanup complete"
echo ""

# 5. Start service
echo "5. Starting service..."
sudo systemctl start vernal-agents
echo "✅ Service started"
echo ""

# 6. Wait for initialization
echo "6. Waiting for service to initialize (30 seconds)..."
sleep 30
echo ""

# 7. Check service status
echo "7. Checking service status..."
if sudo systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is active"
else
    echo "❌ Service is NOT active!"
    sudo systemctl status vernal-agents --no-pager | head -20
    exit 1
fi
echo ""

# 8. Verify port is listening
echo "8. Verifying port 8000 is listening..."
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Port 8000 is listening"
else
    echo "❌ Port 8000 is NOT listening"
    echo "   Checking logs..."
    sudo journalctl -u vernal-agents --since "1 minute ago" --no-pager | tail -30
    exit 1
fi
echo ""

# 9. Test health endpoint
echo "9. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://127.0.0.1:8000/health 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health endpoint responding (HTTP 200)"
else
    echo "❌ Health endpoint NOT responding correctly (HTTP $HTTP_CODE)"
    echo "   Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# 10. Test CORS preflight
echo "10. Testing CORS preflight..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -i 2>&1)

if echo "$OPTIONS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control" | head -3
else
    echo "❌ CORS headers MISSING"
    echo "   Response:"
    echo "$OPTIONS_RESPONSE" | head -10
    exit 1
fi
echo ""

# 11. Test through nginx
echo "11. Testing through nginx..."
NGINX_RESPONSE=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -i 2>&1)

HTTP_CODE_NGINX=$(echo "$NGINX_RESPONSE" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}' || echo "unknown")

if [ "$HTTP_CODE_NGINX" = "502" ]; then
    echo "❌ 502 Bad Gateway - nginx can't reach FastAPI"
    echo "   Service may still be initializing, wait 30 more seconds"
elif echo "$NGINX_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS working through nginx (HTTP $HTTP_CODE_NGINX)"
else
    echo "⚠️  CORS headers missing through nginx (HTTP $HTTP_CODE_NGINX)"
    echo "   Response:"
    echo "$NGINX_RESPONSE" | head -10
fi
echo ""

echo "=== RESTART COMPLETE ==="
echo ""
echo "Service should now be working. If you still see CORS errors:"
echo "1. Clear browser cache (Ctrl+Shift+Delete)"
echo "2. Try incognito/private mode"
echo "3. Wait 30 more seconds for full initialization"
echo ""
echo "To monitor logs: sudo journalctl -u vernal-agents -f"

