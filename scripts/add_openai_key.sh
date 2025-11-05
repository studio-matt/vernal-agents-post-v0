#!/bin/bash
# Script to safely add OPENAI_API_KEY to .env file

ENV_FILE="/home/ubuntu/vernal-agents-post-v0/.env"

echo "🔑 Adding OPENAI_API_KEY to .env file..."
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    echo "Please create it first with database credentials."
    exit 1
fi

# Check if OPENAI_API_KEY already exists
if grep -q "^OPENAI_API_KEY=" "$ENV_FILE"; then
    echo "⚠️  OPENAI_API_KEY already exists in .env"
    echo "Current value (first 10 chars): $(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d '=' -f2 | cut -c1-10)..."
    read -p "Do you want to update it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing key."
        exit 0
    fi
    # Remove old key
    sed -i '/^OPENAI_API_KEY=/d' "$ENV_FILE"
    echo "✅ Removed old OPENAI_API_KEY"
fi

# Prompt for API key
echo "Enter your OpenAI API key (starts with 'sk-'):"
read -s OPENAI_KEY

if [ -z "$OPENAI_KEY" ]; then
    echo "❌ No key provided. Exiting."
    exit 1
fi

# Validate key format (should start with sk-)
if [[ ! "$OPENAI_KEY" =~ ^sk- ]]; then
    echo "⚠️  Warning: OpenAI API keys usually start with 'sk-'. Continuing anyway..."
fi

# Add key to .env
echo "" >> "$ENV_FILE"
echo "# OpenAI API Key for LLM-based topic generation" >> "$ENV_FILE"
echo "OPENAI_API_KEY=$OPENAI_KEY" >> "$ENV_FILE"

echo "✅ OPENAI_API_KEY added to .env file"
echo ""
echo "⚠️  IMPORTANT: Restart the backend service to apply changes:"
echo "   sudo systemctl restart vernal-agents"
echo ""
echo "After restart, topics will be generated using LLM instead of LDA."

