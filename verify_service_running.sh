#!/bin/bash
# Quick service verification script
# Run this on the server to check if service is actually responding

echo "=== SERVICE VERIFICATION ==="
echo ""

# 1. Check service status
echo "1. Systemd service status:"
sudo systemctl status vernal-agents --no-pager | head -10
echo ""

# 2. Check if port 8000 is listening
echo "2. Port 8000 listening check:"
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Port 8000 is listening"
    sudo lsof -i :8000 | head -3
else
    echo "❌ Port 8000 is NOT listening"
    echo "   Service may have crashed or not started"
fi
echo ""

# 3. Test direct connection to FastAPI
echo "3. Testing direct connection to FastAPI (localhost:8000):"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://127.0.0.1:8000/health 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ FastAPI is responding (HTTP 200)"
    echo "   Response: $BODY"
else
    echo "❌ FastAPI is NOT responding correctly"
    echo "   HTTP Code: $HTTP_CODE"
    echo "   Response: $BODY"
    echo ""
    echo "   Checking recent service logs..."
    sudo journalctl -u vernal-agents --since "2 minutes ago" --no-pager | tail -30
fi
echo ""

# 4. Test OPTIONS preflight directly
echo "4. Testing OPTIONS preflight to localhost:8000:"
OPTIONS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -i 2>&1)

if echo "$OPTIONS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present in OPTIONS response"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control" | head -5
else
    echo "❌ CORS headers MISSING in OPTIONS response"
    echo "   Full response:"
    echo "$OPTIONS_RESPONSE" | head -15
fi
echo ""

# 5. Test through nginx
echo "5. Testing through nginx (public URL):"
NGINX_RESPONSE=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -i 2>&1)

HTTP_CODE_NGINX=$(echo "$NGINX_RESPONSE" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}')
echo "   HTTP Status: $HTTP_CODE_NGINX"

if [ "$HTTP_CODE_NGINX" = "502" ]; then
    echo "❌ 502 Bad Gateway - nginx can't reach FastAPI"
    echo "   This means FastAPI is not running or not listening on port 8000"
elif echo "$NGINX_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present through nginx"
    echo "$NGINX_RESPONSE" | grep -i "access-control" | head -5
else
    echo "❌ CORS headers MISSING through nginx"
    echo "   Response headers:"
    echo "$NGINX_RESPONSE" | head -15
fi
echo ""

# 6. Check for Python import errors
echo "6. Testing if main.py can be imported (syntax check):"
cd /home/ubuntu/vernal-agents-post-v0
if python3 -c "import main" 2>&1 | grep -q "SyntaxError\|IndentationError\|ImportError"; then
    echo "❌ Python import FAILED - syntax or import error"
    python3 -c "import main" 2>&1 | head -20
else
    echo "✅ Python import successful (no syntax errors)"
fi
echo ""

# 7. Check recent service logs for errors
echo "7. Recent service errors (last 20 lines):"
sudo journalctl -u vernal-agents --since "5 minutes ago" --no-pager | grep -iE "error|exception|traceback|failed|cors" | tail -20 || echo "   No recent errors found"
echo ""

# Summary
echo "=== SUMMARY ==="
if [ "$HTTP_CODE" = "200" ] && echo "$OPTIONS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ Service is running and CORS is working on localhost"
    if [ "$HTTP_CODE_NGINX" != "502" ] && echo "$NGINX_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
        echo "✅ Service is working through nginx with CORS"
        echo ""
        echo "If browser still shows CORS errors:"
        echo "1. Clear browser cache (Ctrl+Shift+Delete)"
        echo "2. Try incognito/private mode"
        echo "3. Check browser console for actual error"
    else
        echo "⚠️  Service works locally but not through nginx"
        echo "   Check nginx configuration and proxy settings"
    fi
else
    echo "❌ Service is NOT working correctly"
    echo ""
    echo "Next steps:"
    echo "1. Restart service: sudo systemctl restart vernal-agents"
    echo "2. Wait 30-60 seconds for initialization"
    echo "3. Run this script again"
    echo "4. Check logs: sudo journalctl -u vernal-agents -f"
fi

