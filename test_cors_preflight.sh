#!/bin/bash
# Test CORS preflight for admin endpoints

echo "Testing OPTIONS request to admin endpoint..."
curl -X OPTIONS "https://themachine.vernalcontentum.com/admin/settings/research_agents_list" \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  -v 2>&1 | grep -i "access-control\|HTTP/"
