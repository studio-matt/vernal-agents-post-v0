#!/bin/bash
# Test if nginx is forwarding requests to backend
# Run this while making a request from the frontend

echo "🔍 TESTING NGINX REQUEST FORWARDING"
echo "==================================="
echo ""
echo "This will test if nginx receives and forwards requests to backend"
echo ""

# Get token from user
echo "Enter your JWT token (or press Enter to skip token test):"
read -r TOKEN

if [ -z "$TOKEN" ]; then
    echo "⚠️  Skipping authenticated requests (need token)"
    TOKEN_TEST=false
else
    TOKEN_TEST=true
fi

echo ""
echo "📊 Starting tests..."
echo ""

# Test 1: Health endpoint (should work)
echo "1️⃣ Testing health endpoint (should work)..."
HEALTH_START=$(date +%s%N)
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" https://themachine.vernalcontentum.com/health 2>&1)
HEALTH_END=$(date +%s%N)
HEALTH_TIME=$(( (HEALTH_END - HEALTH_START) / 1000000 ))
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
if [ "$HEALTH_CODE" = "200" ]; then
    echo "✅ Health endpoint works (${HEALTH_TIME}ms)"
else
    echo "❌ Health endpoint failed (HTTP $HEALTH_CODE)"
fi

# Test 2: OPTIONS request (CORS preflight - should work)
echo ""
echo "2️⃣ Testing OPTIONS request (CORS preflight)..."
OPTIONS_START=$(date +%s%N)
OPTIONS_RESPONSE=$(curl -X OPTIONS \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  -s -w "\n%{http_code}" \
  https://themachine.vernalcontentum.com/admin/settings/linkedin_client_id \
  --max-time 5 2>&1)
OPTIONS_END=$(date +%s%N)
OPTIONS_TIME=$(( (OPTIONS_END - OPTIONS_START) / 1000000 ))
OPTIONS_CODE=$(echo "$OPTIONS_RESPONSE" | tail -n1)
if [ "$OPTIONS_CODE" = "200" ]; then
    echo "✅ OPTIONS request works (${OPTIONS_TIME}ms)"
else
    echo "❌ OPTIONS request failed (HTTP $OPTIONS_CODE)"
fi

# Test 3: GET request (if token provided)
if [ "$TOKEN_TEST" = true ]; then
    echo ""
    echo "3️⃣ Testing GET request to admin settings..."
    GET_START=$(date +%s%N)
    GET_RESPONSE=$(curl -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -s -w "\n%{http_code}" \
      https://themachine.vernalcontentum.com/admin/settings/linkedin_client_id \
      --max-time 20 2>&1)
    GET_END=$(date +%s%N)
    GET_TIME=$(( (GET_END - GET_START) / 1000000 ))
    GET_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    GET_BODY=$(echo "$GET_RESPONSE" | head -n-1)
    
    if [ "$GET_CODE" = "200" ]; then
        echo "✅ GET request works (${GET_TIME}ms)"
        echo "   Response: $GET_BODY"
    elif [ "$GET_CODE" = "403" ]; then
        echo "⚠️  GET request returned 403 (auth issue, but request reached backend)"
        echo "   Response: $GET_BODY"
    elif [ "$GET_CODE" = "000" ]; then
        echo "❌ GET request timed out or failed to connect (${GET_TIME}ms)"
        echo "   This means nginx isn't forwarding the request"
    else
        echo "❌ GET request failed (HTTP $GET_CODE, ${GET_TIME}ms)"
        echo "   Response: $GET_BODY"
    fi
fi

# Test 4: PUT request (if token provided)
if [ "$TOKEN_TEST" = true ]; then
    echo ""
    echo "4️⃣ Testing PUT request to admin settings..."
    PUT_START=$(date +%s%N)
    PUT_RESPONSE=$(curl -X PUT \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"setting_value":"test_value_12345","description":"Test"}' \
      -s -w "\n%{http_code}" \
      https://themachine.vernalcontentum.com/admin/settings/linkedin_client_id \
      --max-time 20 2>&1)
    PUT_END=$(date +%s%N)
    PUT_TIME=$(( (PUT_END - PUT_START) / 1000000 ))
    PUT_CODE=$(echo "$PUT_RESPONSE" | tail -n1)
    PUT_BODY=$(echo "$PUT_RESPONSE" | head -n-1)
    
    if [ "$PUT_CODE" = "200" ]; then
        echo "✅ PUT request works (${PUT_TIME}ms)"
        echo "   Response: $PUT_BODY"
    elif [ "$PUT_CODE" = "403" ]; then
        echo "⚠️  PUT request returned 403 (auth issue, but request reached backend)"
        echo "   Response: $PUT_BODY"
    elif [ "$PUT_CODE" = "000" ]; then
        echo "❌ PUT request timed out or failed to connect (${PUT_TIME}ms)"
        echo "   This means nginx isn't forwarding the request"
    else
        echo "❌ PUT request failed (HTTP $PUT_CODE, ${PUT_TIME}ms)"
        echo "   Response: $PUT_BODY"
    fi
fi

echo ""
echo "==================================="
echo "✅ Tests complete!"
echo ""
echo "💡 If GET/PUT requests timeout (000 or >20s):"
echo "   - Nginx is not forwarding requests to backend"
echo "   - Check nginx error logs: sudo tail -f /var/log/nginx/error.log"
echo "   - Check nginx config: sudo nginx -t"
echo ""
echo "💡 If GET/PUT requests return 403:"
echo "   - Requests ARE reaching backend (good!)"
echo "   - Issue is authentication/authorization"
echo ""
echo "💡 Watch backend logs while running tests:"
echo "   sudo journalctl -u vernal-agents -f | grep 'INCOMING\|admin/settings'"

