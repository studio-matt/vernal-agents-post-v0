#!/bin/bash
# Emergency Net Compliant CORS Diagnostic Script
# Checks backend server status, CORS configuration, and connectivity
# Follows Emergency Net v13 patterns and best practices

echo "🔍 Starting Backend CORS Diagnostic (Emergency Net Compliant)"
echo "=========================================="
echo ""

# 1. Check if systemd service is running
echo "📋 1. Checking systemd service status..."
if sudo systemctl is-active vernal-agents >/dev/null 2>&1; then
    echo "✅ Service is active"
    sudo systemctl status vernal-agents --no-pager -l | head -15
else
    echo "❌ Service is NOT active"
    sudo systemctl status vernal-agents --no-pager -l | head -15
fi
echo ""

# 2. Check if port 8000 is listening
echo "📋 2. Checking if port 8000 is listening..."
if sudo lsof -i :8000 >/dev/null 2>&1; then
    echo "✅ Port 8000 is listening"
    sudo lsof -i :8000
else
    echo "❌ Nothing listening on port 8000"
fi
echo ""

# 3. Check if process is running
echo "📋 3. Checking for uvicorn/python processes..."
PROCESSES=$(ps aux | grep -E "(uvicorn|python.*main.py)" | grep -v grep)
if [ -n "$PROCESSES" ]; then
    echo "✅ Found backend processes:"
    echo "$PROCESSES"
else
    echo "❌ No uvicorn/python processes found"
fi
echo ""

# 4. Verify .env file exists (Emergency Net v7 requirement)
echo "📋 4. Verifying .env file exists..."
if [ -f "/home/ubuntu/vernal-agents-post-v0/.env" ]; then
    echo "✅ .env file exists"
    # Check for real database credentials (not placeholders)
    if grep -qE "DB_HOST.*50\.6\.198\.220|DB_USER.*vernalcontentum" /home/ubuntu/vernal-agents-post-v0/.env 2>/dev/null; then
        echo "✅ .env contains production database credentials"
    else
        echo "⚠️  Warning: .env may contain placeholder credentials"
    fi
else
    echo "❌ .env file NOT found (CRITICAL - Emergency Net v7)"
fi
echo ""

# 5. Test local health endpoint
echo "📋 5. Testing local health endpoint..."
if curl -f -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "✅ Local health endpoint responding"
    curl -s http://127.0.0.1:8000/health | head -5
else
    echo "❌ Local health endpoint failed"
    curl -v http://127.0.0.1:8000/health 2>&1 | head -10
fi
echo ""

# 6. Test database health endpoint
echo "📋 6. Testing database health endpoint..."
if curl -f -s http://127.0.0.1:8000/mcp/enhanced/health >/dev/null 2>&1; then
    echo "✅ Database health endpoint responding"
    curl -s http://127.0.0.1:8000/mcp/enhanced/health | head -5
else
    echo "❌ Database health endpoint failed"
fi
echo ""

# 7. Check main.py CORS configuration (CRITICAL CHECK)
echo "📋 7. Checking main.py CORS configuration..."
if [ -f "/home/ubuntu/vernal-agents-post-v0/main.py" ]; then
    if grep -q 'allow_origins=\["\*"\]' /home/ubuntu/vernal-agents-post-v0/main.py 2>/dev/null; then
        echo "❌ CRITICAL: main.py uses wildcard origins with credentials (WILL FAIL)"
        echo "   Fix: Change allow_origins=[\"*\"] to specific origins list"
        echo "   See: guardrails/CORS_EMERGENCY_NET.md"
    elif grep -q "allow_origins=\[" /home/ubuntu/vernal-agents-post-v0/main.py 2>/dev/null && \
         grep -q "allow_credentials=True" /home/ubuntu/vernal-agents-post-v0/main.py 2>/dev/null; then
        echo "✅ main.py has specific origins with credentials (correct)"
        echo "   Origins configured:"
        grep -A 5 "allow_origins=\[" /home/ubuntu/vernal-agents-post-v0/main.py | grep -E "https?://" | sed 's/^/     /'
    else
        echo "⚠️  Could not verify CORS configuration in main.py"
    fi
else
    echo "❌ main.py not found"
fi
echo ""

