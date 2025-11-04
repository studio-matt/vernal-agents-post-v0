#!/bin/bash
# Comprehensive fix for ALL missing dependencies
# Checks requirements.txt and installs anything missing

set -e

echo "🔧 Checking and fixing ALL missing dependencies..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

# Check which dependencies are missing
echo "📋 Checking which dependencies are missing..."
echo ""

python3 scripts/check_all_dependencies.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All dependencies are already installed!"
    exit 0
fi

echo ""
echo "📦 Installing missing dependencies from requirements.txt..."
echo ""

# Install all requirements (this will only install missing ones)
pip install -r requirements.txt --no-cache-dir

# Verify all are now installed
echo ""
echo "✅ Verifying all dependencies are now installed..."
echo ""

python3 scripts/check_all_dependencies.py || {
    echo ""
    echo "❌ Some dependencies still missing after installation!"
    echo "   Check the output above for specific errors"
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

