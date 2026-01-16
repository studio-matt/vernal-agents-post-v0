#!/bin/bash
# Comprehensive Testing Script for All 4 Fixes
# Tests backend functionality that can be verified programmatically

set -e

echo "🧪 Testing All Fixes - Backend Verification"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# Test 1: Backend Service Health
echo "1️⃣  Testing Backend Service Health..."
if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend service is running${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ Backend service is not responding${NC}"
    FAILED=$((FAILED + 1))
    echo "   Run: sudo systemctl restart vernal-agents"
    exit 1
fi
echo ""

# Test 2: CORS Configuration
echo "2️⃣  Testing CORS Configuration..."
CORS_RESPONSE=$(curl -s -X OPTIONS "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -v 2>&1)

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin: https://machine.vernalcontentum.com"; then
    echo -e "${GREEN}✅ CORS origin header is correctly set (not wildcard)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ CORS origin header is missing or incorrect${NC}"
    FAILED=$((FAILED + 1))
fi

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-credentials: true"; then
    echo -e "${GREEN}✅ CORS credentials are allowed${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  CORS credentials header missing (may be OK)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test 3: Admin Endpoint Accessibility
echo "3️⃣  Testing Admin Endpoint Accessibility..."
ADMIN_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" 2>&1)

if echo "$ADMIN_RESPONSE" | grep -qi "status\|error\|success"; then
    echo -e "${GREEN}✅ Admin endpoint is accessible${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  Admin endpoint response unclear (may require auth)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test 4: Check main.py for CORS Configuration
echo "4️⃣  Testing CORS Configuration in main.py..."
if [ -f "main.py" ]; then
    if grep -q "allow_origins=\[" main.py && ! grep -q 'allow_origins=\["\*"\]' main.py; then
        echo -e "${GREEN}✅ main.py has specific CORS origins (not wildcard)${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ main.py still uses wildcard CORS origins${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    if grep -q "machine.vernalcontentum.com" main.py; then
        echo -e "${GREEN}✅ main.py includes production domain in CORS origins${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠️  main.py may not include production domain${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}❌ main.py not found${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 5: Check for Domain Detection in Backend (if author_profile_service exists)
echo "5️⃣  Testing Backend Domain Detection Support..."
if find . -name "*author_profile*" -type f | grep -q .; then
    AUTHOR_SERVICE=$(find . -name "*author_profile*" -type f | head -1)
    if grep -qi "domain" "$AUTHOR_SERVICE" 2>/dev/null; then
        echo -e "${GREEN}✅ Backend service has domain detection code${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠️  Backend service may not have domain detection${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Could not find author_profile service file${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test 6: Check Python Syntax
echo "6️⃣  Testing Python Syntax..."
if python3 -m py_compile main.py 2>/dev/null; then
    echo -e "${GREEN}✅ main.py has valid Python syntax${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ main.py has syntax errors${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "============================================"
echo "📊 Test Summary"
echo "============================================"
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test frontend features manually (see MANUAL_TESTING_GUIDE.md)"
    echo "2. Verify domain badges appear in UI"
    echo "3. Test image generation modal"
    echo "4. Test Research Assistant appending"
    echo "5. Test .txt file upload"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please fix issues before proceeding.${NC}"
    exit 1
fi

