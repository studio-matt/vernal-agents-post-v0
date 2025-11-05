#!/bin/bash
# Install langdetect for language filtering

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

echo "📦 Installing langdetect for language detection..."
pip install langdetect>=1.0.9

# Verify installation
python -c "from langdetect import detect; print('✅ langdetect installed successfully')" || {
    echo "❌ Failed to install langdetect"
    exit 1
}

echo "✅ langdetect installation complete!"
echo ""
echo "Language filtering is now enabled. Non-English content will be automatically filtered out."