# 8. Test CORS headers with OPTIONS request (local)
echo "📋 8. Testing CORS headers with OPTIONS request (local)..."
CORS_LOCAL=$(curl -s -i -X OPTIONS \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://127.0.0.1:8000/health 2>&1)
if echo "$CORS_LOCAL" | grep -qi "access-control-allow-origin"; then
    ORIGIN_HEADER=$(echo "$CORS_LOCAL" | grep -i "access-control-allow-origin" | head -1)
    if echo "$ORIGIN_HEADER" | grep -qi "\*"; then
        echo "❌ CRITICAL: CORS response contains wildcard origin (will fail with credentials)"
        echo "   Response: $ORIGIN_HEADER"
        echo "   Fix: Update main.py to use specific origins"
    else
        echo "✅ CORS headers present in local response"
        echo "$CORS_LOCAL" | grep -i "access-control"
    fi
else
    echo "❌ No CORS headers in local response"
    echo "$CORS_LOCAL" | head -15
fi
echo ""

# 9. Test CORS headers with OPTIONS request (external)
echo "📋 9. Testing CORS headers with OPTIONS request (external)..."
CORS_EXTERNAL=$(curl -s -i -X OPTIONS \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://themachine.vernalcontentum.com/health 2>&1)
if echo "$CORS_EXTERNAL" | grep -qi "access-control-allow-origin"; then
    echo "✅ CORS headers present in external response"
    echo "$CORS_EXTERNAL" | grep -i "access-control"
else
    echo "❌ No CORS headers in external response"
    echo "$CORS_EXTERNAL" | head -20
fi
echo ""

# 10. Test actual GET request with Origin header
echo "📋 10. Testing GET request with Origin header..."
GET_CORS=$(curl -s -i \
  -H "Origin: https://machine.vernalcontentum.com" \
  https://themachine.vernalcontentum.com/health 2>&1)
if echo "$GET_CORS" | grep -qi "access-control-allow-origin"; then
    echo "✅ CORS headers present in GET response"
    echo "$GET_CORS" | grep -i "access-control"
else
    echo "❌ No CORS headers in GET response"
fi
echo ""

# 11. Check nginx configuration
echo "📋 11. Checking nginx configuration..."
if sudo nginx -t >/dev/null 2>&1; then
    echo "✅ Nginx configuration is valid"
    # Check if nginx is proxying correctly (no CORS headers in nginx config)
    if sudo grep -q "proxy_pass.*127.0.0.1:8000" /etc/nginx/sites-enabled/themachine 2>/dev/null; then
        echo "✅ Nginx is configured to proxy to backend"
        if sudo grep -qi "access-control" /etc/nginx/sites-enabled/themachine 2>/dev/null; then
            echo "⚠️  Warning: CORS headers found in nginx config (should be handled by FastAPI)"
        else
            echo "✅ No CORS headers in nginx config (correct - FastAPI handles CORS)"
        fi
    else
        echo "⚠️  Warning: Could not verify nginx proxy configuration"
    fi
else
    echo "❌ Nginx configuration has errors"
    sudo nginx -t
fi
echo ""

# 12. Check recent service logs for errors
echo "📋 12. Checking recent service logs for errors..."
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | grep -iE "error|❌|CRITICAL" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT errors in last 10 minutes:"
    sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -iE "error|❌|CRITICAL" | tail -10
else
    echo "✅ No recent errors in logs"
fi
echo ""

# 13. Check recent service logs (last 10 lines)
echo "📋 13. Recent service logs (last 10 lines)..."
sudo journalctl -u vernal-agents -n 10 --no-pager
echo ""

# 14. Test external health endpoint
echo "📋 14. Testing external health endpoint..."
if curl -f -s https://themachine.vernalcontentum.com/health >/dev/null 2>&1; then
    echo "✅ External health endpoint responding"
    curl -s https://themachine.vernalcontentum.com/health | head -3
else
    echo "❌ External health endpoint failed"
    curl -v https://themachine.vernalcontentum.com/health 2>&1 | head -15
fi
echo ""

echo "=========================================="
echo "🔍 Diagnostic Complete"
echo "=========================================="
echo ""
echo "💡 Next Steps:"
echo "  - If service is not running: sudo systemctl restart vernal-agents"
echo "  - If CORS errors persist:"
echo "    1. Check main.py for wildcard origins (allow_origins=[\"*\"] is WRONG)"
echo "    2. Use specific origins list (see guardrails/CORS_EMERGENCY_NET.md)"
echo "    3. Restart service: sudo systemctl restart vernal-agents"
echo "  - If port 8000 not listening: Check service logs for startup errors"
echo "  - If .env missing: Restore from backup or Emergency Net v7 procedures"
echo ""
echo "📚 Documentation:"
echo "  - guardrails/CORS_EMERGENCY_NET.md - Complete CORS fix guide"
echo "  - guardrails/CORS_QUICK_REFERENCE.md - Quick reference"
echo "  - guardrails/SYNTAX_CHECKING.md - Fix syntax errors preventing startup"

