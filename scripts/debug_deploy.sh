#!/bin/bash
# Debug version - shows what's failing step by step

echo "🔍 Debugging deploy script..."
echo ""

# Check prerequisites
echo "1️⃣ Checking prerequisites..."
cd /home/ubuntu/vernal-agents-post-v0 || {
    echo "❌ Directory /home/ubuntu/vernal-agents-post-v0 not found"
    exit 1
}
echo "✅ Directory exists"

command -v jq >/dev/null 2>&1 || {
    echo "❌ jq not installed. Install with: sudo apt install jq"
    exit 1
}
echo "✅ jq installed"

[ -f "venv/bin/activate" ] || {
    echo "❌ venv not found. Create with: python3 -m venv venv"
    exit 1
}
echo "✅ venv exists"

[ -f "requirements.txt" ] || {
    echo "❌ requirements.txt not found"
    exit 1
}
echo "✅ requirements.txt exists"

[ -f ".env" ] || {
    echo "⚠️  .env file not found (might be okay if using environment variables)"
}

echo ""
echo "2️⃣ Testing git operations..."
git fetch origin && echo "✅ git fetch successful" || {
    echo "❌ git fetch failed"
    exit 1
}

git switch main && echo "✅ git switch successful" || {
    echo "❌ git switch failed"
    exit 1
}

git pull --ff-only origin main && echo "✅ git pull successful" || {
    echo "❌ git pull failed (might need to merge or reset)"
    exit 1
}

echo ""
echo "3️⃣ Testing venv activation..."
source venv/bin/activate && echo "✅ venv activated" || {
    echo "❌ venv activation failed"
    exit 1
}

echo ""
echo "4️⃣ Testing pip install..."
pip install -r requirements.txt --no-cache-dir -q && echo "✅ pip install successful" || {
    echo "❌ pip install failed"
    exit 1
}

echo ""
echo "5️⃣ Testing insert_visualizer_settings.py..."
if [ -f "scripts/insert_visualizer_settings.py" ]; then
    python3 scripts/insert_visualizer_settings.py && echo "✅ insert_visualizer_settings.py successful" || {
        echo "⚠️  insert_visualizer_settings.py failed (might be okay)"
    }
else
    echo "ℹ️  insert_visualizer_settings.py not found, skipping..."
fi

echo ""
echo "6️⃣ Testing service restart..."
sudo systemctl restart vernal-agents && echo "✅ Service restart successful" || {
    echo "❌ Service restart failed"
    echo "Check service status: sudo systemctl status vernal-agents"
    exit 1
}

echo ""
echo "7️⃣ Waiting for service to start..."
sleep 3

echo ""
echo "8️⃣ Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/health || echo "error")
echo "Health response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | jq -r '.status // "error"' 2>/dev/null | grep -q "ok"; then
    echo "✅ Health check passed"
    echo "✅ Deploy complete!"
    exit 0
else
    echo "❌ Health check failed"
    echo ""
    echo "📋 Service status:"
    sudo systemctl status vernal-agents --no-pager | head -20
    echo ""
    echo "📋 Recent logs:"
    sudo journalctl -u vernal-agents -n 30 --no-pager
    exit 1
fi

