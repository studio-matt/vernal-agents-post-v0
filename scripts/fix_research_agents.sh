#!/bin/bash
# fix_research_agents.sh - Fix research agent issues (deploy code, fix gensim, clear cache)

set -e

cd /home/ubuntu/vernal-agents-post-v0

echo "=== Step 1: Pull latest code ==="
git fetch origin && git switch main && git pull origin main

echo ""
echo "=== Step 2: Fix Gensim (required for topic extraction) ==="
source venv/bin/activate
if ! python -c "import gensim" 2>/dev/null; then
    echo "Installing gensim..."
    pip install gensim>=4.3.2 --no-cache-dir -q
    echo "✅ Gensim installed"
else
    echo "✅ Gensim already installed"
    python -c "import gensim; print(f'✅ gensim {gensim.__version__}')"
fi

echo ""
echo "=== Step 3: Restart service ==="
sudo systemctl restart vernal-agents
sleep 3

echo ""
echo "=== Step 4: Verify service is running ==="
if sudo systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is running"
else
    echo "❌ Service is not running!"
    sudo systemctl status vernal-agents --no-pager -l | head -20
    exit 1
fi

echo ""
echo "=== Step 5: Test health endpoint ==="
curl -s http://127.0.0.1:8000/health | jq . || echo "❌ Health check failed"

echo ""
echo "=== Step 6: Verify debugging logs are in code ==="
if grep -q "🔍 Research agent endpoint called" main.py; then
    echo "✅ New debugging logs found in code"
else
    echo "❌ New debugging logs NOT found - code might not be updated"
fi

echo ""
echo "=== Step 7: Clear cached topical-map insights (optional) ==="
read -p "Clear cached topical-map insights for campaign 53a427d4-fa5a-4838-91a0-699837f601e1? (y/n): " clear_cache
if [ "$clear_cache" = "y" ]; then
    ./scripts/clear_research_cache.sh 53a427d4-fa5a-4838-91a0-699837f601e1 topical-map
    echo "✅ Cache cleared - topical-map will regenerate on next request"
else
    echo "Skipped cache clearing"
fi

echo ""
echo "=== DONE ==="
echo "Now test the research agents from the frontend."
echo "Watch logs with:"
echo "  sudo journalctl -u vernal-agents -f | grep -E 'research|agent|prompt|LLM|keyword|topical|CRITICAL|ERROR'"
echo ""
echo "You should now see:"
echo "  - 🔍 Research agent endpoint called"
echo "  - ✅ Processing {agent_type} agent"
echo "  - 📝 Prompt template (first 500 chars)"
echo "  - 📝 Formatted prompt (first 500 chars)"
echo "  - 📝 LLM response (first 1000 chars)"

