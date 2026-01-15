#!/bin/bash
# Comprehensive CORS diagnostic script
# Run this on the server to diagnose CORS issues

# Don't exit on error - we want to complete all checks
set +e

echo "=========================================="
echo "COMPREHENSIVE CORS DIAGNOSTIC"
echo "=========================================="
echo ""

cd /home/ubuntu/vernal-agents-post-v0

# Initialize issue counter
ISSUES=0

# 1. Check if code is up to date
echo "1. CHECKING CODE STATUS"
echo "-----------------------"
LATEST_COMMIT=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
echo "   Latest commit on origin/main: $LATEST_COMMIT"
echo "   Current commit: $CURRENT_COMMIT"
if [ "$LATEST_COMMIT" != "$CURRENT_COMMIT" ]; then
    echo "   ⚠️  WARNING: Code is NOT up to date!"
    echo "   Run: git pull origin main"
else
    echo "   ✅ Code is up to date"
fi
echo ""

# 2. Check Python import
echo "2. CHECKING PYTHON IMPORTS"
echo "--------------------------"
source venv/bin/activate 2>/dev/null || true
# Capture both stdout and stderr, but only check for actual errors
IMPORT_OUTPUT=$(python3 -c "import main" 2>&1)
IMPORT_EXIT=$?

# Check for actual error messages (not INFO logs)
if [ $IMPORT_EXIT -ne 0 ] || echo "$IMPORT_OUTPUT" | grep -qiE "SyntaxError|IndentationError|ImportError|NameError|Traceback|Error:"; then
    echo "   ❌ Python import FAILED!"
    echo ""
    echo "   Error details:"
    echo "$IMPORT_OUTPUT" | grep -iE "SyntaxError|IndentationError|ImportError|NameError|Traceback|Error:" | head -20 | sed 's/^/   /'
    if [ -z "$(echo "$IMPORT_OUTPUT" | grep -iE "SyntaxError|IndentationError|ImportError|NameError|Traceback|Error:")" ]; then
        echo "   Exit code: $IMPORT_EXIT"
        echo "   Full output (last 10 lines):"
        echo "$IMPORT_OUTPUT" | tail -10 | sed 's/^/   /'
    fi
    echo ""
    echo "   This will prevent the service from starting!"
    exit 1
else
    echo "   ✅ Python imports successful (exit code: $IMPORT_EXIT)"
    # Show a sample of the output to confirm it's working
    if echo "$IMPORT_OUTPUT" | grep -q "INFO"; then
        echo "   (Database connection successful - INFO logs present)"
    fi
fi
echo ""

# 3. Check CORS configuration in code
echo "3. CHECKING CORS CONFIGURATION IN CODE"
echo "---------------------------------------"
if grep -q "ALLOWED_ORIGINS" main.py && grep -q "machine.vernalcontentum.com" main.py; then
    echo "   ✅ CORS configuration found in main.py"
    echo "   Allowed origins:"
    grep -A 5 "ALLOWED_ORIGINS" main.py | grep -E "https?://" | sed 's/^/     /'
else
    echo "   ❌ CORS configuration NOT found or incomplete!"
fi
echo ""

