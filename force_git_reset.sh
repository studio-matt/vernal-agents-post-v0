#!/bin/bash
# Force production to reset to our git repository version

echo "Forcing production to use git repository version..."

# Stop the service
sudo systemctl stop vernal-agents

# Force reset to our repository version (this will overwrite local changes)
git reset --hard origin/mcp-conversion

# Pull latest changes
git pull origin mcp-conversion

# Restart the service
sudo systemctl start vernal-agents

echo "✅ Production reset to git repository version"

# Wait and test
sleep 15
echo "Testing campaigns endpoint..."
curl http://localhost:8000/campaigns
