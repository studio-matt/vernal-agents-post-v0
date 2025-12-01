#!/bin/bash
# Check service status and recent logs

echo "🔍 Checking service status..."
sudo systemctl status vernal-agents --no-pager | head -15
echo ""

echo "📋 Checking if port 8000 is listening..."
sudo lsof -i:8000 || echo "❌ Port 8000 not listening"
echo ""

echo "📋 Recent logs (last 50 lines)..."
sudo journalctl -u vernal-agents -n 50 --no-pager | tail -50
echo ""

echo "📋 Checking for any errors in last 5 minutes..."
sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -iE "error|exception|traceback|failed|author_personality" | tail -30
echo ""

echo "📋 Testing health endpoint..."
curl -s http://127.0.0.1:8000/health || echo "❌ Health endpoint failed"
echo ""

echo "📋 Checking for POST requests to author_personalities..."
sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -iE "author_personality|POST.*author" | tail -20


