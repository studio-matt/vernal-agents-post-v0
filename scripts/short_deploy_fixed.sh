#!/bin/bash
# Fixed short deploy - handles errors properly
# This is the improved version of the one-liner

set -e  # Exit on any error

cd /home/ubuntu/vernal-agents-post-v0 && \
git fetch origin && \
git switch main && \
git pull --ff-only origin main && \
source venv/bin/activate && \
pip install -r requirements.txt --no-cache-dir -q && \
(python3 scripts/insert_visualizer_settings.py || echo "⚠️  insert_visualizer_settings.py failed, continuing...") && \
sudo systemctl restart vernal-agents && \
sleep 3 && \
(curl -s http://127.0.0.1:8000/health | jq -r '.status // "error"' || echo "error") | grep -q "ok" && \
echo "✅ Deploy complete" || \
(echo "❌ Deploy failed. Check logs: sudo journalctl -u vernal-agents -n 50" && exit 1)

