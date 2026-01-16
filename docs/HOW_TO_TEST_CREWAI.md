# How to Test CrewAI Feature

## Quick Test (Copy & Paste)

### Step 1: Verify Tool is Available
```bash
curl -s https://themachine.vernalcontentum.com/mcp/tools | jq '.[] | select(.name == "crewai_content_generation")'
```

If you see output, the tool is registered ✅

### Step 2: Test CrewAI Workflow
```bash
curl -X POST https://themachine.vernalcontentum.com/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "crewai_content_generation",
    "input_data": {
      "text": "Artificial intelligence is transforming how businesses operate. Machine learning algorithms can now process vast amounts of data to identify patterns and make predictions. This technology is being used across industries from healthcare to finance.",
      "platform": "linkedin",
      "week": 1,
      "use_qc": true
    }
  }'
```

**Expected:** JSON response with `success: true` and data containing research, writing, and QC outputs.

### Step 3: Compare with Manual (Optional)
```bash
curl -X POST https://themachine.vernalcontentum.com/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is transforming how businesses operate. Machine learning algorithms can now process vast amounts of data to identify patterns and make predictions.",
    "platform": "linkedin",
    "week": 1
  }'
```

## What You Should See

**CrewAI Response:**
```json
{
  "success": true,
  "data": {
    "research": "...",
    "writing": "...",
    "quality_control": "...",
    "final_content": "...",
    "platform": "linkedin",
    "week": 1
  },
  "metadata": {
    "workflow": "crewai_content_generation",
    "agents_used": ["script_research_agent", "linkedin_agent", "qc_agent"]
  }
}
```

## Troubleshooting

**If tool not found:**
```bash
# Check all available tools
curl -s https://themachine.vernalcontentum.com/mcp/tools | jq '.[].name'
```

**If request fails:**
```bash
# Check backend logs
sudo journalctl -u vernal-agents -f
```

**If timeout:**
- CrewAI can take 2-5 minutes
- This is normal - agents are collaborating

## Testing from Frontend

Currently, CrewAI is only available via API. To test from the UI, you would need to:
1. Go to a campaign with scraped data
2. Use the content generation features
3. The backend will use CrewAI if configured

**Note:** The current UI uses manual orchestration. CrewAI is available as an alternative API endpoint.

