#!/bin/bash
# Quick deploy script for backend server
# Pulls latest code, restarts service, and verifies health

set -e

echo "🚀 Starting quick deploy..."
echo ""

# Navigate to backend directory
cd /home/ubuntu/vernal-agents-post-v0

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin && git switch main && git pull --ff-only origin main

# Activate venv and install dependencies (if needed)
echo "📦 Checking dependencies..."
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir -q

# Restart systemd service
echo "🔄 Restarting service..."
sudo systemctl restart vernal-agents

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 3

# Verify health
echo "🏥 Checking health..."
if curl -s http://127.0.0.1:8000/health | jq -r '.status // "ok"' | grep -q "ok"; then
    echo ""
    echo "✅ Deploy complete! Service is healthy."
else
    echo ""
    echo "⚠️  Service may not be healthy. Check logs:"
    echo "   sudo journalctl -u vernal-agents -n 50 --no-pager"
    exit 1
fi
