#!/bin/bash
# Check service logs to see why it's not starting

echo "Checking service status..."
sudo systemctl status vernal-agents --no-pager

echo -e "\nChecking recent service logs..."
sudo journalctl -u vernal-agents -n 30 --no-pager

echo -e "\nChecking if main.py runs directly..."
cd /home/ubuntu/vernal-agents-post-v0
python3 main.py &
sleep 5
curl http://localhost:8000/campaigns
pkill -f "python3 main.py"
