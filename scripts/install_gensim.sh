#!/bin/bash
# Install gensim on the production server

set -e

echo "🔧 Installing gensim for topic extraction..."

cd /home/ubuntu/vernal-agents-post-v0

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Install gensim
echo "📦 Installing gensim>=4.3.2..."
pip install gensim>=4.3.2

# Verify installation
echo "🔍 Verifying gensim installation..."
python3 -c "import gensim; print(f'✅ gensim {gensim.__version__} installed successfully')" || {
    echo "❌ gensim import verification failed!"
    exit 1
}

echo ""
echo "✅ Gensim installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Restart the backend service: sudo systemctl restart vernal-agents"
echo "2. Monitor logs: sudo journalctl -u vernal-agents -f | grep -E 'gensim|topic|recommendations'"
echo "3. Test by requesting research agent recommendations for a campaign"

