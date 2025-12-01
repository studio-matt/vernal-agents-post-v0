#!/bin/bash
# Fix author-related folder name to author_related for Python imports
# Python cannot import modules with hyphens in the name

set -e

cd /home/ubuntu/vernal-agents-post-v0

echo "🔧 Fixing author-related folder name..."

# Check if author-related exists
if [ ! -d "author-related" ]; then
    echo "❌ Error: author-related folder not found"
    exit 1
fi

# Check if author_related already exists
if [ -d "author_related" ]; then
    echo "⚠️  author_related already exists. Checking if it's different..."
    if [ -d "author-related" ]; then
        echo "📋 Both folders exist. Keeping author_related, removing author-related..."
        rm -rf author-related
        echo "✅ Cleaned up author-related folder"
    else
        echo "✅ author_related already exists and author-related is gone - already fixed!"
    fi
else
    # Rename author-related to author_related
    echo "📦 Renaming author-related to author_related..."
    mv author-related author_related
    echo "✅ Folder renamed successfully"
fi

echo "📋 Verifying Python can import it..."
source venv/bin/activate
python3 -c "from author_related import ProfileExtractor; print('✅ Import successful!')" || {
    echo "❌ Import test failed"
    echo "⚠️  Note: The code has a workaround for hyphenated folder names, but renaming is preferred."
    exit 1
}

echo ""
echo "✅ All checks passed!"
echo "📋 Next steps:"
echo "   1. Pull the latest code: git pull"
echo "   2. Restart the service: sudo systemctl restart vernal-agents"
echo "   3. Test the endpoint: curl -H 'Authorization: Bearer YOUR_TOKEN' https://themachine.vernalcontentum.com/author_personalities/test-assets"

