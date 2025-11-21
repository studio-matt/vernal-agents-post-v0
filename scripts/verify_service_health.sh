#!/bin/bash
# Verify backend service is fully operational after deployment

echo "🔍 Verifying backend service health..."
echo ""

# 1. Check service status
echo "1️⃣ Service Status:"
sudo systemctl status vernal-agents --no-pager | head -10
echo ""

# 2. Check if port 8000 is listening
echo "2️⃣ Port 8000 Status:"
if netstat -tlnp 2>/dev/null | grep -q ":8000 " || ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo "✅ Port 8000 is listening"
    netstat -tlnp 2>/dev/null | grep ":8000 " || ss -tlnp 2>/dev/null | grep ":8000 "
else
    echo "❌ Port 8000 is NOT listening"
    echo "   Service may still be starting up..."
fi
echo ""

# 3. Wait a bit and retry health check
echo "3️⃣ Waiting 3 seconds for service to fully start..."
sleep 3

# 4. Test local health endpoint
echo "4️⃣ Testing local health endpoint:"
HEALTH_RESPONSE=$(curl -s --max-time 5 http://localhost:8000/health 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q "status.*ok\|ok.*true"; then
    echo "✅ Local health check passed"
    echo "$HEALTH_RESPONSE" | head -3
else
    echo "⚠️  Local health check response:"
    echo "$HEALTH_RESPONSE"
    echo ""
    echo "   Service may still be starting. Wait a few more seconds and try again."
fi
echo ""

# 5. Check recent logs for errors
echo "5️⃣ Recent Errors (last 10 lines):"
sudo journalctl -u vernal-agents --since "1 minute ago" | grep -iE "error|exception|traceback|failed" | tail -10
if [ $? -ne 0 ]; then
    echo "✅ No recent errors found"
fi
echo ""

# 6. Check if service is processing requests
echo "6️⃣ Recent Activity (last 5 lines):"
sudo journalctl -u vernal-agents --since "1 minute ago" | tail -5
echo ""

echo "✅ Health check complete!"
echo ""
echo "If port 8000 is not listening, wait 10-15 seconds and run:"
echo "  curl http://localhost:8000/health"
echo ""
echo "If service is running but health check fails, check logs:"
echo "  sudo journalctl -u vernal-agents -f"

