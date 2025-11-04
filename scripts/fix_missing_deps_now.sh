#!/bin/bash
# IMMEDIATE FIX: Install missing beautifulsoup4 and gensim
# Run this on the backend server right now

set -e

echo "🔧 Installing missing dependencies (beautifulsoup4 and gensim)..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

# Install missing packages
echo "📦 Installing beautifulsoup4..."
pip install beautifulsoup4>=4.12.3

echo "📦 Installing gensim..."
pip install gensim>=4.3.2

# Verify imports succeed
echo ""
echo "✅ Verifying imports..."
python -c "import bs4; import gensim; print(f'✅ bs4 {bs4.__version__}')" || {
    echo "❌ Import verification failed!"
    exit 1
}

python -c "import gensim; print(f'✅ gensim {gensim.__version__}')" || {
    echo "❌ gensim import verification failed!"
    exit 1
}

# Restart service
echo ""
echo "🔄 Restarting backend service..."
sudo systemctl restart vernal-agents

sleep 3

# Verify service is running
echo ""
echo "✅ Verifying service..."
sudo systemctl status vernal-agents --no-pager | head -5

echo ""
echo "✅ Fix complete! Dependencies installed and service restarted."
echo ""
echo "Next steps:"
echo "1. Re-run your campaign"
echo "2. Monitor logs: sudo journalctl -u vernal-agents -f | grep -E 'bs4|gensim|ImportError|ERROR|CRITICAL'"
echo "3. Check database for rows: SELECT COUNT(*) FROM campaign_raw_data WHERE campaign_id='YOUR_CAMPAIGN_ID'"

