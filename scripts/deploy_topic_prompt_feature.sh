#!/bin/bash
# Backend Deployment Script for Topic Extraction Prompt Feature
# Following EMERGENCY_NET.md guidelines

set -e  # Exit on error

echo "🚀 Deploying Topic Extraction Prompt Feature..."

# Step 1: Pull Latest Code (per EMERGENCY_NET.md)
echo "📋 Step 1: Pulling latest code..."
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main

# Step 2: MANDATORY - Activate venv and validate dependencies
echo "📋 Step 2: Validating dependencies (MANDATORY)..."
source venv/bin/activate
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}

# Step 3: Run database migration
echo "📋 Step 3: Running database migration..."
bash scripts/add_system_settings_table.sh

# Step 4: Restart systemd service
echo "📋 Step 4: Restarting backend service..."
sudo systemctl restart vernal-agents
sleep 5

# Step 5: Verification (MANDATORY per EMERGENCY_NET.md)
echo "📋 Step 5: Running health checks (MANDATORY)..."
echo "Testing local health endpoint..."
curl -s http://127.0.0.1:8000/health | jq . || {
    echo "❌ Local health check failed"
    exit 1
}

echo "Testing database health endpoint..."
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq . || {
    echo "❌ Database health check failed"
    exit 1
}

echo "Testing public health endpoint..."
curl -I https://themachine.vernalcontentum.com/health || {
    echo "❌ Public health check failed"
    exit 1
}

echo "Testing auth endpoint..."
curl -I https://themachine.vernalcontentum.com/auth/login || {
    echo "❌ Auth endpoint check failed"
    exit 1
}

# Step 6: Test new system settings endpoint
echo "📋 Step 6: Testing new system settings endpoint..."
curl -s http://127.0.0.1:8000/admin/settings/topic_extraction_prompt | jq . || {
    echo "⚠️  System settings endpoint test (may not exist yet, will be created on first save)"
}

echo "✅ Deployment complete!"
echo "📝 Next steps:"
echo "   1. Navigate to https://machine.vernalcontentum.com/admin"
echo "   2. You should see 'Topic Extraction Prompt' section"
echo "   3. Edit and save the prompt to test"

