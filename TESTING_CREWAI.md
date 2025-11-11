# Testing CrewAI vs Manual Content Generation

## Quick Start

### Option 1: Python Script (Recommended)
```bash
cd backend-repo
python3 test_crewai_vs_manual.py
```

### Option 2: Bash Script
```bash
cd backend-repo
./test_crewai_vs_manual.sh
```

### Option 3: Manual curl Commands

#### Test Manual Orchestration (Existing)
```bash
curl -X POST https://themachine.vernalcontentum.com/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is transforming technology...",
    "platform": "linkedin",
    "week": 1
  }'
```

#### Test CrewAI Orchestration (New)
```bash
curl -X POST https://themachine.vernalcontentum.com/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "crewai_content_generation",
    "input_data": {
      "text": "Artificial intelligence is transforming technology...",
      "platform": "linkedin",
      "week": 1,
      "use_qc": true
    }
  }'
```

#### List Available Tools
```bash
curl https://themachine.vernalcontentum.com/mcp/tools
```

## What to Compare

### Manual Orchestration
- **How it works**: Calls tools sequentially, manually passing data between steps
- **Flow**: Research → QC → Writing (manual data passing)
- **Pros**: Faster, simpler, more predictable
- **Cons**: No agent collaboration, manual error handling

### CrewAI Orchestration
- **How it works**: CrewAI automatically orchestrates agents with context awareness
- **Flow**: Research Agent → Writing Agent → QC Agent (automatic handoffs)
- **Pros**: Agent collaboration, context awareness, better error recovery
- **Cons**: Slightly slower, more complex, higher cost

## Expected Differences

1. **Context Awareness**: CrewAI agents see previous agent outputs automatically
2. **Error Recovery**: CrewAI can retry or delegate tasks
3. **Agent Memory**: CrewAI agents remember previous interactions
4. **Collaboration**: Agents can query each other for clarification

## Troubleshooting

### CrewAI tool not found?
- Check if tool is registered: `curl https://themachine.vernalcontentum.com/mcp/tools`
- Look for `crewai_content_generation` in the list
- Check backend logs for import errors

### Import errors?
- Ensure CrewAI is installed: `pip install crewai>=0.28.0`
- Check backend logs: `sudo journalctl -u vernal-agents -f`

### Timeout errors?
- CrewAI may take longer (up to 5 minutes)
- Increase timeout in your client
- Check backend logs for progress

## Local Testing

For local testing, change the BASE_URL:
```python
BASE_URL = "http://127.0.0.1:8000"
```

Or in bash:
```bash
BASE_URL=http://127.0.0.1:8000 ./test_crewai_vs_manual.sh
```

