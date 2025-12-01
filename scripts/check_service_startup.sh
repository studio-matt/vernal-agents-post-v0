#!/bin/bash
# Check why service isn't listening on port 8000

echo "🔍 Checking service status and logs..."
echo ""

# Check if service is actually running
echo "1. Service status:"
sudo systemctl status vernal-agents --no-pager | head -15
echo ""

# Check recent logs for errors
echo "2. Recent logs (last 30 lines):"
sudo journalctl -u vernal-agents -n 30 --no-pager | tail -30
echo ""

# Check if port 8000 is in use
echo "3. Port 8000 status:"
sudo lsof -i:8000 || echo "   No process listening on port 8000"
echo ""

# Check if uvicorn process is running
echo "4. Uvicorn processes:"
ps aux | grep uvicorn | grep -v grep || echo "   No uvicorn processes found"
echo ""

# Check for Python errors in logs
echo "5. Recent errors in logs:"
sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -iE "error|exception|traceback|failed" | tail -20


