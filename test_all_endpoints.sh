#!/bin/bash
# Test all available endpoints

echo "Testing all available endpoints..."

echo "1. Health endpoint:"
curl -s http://localhost:8000/health

echo -e "\n2. Root endpoint:"
curl -s http://localhost:8000/

echo -e "\n3. Campaigns endpoint:"
curl -s http://localhost:8000/campaigns

echo -e "\n4. Test health endpoint:"
curl -s http://localhost:8000/test-health

echo -e "\n5. Version endpoint:"
curl -s http://localhost:8000/version

echo -e "\n6. Test router health:"
curl -s http://localhost:8000/test/health

echo -e "\n7. Test router ping:"
curl -s http://localhost:8000/test/ping

echo -e "\n8. Debug routes:"
curl -s http://localhost:8000/debug/routes

echo -e "\n9. Service status:"
sudo systemctl status vernal-agents --no-pager | head -5

echo -e "\n10. Public URL test:"
curl -s https://themachine.vernalcontentum.com/health
