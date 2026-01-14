#!/bin/bash
# CORS Diagnostic Script
# Run this on the server to diagnose CORS issues

echo "=== CORS DIAGNOSTIC SCRIPT ==="
echo ""

# 1. Check if service is running
echo "1. Checking if FastAPI service is running..."
if systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is ACTIVE"
else
    echo "❌ Service is NOT ACTIVE"
    echo "   Status: $(systemctl is-active vernal-agents)"
fi
echo ""

# 2. Check recent service logs for errors
echo "2. Checking recent service logs for errors..."
echo "   Last 20 lines:"
sudo journalctl -u vernal-agents --since "5 minutes ago" --no-pager | tail -20
echo ""

# 3. Check if port 8000 is listening
echo "3. Checking if port 8000 is listening..."
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Port 8000 is listening"
    sudo lsof -i :8000 | head -5
else
    echo "❌ Port 8000 is NOT listening"
fi
echo ""

# 4. Test OPTIONS preflight request directly to FastAPI
echo "4. Testing OPTIONS preflight request to localhost:8000..."
OPTIONS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i 2>&1)

if echo "$OPTIONS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present in OPTIONS response"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control"
else
    echo "❌ CORS headers MISSING in OPTIONS response"
    echo "   Full response:"
    echo "$OPTIONS_RESPONSE" | head -20
fi
echo ""

# 5. Test OPTIONS preflight through nginx
echo "5. Testing OPTIONS preflight request through nginx (themachine.vernalcontentum.com)..."
NGINX_RESPONSE=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/campaigns \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i 2>&1)

if echo "$NGINX_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers present through nginx"
    echo "$NGINX_RESPONSE" | grep -i "access-control"
else
    echo "❌ CORS headers MISSING through nginx"
    echo "   Full response:"
    echo "$NGINX_RESPONSE" | head -20
fi
echo ""

# 6. Check nginx configuration for CORS interference
echo "6. Checking nginx configuration for CORS headers..."
if sudo grep -r "add_header.*Access-Control" /etc/nginx/ 2>/dev/null | grep -v "#"; then
    echo "⚠️  WARNING: nginx is adding CORS headers (this can interfere with FastAPI CORS)"
    sudo grep -r "add_header.*Access-Control" /etc/nginx/ 2>/dev/null | grep -v "#"
else
    echo "✅ No CORS headers in nginx config (correct - FastAPI handles CORS)"
fi
echo ""

# 7. Check if Python can import main.py
echo "7. Testing if main.py can be imported..."
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate 2>/dev/null || true
if python3 -c "import main; print('✅ Import successful')" 2>&1; then
    echo "✅ main.py imports successfully"
else
    echo "❌ main.py import FAILED"
    python3 -c "import main" 2>&1 | head -10
fi
echo ""

# 8. Check git status
echo "8. Checking git status..."
cd /home/ubuntu/vernal-agents-post-v0
echo "   Current commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
echo "   Latest commit on main: $(git ls-remote origin main 2>/dev/null | cut -f1 || echo 'unknown')"
echo "   Status: $(git status --short 2>/dev/null | head -5 || echo 'unknown')"
echo ""

echo "=== DIAGNOSTIC COMPLETE ==="
echo ""
echo "Next steps:"
echo "1. If service is not active: sudo systemctl restart vernal-agents"
echo "2. If port 8000 not listening: Check service logs for startup errors"
echo "3. If CORS headers missing: Verify middleware is registered in main.py"
echo "4. If nginx has CORS headers: Remove them - let FastAPI handle CORS"

