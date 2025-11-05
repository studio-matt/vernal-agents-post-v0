#!/bin/bash
# Fix OpenAI API key if truncated and install missing dependencies

ENV_FILE="/home/ubuntu/vernal-agents-post-v0/.env"

echo "🔍 Checking OpenAI API Key..."
echo ""

# Check current key
if grep -q "^OPENAI_API_KEY=" "$ENV_FILE"; then
    CURRENT_KEY=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d '=' -f2)
    KEY_LENGTH=${#CURRENT_KEY}
    
    echo "Current key length: $KEY_LENGTH characters"
    echo "First 10 chars: ${CURRENT_KEY:0:10}"
    echo "Last 10 chars: ${CURRENT_KEY: -10}"
    echo ""
    
    # OpenAI keys are typically 51-52 characters
    if [ $KEY_LENGTH -lt 48 ]; then
        echo "⚠️  API key appears truncated (less than 48 chars)"
        echo ""
        echo "Please provide the complete API key:"
        read -s FULL_KEY
        
        # Remove old key
        sed -i '/^OPENAI_API_KEY=/d' "$ENV_FILE"
        
        # Add new key
        echo "" >> "$ENV_FILE"
        echo "# OpenAI API Key for LLM-based topic generation" >> "$ENV_FILE"
        echo "OPENAI_API_KEY=$FULL_KEY" >> "$ENV_FILE"
        
        echo "✅ API key updated"
    else
        echo "✅ API key length looks correct"
    fi
else
    echo "❌ OPENAI_API_KEY not found in .env"
    echo "Please run: bash scripts/add_openai_key.sh"
    exit 1
fi

echo ""
echo "📦 Installing missing dependencies..."
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

# Install missing packages
pip install bertopic crewai --no-cache-dir

echo ""
echo "✅ All fixes complete!"
echo ""
echo "Restart the service:"
echo "  sudo systemctl restart vernal-agents"

