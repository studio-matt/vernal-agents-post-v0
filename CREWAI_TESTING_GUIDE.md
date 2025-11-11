# CrewAI Testing - Simple Guide

## Option 1: Test in AWS Terminal

### Test 1: Check if CrewAI is installed
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
python3 -c "import crewai; print('CrewAI version:', crewai.__version__)"
```
**Expected:** Prints version number (e.g., `CrewAI version: 1.4.1`)

---

### Test 2: Test Manual Mode (Fast)
```bash
curl -X POST http://127.0.0.1:8000/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{"text": "AI is changing business", "platform": "linkedin", "week": 1, "use_crewai": false}' | jq .
```
**Expected:** 
- Returns JSON with `"success": true`
- Has `"platform_content"` field with generated text
- Takes 30-60 seconds

---

### Test 3: Test CrewAI Mode (Slower)
```bash
curl -X POST http://127.0.0.1:8000/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{"text": "AI is changing business", "platform": "linkedin", "week": 1, "use_crewai": true}' | jq .
```
**Expected:**
- Returns JSON with `"success": true`
- Has `"platform_content"` field with generated text
- Has `"metadata"` with `"workflow": "crewai_content_generation"`
- Takes 2-5 minutes (slower than manual)

---

## Option 2: Test in Frontend UI

### Step 1: Open Content Creation
1. Go to your campaign
2. Click "Generate Content" or similar button
3. Complete Step 1 (select ideas)

### Step 2: Find the Toggle
On Step 2, look for a checkbox that says:
- **"☑️ Use CrewAI (Agent Collaboration)"**
- It should be near the "Next" button
- There's an info icon (ℹ️) next to it

**Expected:** Checkbox is visible and clickable

---

### Step 3: Test Manual Mode (Toggle OFF)
1. Make sure checkbox is **unchecked**
2. Click "Next"
3. Wait for content to generate

**Expected:**
- Button shows "Generating..."
- Content appears in 30-60 seconds
- Content is displayed in Step 3

---

### Step 4: Test CrewAI Mode (Toggle ON)
1. Go back to Step 2
2. **Check** the CrewAI checkbox
3. Click "Next"
4. Wait for content to generate

**Expected:**
- Button shows "Generating with CrewAI..." or similar
- Content appears in 2-5 minutes (slower)
- Content is displayed in Step 3

---

## What Success Looks Like

✅ **Both modes work:**
- Manual: Fast (30-60 sec), generates content
- CrewAI: Slow (2-5 min), generates content

✅ **No errors:**
- Terminal: No error messages in curl response
- Frontend: No red errors in browser console (F12)

✅ **Different workflows:**
- Manual: `"workflow": "content_generation"` in response
- CrewAI: `"workflow": "crewai_content_generation"` in response

---

## If Something Fails

### CrewAI not installed:
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
pip install crewai>=0.28.0
sudo systemctl restart vernal-agents
```

### Check backend logs:
```bash
sudo journalctl -u vernal-agents -f
```
Look for errors mentioning "crewai" or "CrewAI"

### Check if endpoint exists:
```bash
curl -s http://127.0.0.1:8000/mcp/tools | jq '.[] | select(.name == "crewai_content_generation")'
```
**Expected:** Returns tool definition (not empty)

---

## Quick Summary

**Terminal Test:**
- Copy/paste the curl commands above
- Check for `"success": true` in response

**Frontend Test:**
- Find checkbox on Step 2
- Test with checkbox OFF (fast)
- Test with checkbox ON (slow)
- Both should generate content

That's it! 🎉
