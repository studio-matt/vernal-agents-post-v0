#!/bin/bash
# Quick verification script for service health
# Run this after restarting the service

set -e

echo "🔍 Verifying service health..."
echo ""

# 1. Check service status
echo "1️⃣  Service Status:"
sudo systemctl is-active vernal-agents && echo "   ✅ Service is active" || echo "   ❌ Service is not active"

# 2. Test health endpoint
echo ""
echo "2️⃣  Health Endpoint:"
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/health 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo "   ✅ Health endpoint responding"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo "   ❌ Health endpoint failed"
    echo "   Response: $HEALTH_RESPONSE"
fi

# 3. Test root endpoint
echo ""
echo "3️⃣  Root Endpoint:"
ROOT_RESPONSE=$(curl -s http://127.0.0.1:8000/ 2>&1)
if echo "$ROOT_RESPONSE" | grep -q "status\|message"; then
    echo "   ✅ Root endpoint responding"
    echo "   Response: $ROOT_RESPONSE"
else
    echo "   ❌ Root endpoint failed"
    echo "   Response: $ROOT_RESPONSE"
fi

# 4. Check CORS headers
echo ""
echo "4️⃣  CORS Headers:"
CORS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/health \
    -H "Origin: https://machine.vernalcontentum.com" \
    -H "Access-Control-Request-Method: GET" \
    -v 2>&1)
if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin"; then
    echo "   ✅ CORS headers present"
else
    echo "   ⚠️  CORS headers not detected (may be normal for GET requests)"
fi

# 5. Check recent logs for errors
echo ""
echo "5️⃣  Recent Logs (last 10 lines):"
sudo journalctl -u vernal-agents -n 10 --no-pager | tail -5

# 6. Verify main.py structure
echo ""
echo "6️⃣  main.py Structure:"
if [ -f "main.py" ]; then
    LINE_COUNT=$(wc -l < main.py)
    ROUTER_COUNT=$(grep -c "app.include_router" main.py || echo "0")
    echo "   ✅ main.py exists ($LINE_COUNT lines, $ROUTER_COUNT routers)"
else
    echo "   ❌ main.py not found!"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Verification complete!"
echo ""
echo "💡 Next steps:"
echo "   - Test admin settings in browser"
echo "   - Check browser console for CORS errors"
echo "   - Verify endpoints are accessible"

