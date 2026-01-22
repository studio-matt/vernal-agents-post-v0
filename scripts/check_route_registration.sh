#!/bin/bash
# Check if generate-content route is registered

echo "=========================================="
echo "Checking route registration"
echo "=========================================="

cd /home/ubuntu/vernal-agents-post-v0 || exit 1

# Check if the route exists in the code
echo ""
echo "1. Checking if route exists in code..."
if grep -q "@brand_personalities_router.post(\"/campaigns/{campaign_id}/generate-content\")" app/routes/brand_personalities.py; then
    echo "   ✅ Route definition found in code"
else
    echo "   ❌ Route definition NOT found in code"
    exit 1
fi

# Check if Body is imported
echo ""
echo "2. Checking if Body is imported..."
if grep -q "from fastapi import.*Body" app/routes/brand_personalities.py; then
    echo "   ✅ Body is imported"
else
    echo "   ❌ Body is NOT imported"
    exit 1
fi

# Check if Body(...) is used in the endpoint
echo ""
echo "3. Checking if Body(...) is used in endpoint..."
if grep -A 5 "@brand_personalities_router.post(\"/campaigns/{campaign_id}/generate-content\")" app/routes/brand_personalities.py | grep -q "Body(...)"; then
    echo "   ✅ Body(...) is used in endpoint"
else
    echo "   ❌ Body(...) is NOT used in endpoint"
    exit 1
fi

# Check if router is included in main.py
echo ""
echo "4. Checking if router is included in main.py..."
if grep -q "from app.routes.brand_personalities import brand_personalities_router" main.py && grep -q "app.include_router(brand_personalities_router)" main.py; then
    echo "   ✅ Router is included in main.py"
else
    echo "   ❌ Router is NOT included in main.py"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All checks passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart the backend service:"
echo "   sudo systemctl restart vernal-backend"
echo ""
echo "2. Check service status:"
echo "   sudo systemctl status vernal-backend"
echo ""
echo "3. Check logs for any errors:"
echo "   sudo journalctl -u vernal-backend -n 50 --no-pager"
echo ""

