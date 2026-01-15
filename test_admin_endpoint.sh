#!/bin/bash
# Test admin endpoint directly to see if it's accessible

echo "Testing admin endpoint accessibility..."
echo ""

# Test 1: OPTIONS preflight
echo "1. Testing OPTIONS preflight:"
curl -X OPTIONS "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  -v 2>&1 | grep -E "HTTP/|access-control|OPTIONS" | head -10

echo ""
echo "2. Testing GET (should require auth, but should return CORS headers):"
curl -X GET "http://127.0.0.1:8000/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -v 2>&1 | grep -E "HTTP/|access-control" | head -10

