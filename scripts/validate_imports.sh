#!/bin/bash
# Pre-commit validation script to catch missing imports
# Run this before committing refactoring changes

set -e

echo "=== IMPORT VALIDATION CHECK ==="
echo ""

ERRORS=0

# 1. Test Python import (catches NameError, ImportError, SyntaxError)
echo "1. Testing Python import..."
if python3 -c "import main" 2>&1 | tee /tmp/import_check.log | grep -qi "NameError\|ImportError\|SyntaxError\|IndentationError"; then
    echo "❌ Import check FAILED"
    echo ""
    echo "Errors found:"
    grep -iE "NameError|ImportError|SyntaxError|IndentationError" /tmp/import_check.log | head -10
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Python import successful (no NameError/ImportError/SyntaxError)"
fi
echo ""

# 2. Check route files for missing imports
echo "2. Checking route files for missing imports..."
for file in app/routes/*.py; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Extract all type hints used in function parameters
    TYPES=$(grep -oE ":\s*[A-Z][a-zA-Z]*(Create|Update|Request|Response|Enum)" "$file" 2>/dev/null | \
            sed 's/.*:\s*//' | sort -u || true)
    
    if [ -z "$TYPES" ]; then
        continue
    fi
    
    # Check each type is imported
    for type in $TYPES; do
        # Skip built-in types
        if [[ "$type" =~ ^(str|int|float|bool|list|dict|Optional|List|Dict|Any|Session|Request|Response)$ ]]; then
            continue
        fi
        
        # Check if type is imported
        if ! grep -q "^from.*import.*$type\|^import.*$type" "$file" 2>/dev/null; then
            # Check if it's defined in the same file (class definition)
            if ! grep -q "^class $type\|^def $type" "$file" 2>/dev/null; then
                echo "⚠️  WARNING: $type used in $file but not imported"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
done

if [ $ERRORS -eq 0 ]; then
    echo "✅ All types are properly imported"
fi
echo ""

# 3. Verify all routers can be imported
echo "3. Verifying router imports..."
if python3 -c "
try:
    from app.routes import campaigns, admin, author_personalities, brand_personalities, platforms
    print('✅ All routers import successfully')
except Exception as e:
    print(f'❌ Router import failed: {e}')
    exit(1)
" 2>&1; then
    echo "✅ Router import check passed"
else
    echo "❌ Router import check failed"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 4. Check for common missing imports after refactoring
echo "4. Checking for common missing imports..."
MISSING=0

# Check if Pydantic models are imported where used
for file in app/routes/*.py; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Check for Create/Update/Request/Response types
    if grep -qE ":\s*[A-Z][a-zA-Z]*(Create|Update|Request|Response)" "$file" 2>/dev/null; then
        # Check if schemas are imported
        if ! grep -q "^from.*schemas.*import\|^from app.schemas" "$file" 2>/dev/null; then
            echo "⚠️  WARNING: $file uses Pydantic models but may not import from schemas"
            MISSING=$((MISSING + 1))
        fi
    fi
done

if [ $MISSING -eq 0 ]; then
    echo "✅ No obvious missing schema imports"
fi
echo ""

# Summary
echo "=== SUMMARY ==="
if [ $ERRORS -eq 0 ] && [ $MISSING -eq 0 ]; then
    echo "✅ All import checks passed. Safe to commit."
    exit 0
else
    echo "❌ Import validation FAILED"
    echo "   Found $ERRORS error(s) and $MISSING warning(s)"
    echo ""
    echo "Fix the issues above before committing."
    echo "See EMERGENCY_NET.md section: 'Missing Imports During Refactoring'"
    exit 1
fi

