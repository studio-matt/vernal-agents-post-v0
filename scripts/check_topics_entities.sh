#!/bin/bash
# Diagnostic script to check why topics are still single words and entities are zero

CAMPAIGN_ID="${1:-1714aa24-594b-49b4-9650-17b830213d99}"

echo "🔍 Diagnosing topics and entities for campaign: $CAMPAIGN_ID"
echo ""

# Check if OPENAI_API_KEY is set
echo "📋 Step 1: Check OpenAI API Key..."
if [ -f /home/ubuntu/vernal-agents-post-v0/.env ]; then
    if grep -q "OPENAI_API_KEY" /home/ubuntu/vernal-agents-post-v0/.env; then
        API_KEY=$(grep "OPENAI_API_KEY" /home/ubuntu/vernal-agents-post-v0/.env | cut -d '=' -f2)
        if [ -n "$API_KEY" ] && [ "$API_KEY" != "" ]; then
            echo "✅ OPENAI_API_KEY is set (length: ${#API_KEY})"
        else
            echo "❌ OPENAI_API_KEY is empty or not set"
        fi
    else
        echo "❌ OPENAI_API_KEY not found in .env"
    fi
else
    echo "❌ .env file not found"
fi
echo ""

# Check backend logs for extract_topics calls
echo "📋 Step 2: Check recent backend logs for extract_topics..."
echo "Looking for extract_topics calls in last 30 minutes..."
sudo journalctl -u vernal-agents --since "30 minutes ago" | grep -E "extract_topics|topic phrases|Generated.*topics|Error extracting topics|LLM extracted|LLM failed" | tail -20
echo ""

# Check for entity extraction logs
echo "📋 Step 3: Check entity extraction logs..."
sudo journalctl -u vernal-agents --since "30 minutes ago" | grep -E "Entity extraction|📝 Text|No entities found|Sample text" | tail -20
echo ""

# Check research endpoint response
echo "📋 Step 4: Test research endpoint directly..."
echo "Calling /campaigns/$CAMPAIGN_ID/research..."
curl -s "http://127.0.0.1:8000/campaigns/$CAMPAIGN_ID/research" | jq -r '.topics[] | "\(.label) (score: \(.score))"' | head -10
echo ""

# Check if topics are phrases or single words
echo "📋 Step 5: Analyze topic format..."
TOPICS=$(curl -s "http://127.0.0.1:8000/campaigns/$CAMPAIGN_ID/research" | jq -r '.topics[].label' | head -5)
PHRASE_COUNT=0
WORD_COUNT=0
for topic in $TOPICS; do
    WORD_COUNT_IN_TOPIC=$(echo "$topic" | wc -w)
    if [ "$WORD_COUNT_IN_TOPIC" -gt 1 ]; then
        PHRASE_COUNT=$((PHRASE_COUNT + 1))
        echo "✅ Phrase: $topic ($WORD_COUNT_IN_TOPIC words)"
    else
        WORD_COUNT=$((WORD_COUNT + 1))
        echo "❌ Single word: $topic"
    fi
done
echo "Summary: $PHRASE_COUNT phrases, $WORD_COUNT single words"
echo ""

# Check entities
echo "📋 Step 6: Check entity counts..."
ENTITIES=$(curl -s "http://127.0.0.1:8000/campaigns/$CAMPAIGN_ID/research" | jq '.entities')
echo "Persons: $(echo "$ENTITIES" | jq '.persons | length')"
echo "Organizations: $(echo "$ENTITIES" | jq '.organizations | length')"
echo "Locations: $(echo "$ENTITIES" | jq '.locations | length')"
echo "Dates: $(echo "$ENTITIES" | jq '.dates | length')"
echo ""

echo "✅ Diagnostic complete!"
echo ""
echo "If topics are single words, check:"
echo "  1. OPENAI_API_KEY is set in .env"
echo "  2. Backend logs show 'LLM extracted' or 'LLM failed'"
echo "  3. Backend was restarted after code changes"
echo ""
echo "If entities are zero, check:"
echo "  1. Backend logs show 'Entity extraction' messages"
echo "  2. Texts are being processed (check 'Sample text' logs)"
echo "  3. NLTK data is downloaded"

