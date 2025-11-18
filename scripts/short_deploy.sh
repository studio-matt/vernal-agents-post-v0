#!/bin/bash
# Short deploy script - optimized one-liner version
# Usage: cd /home/ubuntu/vernal-agents-post-v0 && bash scripts/short_deploy.sh

set -e  # Exit on any error

echo "🚀 Starting short deploy..."

# Step 1: Git operations
echo "📥 Pulling latest code..."
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main || {
    echo "❌ Git pull failed"
    exit 1
}

# Step 2: Activate venv and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate || {
    echo "❌ Failed to activate venv"
    exit 1
}

pip install -r requirements.txt --no-cache-dir -q || {
    echo "❌ pip install failed"
    exit 1
}

# Step 3: Run insert_visualizer_settings.py (if it exists and is needed)
if [ -f "scripts/insert_visualizer_settings.py" ]; then
    echo "🔧 Running insert_visualizer_settings.py..."
    python3 scripts/insert_visualizer_settings.py || {
        echo "⚠️  insert_visualizer_settings.py failed, but continuing..."
        # Don't exit - this might be optional
    }
else
    echo "ℹ️  insert_visualizer_settings.py not found, skipping..."
fi

# Step 4: Restart service
echo "🔄 Restarting service..."
sudo systemctl restart vernal-agents || {
    echo "❌ Service restart failed"
    exit 1
}

# Step 5: Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 3

# Step 6: Verify health
echo "🏥 Checking health..."
HEALTH_STATUS=$(curl -s http://127.0.0.1:8000/health | jq -r '.status // "error"' 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "ok" ]; then
    echo "✅ Deploy complete!"
    exit 0
else
    echo "❌ Health check failed. Status: $HEALTH_STATUS"
    echo "📋 Service logs:"
    sudo journalctl -u vernal-agents -n 20 --no-pager
    exit 1
fi

