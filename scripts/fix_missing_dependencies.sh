#!/bin/bash
# Quick fix for missing dependencies (beautifulsoup4/bs4 and gensim)
# These are causing scraping and topic processing to fail silently

set -e

echo "🔧 Fixing missing dependencies (beautifulsoup4/bs4 and gensim)..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

# Install beautifulsoup4 (required for web scraping text/link extraction)
echo "📦 Installing beautifulsoup4 (required for scraping)..."
pip install beautifulsoup4>=4.12.3

# Install gensim (required for topic processing)
echo "📦 Installing gensim (required for topic processing)..."
pip install gensim>=4.3.2

# Verify installations
echo ""
echo "✅ Verifying installations..."
python3 -c "from bs4 import BeautifulSoup; print('✅ beautifulsoup4 (bs4) installed successfully')" || {
    echo "❌ beautifulsoup4 installation failed!"
    exit 1
}

python3 -c "import gensim; print('✅ gensim installed successfully')" || {
    echo "❌ gensim installation failed!"
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
echo "✅ Fix complete! All dependencies are now installed:"
echo "   - beautifulsoup4 (bs4) - for web scraping text/link extraction"
echo "   - gensim - for topic processing"
echo ""
echo "Next steps:"
echo "1. Re-run your campaign build"
echo "2. Check logs: sudo journalctl -u vernal-agents -f | grep -E 'scraping|gensim'"
echo "3. You should no longer see 'No module named bs4' or 'No module named gensim' errors"

