#!/bin/bash
# Test CORS fix - verify all endpoints work with credentials

echo "🧪 Testing CORS Fix..."
echo ""

# 1. Test OPTIONS preflight
echo "1. Testing OPTIONS preflight..."
RESPONSE=$(curl -s -X OPTIONS "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -v 2>&1)

if echo "$RESPONSE" | grep -qi "access-control-allow-origin: https://machine.vernalcontentum.com"; then
    echo "✅ OPTIONS preflight: CORS origin header correct"
else
    echo "❌ OPTIONS preflight: CORS origin header missing or incorrect"
fi

if echo "$RESPONSE" | grep -qi "access-control-allow-credentials: true"; then
    echo "✅ OPTIONS preflight: Credentials allowed"
else
    echo "❌ OPTIONS preflight: Credentials not allowed"
fi

if echo "$RESPONSE" | grep -qi "access-control-allow-methods"; then
    echo "✅ OPTIONS preflight: Methods header present"
else
    echo "❌ OPTIONS preflight: Methods header missing"
fi

echo ""

# 2. Test actual GET request
echo "2. Testing GET request with CORS..."
GET_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8000/health" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -v 2>&1)

if echo "$GET_RESPONSE" | grep -qi "access-control-allow-origin: https://machine.vernalcontentum.com"; then
    echo "✅ GET request: CORS origin header present"
else
    echo "❌ GET request: CORS origin header missing"
fi

echo ""
echo "🎉 CORS fix verification complete!"
