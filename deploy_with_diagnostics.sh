#!/bin/bash
# Deploy script with step-by-step diagnostics
# Helps identify where deployment is hanging

set -e

echo "🚀 Starting deployment with diagnostics..."
echo ""

REPO_DIR="/home/ubuntu/vernal-agents-post-v0"
cd "$REPO_DIR" || exit 1

# Step 1: Git fetch
echo "📥 Step 1/8: Fetching from origin..."
if timeout 30 git fetch origin; then
    echo "✅ Git fetch complete"
else
    echo "❌ Git fetch timed out or failed"
    exit 1
fi

# Step 2: Switch to main
echo ""
echo "🔄 Step 2/8: Switching to main branch..."
git switch main
echo "✅ Switched to main"

# Step 3: Git pull
echo ""
echo "📥 Step 3/8: Pulling latest changes..."
if timeout 30 git pull origin main; then
    echo "✅ Git pull complete"
else
    echo "❌ Git pull timed out or failed"
    exit 1
fi

# Step 4: Activate venv
echo ""
echo "🐍 Step 4/8: Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"

# Step 5: Install dependencies
echo ""
echo "📦 Step 5/8: Installing dependencies (this may take 2-5 minutes)..."
if timeout 300 pip install -r requirements.txt --no-cache-dir -q; then
    echo "✅ Dependencies installed"
else
    echo "❌ pip install timed out or failed"
    echo "💡 Try running manually: pip install -r requirements.txt --no-cache-dir"
    exit 1
fi

# Step 6: Insert visualizer settings
echo ""
echo "⚙️  Step 6/8: Inserting visualizer settings..."
if timeout 60 python3 scripts/insert_visualizer_settings.py; then
    echo "✅ Visualizer settings inserted"
else
    echo "⚠️  Warning: insert_visualizer_settings.py timed out or failed"
    echo "💡 This may be due to database connection issues"
    echo "💡 Service may still start without these settings"
    # Don't exit - continue with deployment
fi

# Step 7: Restart service
echo ""
echo "🔄 Step 7/8: Restarting service..."
echo "   (This may take 10-30 seconds if service starts successfully)"
echo "   (Will timeout after 60 seconds if service fails to start)"

# Use timeout for systemctl restart to prevent hanging
if timeout 60 sudo systemctl restart vernal-agents; then
    echo "✅ Service restart command completed"
else
    echo "⚠️  Warning: systemctl restart timed out"
    echo "💡 Service may still be starting - checking status..."
fi

# Check service status
echo ""
echo "📊 Checking service status..."
sudo systemctl status vernal-agents --no-pager -l | head -15

# Step 8: Health check
echo ""
echo "🏥 Step 8/8: Health check..."
sleep 5

HEALTH_STATUS=""
for i in {1..6}; do
    echo "   Attempt $i/6..."
    if HEALTH_RESPONSE=$(timeout 10 curl -s http://127.0.0.1:8000/health 2>/dev/null); then
        HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status // "ok"' 2>/dev/null || echo "ok")
        if [ -n "$HEALTH_STATUS" ]; then
            echo "✅ Health check passed: $HEALTH_STATUS"
            break
        fi
    fi
    if [ $i -lt 6 ]; then
        sleep 2
    fi
done

if [ -z "$HEALTH_STATUS" ]; then
    echo "❌ Health check failed after 6 attempts"
    echo "💡 Service may not be running - check logs:"
    echo "   sudo journalctl -u vernal-agents --since '2 minutes ago' | tail -50"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deploy complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

