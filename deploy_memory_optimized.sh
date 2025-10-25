#!/bin/bash
# Memory-optimized deployment script
# Installs dependencies in chunks to reduce memory pressure

set -e

echo "🚀 MEMORY-OPTIMIZED DEPLOYMENT STARTING..."

# 1. Stop service and cleanup
echo "🛑 Stopping service..."
sudo systemctl stop vernal-agents || true
sudo pkill -9 -f python || true
sudo pkill -9 -f uvicorn || true

# 2. Minimal cleanup
echo "🧹 Minimal cleanup..."
sudo rm -rf /home/ubuntu/vernal-agents-post-v0/venv
sudo rm -rf /home/ubuntu/vernal-agents-post-v0/__pycache__

# 3. Update code
echo "📦 Updating code..."
git pull origin main
cd /home/ubuntu/vernal-agents-post-v0

# 4. Create venv
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 5. Memory monitoring function
check_memory() {
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    echo "📊 Available memory: ${AVAILABLE_MEM}MB"
    if [ "$AVAILABLE_MEM" -lt 200 ]; then
        echo "⚠️ WARNING: Low memory detected ($AVAILABLE_MEM MB available)"
        echo "🧹 Running emergency cleanup..."
        sudo sync
        echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
        pip cache purge
        echo "📊 Memory after cleanup:"
        free -h
    fi
}

# 6. Install core dependencies first
echo "📦 Installing core dependencies..."
check_memory
pip install --upgrade pip --no-cache-dir
pip install -r requirements-core.txt --no-cache-dir --progress-bar off
check_memory

# 7. Install AI dependencies
echo "📦 Installing AI dependencies..."
pip install -r requirements-ai.txt --no-cache-dir --progress-bar off
check_memory

# 8. Install remaining dependencies
echo "📦 Installing remaining dependencies..."
pip install -r requirements-remaining.txt --no-cache-dir --progress-bar off
check_memory

# 9. Clean up
echo "🧹 Final cleanup..."
pip cache purge
check_memory

# 10. Set environment
export PYTHONPATH="/home/ubuntu/vernal-agents-post-v0:$PYTHONPATH"

# 11. Start service
echo "🚀 Starting service..."
sudo systemctl start vernal-agents
sudo systemctl enable vernal-agents

# 12. Wait and verify
echo "⏳ Waiting for service to start..."
sleep 15

# 13. Health check
echo "🔍 Health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Service is running"
    
    # Write completion marker
    COMMIT_HASH=$(git rev-parse HEAD)
    echo "DEPLOY_COMPLETE_$(date +%s)_$COMMIT_HASH" > /home/ubuntu/vernal_agents_deploy_complete.txt
    
    echo "🎉 MEMORY-OPTIMIZED DEPLOYMENT SUCCESSFUL!"
    echo "🔗 Commit: $COMMIT_HASH"
    echo "📊 Final memory status:"
    free -h
else
    echo "❌ Service health check failed"
    exit 1
fi
