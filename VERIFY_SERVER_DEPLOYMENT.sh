#!/bin/bash
# Verify what's actually running on the server vs what's in the repo
# Run this ON THE SERVER to diagnose deployment issues

echo "🔍 Server Deployment Verification"
echo "=================================="
echo ""

REPO_DIR="/home/ubuntu/vernal-agents-post-v0"
cd "$REPO_DIR" || exit 1

echo "📋 Step 1: Check current git commit"
echo "-----------------------------------"
CURRENT_COMMIT=$(git rev-parse HEAD)
CURRENT_COMMIT_SHORT=$(git rev-parse --short HEAD)
echo "Current commit: $CURRENT_COMMIT_SHORT ($CURRENT_COMMIT)"
echo ""

echo "📋 Step 2: Check if router files exist"
echo "-----------------------------------"
if [ -f "app/routes/campaigns.py" ]; then
    echo "✅ app/routes/campaigns.py exists"
    ROUTER_LINES=$(grep -c "campaigns_router" app/routes/campaigns.py || echo "0")
    echo "   Router references: $ROUTER_LINES"
else
    echo "❌ app/routes/campaigns.py MISSING"
fi

if [ -f "app/routes/author_personalities.py" ]; then
    echo "✅ app/routes/author_personalities.py exists"
    ROUTER_LINES=$(grep -c "author_personalities_router" app/routes/author_personalities.py || echo "0")
    echo "   Router references: $ROUTER_LINES"
else
    echo "❌ app/routes/author_personalities.py MISSING"
fi
echo ""

echo "📋 Step 3: Check if routers are in main.py"
echo "-----------------------------------"
if grep -q "from app.routes.campaigns import campaigns_router" main.py; then
    echo "✅ campaigns_router imported in main.py"
else
    echo "❌ campaigns_router NOT imported in main.py"
fi

if grep -q "from app.routes.author_personalities import author_personalities_router" main.py; then
    echo "✅ author_personalities_router imported in main.py"
else
    echo "❌ author_personalities_router NOT imported in main.py"
fi

if grep -q "app.include_router(campaigns_router)" main.py; then
    echo "✅ campaigns_router included in main.py"
else
    echo "❌ campaigns_router NOT included in main.py"
fi

if grep -q "app.include_router(author_personalities_router)" main.py; then
    echo "✅ author_personalities_router included in main.py"
else
    echo "❌ author_personalities_router NOT included in main.py"
fi
echo ""

echo "📋 Step 4: Check service status"
echo "-----------------------------------"
sudo systemctl status vernal-agents --no-pager -l | head -15
echo ""

echo "📋 Step 5: Check if service is using current code"
echo "-----------------------------------"
# Check when main.py was last modified
MAIN_MODIFIED=$(stat -c %y main.py 2>/dev/null || stat -f "%Sm" main.py 2>/dev/null)
echo "main.py last modified: $MAIN_MODIFIED"

# Check service start time
SERVICE_START=$(sudo systemctl show vernal-agents -p ActiveEnterTimestamp --value 2>/dev/null || echo "unknown")
echo "Service started: $SERVICE_START"
echo ""

echo "📋 Step 6: Test endpoints locally"
echo "-----------------------------------"
echo "Testing /health..."
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ /health endpoint responding"
else
    echo "❌ /health endpoint NOT responding"
fi

echo "Testing /campaigns (should return 401/403 if auth required, 404 if router missing)..."
CAMPAIGNS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/campaigns 2>/dev/null || echo "000")
echo "   Status code: $CAMPAIGNS_STATUS"
if [ "$CAMPAIGNS_STATUS" = "404" ]; then
    echo "   ❌ 404 = Router not included or endpoint doesn't exist"
elif [ "$CAMPAIGNS_STATUS" = "401" ] || [ "$CAMPAIGNS_STATUS" = "403" ]; then
    echo "   ✅ Router is working (auth required)"
elif [ "$CAMPAIGNS_STATUS" = "200" ]; then
    echo "   ✅ Router is working"
else
    echo "   ⚠️  Unexpected status: $CAMPAIGNS_STATUS"
fi

echo "Testing /author_personalities..."
AUTHOR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/author_personalities 2>/dev/null || echo "000")
echo "   Status code: $AUTHOR_STATUS"
if [ "$AUTHOR_STATUS" = "404" ]; then
    echo "   ❌ 404 = Router not included or endpoint doesn't exist"
elif [ "$AUTHOR_STATUS" = "401" ] || [ "$AUTHOR_STATUS" = "403" ]; then
    echo "   ✅ Router is working (auth required)"
elif [ "$AUTHOR_STATUS" = "200" ]; then
    echo "   ✅ Router is working"
else
    echo "   ⚠️  Unexpected status: $AUTHOR_STATUS"
fi
echo ""

echo "📋 Step 7: Check recent service logs"
echo "-----------------------------------"
echo "Last 20 lines of service logs:"
sudo journalctl -u vernal-agents --since "5 minutes ago" --no-pager | tail -20
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If endpoints return 404 but code is correct:"
echo "  1. Service needs to be restarted: sudo systemctl restart vernal-agents"
echo "  2. Or code needs to be pulled: git pull origin main"
echo ""
echo "If routers are missing from main.py:"
echo "  1. Pull latest code: git pull origin main"
echo "  2. Verify routers are included: grep 'include_router' main.py"
echo "  3. Restart service: sudo systemctl restart vernal-agents"
echo ""

