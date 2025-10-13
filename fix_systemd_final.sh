#!/bin/bash
# Final fix for systemd service configuration

echo "Fixing systemd service configuration..."

# Update the service file with the correct configuration
sudo tee /etc/systemd/system/vernal-agents.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Vernal Agents Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vernal-agents-post-v0
Environment="PATH=/home/ubuntu/vernal-agents-post-v0/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/vernal-agents-post-v0/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Reload systemd and restart the service
sudo systemctl daemon-reload
sudo systemctl restart vernal-agents

echo "✅ Fixed systemd service configuration"
echo "✅ Service should now use correct directory and Python interpreter"

# Wait and test
sleep 5
echo "Checking service status..."
sudo systemctl status vernal-agents --no-pager

echo "Testing campaigns endpoint..."
curl http://localhost:8000/campaigns
