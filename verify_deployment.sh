#!/bin/bash
# Deployment Verification Script
# Run this after any deployment to verify it completed successfully

set -e

echo "🔍 VERIFYING DEPLOYMENT COMPLETION..."

# Check if completion marker exists
if [ -f "/home/ubuntu/vernal_agents_deploy_complete.txt" ]; then
    echo "✅ Completion marker found:"
    cat /home/ubuntu/vernal_agents_deploy_complete.txt
else
    echo "❌ Completion marker NOT found - deployment may not have finished"
    exit 1
fi

# Check if service is running
if systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is running"
else
    echo "❌ Service is not running"
    exit 1
fi

# Check if port 8000 is listening
if netstat -tlnp | grep -q ":8000 "; then
    echo "✅ Port 8000 is listening"
else
    echo "❌ Port 8000 is not listening"
    exit 1
fi

# Test health endpoints
echo "🔍 Testing health endpoints..."

# Test local health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Local health check passed"
else
    echo "❌ Local health check failed"
    exit 1
fi

# Test version endpoint
if curl -f http://localhost:8000/version > /dev/null 2>&1; then
    echo "✅ Version endpoint working"
else
    echo "❌ Version endpoint failed"
    exit 1
fi

# Test commit hash endpoint
echo "🔍 Testing commit hash endpoint..."
COMMIT_RESPONSE=$(curl -s http://localhost:8000/deploy/commit)
if echo "$COMMIT_RESPONSE" | grep -q '"status":"ok"'; then
    COMMIT_HASH=$(echo "$COMMIT_RESPONSE" | grep -o '"commit":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Commit hash endpoint working: $COMMIT_HASH"
else
    echo "❌ Commit hash endpoint failed: $COMMIT_RESPONSE"
    exit 1
fi

# Test external access
echo "🔍 Testing external access..."
if curl -f https://themachine.vernalcontentum.com/health > /dev/null 2>&1; then
    echo "✅ External health check passed"
else
    echo "❌ External health check failed"
    exit 1
fi

echo "🎉 DEPLOYMENT VERIFICATION SUCCESSFUL!"
echo "📝 All checks passed - backend is fully operational"
