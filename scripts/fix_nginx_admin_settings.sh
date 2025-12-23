#!/bin/bash
# Fix nginx configuration for admin settings timeout
# Run on backend server: bash scripts/fix_nginx_admin_settings.sh

echo "🔧 FIXING NGINX CONFIGURATION FOR ADMIN SETTINGS"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NGINX_CONFIG="/etc/nginx/sites-enabled/themachine"

# Step 1: Backup current config
echo "1️⃣ Backing up nginx config..."
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✅ Backup created${NC}"

# Step 2: Check current timeout settings
echo ""
echo "2️⃣ Checking current timeout settings..."
if grep -q "proxy_read_timeout\|proxy_connect_timeout\|proxy_send_timeout" "$NGINX_CONFIG"; then
    echo "Current timeout settings:"
    grep -E "proxy_read_timeout|proxy_connect_timeout|proxy_send_timeout" "$NGINX_CONFIG"
else
    echo -e "${YELLOW}⚠️  No timeout settings found${NC}"
fi

# Step 3: Check if backend proxy location exists
echo ""
echo "3️⃣ Checking backend proxy configuration..."
if grep -q "proxy_pass.*127.0.0.1:8000\|proxy_pass.*localhost:8000" "$NGINX_CONFIG"; then
    echo -e "${GREEN}✅ Backend proxy found${NC}"
    grep -B 2 -A 5 "proxy_pass.*127.0.0.1:8000\|proxy_pass.*localhost:8000" "$NGINX_CONFIG" | head -10
else
    echo -e "${RED}❌ No backend proxy found!${NC}"
    echo "   This might be the issue - requests go directly to backend domain"
    echo "   Checking if requests bypass nginx..."
    
    # Check if frontend calls backend directly
    echo ""
    echo "   Frontend calls backend at: https://themachine.vernalcontentum.com"
    echo "   If nginx is NOT proxying, requests go directly to backend (port 443)"
    echo "   Backend should be listening on port 8000, not 443"
    echo ""
    echo "   Checking backend port..."
    if netstat -tlnp 2>/dev/null | grep -q ":8000 " || ss -tlnp 2>/dev/null | grep -q ":8000 "; then
        echo -e "${GREEN}✅ Backend is listening on port 8000${NC}"
    else
        echo -e "${RED}❌ Backend is NOT listening on port 8000${NC}"
        exit 1
    fi
fi

# Step 4: Add/update timeout settings
echo ""
echo "4️⃣ Adding/updating timeout settings..."

# Check if there's a location block that proxies to backend
LOCATION_BLOCK=$(grep -n "location.*/" "$NGINX_CONFIG" | head -1 | cut -d: -f1)

if [ -z "$LOCATION_BLOCK" ]; then
    echo -e "${YELLOW}⚠️  Could not find location block automatically${NC}"
    echo "   Please manually check nginx config:"
    echo "   sudo nano $NGINX_CONFIG"
    echo ""
    echo "   Add these lines inside the location block that proxies to backend:"
    echo "   proxy_read_timeout 30s;"
    echo "   proxy_connect_timeout 30s;"
    echo "   proxy_send_timeout 30s;"
    exit 1
fi

# Create temp file with updated config
TEMP_CONFIG=$(mktemp)
sudo cp "$NGINX_CONFIG" "$TEMP_CONFIG"

# Add timeout settings if they don't exist
if ! grep -q "proxy_read_timeout" "$TEMP_CONFIG"; then
    # Find the location block that proxies to backend and add timeouts
    # This is a simple approach - might need manual adjustment
    sed -i '/proxy_pass.*127.0.0.1:8000/a\        proxy_read_timeout 30s;\n        proxy_connect_timeout 30s;\n        proxy_send_timeout 30s;' "$TEMP_CONFIG" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Could not auto-add timeout settings${NC}"
        echo "   Please manually edit: sudo nano $NGINX_CONFIG"
        echo ""
        echo "   Add these lines inside the location block:"
        echo "   proxy_read_timeout 30s;"
        echo "   proxy_connect_timeout 30s;"
        echo "   proxy_send_timeout 30s;"
        rm "$TEMP_CONFIG"
        exit 1
    }
fi

# Step 5: Test nginx config
echo ""
echo "5️⃣ Testing nginx configuration..."
if sudo nginx -t; then
    echo -e "${GREEN}✅ Nginx config is valid${NC}"
    
    # Ask if user wants to apply changes
    echo ""
    read -p "Apply changes? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo cp "$TEMP_CONFIG" "$NGINX_CONFIG"
        sudo systemctl reload nginx
        echo -e "${GREEN}✅ Nginx reloaded with new timeout settings${NC}"
    else
        echo -e "${YELLOW}⚠️  Changes not applied. Config saved to: $TEMP_CONFIG${NC}"
    fi
else
    echo -e "${RED}❌ Nginx config test failed!${NC}"
    echo "   Restoring backup..."
    sudo cp "${NGINX_CONFIG}.backup."* "$NGINX_CONFIG" 2>/dev/null || true
    rm "$TEMP_CONFIG"
    exit 1
fi

rm "$TEMP_CONFIG"

# Step 6: Test backend connectivity
echo ""
echo "6️⃣ Testing backend connectivity through nginx..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" https://themachine.vernalcontentum.com/health 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Backend is reachable through nginx (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $BODY"
else
    echo -e "${RED}❌ Backend NOT reachable through nginx (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $BODY"
fi

echo ""
echo "================================================"
echo "✅ Fix complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Try saving LinkedIn settings again"
echo "   2. Watch backend logs: sudo journalctl -u vernal-agents -f"
echo "   3. Watch nginx logs: sudo tail -f /var/log/nginx/error.log"

