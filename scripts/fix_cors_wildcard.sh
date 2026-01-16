#!/bin/bash
# Emergency Fix Script: Replace wildcard CORS origins with specific origins
# Use this if main.py has allow_origins=["*"] with allow_credentials=True

set -e

MAIN_PY="/home/ubuntu/vernal-agents-post-v0/main.py"
BACKUP_PY="${MAIN_PY}.backup.$(date +%Y%m%d_%H%M%S)"

echo "🔧 Fixing CORS wildcard issue in main.py"
echo "=========================================="
echo ""

# Check if main.py exists
if [ ! -f "$MAIN_PY" ]; then
    echo "❌ Error: main.py not found at $MAIN_PY"
    exit 1
fi

# Check if wildcard is present
if ! grep -q 'allow_origins=\["\*"\]' "$MAIN_PY" 2>/dev/null; then
    echo "✅ No wildcard CORS configuration found"
    echo "   main.py appears to already have specific origins"
    exit 0
fi

echo "⚠️  Found wildcard CORS configuration"
echo "   Creating backup: $BACKUP_PY"
cp "$MAIN_PY" "$BACKUP_PY"

echo ""
echo "📝 Replacing wildcard with specific origins..."

# Create temporary file with fix
TEMP_FILE=$(mktemp)
python3 << 'PYTHON_SCRIPT' > "$TEMP_FILE"
import re
import sys

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Pattern to match allow_origins=["*"]
pattern = r'allow_origins=\["\*"\]'

# Replacement with specific origins
replacement = '''allow_origins=[
        "https://machine.vernalcontentum.com",
        "https://themachine.vernalcontentum.com",
        "http://localhost:3000",
        "http://localhost:3001",
    ]'''

# Replace
new_content = re.sub(pattern, replacement, content)

# Write back
with open(sys.argv[1], 'w') as f:
    f.write(new_content)

print("✅ Replacement complete")
PYTHON_SCRIPT
python3 "$TEMP_FILE" "$MAIN_PY"
rm "$TEMP_FILE"

echo ""
echo "✅ Fixed main.py CORS configuration"
echo ""
echo "📋 Verifying fix..."
if grep -q 'allow_origins=\["\*"\]' "$MAIN_PY" 2>/dev/null; then
    echo "❌ Error: Wildcard still present after fix"
    echo "   Restoring backup..."
    cp "$BACKUP_PY" "$MAIN_PY"
    exit 1
fi

if grep -q "https://machine.vernalcontentum.com" "$MAIN_PY"; then
    echo "✅ Specific origins found in main.py"
    echo ""
    echo "📋 New configuration:"
    grep -A 5 "allow_origins=\[" "$MAIN_PY" | head -6
else
    echo "⚠️  Warning: Could not verify specific origins"
fi

echo ""
echo "🔄 Restarting service..."
sudo systemctl restart vernal-agents
sleep 2

echo ""
echo "📋 Service status:"
sudo systemctl status vernal-agents --no-pager | head -10

echo ""
echo "✅ Fix complete!"
echo ""
echo "💡 Next steps:"
echo "  1. Test CORS: bash scripts/diagnose_cors.sh"
echo "  2. Verify frontend can connect"
echo "  3. If issues persist, see: guardrails/CORS_EMERGENCY_NET.md"

