#!/bin/bash
# Test script to compare CrewAI vs Manual content generation

BASE_URL="${BASE_URL:-https://themachine.vernalcontentum.com}"
TEST_TEXT="Artificial intelligence is transforming the way we work and think about technology. Machine learning algorithms are becoming more sophisticated, enabling computers to process information in ways that were previously impossible. This revolution is affecting industries from healthcare to finance, creating new opportunities and challenges."

echo "🧪 Testing Content Generation: CrewAI vs Manual"
echo "=============================================="
echo ""

# Test 1: Manual Orchestration (existing)
echo "📋 Test 1: Manual Orchestration"
echo "Endpoint: POST /mcp/generate-content"
echo ""

MANUAL_RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/generate-content" \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"${TEST_TEXT}\",
    \"platform\": \"linkedin\",
    \"week\": 1
  }")

echo "Response:"
echo "$MANUAL_RESPONSE" | jq '.' 2>/dev/null || echo "$MANUAL_RESPONSE"
echo ""
echo "---"
echo ""

# Test 2: CrewAI Orchestration (new)
echo "📋 Test 2: CrewAI Orchestration"
echo "Endpoint: POST /mcp/tools/execute"
echo "Tool: crewai_content_generation"
echo ""

CREWAI_RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/tools/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"tool_name\": \"crewai_content_generation\",
    \"input_data\": {
      \"text\": \"${TEST_TEXT}\",
      \"platform\": \"linkedin\",
      \"week\": 1,
      \"use_qc\": true
    }
  }")

echo "Response:"
echo "$CREWAI_RESPONSE" | jq '.' 2>/dev/null || echo "$CREWAI_RESPONSE"
echo ""
echo "---"
echo ""

# Test 3: List available tools
echo "📋 Test 3: List Available Tools"
echo "Endpoint: GET /mcp/tools"
echo ""

TOOLS_RESPONSE=$(curl -s -X GET "${BASE_URL}/mcp/tools")
echo "Available tools:"
echo "$TOOLS_RESPONSE" | jq '.' 2>/dev/null || echo "$TOOLS_RESPONSE"
echo ""

# Summary
echo "✅ Testing Complete!"
echo ""
echo "Compare the outputs above to see differences between:"
echo "  - Manual: Step-by-step tool execution"
echo "  - CrewAI: Agent-to-agent orchestration with context"

