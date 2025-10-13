#!/bin/bash
# Fix the systemd service configuration

# Update the service file to use the correct directory and Python interpreter
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
