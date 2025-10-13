#!/bin/bash
# Deploy the campaigns endpoint fix

echo "Deploying campaigns endpoint fix..."

# Pull latest changes
git pull origin mcp-conversion

# Restart the service
sudo systemctl restart vernal-agents

echo "✅ Service restarted with campaigns endpoint"

# Wait and test
sleep 10
echo "Testing campaigns endpoint..."
curl http://localhost:8000/campaigns

echo -e "\nTesting other endpoints..."
curl -s http://localhost:8000/health
curl -s http://localhost:8000/debug/routes
