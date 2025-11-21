#!/bin/bash
# Quick diagnostic script for 502 Bad Gateway errors

echo "🔍 Diagnosing 502 Bad Gateway Error..."
echo ""

# 1. Check if service is running
echo "1️⃣ Checking systemd service status..."
if systemctl is-active --quiet vernal-agents; then
    echo "✅ Service is active"
else
    echo "❌ Service is NOT active - this is likely the problem!"
    echo "   Run: sudo systemctl restart vernal-agents"
fi
systemctl status vernal-agents --no-pager | head -10
echo ""

# 2. Check if port 8000 is listening
echo "2️⃣ Checking if port 8000 is listening..."
if netstat -tlnp 2>/dev/null | grep -q ":8000 " || ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo "✅ Port 8000 is listening"
    netstat -tlnp 2>/dev/null | grep ":8000 " || ss -tlnp 2>/dev/null | grep ":8000 "
else
    echo "❌ Port 8000 is NOT listening - service may have crashed"
    echo "   Check logs: sudo journalctl -u vernal-agents --since '10 minutes ago' | tail -50"
fi
echo ""

# 3. Test local health endpoint
echo "3️⃣ Testing local health endpoint..."
HEALTH_RESPONSE=$(curl -s --max-time 5 http://localhost:8000/health 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q "status.*ok"; then
    echo "✅ Local health check passed"
    echo "$HEALTH_RESPONSE" | head -3
else
    echo "❌ Local health check failed"
    echo "   Response: $HEALTH_RESPONSE"
    echo "   This means the backend is not responding on port 8000"
fi
echo ""

# 4. Check recent logs for errors
echo "4️⃣ Checking recent logs for errors..."
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | grep -iE "error|exception|traceback|failed" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT errors in last 10 minutes"
    echo "   Recent errors:"
    sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | grep -iE "error|exception|traceback|failed" | tail -5
else
    echo "✅ No recent errors in logs"
fi
echo ""

# 5. Check if service is enabled
echo "5️⃣ Checking if service is enabled..."
if systemctl is-enabled --quiet vernal-agents; then
    echo "✅ Service is enabled (will start on boot)"
else
    echo "⚠️  Service is NOT enabled (won't start on boot)"
    echo "   Run: sudo systemctl enable vernal-agents"
fi
echo ""

# Summary and recommendations
echo "📋 SUMMARY:"
if ! systemctl is-active --quiet vernal-agents; then
    echo "❌ Service is not running - this is the root cause of 502 errors"
    echo ""
    echo "🔧 QUICK FIX:"
    echo "   sudo systemctl restart vernal-agents"
    echo "   sleep 5"
    echo "   curl http://localhost:8000/health"
elif ! curl -s --max-time 5 http://localhost:8000/health | grep -q "status.*ok"; then
    echo "❌ Service is running but not responding - check logs for errors"
    echo ""
    echo "🔧 QUICK FIX:"
    echo "   sudo journalctl -u vernal-agents --since '10 minutes ago' | tail -50"
    echo "   sudo systemctl restart vernal-agents"
else
    echo "✅ Service appears to be running correctly"
    echo "   If you're still getting 502 errors, check nginx configuration:"
    echo "   sudo nginx -t"
    echo "   sudo systemctl reload nginx"
fi

