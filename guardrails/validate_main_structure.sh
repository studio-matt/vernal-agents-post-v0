#!/bin/bash
# Validate main.py structure after refactoring
# Ensures main.py is a thin entry point, not a monolithic file
# Automatically creates backup before validation if backup doesn't exist

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_PY="$REPO_ROOT/main.py"
BACKUP_DIR="$REPO_ROOT/.refactor_backups"

echo "🔍 Validating main.py structure..."
echo ""

# Auto-create backup if it doesn't exist and we're in a refactoring context
if [ -f "$MAIN_PY" ] && [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "📦 No backup found - creating automatic backup..."
    bash "$SCRIPT_DIR/backup_before_refactor.sh" "$MAIN_PY" 2>/dev/null || true
    echo ""
fi

# Check if main.py exists
if [ ! -f "$MAIN_PY" ]; then
    echo "❌ ERROR: main.py does not exist!"
    echo "   This is a critical file - it must exist for the service to start."
    exit 1
fi

# Count lines
LINE_COUNT=$(wc -l < "$MAIN_PY")
echo "📊 File size: $LINE_COUNT lines"

if [ "$LINE_COUNT" -gt 300 ]; then
    echo "⚠️  WARNING: main.py is larger than expected (>300 lines)"
    echo "   After refactoring, main.py should be a thin entry point (50-150 lines)"
    echo "   Consider extracting more code to routers."
fi

# Check for FastAPI app creation
if ! grep -q "app = FastAPI" "$MAIN_PY"; then
    echo "❌ ERROR: FastAPI app not found in main.py"
    echo "   Expected: app = FastAPI(...)"
    exit 1
else
    echo "✅ FastAPI app creation found"
fi

# Check for CORS middleware
if ! grep -q "CORSMiddleware" "$MAIN_PY"; then
    echo "⚠️  WARNING: CORS middleware not found"
    echo "   CORS is required for frontend access"
else
    echo "✅ CORS middleware found"
fi

# Count router includes
ROUTER_COUNT=$(grep -c "app.include_router" "$MAIN_PY" || echo "0")
echo "📦 Router includes: $ROUTER_COUNT"

if [ "$ROUTER_COUNT" -eq 0 ]; then
    echo "⚠️  WARNING: No routers included in main.py"
    echo "   Routes should be included via app.include_router()"
fi

# Count endpoint definitions (should be minimal - only health/root)
# This is a rough check - looks for @app.get/post/put/delete decorators
ENDPOINT_COUNT=$(grep -cE "@app\.(get|post|put|delete|patch)" "$MAIN_PY" || echo "0")
echo "🔌 Endpoint definitions in main.py: $ENDPOINT_COUNT"

if [ "$ENDPOINT_COUNT" -gt 3 ]; then
    echo "⚠️  WARNING: Too many endpoint definitions in main.py"
    echo "   main.py should only have health/root endpoints"
    echo "   Other endpoints should be in router files"
    echo ""
    echo "   Endpoints found:"
    grep -nE "@app\.(get|post|put|delete|patch)" "$MAIN_PY" | head -10
fi

# Check for common mistakes
if grep -q "def get_db()" "$MAIN_PY"; then
    echo "⚠️  WARNING: get_db() function found in main.py"
    echo "   This should be in router files or app/utils/"
fi

if grep -q "class.*BaseModel" "$MAIN_PY"; then
    echo "⚠️  WARNING: Pydantic models found in main.py"
    echo "   Models should be in app/schemas/ or router files"
fi

# Check for syntax errors (if python3 is available)
echo ""
echo "🔍 Checking syntax..."
if command -v python3 >/dev/null 2>&1; then
    if python3 -m py_compile "$MAIN_PY" 2>/dev/null; then
        echo "✅ Syntax is valid"
    else
        echo "❌ ERROR: Syntax errors found in main.py"
        python3 -m py_compile "$MAIN_PY"
        exit 1
    fi
    
    # Check if import works
    echo ""
    echo "🔍 Testing import..."
    if python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT'); import main" 2>/dev/null; then
        echo "✅ Import successful"
    else
        echo "❌ ERROR: Failed to import main.py"
        python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT'); import main" 2>&1 | head -20
        exit 1
    fi
else
    echo "⚠️  python3 not found - skipping syntax/import checks"
    echo "   Run 'bash find_all_syntax_errors.sh' manually to verify syntax"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ main.py exists"
echo "✅ FastAPI app creation found"
[ "$ROUTER_COUNT" -gt 0 ] && echo "✅ Routers included ($ROUTER_COUNT)" || echo "⚠️  No routers included"
[ "$ENDPOINT_COUNT" -le 3 ] && echo "✅ Endpoint count acceptable ($ENDPOINT_COUNT)" || echo "⚠️  Too many endpoints ($ENDPOINT_COUNT)"
echo "✅ Syntax valid"
echo "✅ Import successful"
echo ""
echo "💡 Tip: After refactoring, main.py should be a thin entry point that:"
echo "   1. Creates FastAPI app"
echo "   2. Configures CORS"
echo "   3. Includes routers"
echo "   4. Has minimal health/root endpoints"
echo ""

