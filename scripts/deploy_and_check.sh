#!/bin/bash
# deploy_and_check.sh - Deploy latest code and verify research agents work

set -e

cd /home/ubuntu/vernal-agents-post-v0

echo "=== Step 1: Pull latest code ==="
git fetch origin && git switch main && git pull origin main

echo ""
echo "=== Step 2: Restart service ==="
sudo systemctl restart vernal-agents
sleep 3

echo ""
echo "=== Step 3: Check service status ==="
sudo systemctl status vernal-agents --no-pager -l | head -20

echo ""
echo "=== Step 4: Test health endpoint ==="
curl -s http://127.0.0.1:8000/health | jq . || echo "❌ Health check failed"

echo ""
echo "=== Step 5: Check if debugging logs are in code ==="
if grep -q "📝 Prompt template (first 500 chars)" main.py; then
    echo "✅ Debugging logs found in code"
else
    echo "❌ Debugging logs NOT found in code - code might not be updated"
fi

echo ""
echo "=== Step 6: Watch logs for research agent calls ==="
echo "Now trigger a research agent from the frontend and watch for:"
echo "  - ✅ Using prompt for {agent_type} agent"
echo "  - 📝 Prompt template (first 500 chars)"
echo "  - 📝 Formatted prompt (first 500 chars)"
echo "  - 📝 LLM response (first 1000 chars)"
echo ""
echo "Run this to watch logs:"
echo "  sudo journalctl -u vernal-agents -f | grep -E 'research|agent|prompt|LLM|keyword|topical'"

