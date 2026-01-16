#!/bin/bash
# Validate that all routers in app/routes/ are included in main.py
# Prevents 404 errors from missing router includes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROUTES_DIR="$REPO_ROOT/app/routes"
MAIN_PY="$REPO_ROOT/main.py"

echo "🔍 Validating all routers are included in main.py..."
echo ""

if [ ! -d "$ROUTES_DIR" ]; then
    echo "❌ ERROR: app/routes/ directory not found"
    exit 1
fi

if [ ! -f "$MAIN_PY" ]; then
    echo "❌ ERROR: main.py not found"
    exit 1
fi

# Find all router definitions in app/routes/
echo "📦 Scanning app/routes/ for router definitions..."
ROUTERS_FOUND=()
while IFS= read -r file; do
    # Extract router name from file (e.g., campaigns.py -> campaigns_router)
    # Look for pattern like "campaigns_router = APIRouter()"
    router_name=$(grep -hE "[a-z_]+_router\s*=\s*APIRouter\(\)" "$file" 2>/dev/null | sed -E 's/^[[:space:]]*([a-z_]+_router)[[:space:]]*=.*/\1/' | head -1)
    if [ -n "$router_name" ]; then
        filename=$(basename "$file" .py)
        ROUTERS_FOUND+=("$filename:$router_name")
    fi
done < <(find "$ROUTES_DIR" -name "*.py" -type f ! -name "__init__.py")

if [ ${#ROUTERS_FOUND[@]} -eq 0 ]; then
    echo "⚠️  WARNING: No routers found in app/routes/"
    exit 0
fi

echo "✅ Found ${#ROUTERS_FOUND[@]} router(s):"
for router_info in "${ROUTERS_FOUND[@]}"; do
    filename=$(echo "$router_info" | cut -d: -f1)
    router_name=$(echo "$router_info" | cut -d: -f2)
    echo "   - $filename.py: $router_name"
done
echo ""

# Check if each router is imported and included in main.py
echo "🔍 Checking main.py for router includes..."
echo ""

MISSING_ROUTERS=()
ALL_INCLUDED=true

for router_info in "${ROUTERS_FOUND[@]}"; do
    filename=$(echo "$router_info" | cut -d: -f1)
    router_name=$(echo "$router_info" | cut -d: -f2)
    
    # Check if router is imported (flexible pattern to match variations)
    # Match: "from app.routes.filename import router_name" or "from app.routes.filename import router_name as ..."
    if grep -qE "from app\.routes\.$filename import $router_name" "$MAIN_PY" 2>/dev/null; then
        # Check if router is included (match "app.include_router(router_name)" with optional whitespace)
        if grep -qE "app\.include_router\($router_name\)" "$MAIN_PY" 2>/dev/null; then
            echo "✅ $router_name: imported and included"
        else
            echo "⚠️  $router_name: imported but NOT included"
            MISSING_ROUTERS+=("$router_name (from $filename.py) - imported but not included")
            ALL_INCLUDED=false
        fi
    else
        echo "❌ $router_name: MISSING from main.py"
        MISSING_ROUTERS+=("$router_name (from $filename.py)")
        ALL_INCLUDED=false
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$ALL_INCLUDED" = true ]; then
    echo "✅ All routers are included in main.py"
    echo ""
    exit 0
else
    echo "❌ ERROR: Missing routers in main.py:"
    for router in "${MISSING_ROUTERS[@]}"; do
        echo "   - $router"
    done
    echo ""
    echo "💡 To fix, add to main.py:"
    echo ""
    for router_info in "${ROUTERS_FOUND[@]}"; do
        filename=$(echo "$router_info" | cut -d: -f1)
        router_name=$(echo "$router_info" | cut -d: -f2)
        if [[ " ${MISSING_ROUTERS[@]} " =~ " ${router_name} " ]]; then
            echo "try:"
            echo "    from app.routes.$filename import $router_name"
            echo "    app.include_router($router_name)"
            echo "    logger.info(\"✅ $router_name included successfully\")"
            echo "except Exception as e:"
            echo "    logger.error(f\"❌ Failed to include $router_name: {e}\")"
            echo ""
        fi
    done
    exit 1
fi

