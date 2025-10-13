#!/bin/bash
# Final fix for systemd service - force correct configuration

echo "Fixing systemd service configuration..."

# Stop the service
sudo systemctl stop vernal-agents

# Create the correct service file
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

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start vernal-agents

echo "✅ Systemd service fixed and started"

# Wait and test
sleep 15
echo "Testing campaigns endpoint..."
curl http://localhost:8000/campaigns
