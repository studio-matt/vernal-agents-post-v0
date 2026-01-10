#!/bin/bash
# Safe deployment script with error handling and timeout protection

set -e  # Exit on error

cd /home/ubuntu/vernal-agents-post-v0 || { echo "❌ Failed to cd to directory"; exit 1; }

echo "1️⃣ Fetching latest changes..."
git fetch origin || { echo "⚠️  Git fetch failed, continuing..."; }

echo "2️⃣ Switching to main branch..."
git switch main || { echo "⚠️  Git switch failed, continuing..."; }

echo "3️⃣ Pulling latest changes..."
if ! git pull --ff-only origin main; then
    echo "⚠️  Git pull failed (may have conflicts or diverged branches)"
    echo "💡 Try: git pull --no-ff origin main"
    exit 1
fi

echo "4️⃣ Activating virtual environment..."
source venv/bin/activate || { echo "❌ Failed to activate venv"; exit 1; }

echo "5️⃣ Installing dependencies..."
timeout 300 pip install -r requirements.txt --no-cache-dir -q || { 
    echo "⚠️  pip install failed or timed out"
    exit 1
}

echo "6️⃣ Running insert_visualizer_settings.py..."
timeout 60 python3 scripts/insert_visualizer_settings.py || {
    echo "⚠️  insert_visualizer_settings.py failed, but continuing..."
}

echo "7️⃣ Restarting service..."
sudo systemctl restart vernal-agents || { 
    echo "❌ Failed to restart service"
    exit 1
}

echo "8️⃣ Waiting for service to start..."
sleep 5

echo "9️⃣ Checking service health..."
for i in {1..10}; do
    if curl -s --max-time 5 http://127.0.0.1:8000/health > /dev/null 2>&1; then
        STATUS=$(curl -s --max-time 5 http://127.0.0.1:8000/health | jq -r '.status // "ok"' 2>/dev/null || echo "ok")
        echo "✅ Service is healthy: $STATUS"
        echo "✅ Deploy complete"
        exit 0
    fi
    echo "⏳ Waiting for service... ($i/10)"
    sleep 2
done

echo "❌ Service health check failed after 20 seconds"
echo "💡 Check service status: sudo systemctl status vernal-agents"
echo "💡 Check logs: sudo journalctl -u vernal-agents -n 50 --no-pager"
exit 1

