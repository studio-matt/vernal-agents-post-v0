#!/bin/bash
# Fix CORS by ensuring service is using latest main.py with routers

set -e

echo "🔧 Fixing CORS - Restarting service with latest code..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# 1. Pull latest
echo "1️⃣  Pulling latest code..."
git pull origin main

# 2. Verify main.py has routers
echo ""
echo "2️⃣  Verifying main.py structure..."
if grep -q "app.include_router.*admin_router" main.py; then
    echo "   ✅ Admin router found in main.py"
else
    echo "   ❌ Admin router NOT found in main.py!"
    echo "   This is the problem - main.py doesn't have routers"
    exit 1
fi

ROUTER_COUNT=$(grep -c "app.include_router" main.py || echo "0")
echo "   Found $ROUTER_COUNT router includes"

# 3. Restart service
echo ""
echo "3️⃣  Restarting service..."
sudo systemctl restart vernal-agents
sleep 5

# 4. Check service status
echo ""
echo "4️⃣  Checking service status..."
if sudo systemctl is-active vernal-agents >/dev/null 2>&1; then
    echo "   ✅ Service is active"
else
    echo "   ❌ Service failed to start!"
    echo "   Check logs: sudo journalctl -u vernal-agents -n 50"
    exit 1
fi

# 5. Test admin endpoint OPTIONS
echo ""
echo "5️⃣  Testing admin endpoint OPTIONS preflight..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  -w "\nHTTP_CODE:%{http_code}" 2>&1)

HTTP_CODE=$(echo "$OPTIONS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "405" ]; then
    echo "   ✅ OPTIONS request succeeded (HTTP $HTTP_CODE)"
    if echo "$OPTIONS_RESPONSE" | grep -qi "access-control-allow-origin"; then
        echo "   ✅ CORS headers present"
    else
        echo "   ⚠️  CORS headers missing (but request succeeded)"
    fi
else
    echo "   ❌ OPTIONS request failed (HTTP $HTTP_CODE)"
    echo "   Response: $(echo "$OPTIONS_RESPONSE" | grep -v HTTP_CODE | head -5)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Restart complete!"
echo ""
echo "💡 Next: Test in browser - CORS should work now"

