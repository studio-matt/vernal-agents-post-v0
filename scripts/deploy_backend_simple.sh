#!/bin/bash
# Simple backend deployment script
# Deploys text_processing.py changes to production

set -e

echo "🚀 Backend Deployment Script"
echo "=============================="
echo ""

# Navigate to backend directory
cd /home/ubuntu/vernal-agents-post-v0 || {
    echo "❌ ERROR: Backend directory not found"
    exit 1
}

echo "📋 Step 1: Pull latest code from GitHub..."
git fetch origin
git switch main
git pull --ff-only origin main

echo ""
echo "📋 Step 2: Activate virtual environment..."
source venv/bin/activate

echo ""
echo "📋 Step 3: Restart systemd service..."
sudo systemctl restart vernal-agents
sleep 5

echo ""
echo "📋 Step 4: Verification (MANDATORY per EMERGENCY_NET.md)..."
echo "Checking health endpoints..."

if curl -s http://127.0.0.1:8000/health | jq . > /dev/null 2>&1; then
    echo "✅ /health endpoint: OK"
else
    echo "❌ /health endpoint: FAILED"
    exit 1
fi

if curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq . > /dev/null 2>&1; then
    echo "✅ /mcp/enhanced/health endpoint: OK"
else
    echo "❌ /mcp/enhanced/health endpoint: FAILED"
    exit 1
fi

echo ""
echo "✅ Deployment successful!"
echo ""
echo "📊 Service status:"
sudo systemctl status vernal-agents --no-pager | head -10

