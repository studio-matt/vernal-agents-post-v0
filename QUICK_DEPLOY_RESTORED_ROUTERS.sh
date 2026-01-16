#!/bin/bash
# Quick deploy script specifically for restoring missing routers
# This pulls the latest code and restarts the service

set -e

echo "🚀 Quick Deploy: Restoring Missing Routers"
echo "=========================================="
echo ""

REPO_DIR="/home/ubuntu/vernal-agents-post-v0"
cd "$REPO_DIR" || exit 1

# Step 1: Pull latest code
echo "📥 Pulling latest code..."
git fetch origin
git switch main
git pull origin main
echo "✅ Code pulled"
echo ""

# Step 2: Check if routers exist
echo "🔍 Verifying routers exist..."
if [ -f "app/routes/campaigns.py" ] && [ -f "app/routes/author_personalities.py" ]; then
    echo "✅ campaigns.py found"
    echo "✅ author_personalities.py found"
else
    echo "❌ ERROR: Router files not found!"
    echo "   Expected: app/routes/campaigns.py"
    echo "   Expected: app/routes/author_personalities.py"
    exit 1
fi

# Step 3: Check if main.py includes routers
echo ""
echo "🔍 Verifying main.py includes routers..."
if grep -q "from app.routes.campaigns import campaigns_router" main.py && \
   grep -q "from app.routes.author_personalities import author_personalities_router" main.py; then
    echo "✅ campaigns_router included in main.py"
    echo "✅ author_personalities_router included in main.py"
else
    echo "❌ ERROR: Routers not included in main.py!"
    exit 1
fi

# Step 4: Check syntax
echo ""
echo "🔍 Checking syntax..."
if command -v python3 >/dev/null 2>&1; then
    if python3 -m py_compile main.py 2>/dev/null; then
        echo "✅ Syntax check passed"
    else
        echo "❌ Syntax errors found!"
        python3 -m py_compile main.py
        exit 1
    fi
else
    echo "⚠️  python3 not found - skipping syntax check"
fi

# Step 5: Restart service
echo ""
echo "🔄 Restarting service..."
if timeout 60 sudo systemctl restart vernal-agents; then
    echo "✅ Service restart command completed"
else
    echo "⚠️  Service restart timed out - checking status..."
fi

# Step 6: Wait and check status
echo ""
echo "⏳ Waiting 5 seconds for service to start..."
sleep 5

echo ""
echo "📊 Service status:"
sudo systemctl status vernal-agents --no-pager -l | head -15

# Step 7: Health check
echo ""
echo "🏥 Health check..."
for i in {1..5}; do
    if HEALTH=$(timeout 5 curl -s http://127.0.0.1:8000/health 2>/dev/null); then
        if echo "$HEALTH" | grep -q "ok\|running"; then
            echo "✅ Service is running"
            break
        fi
    fi
    if [ $i -lt 5 ]; then
        echo "   Attempt $i/5 failed, retrying..."
        sleep 2
    else
        echo "❌ Health check failed"
        echo "💡 Check logs: sudo journalctl -u vernal-agents --since '2 minutes ago' | tail -50"
        exit 1
    fi
done

# Step 8: Test endpoints
echo ""
echo "🧪 Testing endpoints..."
ENDPOINTS=(
    "/campaigns"
    "/author_personalities"
    "/brand_personalities"
    "/platforms/credentials/all"
)

FAILED=0
for endpoint in "${ENDPOINTS[@]}"; do
    if timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000$endpoint" | grep -q "200\|401\|403"; then
        echo "✅ $endpoint - responding (may require auth)"
    else
        echo "❌ $endpoint - 404 or not responding"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
if [ $FAILED -eq 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Deploy complete! All endpoints responding"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Deploy complete but $FAILED endpoint(s) still failing"
    echo "💡 Check logs: sudo journalctl -u vernal-agents --since '2 minutes ago' | tail -50"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

