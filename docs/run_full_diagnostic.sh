#!/bin/bash
# Master Diagnostic Script - Runs comprehensive system health check
# Based on docs/MASTER_DIAGNOSTIC_ROUTER.md

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 Master Diagnostic - Complete System Health Check"
echo "=================================================="
echo ""
echo "Based on: docs/MASTER_DIAGNOSTIC_ROUTER.md"
echo ""

cd /home/ubuntu/vernal-agents-post-v0 || exit 1

ISSUES=0
PASSED=0

# Phase 1: Service Health
echo "📋 Phase 1: Service Health"
echo "---------------------------"

# Step 1: Service Running
echo -n "1. Service status: "
if sudo systemctl is-active vernal-agents >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ NOT Running${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → Service Won't Start"
    ((ISSUES++))
fi

# Step 2: Port 8000 Listening
echo -n "2. Port 8000 listening: "
if sudo lsof -i :8000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Yes${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ No${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → Service Won't Start"
    ((ISSUES++))
fi

# Step 3: Health Endpoint
echo -n "3. Health endpoint: "
if curl -f -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Responding${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not responding${NC}"
    ((ISSUES++))
fi

echo ""

# Phase 2: CORS
echo "📋 Phase 2: CORS Configuration"
echo "-------------------------------"

# Step 4: CORS Check
echo -n "4. CORS configuration: "
if grep -q 'allow_origins=\["\*"\]' main.py 2>/dev/null; then
    echo -e "${RED}❌ Wildcard origins (WILL FAIL)${NC}"
    echo "   → Route to: guardrails/CORS_EMERGENCY_NET.md"
    echo "   → Quick fix: bash scripts/fix_cors_wildcard.sh"
    ((ISSUES++))
elif grep -q "allow_origins=\[" main.py 2>/dev/null && grep -q "allow_credentials=True" main.py 2>/dev/null; then
    echo -e "${GREEN}✅ Specific origins with credentials${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Could not verify CORS config${NC}"
    ((ISSUES++))
fi

# Test CORS headers
echo -n "5. CORS headers: "
CORS_TEST=$(curl -s -i -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control-allow-origin" | head -1)
if [ -n "$CORS_TEST" ]; then
    if echo "$CORS_TEST" | grep -qi "\*"; then
        echo -e "${RED}❌ Wildcard in response${NC}"
        ((ISSUES++))
    else
        echo -e "${GREEN}✅ Present${NC}"
        ((PASSED++))
    fi
else
    echo -e "${RED}❌ Missing${NC}"
    ((ISSUES++))
fi

echo ""

# Phase 3: Code Health
echo "📋 Phase 3: Code Health"
echo "------------------------"

# Step 5: Syntax Check
echo -n "6. Syntax check: "
if [ -f "find_all_syntax_errors.sh" ]; then
    if bash find_all_syntax_errors.sh 2>&1 | grep -qi "error\|failed"; then
        echo -e "${RED}❌ Errors found${NC}"
        echo "   → Route to: guardrails/SYNTAX_CHECKING.md"
        ((ISSUES++))
    else
        echo -e "${GREEN}✅ No errors${NC}"
        ((PASSED++))
    fi
else
    echo -e "${YELLOW}⚠️  Script not found${NC}"
fi

# Step 6: Import Check
echo -n "7. Import validation: "
if python3 -c "import main" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Import errors${NC}"
    echo "   → Route to: guardrails/SYNTAX_CHECKING.md → Import Errors"
    python3 -c "import main" 2>&1 | head -5
    ((ISSUES++))
fi

# Step 7: Structure Validation
echo -n "8. main.py structure: "
if [ -f "guardrails/validate_main_structure.sh" ]; then
    if bash guardrails/validate_main_structure.sh 2>&1 | grep -qi "error\|failed\|missing"; then
        echo -e "${RED}❌ Issues found${NC}"
        echo "   → Route to: guardrails/REFACTORING.md"
        ((ISSUES++))
    else
        echo -e "${GREEN}✅ Valid${NC}"
        ((PASSED++))
    fi
else
    echo -e "${YELLOW}⚠️  Script not found${NC}"
fi

echo ""

# Phase 4: Routers
echo "📋 Phase 4: Router & Endpoints"
echo "------------------------------"

# Step 8: Router Check
echo -n "9. Router inclusion: "
ROUTER_COUNT=$(grep -c "app.include_router" main.py 2>/dev/null || echo "0")
if [ "$ROUTER_COUNT" -ge 6 ]; then
    echo -e "${GREEN}✅ $ROUTER_COUNT routers included${NC}"
    ((PASSED++))
elif [ "$ROUTER_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Only $ROUTER_COUNT routers (expected 6+)${NC}"
    ((ISSUES++))
else
    echo -e "${RED}❌ No routers found${NC}"
    echo "   → Route to: guardrails/REFACTORING.md → Router Extraction"
    ((ISSUES++))
fi

# Step 9: Endpoint Check
echo -n "10. Endpoint health: "
if curl -f -s http://127.0.0.1:8000/health >/dev/null 2>&1 && \
   curl -f -s http://127.0.0.1:8000/ >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Endpoints responding${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Endpoints not responding${NC}"
    ((ISSUES++))
fi

echo ""

# Phase 5: Configuration
echo "📋 Phase 5: Configuration"
echo "------------------------"

# Step 10: Database (if endpoint exists)
echo -n "11. Database connectivity: "
if curl -f -s http://127.0.0.1:8000/mcp/enhanced/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Endpoint not available or error${NC}"
fi

# Step 11: .env File
echo -n "12. .env file: "
if [ -f ".env" ]; then
    if grep -qE "DB_HOST.*50\.6\.198\.220|DB_USER.*vernalcontentum" .env 2>/dev/null; then
        echo -e "${GREEN}✅ Exists with credentials${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  Exists but may have placeholder credentials${NC}"
    fi
else
    echo -e "${RED}❌ NOT found${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → Environment Setup"
    ((ISSUES++))
fi

echo ""

# Phase 6: External Access
echo "📋 Phase 6: External Access"
echo "---------------------------"

# Step 12: Nginx
echo -n "13. Nginx configuration: "
if sudo nginx -t >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Valid${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Invalid${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → Nginx Configuration"
    ((ISSUES++))
fi

# Step 13: External Access
echo -n "14. External access: "
if curl -f -s https://themachine.vernalcontentum.com/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Failed${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → External Access"
    ((ISSUES++))
fi

echo ""

# Phase 7: Errors
echo "📋 Phase 7: Recent Errors"
echo "------------------------"

# Step 14: Recent Errors
echo -n "15. Recent errors: "
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | \
    grep -iE "error|❌|CRITICAL|Exception|Traceback" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ None${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ $ERROR_COUNT errors found${NC}"
    echo "   → Route to: docs/EMERGENCY_NET_BACKEND.md → Troubleshooting"
    sudo journalctl -u vernal-agents --since "10 minutes ago" | \
        grep -iE "error|❌|CRITICAL|Exception|Traceback" | tail -5
    ((ISSUES++))
fi

echo ""
echo "=================================================="
echo "📊 Diagnostic Summary"
echo "=================================================="
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Issues: $ISSUES${NC}"
echo ""

if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! System is healthy.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Issues found. See routes above for detailed fixes.${NC}"
    echo ""
    echo "📚 For complete diagnostic procedures, see:"
    echo "   docs/MASTER_DIAGNOSTIC_ROUTER.md"
    exit 1
fi