# 3a. GUARDRAIL CHECK: Missing Router Decorators (CRITICAL - REFACTORING PITFALL)
echo "3a. GUARDRAIL CHECK: Missing Router Decorators"
echo "------------------------------------------------"
if [ -d "app/routes" ]; then
    MISSING_DECORATORS=$(grep -n "^[a-z_]*_router\.\(get\|post\|put\|delete\|patch\)" app/routes/*.py 2>/dev/null || true)
    if [ -n "$MISSING_DECORATORS" ]; then
        echo "   ❌ CRITICAL: Found routes missing @ decorator!"
        echo "   These routes will NOT be registered and will cause CORS errors:"
        echo "$MISSING_DECORATORS" | sed 's/^/     /'
        echo ""
        echo "   Fix: sed -i 's/^\\([a-z_]*_router\\)\\./@\\1./g' app/routes/*.py"
        ISSUES=$((ISSUES + 1))
    else
        echo "   ✅ All router routes have @ decorators"
    fi
else
    echo "   ⚠️  app/routes directory not found (may not be refactored yet)"
fi
echo ""

# 3b. GUARDRAIL CHECK: Router Inclusion in main.py
echo "3b. GUARDRAIL CHECK: Router Inclusion in main.py"
echo "--------------------------------------------------"
ROUTER_INCLUDES=$(grep -c "app.include_router" main.py 2>/dev/null || echo "0")
if [ "$ROUTER_INCLUDES" -gt 0 ]; then
    echo "   ✅ Found $ROUTER_INCLUDES router includes in main.py"
    echo "   Routers included:"
    grep "app.include_router" main.py | sed 's/^/     /'
else
    echo "   ⚠️  No router includes found (may not be refactored yet)"
fi
echo ""

# 3c. GUARDRAIL CHECK: Missing Imports (NameError/ImportError)
echo "3c. GUARDRAIL CHECK: Missing Imports (NameError/ImportError)"
echo "------------------------------------------------------------"
if echo "$IMPORT_OUTPUT" | grep -qiE "NameError|ImportError"; then
    echo "   ❌ CRITICAL: Found NameError or ImportError in Python import!"
    echo "   This will prevent the service from starting:"
    echo "$IMPORT_OUTPUT" | grep -iE "NameError|ImportError" | head -10 | sed 's/^/     /'
    echo ""
    echo "   Common causes:"
    echo "   - Missing imports in app/routes/*.py files"
    echo "   - Pydantic models not imported (e.g., BrandPersonalityCreate)"
    echo "   - Dependencies not installed"
    echo ""
    echo "   Fix: Check the error above and add missing imports"
    ISSUES=$((ISSUES + 1))
else
    echo "   ✅ No NameError or ImportError detected"
fi
echo ""

# 3d. GUARDRAIL CHECK: Missing Type Imports in Route Files
echo "3d. GUARDRAIL CHECK: Missing Type Imports in Route Files"
echo "--------------------------------------------------------"
if [ -d "app/routes" ]; then
    MISSING_TYPE_IMPORTS=0
    for file in app/routes/*.py; do
        if [ -f "$file" ]; then
            # Extract type hints used in function parameters
            TYPES=$(grep -oE ":\s*[A-Z][a-zA-Z]*(Create|Update|Request|Response|Enum)" "$file" 2>/dev/null | \
                    sed 's/.*:\s*//' | sort -u || true)
            
            if [ -n "$TYPES" ]; then
                for type in $TYPES; do
                    # Check if type is imported
                    if ! grep -qE "^from.*import.*$type|^import.*$type" "$file" 2>/dev/null; then
                        if [ $MISSING_TYPE_IMPORTS -eq 0 ]; then
                            echo "   ⚠️  Potential missing type imports found:"
                        fi
                        echo "     - $type used in $(basename $file) but not imported"
                        MISSING_TYPE_IMPORTS=$((MISSING_TYPE_IMPORTS + 1))
                    fi
                done
            fi
        fi
    done
    
    if [ $MISSING_TYPE_IMPORTS -eq 0 ]; then
        echo "   ✅ All type hints appear to be imported"
    else
        echo "   ⚠️  Found $MISSING_TYPE_IMPORTS potential missing imports"
        echo "   (This is a warning - verify manually if service fails to start)"
    fi
else
    echo "   ⚠️  app/routes directory not found (may not be refactored yet)"
fi
echo ""

# 4. Check service status
echo "4. CHECKING SERVICE STATUS"
echo "---------------------------"
SERVICE_STATUS=$(sudo systemctl is-active vernal-agents 2>&1 || echo "inactive")
if [ "$SERVICE_STATUS" = "active" ]; then
    echo "   ✅ Service is active"
else
    echo "   ❌ Service is NOT active (status: $SERVICE_STATUS)"
    echo ""
    echo "   Recent service logs:"
    sudo journalctl -u vernal-agents --since "5 minutes ago" --no-pager | tail -20 | sed 's/^/   /'
fi
echo ""

# 5. Check if port 8000 is listening
echo "5. CHECKING PORT 8000"
echo "---------------------"
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "   ✅ Port 8000 is listening"
    echo "   Process details:"
    sudo lsof -i :8000 | head -3 | sed 's/^/     /'
else
    echo "   ❌ Port 8000 is NOT listening"
    echo "   This means FastAPI is not running!"
fi
echo ""

# 6. Test direct connection to FastAPI
echo "6. TESTING DIRECT CONNECTION TO FASTAPI"
echo "----------------------------------------"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://127.0.0.1:8000/health 2>&1 || echo "CONNECTION_FAILED")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2 || echo "none")

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ FastAPI is responding (HTTP 200)"
    BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE")
    echo "   Response: $BODY"
elif [ "$HEALTH_RESPONSE" = "CONNECTION_FAILED" ] || [ -z "$HTTP_CODE" ]; then
    echo "   ❌ Cannot connect to FastAPI"
    echo "   This means the service is not running or crashed"
else
    echo "   ❌ FastAPI returned HTTP $HTTP_CODE"
    echo "   Response: $HEALTH_RESPONSE"
fi
echo ""

# 7. Test OPTIONS preflight directly
echo "7. TESTING CORS PREFLIGHT (localhost)"
echo "-------------------------------------"
OPTIONS_RESPONSE=$(curl -s -X OPTIONS http://127.0.0.1:8000/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -i 2>&1 || echo "CONNECTION_FAILED")

if [ "$OPTIONS_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo "   ❌ Cannot connect to FastAPI for OPTIONS request"
elif echo "$OPTIONS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "   ✅ CORS headers present in OPTIONS response"
    echo ""
    echo "   CORS headers found:"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control" | sed 's/^/     /'
else
    echo "   ❌ CORS headers MISSING in OPTIONS response"
    echo ""
    echo "   Full response:"
    echo "$OPTIONS_RESPONSE" | head -15 | sed 's/^/     /'
fi
echo ""

# 8. Test actual PUT request (not preflight)
echo "8. TESTING ACTUAL PUT REQUEST (localhost)"
echo "------------------------------------------"
PUT_RESPONSE=$(curl -s -X PUT http://127.0.0.1:8000/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"test": "data"}' \
  -i 2>&1 | head -20 || echo "CONNECTION_FAILED")

if [ "$PUT_RESPONSE" = "CONNECTION_FAILED" ]; then
    echo "   ❌ Cannot connect to FastAPI for PUT request"
elif echo "$PUT_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo "   ✅ CORS headers present in PUT response"
    echo "$PUT_RESPONSE" | grep -i "access-control" | sed 's/^/     /'
else
    echo "   ⚠️  CORS headers missing in PUT response (may be expected if auth fails)"
    echo "   Status line:"
    echo "$PUT_RESPONSE" | head -1 | sed 's/^/     /'
fi
echo ""

# 9. Test through nginx
echo "9. TESTING THROUGH NGINX (public URL)"
echo "-------------------------------------"
NGINX_OPTIONS=$(curl -s -X OPTIONS https://themachine.vernalcontentum.com/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -i 2>&1 | head -20)

HTTP_CODE_NGINX=$(echo "$NGINX_OPTIONS" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}' || echo "unknown")
echo "   HTTP Status: $HTTP_CODE_NGINX"

if [ "$HTTP_CODE_NGINX" = "502" ]; then
    echo "   ❌ 502 Bad Gateway - nginx can't reach FastAPI"
    echo "   This means FastAPI is not running on port 8000"
elif [ "$HTTP_CODE_NGINX" = "unknown" ]; then
    echo "   ❌ Cannot connect through nginx"
elif echo "$NGINX_OPTIONS" | grep -qi "Access-Control-Allow-Origin"; then
    echo "   ✅ CORS headers present through nginx"
    echo "$NGINX_OPTIONS" | grep -i "access-control" | sed 's/^/     /'
else
    echo "   ❌ CORS headers MISSING through nginx"
    echo "   Response headers:"
    echo "$NGINX_OPTIONS" | head -10 | sed 's/^/     /'
fi
echo ""

# 10. Check nginx configuration
echo "10. CHECKING NGINX CONFIGURATION"
echo "---------------------------------"
if [ -f /etc/nginx/sites-enabled/default ] || [ -f /etc/nginx/sites-enabled/vernal ]; then
    NGINX_CONFIG=$(find /etc/nginx/sites-enabled -name "*vernal*" -o -name "*default*" | head -1)
    if [ -n "$NGINX_CONFIG" ]; then
        echo "   Found nginx config: $NGINX_CONFIG"
        if grep -q "proxy_pass.*8000" "$NGINX_CONFIG"; then
            echo "   ✅ nginx configured to proxy to port 8000"
        else
            echo "   ⚠️  nginx proxy_pass to 8000 not found in config"
        fi
    fi
else
    echo "   ⚠️  Could not find nginx configuration"
fi
echo ""

# 11. Check recent errors
echo "11. RECENT SERVICE ERRORS"
echo "--------------------------"
RECENT_ERRORS=$(sudo journalctl -u vernal-agents --since "10 minutes ago" --no-pager | grep -iE "error|exception|traceback|failed|cors|nameerror|importerror" | tail -10)
if [ -n "$RECENT_ERRORS" ]; then
    echo "   Recent errors found:"
    echo "$RECENT_ERRORS" | sed 's/^/     /'
else
    echo "   ✅ No recent errors in logs"
fi
echo ""

# SUMMARY
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""

# Note: ISSUES counter already initialized at start and incremented by guardrail checks

if [ "$SERVICE_STATUS" != "active" ]; then
    echo "❌ ISSUE 1: Service is not active"
    echo "   Fix: sudo systemctl restart vernal-agents"
    ISSUES=$((ISSUES + 1))
fi

if ! sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "❌ ISSUE 2: Port 8000 is not listening"
    echo "   Fix: Service needs to be restarted"
    ISSUES=$((ISSUES + 1))
fi

if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ ISSUE 3: FastAPI health endpoint not responding"
    echo "   Fix: Check service logs: sudo journalctl -u vernal-agents -f"
    ISSUES=$((ISSUES + 1))
fi

if [ "$HTTP_CODE_NGINX" = "502" ]; then
    echo "❌ ISSUE 4: nginx returns 502 Bad Gateway"
    echo "   Fix: FastAPI service must be running on port 8000"
    ISSUES=$((ISSUES + 1))
fi

if [ "$LATEST_COMMIT" != "$CURRENT_COMMIT" ]; then
    echo "⚠️  ISSUE 5: Code is not up to date"
    echo "   Fix: git pull origin main && bash restart_service.sh"
    ISSUES=$((ISSUES + 1))
fi

# Check if guardrail issues were found (they increment ISSUES earlier)
GUARDRAIL_ISSUES_FOUND=0
if [ -d "app/routes" ]; then
    if grep -q "^[a-z_]*_router\.\(get\|post\|put\|delete\|patch\)" app/routes/*.py 2>/dev/null; then
        GUARDRAIL_ISSUES_FOUND=$((GUARDRAIL_ISSUES_FOUND + 1))
    fi
fi
if echo "$IMPORT_OUTPUT" | grep -qiE "NameError|ImportError"; then
    GUARDRAIL_ISSUES_FOUND=$((GUARDRAIL_ISSUES_FOUND + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    if [ $GUARDRAIL_ISSUES_FOUND -gt 0 ]; then
        echo "⚠️  Note: Guardrail checks found potential issues (see sections 3a-3d above)"
    fi
    echo ""
    echo "If you still see CORS errors in the browser:"
    echo "1. Clear browser cache (Ctrl+Shift+Delete)"
    echo "2. Try incognito/private mode"
    echo "3. Check browser console for actual error"
    echo "4. Verify the Origin header matches exactly: https://machine.vernalcontentum.com"
else
    echo ""
    if [ $GUARDRAIL_ISSUES_FOUND -gt 0 ]; then
        echo "🚨 GUARDRAIL ISSUES FOUND (CRITICAL - REFACTORING PITFALLS):"
        echo "   - Check sections 3a-3d above for details"
        echo "   - These issues can cause CORS errors even if service is running"
        echo ""
    fi
    echo "🔧 RECOMMENDED FIX:"
    echo "   cd /home/ubuntu/vernal-agents-post-v0"
    echo "   git pull origin main"
    if [ $GUARDRAIL_ISSUES_FOUND -gt 0 ]; then
        echo "   # Fix guardrail issues first (missing decorators/imports)"
        echo "   # Then restart:"
    fi
    echo "   bash restart_service.sh"
fi

echo ""

