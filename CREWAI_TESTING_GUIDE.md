# CrewAI Testing Guide - Step by Step

## Prerequisites
- Backend deployed with latest code
- Frontend deployed with latest code
- You have a campaign with scraped data (or can create one)

---

## Step 1: Verify Backend Deployment

### Action:
```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
sudo systemctl restart vernal-agents
```

### Expected Outcome:
- ✅ Git pull succeeds (no conflicts)
- ✅ Service restarts without errors
- ✅ Service shows `active (running)` status

### Verification:
```bash
sudo systemctl status vernal-agents | grep "active (running)"
curl -s http://127.0.0.1:8000/health | jq .
```

**Expected:** Service is active, health endpoint returns `{"status": "ok"}`

---

## Step 2: Verify CrewAI Tool is Available

### Action:
```bash
curl -s http://127.0.0.1:8000/mcp/tools | jq '.[] | select(.name == "crewai_content_generation")'
```

### Expected Outcome:
- ✅ Returns JSON object with `name: "crewai_content_generation"`
- ✅ Shows tool description and input schema

### If Missing:
- Check logs: `sudo journalctl -u vernal-agents -f | grep -i crewai`
- Verify CrewAI is installed: `python3 -c "import crewai; print(crewai.__version__)"`

---

## Step 3: Test Backend Endpoint Directly (Manual Mode)

### Action:
```bash
curl -X POST http://127.0.0.1:8000/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is transforming business operations",
    "platform": "linkedin",
    "week": 1,
    "use_crewai": false
  }'
```

### Expected Outcome:
- ✅ Returns JSON with `success: true`
- ✅ Contains `data` object with:
  - `research`: Research analysis
  - `quality_control`: QC results
  - `platform_content`: Generated content
- ✅ `metadata.workflow` = `"content_generation"`
- ✅ `metadata.use_crewai` = `false`

### Response Time:
- Should complete in 30-60 seconds

---

## Step 4: Test Backend Endpoint with CrewAI

### Action:
```bash
curl -X POST http://127.0.0.1:8000/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is transforming business operations",
    "platform": "linkedin",
    "week": 1,
    "use_crewai": true
  }'
```

### Expected Outcome:
- ✅ Returns JSON with `success: true`
- ✅ Contains `data` object with:
  - `research`: Research analysis (from CrewAI agent)
  - `quality_control`: QC results (from CrewAI agent)
  - `platform_content`: Generated content (from CrewAI agent)
  - `crewai_metadata`: Additional CrewAI metadata
- ✅ `metadata.workflow` = `"crewai_content_generation"`
- ✅ Response may include agent collaboration details

### Response Time:
- May take 2-5 minutes (CrewAI is slower due to agent orchestration)

### Differences from Manual:
- More detailed agent interactions
- Better context awareness between steps
- May show agent-to-agent communication in logs

---

## Step 5: Verify Frontend Deployment

### Action:
1. Open your frontend application
2. Navigate to a campaign
3. Go to content creation flow

### Expected Outcome:
- ✅ Page loads without errors
- ✅ Content creation flow is accessible
- ✅ No console errors in browser dev tools

### Verification:
- Open browser dev tools (F12)
- Check Console tab for errors
- Should see no red errors related to CrewAI or content generation

---

## Step 6: Test UI Toggle (Step 2 of Content Creation)

### Action:
1. Start content creation flow
2. Complete Step 1 (generate ideas)
3. On Step 2, look for checkbox before "Next" button

### Expected Outcome:
- ✅ Checkbox appears: "☑️ Use CrewAI (Agent Collaboration)"
- ✅ Info icon (ℹ️) next to checkbox
- ✅ Tooltip appears on hover explaining CrewAI

### Verification:
- Hover over ℹ️ icon
- Should see tooltip: "CrewAI enables agent-to-agent collaboration..."

---

## Step 7: Test Manual Generation (Toggle OFF)

### Action:
1. Ensure CrewAI checkbox is **unchecked**
2. Click "Next" button
3. Wait for generation to complete

### Expected Outcome:
- ✅ Button shows "Generating..." (not "Generating with CrewAI...")
- ✅ Content generates in 30-60 seconds
- ✅ Results appear in Step 3
- ✅ Content is formatted correctly

### Verification:
- Check browser Network tab
- Request to `/mcp/generate-content` should have `use_crewai: false` (or missing)
- Response should match Step 3 format

---

## Step 8: Test CrewAI Generation (Toggle ON)

### Action:
1. Go back to Step 2
2. **Check** the CrewAI checkbox
3. Click "Next" button
4. Wait for generation to complete

### Expected Outcome:
- ✅ Button shows "Generating with CrewAI..." while loading
- ✅ Button is disabled during generation
- ✅ Content generates in 2-5 minutes (longer than manual)
- ✅ Results appear in Step 3
- ✅ Content may be more refined due to agent collaboration

### Verification:
- Check browser Network tab
- Request to `/mcp/generate-content` should have `use_crewai: true`
- Response should have `metadata.workflow = "crewai_content_generation"`

### Differences to Look For:
- **Quality**: CrewAI may produce more contextually aware content
- **Structure**: May show better flow between research → writing → QC
- **Metadata**: Response includes `crewai_metadata` with agent details

---

## Step 9: Compare Results

### Action:
Compare the content generated in Step 7 vs Step 8

### Expected Differences:

**Manual Mode:**
- Faster generation (30-60 seconds)
- Direct tool execution
- Simpler output structure

**CrewAI Mode:**
- Slower generation (2-5 minutes)
- Agent collaboration visible in logs
- More sophisticated output
- Better context awareness
- May show agent handoffs in metadata

### What Success Looks Like:
- ✅ Both modes generate valid content
- ✅ CrewAI content shows improved quality/context
- ✅ No errors in either mode
- ✅ UI correctly reflects which mode was used

---

## Troubleshooting

### Issue: CrewAI checkbox doesn't appear
**Check:**
- Frontend code is deployed
- Browser cache cleared (Ctrl+Shift+R)
- You're on Step 2 of content creation

### Issue: CrewAI request fails
**Check:**
- Backend logs: `sudo journalctl -u vernal-agents -f`
- Look for CrewAI import errors
- Verify CrewAI is installed: `pip list | grep crewai`

### Issue: Both modes produce same results
**This is OK** - CrewAI may not always produce dramatically different content, but:
- Check metadata to confirm which workflow was used
- CrewAI benefits are more visible in complex scenarios
- Agent collaboration is more apparent in logs

### Issue: CrewAI takes too long
**Expected behavior:**
- CrewAI is slower (2-5 minutes is normal)
- This is due to agent orchestration overhead
- Consider this a trade-off for better quality

---

## Success Criteria Summary

✅ **Backend:**
- Service running
- CrewAI tool registered
- Both endpoints work (manual and CrewAI)

✅ **Frontend:**
- Toggle appears on Step 2
- Both modes generate content
- UI correctly shows loading states

✅ **Results:**
- Manual mode: Fast, functional
- CrewAI mode: Slower, but with agent collaboration
- Both produce valid content

---

## Next Steps

Once testing passes:
1. Monitor production usage
2. Compare content quality between modes
3. Consider making CrewAI default for certain use cases
4. Collect user feedback on which mode they prefer

