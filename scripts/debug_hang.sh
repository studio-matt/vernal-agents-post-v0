#!/bin/bash
# Debug script to identify where deployment is hanging

echo "🔍 Debugging deployment hang..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0 || { echo "❌ Can't cd to directory"; exit 1; }

echo "1️⃣ Testing git operations..."
timeout 10 git fetch origin && echo "✅ Git fetch OK" || echo "❌ Git fetch failed/hung"
timeout 10 git status && echo "✅ Git status OK" || echo "❌ Git status failed/hung"

echo ""
echo "2️⃣ Testing virtual environment..."
timeout 5 source venv/bin/activate && echo "✅ Venv activate OK" || echo "❌ Venv activate failed/hung"

echo ""
echo "3️⃣ Testing pip..."
timeout 30 pip --version && echo "✅ Pip OK" || echo "❌ Pip failed/hung"

echo ""
echo "4️⃣ Testing database connection (via script)..."
timeout 30 python3 -c "
import sys
sys.path.insert(0, '/home/ubuntu/vernal-agents-post-v0')
from database import SessionLocal
db = SessionLocal()
try:
    db.execute('SELECT 1')
    print('✅ Database connection OK')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
finally:
    db.close()
" || echo "❌ Database test failed/hung"

echo ""
echo "5️⃣ Testing service status..."
timeout 5 sudo systemctl status vernal-agents --no-pager | head -10 || echo "❌ Service status check failed/hung"

echo ""
echo "6️⃣ Testing health endpoint..."
timeout 10 curl -s --max-time 5 http://127.0.0.1:8000/health && echo "✅ Health endpoint OK" || echo "❌ Health endpoint failed/hung"

echo ""
echo "✅ Diagnostic complete"


