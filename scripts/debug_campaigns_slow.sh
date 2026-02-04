#!/bin/bash
# Debug script for slow campaigns endpoint
# Run this on the AWS server: bash scripts/debug_campaigns_slow.sh

set -e

echo "🔍 DEBUGGING SLOW CAMPAIGNS ENDPOINT"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check service status
echo "1️⃣ Checking service status..."
if systemctl is-active --quiet vernal-agents; then
    echo -e "${GREEN}✅ Service is running${NC}"
else
    echo -e "${RED}❌ Service is NOT running${NC}"
    exit 1
fi
echo ""

# 2. Check recent logs for campaigns endpoint
echo "2️⃣ Checking recent /campaigns endpoint logs..."
echo "--- Last 50 lines mentioning 'campaigns' ---"
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -i "campaigns" | tail -50
echo ""

# 3. Check for errors
echo "3️⃣ Checking for errors in logs..."
ERROR_COUNT=$(sudo journalctl -u vernal-agents -n 500 --no-pager | grep -i "error\|exception\|traceback" | wc -l)
echo "Found $ERROR_COUNT error/exception lines in last 500 log entries"
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Recent errors:${NC}"
    sudo journalctl -u vernal-agents -n 500 --no-pager | grep -i "error\|exception\|traceback" | tail -10
fi
echo ""

# 4. Check server resources
echo "4️⃣ Checking server resources..."
echo "--- CPU and Memory ---"
top -bn1 | head -5
echo ""
echo "--- System Load ---"
uptime
echo ""
echo "--- Disk Usage ---"
df -h | head -5
echo ""

# 5. Test endpoint directly (if token provided)
if [ -n "$1" ]; then
    TOKEN=$1
    echo "5️⃣ Testing /campaigns endpoint with timing..."
    echo "Making request..."
    START_TIME=$(date +%s.%N)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}" \
        -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/campaigns 2>&1)
    END_TIME=$(date +%s.%N)
    
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    TIME_TOTAL=$(echo "$RESPONSE" | grep "TIME_TOTAL" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d' | sed '/TIME_TOTAL/d')
    
    echo "HTTP Status: $HTTP_CODE"
    echo "Time taken: ${TIME_TOTAL}s"
    
    if [ "$HTTP_CODE" = "200" ]; then
        CAMPAIGN_COUNT=$(echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('campaigns', [])))" 2>/dev/null || echo "N/A")
        echo "Campaigns returned: $CAMPAIGN_COUNT"
        RESPONSE_SIZE=$(echo "$BODY" | wc -c)
        echo "Response size: $RESPONSE_SIZE bytes ($(echo "scale=2; $RESPONSE_SIZE/1024" | bc) KB)"
    else
        echo -e "${RED}Request failed with status $HTTP_CODE${NC}"
        echo "Response: $BODY"
    fi
    echo ""
else
    echo "5️⃣ Skipping endpoint test (provide token as argument: bash $0 YOUR_TOKEN)"
    echo ""
fi

# 6. Check MySQL status
echo "6️⃣ Checking MySQL status..."
if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mariadb 2>/dev/null; then
    echo -e "${GREEN}✅ MySQL/MariaDB is running${NC}"
    
    # Check if we can get MySQL config
    if [ -f "/etc/mysql/my.cnf" ] || [ -f "/etc/my.cnf" ]; then
        echo "MySQL config file found"
    fi
else
    echo -e "${YELLOW}⚠️  MySQL/MariaDB status unknown or not running${NC}"
fi
echo ""

# 7. Check for slow queries (if slow query log exists)
echo "7️⃣ Checking for slow queries..."
if [ -f "/var/log/mysql/slow-query.log" ]; then
    SLOW_COUNT=$(sudo tail -100 /var/log/mysql/slow-query.log | grep -c "Query_time" || echo "0")
    echo "Found $SLOW_COUNT slow queries in last 100 lines"
    if [ "$SLOW_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}Recent slow queries:${NC}"
        sudo tail -100 /var/log/mysql/slow-query.log | grep -A 5 "Query_time" | head -20
    fi
else
    echo "Slow query log not found at /var/log/mysql/slow-query.log"
fi
echo ""

# 8. Check database connection pool (if we can access Python)
echo "8️⃣ Checking application logs for database connection issues..."
DB_CONNECTION_ERRORS=$(sudo journalctl -u vernal-agents -n 500 --no-pager | grep -i "connection\|pool\|timeout" | wc -l)
if [ "$DB_CONNECTION_ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}Found $DB_CONNECTION_ERRORS database connection-related log entries:${NC}"
    sudo journalctl -u vernal-agents -n 500 --no-pager | grep -i "connection\|pool\|timeout" | tail -5
fi
echo ""

# 9. Check process list
echo "9️⃣ Checking running processes..."
echo "--- Python processes ---"
ps aux | grep -i python | grep -v grep | head -5
echo ""

# 10. Summary and recommendations
echo "📋 SUMMARY AND RECOMMENDATIONS"
echo "=============================="
echo ""
echo "Next steps:"
echo "1. Check the detailed logs: sudo journalctl -u vernal-agents -f"
echo "2. Test the endpoint with a token: curl -H 'Authorization: Bearer TOKEN' http://localhost:8000/campaigns"
echo "3. Check database: mysql -u vernalcontentum_vernaluse -p vernalcontentum_contentMachine"
echo "   (Repo path: /home/ubuntu/vernal-agents-post-v0)"
echo "4. Review the campaigns table: SELECT COUNT(*) FROM campaigns;"
echo "5. Check for missing indexes: SHOW INDEXES FROM campaigns;"
echo ""
echo "Common fixes:"
echo "- Add database indexes on user_id and campaign_id columns"
echo "- Check if there are too many campaigns being returned"
echo "- Check database connection pool settings"
echo "- Review the campaigns.py endpoint code for N+1 queries"
echo ""
