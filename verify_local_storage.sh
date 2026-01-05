#!/bin/bash
echo "🔍 Verifying Local Image Storage Setup"
echo "======================================"
echo ""

cd /home/ubuntu/vernal-agents-post-v0

echo "1. Checking tools.py..."
if grep -q "def save_image_locally" tools.py; then
    echo "✅ save_image_locally function exists"
else
    echo "❌ save_image_locally function NOT found"
fi

if grep -q "save_image_locally(image_data, filename)" tools.py; then
    echo "✅ Function call updated"
else
    echo "❌ Function call NOT updated"
fi

echo ""
echo "2. Checking main.py..."
if grep -q "from fastapi.staticfiles import StaticFiles" main.py; then
    echo "✅ StaticFiles import found"
else
    echo "❌ StaticFiles import NOT found"
fi

if grep -q 'app.mount("/images"' main.py; then
    echo "✅ Static file mounting found"
    grep 'app.mount("/images"' main.py
else
    echo "❌ Static file mounting NOT found"
fi

echo ""
echo "3. Checking directory..."
if [ -d "uploads/images" ]; then
    echo "✅ uploads/images directory exists"
    ls -ld uploads/images
else
    echo "❌ uploads/images directory NOT found"
fi

echo ""
echo "4. Testing static file serving..."
# Create test file
echo "test content" > uploads/images/test.txt
sleep 2

# Test via FastAPI (direct backend)
echo "   Testing direct backend (127.0.0.1:8000)..."
BACKEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/images/test.txt 2>/dev/null || echo "000")
if [ "$BACKEND_CODE" = "200" ]; then
    echo "✅ Backend serving files (HTTP $BACKEND_CODE)"
    curl -s http://127.0.0.1:8000/images/test.txt
else
    echo "⚠️  Backend returned HTTP $BACKEND_CODE"
fi

# Test via nginx (external)
echo ""
echo "   Testing via nginx (themachine.vernalcontentum.com)..."
EXTERNAL_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://themachine.vernalcontentum.com/images/test.txt 2>/dev/null || echo "000")
if [ "$EXTERNAL_CODE" = "200" ]; then
    echo "✅ External URL works (HTTP $EXTERNAL_CODE)"
    curl -s https://themachine.vernalcontentum.com/images/test.txt
else
    echo "⚠️  External URL returned HTTP $EXTERNAL_CODE"
    echo "   (May need nginx configuration for /images/ path)"
fi

# Cleanup
rm -f uploads/images/test.txt

echo ""
echo "5. Checking service logs for static file mount..."
sudo journalctl -u vernal-agents --since "2 minutes ago" | grep -i "static\|images" | tail -5 || echo "   (No recent logs about static files)"

echo ""
echo "✅ Verification complete!"
