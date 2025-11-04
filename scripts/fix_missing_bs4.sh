#!/bin/bash
# Quick fix for missing beautifulsoup4 (bs4) module
# This is causing scraping to fail silently

set -e

echo "🔧 Fixing missing beautifulsoup4 (bs4) module..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

# Install beautifulsoup4
echo "📦 Installing beautifulsoup4..."
pip install beautifulsoup4>=4.12.3

# Verify installation
echo ""
echo "✅ Verifying installation..."
python3 -c "from bs4 import BeautifulSoup; print('✅ beautifulsoup4 (bs4) installed successfully')" || {
    echo "❌ Installation failed!"
    exit 1
}

# Restart service
echo ""
echo "🔄 Restarting backend service..."
sudo systemctl restart vernal-agents

# Wait for service to start
sleep 3

# Verify service is running
echo ""
echo "✅ Verifying service..."
sudo systemctl status vernal-agents --no-pager | head -5

echo ""
echo "✅ Fix complete! beautifulsoup4 is now installed."
echo ""
echo "Next steps:"
echo "1. Re-run your campaign build"
echo "2. Check logs: sudo journalctl -u vernal-agents -f | grep scraping"
echo "3. You should no longer see 'No module named bs4' errors"

