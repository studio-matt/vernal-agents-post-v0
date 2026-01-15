#!/bin/bash
# Find syntax errors in Python files
# Run this on the server to locate the exact file and line with the error

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate 2>/dev/null || true

echo "Checking Python syntax in all files..."
echo ""

# Check main.py first
echo "=== Checking main.py ==="
python3 -m py_compile main.py 2>&1 | head -10
if [ $? -eq 0 ]; then
    echo "✅ main.py syntax OK"
else
    echo "❌ main.py has syntax errors"
fi
echo ""

# Check all route files
if [ -d "app/routes" ]; then
    echo "=== Checking app/routes/*.py ==="
    for file in app/routes/*.py; do
        if [ -f "$file" ]; then
            python3 -m py_compile "$file" 2>&1 | head -5
            if [ $? -eq 0 ]; then
                echo "✅ $(basename $file) syntax OK"
            else
                echo "❌ $(basename $file) has syntax errors"
            fi
        fi
    done
fi
echo ""

# Try importing main to see the full error
echo "=== Full import error ==="
python3 -c "import main" 2>&1 | head -30

