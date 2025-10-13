#!/bin/bash
# Test all available endpoints

echo "Testing all endpoints..."

echo "1. Health endpoint:"
curl -s http://localhost:8000/health

echo -e "\n2. Root endpoint:"
curl -s http://localhost:8000/

echo -e "\n3. OpenAPI docs:"
curl -s http://localhost:8000/docs

echo -e "\n4. Available endpoints from OpenAPI:"
curl -s http://localhost:8000/openapi.json | jq '.paths | keys' 2>/dev/null || echo "Could not parse OpenAPI"

echo -e "\n5. Service status:"
sudo systemctl status vernal-agents --no-pager | head -10
