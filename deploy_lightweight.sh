#!/bin/bash
# Lightweight deployment script for CI with memory constraints
# This version minimizes memory usage and skips heavy operations

set -e

echo "🚀 LIGHTWEIGHT DEPLOYMENT STARTING..."

# 1. Stop service and cleanup
echo "🛑 Stopping service..."
sudo systemctl stop vernal-agents || true
sudo pkill -9 -f python || true
sudo pkill -9 -f uvicorn || true

# 2. Minimal cleanup (don't remove everything to save time/memory)
echo "🧹 Minimal cleanup..."
sudo rm -rf /home/ubuntu/vernal-agents-post-v0/venv
sudo rm -rf /home/ubuntu/vernal-agents-post-v0/__pycache__

# 3. Update code (assume we're already in the right directory)
echo "📦 Updating code..."
git pull origin main

# 4. Create minimal venv
echo "🐍 Creating minimal virtual environment..."
python3 -m venv venv --clear
source venv/bin/activate

# 5. Install only essential packages
echo "📦 Installing essential packages only..."
pip install --upgrade pip --no-cache-dir
pip install fastapi uvicorn sqlalchemy pymysql python-multipart --no-cache-dir

# 6. Install remaining packages from requirements.txt
echo "📦 Installing remaining packages..."
pip install -r requirements.txt --no-cache-dir --no-deps --progress-bar off

# 7. Clean up
pip cache purge

# 8. Set environment
export PYTHONPATH="/home/ubuntu/vernal-agents-post-v0:$PYTHONPATH"

# 9. Start service
echo "🚀 Starting service..."
sudo systemctl start vernal-agents
sudo systemctl enable vernal-agents

# 10. Wait and verify
echo "⏳ Waiting for service to start..."
sleep 15

# 11. Basic health check
echo "🔍 Basic health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Service is running"
    
    # Write completion marker
    COMMIT_HASH=$(git rev-parse HEAD)
    echo "DEPLOY_COMPLETE_$(date +%s)_$COMMIT_HASH" > /home/ubuntu/vernal_agents_deploy_complete.txt
    
    echo "🎉 LIGHTWEIGHT DEPLOYMENT SUCCESSFUL!"
    echo "🔗 Commit: $COMMIT_HASH"
else
    echo "❌ Service health check failed"
    exit 1
fi
