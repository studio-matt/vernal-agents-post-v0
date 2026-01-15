#!/bin/bash
# Comprehensive syntax error finder for all Python files
# This will find ALL syntax errors at once, not one at a time

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate 2>/dev/null || true

echo "=========================================="
echo "COMPREHENSIVE SYNTAX ERROR CHECK"
echo "=========================================="
echo ""

ERRORS_FOUND=0

# Function to check a file
check_file() {
    local file=$1
    if [ ! -f "$file" ]; then
        return
    fi
    
    # Try to compile the file
    OUTPUT=$(python3 -m py_compile "$file" 2>&1)
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "❌ $file"
        echo "$OUTPUT" | sed 's/^/   /'
        echo ""
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
        return 1
    else
        echo "✅ $file"
        return 0
    fi
}

# Check main.py
echo "=== Checking main.py ==="
check_file "main.py"
echo ""

# Check all route files
echo "=== Checking app/routes/*.py ==="
if [ -d "app/routes" ]; then
    for file in app/routes/*.py; do
        if [ -f "$file" ]; then
            check_file "$file"
        fi
    done
else
    echo "⚠️  app/routes directory not found"
fi
echo ""

# Check other Python files in app/
echo "=== Checking app/**/*.py ==="
find app -name "*.py" -type f 2>/dev/null | while read file; do
    if [[ ! "$file" =~ "app/routes" ]]; then
        check_file "$file"
    fi
done
echo ""

# Try full import to catch any import-time errors
echo "=== Testing full import ==="
IMPORT_OUTPUT=$(python3 -c "import main" 2>&1)
IMPORT_EXIT=$?

if [ $IMPORT_EXIT -ne 0 ] || echo "$IMPORT_OUTPUT" | grep -qiE "SyntaxError|IndentationError|ImportError|NameError|Traceback"; then
    echo "❌ Full import FAILED!"
    echo ""
    echo "Error details:"
    echo "$IMPORT_OUTPUT" | grep -iE "SyntaxError|IndentationError|ImportError|NameError|Traceback|Error:" | head -30 | sed 's/^/   /'
    if [ -z "$(echo "$IMPORT_OUTPUT" | grep -iE "SyntaxError|IndentationError|ImportError|NameError|Traceback|Error:")" ]; then
        echo "   Exit code: $IMPORT_EXIT"
        echo "   Full output (last 20 lines):"
        echo "$IMPORT_OUTPUT" | tail -20 | sed 's/^/   /'
    fi
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
else
    echo "✅ Full import successful"
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
if [ $ERRORS_FOUND -eq 0 ]; then
    echo "✅ All syntax checks passed! No errors found."
    exit 0
else
    echo "❌ Found $ERRORS_FOUND file(s) with syntax errors"
    echo ""
    echo "Next steps:"
    echo "1. Review the errors above"
    echo "2. Fix each file"
    echo "3. Run this script again to verify"
    exit 1
fi

