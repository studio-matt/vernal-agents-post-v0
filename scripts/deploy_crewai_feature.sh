#!/bin/bash
# Backend Deployment Script for CrewAI Content Generation Feature
# Following EMERGENCY_NET.md guidelines

set -e  # Exit on error

echo "🚀 Deploying CrewAI Content Generation Feature..."
echo "=================================================="
echo ""

# Step 1: Pull Latest Code (per EMERGENCY_NET.md)
echo "📋 Step 1: Pulling latest code..."
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main

# Step 2: MANDATORY - Activate venv and validate dependencies
echo ""
echo "📋 Step 2: Validating dependencies (MANDATORY)..."
source venv/bin/activate
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}

# Step 3: Verify CrewAI is installed
echo ""
echo "📋 Step 3: Verifying CrewAI installation..."
if python3 -c "import crewai; print('✅ CrewAI version:', crewai.__version__)" 2>/dev/null; then
    echo "✅ CrewAI is installed"
else
    echo "⚠️  CrewAI not found. Installing..."
    pip install crewai>=0.28.0 --no-cache-dir
    echo "✅ CrewAI installed"
fi

# Step 4: Verify new files are present
echo ""
echo "📋 Step 4: Verifying new files..."
if [ -f "crewai_workflows.py" ]; then
    echo "✅ crewai_workflows.py found"
else
    echo "❌ crewai_workflows.py not found!"
    exit 1
fi

if [ -f "simple_mcp.py" ]; then
    echo "✅ simple_mcp.py found (updated)"
else
    echo "❌ simple_mcp.py not found!"
    exit 1
fi

# Step 5: Test imports
echo ""
echo "📋 Step 5: Testing imports..."
if python3 -c "from crewai_workflows import create_content_generation_crew, create_research_to_writing_crew; print('✅ CrewAI workflows import successful')" 2>/dev/null; then
    echo "✅ CrewAI workflows can be imported"
else
    echo "❌ Failed to import CrewAI workflows"
    echo "Checking error..."
    python3 -c "from crewai_workflows import create_content_generation_crew" 2>&1 | head -20
    exit 1
fi

# Step 6: Restart systemd service
echo ""
echo "📋 Step 6: Restarting backend service..."
sudo systemctl restart vernal-agents
sleep 5

# Step 7: Verification (MANDATORY per EMERGENCY_NET.md)
echo ""
echo "📋 Step 7: Running health checks (MANDATORY)..."
echo "Testing local health endpoint..."
if curl -s http://127.0.0.1:8000/health | jq . > /dev/null 2>&1; then
    echo "✅ Local health check: OK"
else
    echo "❌ Local health check failed"
    echo "Service logs:"
    sudo journalctl -u vernal-agents --since "1 minute ago" | tail -20
    exit 1
fi

echo "Testing database health endpoint..."
if curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq . > /dev/null 2>&1; then
    echo "✅ Database health check: OK"
else
    echo "❌ Database health check failed"
    exit 1
fi

echo "Testing public health endpoint..."
if curl -I https://themachine.vernalcontentum.com/health > /dev/null 2>&1; then
    echo "✅ Public health check: OK"
else
    echo "❌ Public health check failed"
    exit 1
fi

# Step 8: Test new CrewAI tool endpoint
echo ""
echo "📋 Step 8: Testing CrewAI tool registration..."
TOOLS_RESPONSE=$(curl -s http://127.0.0.1:8000/mcp/tools)
if echo "$TOOLS_RESPONSE" | grep -q "crewai_content_generation"; then
    echo "✅ CrewAI tool is registered"
    echo "   Available tools include: crewai_content_generation"
else
    echo "⚠️  CrewAI tool not found in tools list"
    echo "   This may be OK if CrewAI import failed gracefully"
    echo "   Tools available:"
    echo "$TOOLS_RESPONSE" | jq -r '.[].name' 2>/dev/null || echo "$TOOLS_RESPONSE"
fi

# Step 9: Check service logs for CrewAI registration
echo ""
echo "📋 Step 9: Checking service logs for CrewAI..."
if sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -q "CrewAI"; then
    echo "✅ CrewAI mentioned in logs"
    sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -i "crewai" | tail -5
else
    echo "⚠️  No CrewAI messages in logs (may be normal if import failed gracefully)"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Test CrewAI workflow:"
echo "      curl -X POST https://themachine.vernalcontentum.com/mcp/tools/execute \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"tool_name\":\"crewai_content_generation\",\"input_data\":{\"text\":\"test\",\"platform\":\"linkedin\"}}'"
echo ""
echo "   2. Compare with manual orchestration:"
echo "      curl -X POST https://themachine.vernalcontentum.com/mcp/generate-content \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"text\":\"test\",\"platform\":\"linkedin\"}'"
echo ""
echo "   3. Run test script:"
echo "      cd /home/ubuntu/vernal-agents-post-v0"
echo "      python3 test_crewai_vs_manual.py"
echo ""

