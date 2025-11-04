#!/bin/bash
# quick_install_missing_packages.sh - Install missing packages without full redeploy

set -e

echo "🔧 Quick Fix: Installing Missing Packages"
echo "=========================================="

cd /home/ubuntu/vernal-agents-post-v0

# Activate venv
source venv/bin/activate

echo "📦 Installing missing packages (ddgs, nltk, email-validator, passlib, python-jose)..."
pip install ddgs>=9.0.0 nltk>=3.8.1 "email-validator>=2.1.0" "passlib[bcrypt]>=1.7.4" "python-jose[cryptography]>=3.3.0" --no-cache-dir

echo "📦 Installing Playwright browsers (required for web scraping)..."
playwright install chromium || { echo "⚠️ Playwright browser installation failed - scraping will not work"; }

echo "✅ Packages installed successfully"

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart vernal-agents
sleep 5

# Verify
echo "🔍 Verifying installation..."
python3 -c "
import ddgs, nltk, email_validator, passlib, jose
print('✅ All packages are available')
print('  - ddgs: web scraping')
print('  - nltk: text processing')
print('  - email_validator: email validation')
print('  - passlib: password hashing')
print('  - jose: JWT tokens')
" || { echo "❌ Import failed!"; exit 1; }

curl -s http://127.0.0.1:8000/health | jq . || { echo "❌ Health check failed!"; exit 1; }

# Test auth endpoint is accessible (not 404 or 500)
echo "🔍 Testing auth endpoint..."
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"test","password":"test"}')
if [ "$AUTH_STATUS" = "404" ]; then
    echo "❌ Auth endpoint returned 404 - router not loaded!"
    exit 1
elif [ "$AUTH_STATUS" = "500" ]; then
    echo "❌ Auth endpoint returned 500 - check backend logs!"
    exit 1
elif [ "$AUTH_STATUS" = "422" ] || [ "$AUTH_STATUS" = "401" ]; then
    echo "✅ Auth endpoint accessible (returned $AUTH_STATUS - expected for invalid credentials)"
else
    echo "⚠️  Auth endpoint returned: $AUTH_STATUS"
fi

echo "🎉 Quick fix complete! Packages installed and service restarted."

