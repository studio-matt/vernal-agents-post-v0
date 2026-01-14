#!/bin/bash
# Complete CORS Fix Script
# Run this on the server to diagnose and fix CORS issues

set -e

echo "=== COMPLETE CORS FIX SCRIPT ==="
echo ""

# 1. Check service status
echo "1. Checking service status..."
if systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is ACTIVE"
else
    echo "❌ Service is NOT ACTIVE - starting it..."
    sudo systemctl start vernal-agents
    sleep 5
fi

# 2. Wait for service to fully initialize (agent creation takes 30-60 seconds)
echo ""
echo "2. Waiting for service to fully initialize (this can take 30-60 seconds)..."
for i in {1..12}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ Service is responding on port 8000"
        break
    else
        echo "   Waiting... ($i/12)"
        sleep 5
    fi
done

# 3. Check if port 8000 is listening
echo ""
echo "3. Checking if port 8000 is listening..."
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Port 8000 is listening"
    sudo lsof -i :8000 | head -3
else
    echo "❌ Port 8000 is NOT listening"
    echo "   Checking service logs for errors..."
    sudo journalctl -u vernal-agents --since "2 minutes ago" --no-pager | tail -30
    exit 1
fi

# 4. Test OPTIONS preflight directly to FastAPI
echo ""
echo "4. Testing OPTIONS preflight request to localhost:8000..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i 2>&1)

if echo "$OPTIONS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present in OPTIONS response"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control"
else
    echo "❌ CORS headers MISSING in OPTIONS response"
    echo "   Full response:"
    echo "$OPTIONS_RESPONSE" | head -20
    echo ""
    echo "   This means FastAPI CORS middleware is not working!"
    echo "   Checking service logs..."
    sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -iE "cors|error|exception" | tail -20
    exit 1
fi

# 5. Test OPTIONS preflight through nginx
echo ""
echo "5. Testing OPTIONS preflight request through nginx..."
NGINX_RESPONSE=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i 2>&1)

if echo "$NGINX_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present through nginx"
    echo "$NGINX_RESPONSE" | grep -i "access-control"
else
    echo "❌ CORS headers MISSING through nginx"
    HTTP_CODE=$(echo "$NGINX_RESPONSE" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}')
    echo "   HTTP Status: $HTTP_CODE"
    if [ "$HTTP_CODE" = "502" ]; then
        echo "   ⚠️  502 Bad Gateway - Backend not responding through nginx"
        echo "   This means nginx can't reach FastAPI on port 8000"
        echo "   Check: sudo journalctl -u vernal-agents --since '2 minutes ago' | tail -30"
    else
        echo "   Full response:"
        echo "$NGINX_RESPONSE" | head -20
    fi
fi

# 6. Check nginx configuration for CORS interference
echo ""
echo "6. Checking nginx configuration for CORS headers..."
NGINX_CORS=$(sudo grep -r "add_header.*Access-Control" /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "#" | head -5)
if [ -n "$NGINX_CORS" ]; then
    echo "⚠️  WARNING: nginx is adding CORS headers (this can interfere with FastAPI CORS)"
    echo "$NGINX_CORS"
    echo ""
    echo "   According to EMERGENCY_NET.md:"
    echo "   'Nginx must correctly proxy all requests to FastAPI. CORS must be handled by FastAPI, not nginx.'"
    echo ""
    echo "   The active nginx config should NOT have CORS headers."
    echo "   Check: /etc/nginx/sites-enabled/themachine"
    echo ""
    read -p "   Do you want to check the nginx config? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Active nginx config:"
        sudo cat /etc/nginx/sites-enabled/themachine | grep -A 10 -B 2 "add_header" || echo "   No CORS headers in active config (good!)"
    fi
else
    echo "✅ No CORS headers in active nginx config (correct - FastAPI handles CORS)"
fi

# 7. Verify main.py has CORS middleware registered correctly
echo ""
echo "7. Verifying CORS middleware is registered in main.py..."
cd /home/ubuntu/vernal-agents-post-v0
if grep -q "app.add_middleware(CORSMiddleware" main.py; then
    echo "✅ CORS middleware found in main.py"
    CORS_LINE=$(grep -n "app.add_middleware(CORSMiddleware" main.py | head -1)
    echo "   Found at line: $CORS_LINE"
    
    # Check if it's registered early (before exception handlers)
    CORS_LINE_NUM=$(echo "$CORS_LINE" | cut -d: -f1)
    if [ "$CORS_LINE_NUM" -lt 200 ]; then
        echo "✅ CORS middleware registered early (before line 200)"
    else
        echo "⚠️  WARNING: CORS middleware registered late (after line 200)"
        echo "   According to EMERGENCY_NET.md, it should be registered immediately after app creation"
    fi
else
    echo "❌ CORS middleware NOT found in main.py!"
    echo "   This is the problem - CORS middleware must be registered"
    exit 1
fi

# 8. Test actual GET request with CORS
echo ""
echo "8. Testing actual GET request with CORS..."
GET_RESPONSE=$(curl -s -X GET http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  -i 2>&1)

if echo "$GET_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present in GET response"
    echo "$GET_RESPONSE" | grep -i "access-control"
else
    echo "❌ CORS headers MISSING in GET response"
    echo "   This means CORS middleware is not adding headers to responses"
fi

# 9. Summary
echo ""
echo "=== SUMMARY ==="
echo ""
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1 && \
   curl -s -X OPTIONS http://127.0.0.1:8000/campaigns \
     -H "Origin: https://machine.vernalcontentum.com" \
     -H "Access-Control-Request-Method: GET" | grep -qi "access-control"; then
    echo "✅ CORS is working correctly!"
    echo ""
    echo "If you're still seeing CORS errors in the browser:"
    echo "1. Clear browser cache (Ctrl+Shift+Delete)"
    echo "2. Try incognito/private mode"
    echo "3. Check browser console for actual error messages"
    echo "4. Verify frontend is calling: https://themachine.vernalcontentum.com (not localhost)"
else
    echo "❌ CORS is NOT working correctly"
    echo ""
    echo "Next steps:"
    echo "1. Check service logs: sudo journalctl -u vernal-agents --since '5 minutes ago' | tail -50"
    echo "2. Verify main.py has CORS middleware registered early"
    echo "3. Restart service: sudo systemctl restart vernal-agents"
    echo "4. Wait 30-60 seconds for full initialization"
    echo "5. Run this script again"
fi

