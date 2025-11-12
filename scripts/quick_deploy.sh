#!/bin/bash
# Quick deploy script with visualizer settings initialization
cd /home/ubuntu/vernal-agents-post-v0 && \
git fetch origin && git switch main && git pull --ff-only origin main && \
source venv/bin/activate && \
pip install -r requirements.txt --no-cache-dir -q && \
python3 scripts/insert_visualizer_settings.py && \
sudo systemctl restart vernal-agents && \
sleep 3 && \
curl -s http://127.0.0.1:8000/health | jq -r '.status // "ok"' && \
echo "✅ Deploy complete"

