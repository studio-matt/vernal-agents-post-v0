#!/bin/bash
# quick_install_missing_packages.sh - Install missing packages without full redeploy

set -e

echo "🔧 Quick Fix: Installing Missing Packages"
echo "=========================================="

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

echo "📦 Installing missing packages (ddgs, nltk, email-validator)..."
pip install ddgs>=9.0.0 nltk>=3.8.1 "email-validator>=2.1.0" --no-cache-dir

echo "✅ Packages installed successfully"

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart vernal-agents
sleep 5

# Verify
echo "🔍 Verifying installation..."
python3 -c "import ddgs; import nltk; print('✅ ddgs and nltk are available')" || { echo "❌ Import failed!"; exit 1; }

curl -s http://127.0.0.1:8000/health | jq . || { echo "❌ Health check failed!"; exit 1; }

echo "🎉 Quick fix complete! Packages installed and service restarted."

