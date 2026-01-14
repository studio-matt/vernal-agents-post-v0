#!/bin/bash
# Diagnose service crash
# Run this on the server when service won't start

echo "=== SERVICE CRASH DIAGNOSIS ==="
echo ""

# 1. Check recent logs for errors
echo "1. Recent service logs (last 50 lines):"
sudo journalctl -u vernal-agents --since "5 minutes ago" --no-pager | tail -50
echo ""

# 2. Check for Python syntax errors
echo "2. Testing Python import (syntax check):"
cd /home/ubuntu/vernal-agents-post-v0
if python3 -c "import main" 2>&1 | tee /tmp/python_import_error.log | grep -q "SyntaxError\|IndentationError\|ImportError"; then
    echo "❌ Python import FAILED - syntax or import error"
    echo ""
    echo "Error details:"
    cat /tmp/python_import_error.log | head -30
    echo ""
    echo "This is likely the cause of the crash!"
else
    echo "✅ Python import successful (no syntax errors)"
fi
echo ""

# 3. Check for missing dependencies
echo "3. Checking for missing critical imports:"
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate 2>/dev/null || true

MISSING_DEPS=()
for dep in "fastapi" "uvicorn" "sqlalchemy" "pymysql" "dotenv"; do
    if ! python3 -c "import $dep" 2>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "❌ Missing dependencies: ${MISSING_DEPS[*]}"
    echo "   Run: pip install -r requirements.txt"
else
    echo "✅ All critical dependencies available"
fi
echo ""

# 4. Check .env file
echo "4. Checking .env file:"
if [ ! -f /home/ubuntu/vernal-agents-post-v0/.env ]; then
    echo "❌ CRITICAL: .env file missing!"
    echo "   This will cause the service to fail"
    echo "   Restore from backup: cp /home/ubuntu/.env.backup /home/ubuntu/vernal-agents-post-v0/.env"
else
    echo "✅ .env file exists"
    # Check for placeholder values
    if grep -q "myuser\|localhost\|dummy\|mypassword" /home/ubuntu/vernal-agents-post-v0/.env 2>/dev/null; then
        echo "⚠️  WARNING: .env contains placeholder values (myuser, localhost, dummy, mypassword)"
        echo "   These should be real production credentials"
    fi
fi
echo ""

# 5. Try to start manually to see error
echo "5. Attempting manual start to capture error:"
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate 2>/dev/null || true
timeout 10 python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 2>&1 | head -30 || true
echo ""

# 6. Check systemd service file
echo "6. Checking systemd service configuration:"
sudo cat /etc/systemd/system/vernal-agents.service | head -20
echo ""

# 7. Summary
echo "=== SUMMARY ==="
echo ""
if [ -f /tmp/python_import_error.log ] && grep -q "SyntaxError\|IndentationError\|ImportError" /tmp/python_import_error.log; then
    echo "❌ SERVICE CRASHING DUE TO: Python syntax/import error"
    echo ""
    echo "Fix:"
    echo "1. Review the error above"
    echo "2. Fix the syntax/import error in the code"
    echo "3. Test: python3 -c 'import main'"
    echo "4. Restart: sudo systemctl restart vernal-agents"
elif [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "❌ SERVICE CRASHING DUE TO: Missing dependencies"
    echo ""
    echo "Fix:"
    echo "1. cd /home/ubuntu/vernal-agents-post-v0"
    echo "2. source venv/bin/activate"
    echo "3. pip install -r requirements.txt"
    echo "4. sudo systemctl restart vernal-agents"
elif [ ! -f /home/ubuntu/vernal-agents-post-v0/.env ]; then
    echo "❌ SERVICE CRASHING DUE TO: Missing .env file"
    echo ""
    echo "Fix:"
    echo "1. Restore .env: cp /home/ubuntu/.env.backup /home/ubuntu/vernal-agents-post-v0/.env"
    echo "2. Verify it has real DB credentials (not myuser/localhost/dummy)"
    echo "3. sudo systemctl restart vernal-agents"
else
    echo "⚠️  Service is crashing but root cause unclear"
    echo ""
    echo "Check the logs above for specific error messages"
    echo "Most common causes:"
    echo "- Python syntax/import errors"
    echo "- Missing dependencies"
    echo "- Missing .env file"
    echo "- Database connection failure"
fi

