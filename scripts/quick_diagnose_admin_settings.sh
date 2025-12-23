#!/bin/bash
# Quick diagnostic script for admin settings timeout issue
# Run on backend server: bash scripts/quick_diagnose_admin_settings.sh

echo "🔍 QUICK ADMIN SETTINGS DIAGNOSTIC"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check backend service
echo "1️⃣ Checking backend service status..."
if systemctl is-active --quiet vernal-agents; then
    echo -e "${GREEN}✅ Backend service is running${NC}"
else
    echo -e "${RED}❌ Backend service is NOT running${NC}"
    exit 1
fi

# Step 2: Check if port 8000 is listening
echo ""
echo "2️⃣ Checking if port 8000 is listening..."
if netstat -tlnp 2>/dev/null | grep -q ":8000 " || ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo -e "${GREEN}✅ Port 8000 is listening${NC}"
    netstat -tlnp 2>/dev/null | grep ":8000 " || ss -tlnp 2>/dev/null | grep ":8000 "
else
    echo -e "${RED}❌ Port 8000 is NOT listening${NC}"
    exit 1
fi

# Step 3: Test health endpoint (should be fast)
echo ""
echo "3️⃣ Testing health endpoint (should be <1s)..."
START=$(date +%s%N)
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8000/health 2>&1)
END=$(date +%s%N)
HEALTH_TIME=$(( (END - START) / 1000000 ))
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health endpoint works (${HEALTH_TIME}ms)${NC}"
    echo "   Response: $BODY"
else
    echo -e "${RED}❌ Health endpoint failed (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $BODY"
fi

# Step 4: Check recent backend logs for admin settings requests
echo ""
echo "4️⃣ Checking recent backend logs for admin settings requests..."
echo "   (Looking for requests in last 2 minutes)"
RECENT_REQUESTS=$(sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -i "admin/settings" | wc -l)
if [ "$RECENT_REQUESTS" -gt 0 ]; then
    echo -e "${GREEN}✅ Found $RECENT_REQUESTS admin settings requests in logs${NC}"
    echo ""
    echo "   Recent requests:"
    sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -i "admin/settings" | tail -5
else
    echo -e "${YELLOW}⚠️  No admin settings requests found in logs (requests may not be reaching backend)${NC}"
fi

# Step 5: Check database connection
echo ""
echo "5️⃣ Testing database connection..."
cd /home/ubuntu/vernal-agents-post-v0
if [ -f .env ]; then
    source .env 2>/dev/null || true
    DB_TEST=$(mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SELECT 1" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database connection works${NC}"
    else
        echo -e "${RED}❌ Database connection failed${NC}"
        echo "   Error: $DB_TEST"
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found, skipping DB test${NC}"
fi

# Step 6: Test admin settings query directly
echo ""
echo "6️⃣ Testing admin settings database query..."
if [ -f .env ]; then
    QUERY_START=$(date +%s%N)
    DB_QUERY=$(mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SELECT setting_key, setting_value FROM system_settings WHERE setting_key = 'linkedin_client_id' LIMIT 1" 2>&1)
    QUERY_END=$(date +%s%N)
    QUERY_TIME=$(( (QUERY_END - QUERY_START) / 1000000 ))
    
    if echo "$DB_QUERY" | grep -q "linkedin_client_id"; then
        echo -e "${GREEN}✅ Database query works (${QUERY_TIME}ms)${NC}"
        echo "$DB_QUERY" | grep -v "setting_key"
    else
        echo -e "${YELLOW}⚠️  Query executed but no linkedin_client_id found (${QUERY_TIME}ms)${NC}"
        if echo "$DB_QUERY" | grep -q "ERROR"; then
            echo -e "${RED}   Error: $DB_QUERY${NC}"
        fi
    fi
fi

# Step 7: Check for database locks
echo ""
echo "7️⃣ Checking for database locks..."
if [ -f .env ]; then
    LOCKS=$(mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SHOW PROCESSLIST" 2>&1 | grep -i "lock\|wait" | wc -l)
    if [ "$LOCKS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $LOCKS processes with locks/waits${NC}"
        mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SHOW PROCESSLIST" 2>&1 | grep -i "lock\|wait"
    else
        echo -e "${GREEN}✅ No database locks found${NC}"
    fi
fi

# Step 8: Check nginx (if requests go through nginx)
echo ""
echo "8️⃣ Checking nginx status and recent errors..."
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx is running${NC}"
    NGINX_ERRORS=$(sudo tail -20 /var/log/nginx/error.log | grep -i "timeout\|admin" | wc -l)
    if [ "$NGINX_ERRORS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $NGINX_ERRORS recent nginx errors related to timeout/admin${NC}"
        sudo tail -20 /var/log/nginx/error.log | grep -i "timeout\|admin"
    else
        echo -e "${GREEN}✅ No recent nginx errors${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Nginx is not running (may not be needed)${NC}"
fi

# Step 9: Check backend logs for errors
echo ""
echo "9️⃣ Checking backend logs for recent errors..."
RECENT_ERRORS=$(sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -iE "error|exception|timeout|failed" | wc -l)
if [ "$RECENT_ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $RECENT_ERRORS recent errors in backend logs${NC}"
    echo "   Recent errors:"
    sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -iE "error|exception|timeout|failed" | tail -5
else
    echo -e "${GREEN}✅ No recent errors in backend logs${NC}"
fi

# Step 10: Test with a real request (need token)
echo ""
echo "🔟 Testing admin settings endpoint directly..."
echo "   (This requires a JWT token)"
echo ""
echo "   To test:"
echo "   1. Get token from browser: localStorage.getItem('token')"
echo "   2. Run:"
echo "      TOKEN='your_token_here'"
echo "      curl -H \"Authorization: Bearer \$TOKEN\" \\"
echo "        -H \"Content-Type: application/json\" \\"
echo "        http://127.0.0.1:8000/admin/settings/linkedin_client_id"
echo ""
echo "   Watch logs: sudo journalctl -u vernal-agents -f"

echo ""
echo "=================================="
echo "✅ Diagnostic complete!"
echo ""
echo "💡 Next steps:"
echo "   - If requests aren't in logs: Check CORS/nginx"
echo "   - If requests are slow: Check database/indexes"
echo "   - If health works but admin doesn't: Check authentication"

