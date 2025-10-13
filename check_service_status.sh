#!/bin/bash
# Check why the service isn't starting

echo "Checking service status..."
sudo systemctl status vernal-agents --no-pager

echo -e "\nChecking service logs..."
sudo journalctl -u vernal-agents -n 20 --no-pager

echo -e "\nChecking if main.py exists and is correct size..."
ls -la main.py
wc -l main.py

echo -e "\nTesting main.py directly..."
python3 main.py &
sleep 5
curl http://localhost:8000/campaigns
pkill -f "python3 main.py"
