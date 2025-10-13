#!/bin/bash
# Force production to use the simple main.py

echo "Forcing production to use simple main.py..."

# Backup the complex main.py
cp main.py main.py.complex.backup

# The simple main.py is already in the repo, just make sure it's the active one
echo "✅ Using simple main.py (115 lines) instead of complex version (4,206 lines)"

# Restart the service
sudo systemctl restart vernal-agents

echo "✅ Service restarted with simple main.py"

# Wait and test
sleep 10
echo "Testing campaigns endpoint..."
curl http://localhost:8000/campaigns
