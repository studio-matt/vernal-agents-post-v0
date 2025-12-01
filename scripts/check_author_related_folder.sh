#!/bin/bash
# Check the status of author-related/author_related folder on server

cd /home/ubuntu/vernal-agents-post-v0

echo "🔍 Checking author-related folder status..."
echo ""

# Check if author-related exists
if [ -d "author-related" ]; then
    echo "❌ Found: author-related (with hyphen) - needs to be renamed"
    echo "   Files in author-related:"
    ls -la author-related/ | head -10
elif [ -d "author_related" ]; then
    echo "✅ Found: author_related (with underscore) - correct!"
    echo "   Files in author_related:"
    ls -la author_related/ | head -10
    echo ""
    echo "📋 Checking if __init__.py exists:"
    if [ -f "author_related/__init__.py" ]; then
        echo "   ✅ __init__.py exists"
    else
        echo "   ❌ __init__.py missing!"
    fi
else
    echo "❌ Neither author-related nor author_related folder found!"
    echo "   Current directory contents:"
    ls -la | grep -E "author|Author" || echo "   (no author-related folders found)"
fi

echo ""
echo "📋 Testing Python import..."
source venv/bin/activate
python3 -c "
import sys
from pathlib import Path
backend_dir = Path('/home/ubuntu/vernal-agents-post-v0')
print(f'Backend dir: {backend_dir}')
print(f'Backend dir exists: {backend_dir.exists()}')
print(f'Python path: {sys.path[:3]}')
print('')
if (backend_dir / 'author_related').exists():
    print('✅ author_related folder exists')
    if (backend_dir / 'author_related' / '__init__.py').exists():
        print('✅ __init__.py exists')
    else:
        print('❌ __init__.py missing')
elif (backend_dir / 'author-related').exists():
    print('⚠️  author-related folder exists (needs rename)')
else:
    print('❌ Neither folder found')
"

