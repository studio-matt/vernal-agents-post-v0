# Debugging Research Agent Prompt Mismatch

## Problem
Research agent outputs don't match the prompts configured in the Admin Panel. For example, keyword agent should output "one word/phrase per line, then recommendations" but shows formatted paragraphs instead.

## Complete Flow Trace

### Step 1: Check What Prompt is Stored in Database

```bash
# SSH to backend server
ssh ubuntu@18.235.104.132

# Connect to database
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT 
    setting_key,
    LEFT(setting_value, 500) as prompt_preview,
    LENGTH(setting_value) as prompt_length,
    updated_at
  FROM system_settings
  WHERE setting_key LIKE 'research_agent_%_prompt'
  ORDER BY setting_key;
"
```

**What to check:**
- ✅ Prompt exists in database (`setting_key` matches `research_agent_{agent_type}_prompt`)
- ✅ Prompt contains `{context}` placeholder (required for formatting)
- ✅ Prompt matches what you see in Admin Panel
- ✅ Prompt was updated recently (check `updated_at`)

### Step 2: Watch Backend Logs in Real-Time

```bash
# Start watching logs (leave this running)
sudo journalctl -u vernal-agents -f | grep -E "research|agent|prompt|LLM|keyword|sentiment|topical|hashtag|knowledge"
```

**Then trigger the research agent from frontend:**
1. Go to campaign page
2. Click on a research agent tab (Keyword, Sentiment, etc.)
3. Watch the logs appear

### Step 3: Identify the Log Sequence

When you trigger a research agent, you should see this sequence in logs:

```
✅ Using prompt for {agent_type} agent (key: research_agent_{agent_type}_prompt)
📝 Prompt template (first 500 chars): {prompt_template_preview}
📝 Formatted prompt (first 500 chars): {formatted_prompt_preview}
✅ Successfully generated {agent_type} recommendations ({length} chars)
📝 LLM response (first 1000 chars): {llm_response_preview}
```

**What each log tells you:**

1. **"✅ Using prompt for..."** - Confirms prompt was loaded from database
2. **"📝 Prompt template..."** - Shows the raw prompt from database (before formatting)
3. **"📝 Formatted prompt..."** - Shows prompt after `{context}` is replaced with actual data
4. **"✅ Successfully generated..."** - Confirms LLM call succeeded
5. **"📝 LLM response..."** - Shows what the LLM actually returned

### Step 4: Check Frontend Console Logs

Open browser DevTools (F12) → Console tab, then trigger the research agent.

**Look for these logs:**
```
🔍 Fetching {agent_type} recommendations for campaign {campaign_id}
📊 {agent_type} recommendations response: {status, hasRecommendations}
📝 Raw {agent_type} response from backend (first 1000 chars): {raw_response}
📝 Cleaned {agent_type} response (first 1000 chars): {cleaned_response}
✅ {agent_type} recommendations loaded: {preview}
```

**What each log tells you:**

1. **"🔍 Fetching..."** - Frontend is calling the API
2. **"📊 ... response"** - Backend returned data
3. **"📝 Raw ... response"** - What backend sent (should match backend log "📝 LLM response")
4. **"📝 Cleaned ... response"** - After frontend cleaning (removes markdown, numbers, etc.)
5. **"✅ ... loaded"** - Final result displayed to user

### Step 5: Compare Each Stage

Create a comparison table:

| Stage | Expected | Actual | Issue? |
|-------|----------|--------|--------|
| **Database Prompt** | Contains format instructions | ? | Check Step 1 |
| **Formatted Prompt** | Includes context data | ? | Check Step 3 log #3 |
| **LLM Response** | Follows prompt format | ? | Check Step 3 log #5 |
| **Frontend Raw** | Matches LLM response | ? | Check Step 4 log #3 |
| **Frontend Cleaned** | Removes markdown/numbers | ? | Check Step 4 log #4 |
| **Displayed** | Shows cleaned version | ? | What user sees |

## Common Issues and Fixes

### Issue 1: Prompt Not in Database

**Symptoms:**
- Backend log: `❌ Prompt not configured for {agent_type} agent`
- Frontend shows: `ERROR: Prompt not configured...`

**Fix:**
```bash
# Initialize default prompts
curl -X POST https://themachine.vernalcontentum.com/admin/initialize-research-agent-prompts \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Issue 2: Prompt Template Missing `{context}` Placeholder

**Symptoms:**
- Backend log: `KeyError: 'context'` or `TypeError: format()`
- Frontend shows: `ERROR: LLM call failed`

**Fix:**
1. Go to Admin Panel → Research Agents
2. Edit the prompt
3. Ensure it contains `{context}` placeholder
4. Save and test again

### Issue 3: LLM Ignoring Format Instructions

**Symptoms:**
- Database prompt has format instructions
- Formatted prompt includes instructions
- LLM response doesn't follow format

**Possible Causes:**
- Prompt instructions are too weak
- Context data is too long (dilutes instructions)
- LLM model (`gpt-4o-mini`) is not following instructions

**Fix:**
1. Make format instructions more explicit in prompt
2. Put format instructions at the END of prompt (after context)
3. Use stronger language: "CRITICAL:", "MANDATORY:", "YOU MUST:"
4. Add examples of correct format in prompt

### Issue 4: Frontend Cleaning Too Aggressive

**Symptoms:**
- LLM response is correct (check backend log)
- Frontend raw response is correct (check console)
- Frontend cleaned response is wrong (check console)
- Displayed result is wrong

**Fix:**
Check `components/ResearchAssistant.tsx` cleaning logic:
```typescript
// Lines 362-383 in ResearchAssistant.tsx
// The cleaning removes:
// - Markdown headers (###, ##, #)
// - Title lines
// - Numbering (1., 2., 3.)
// - List markers (-, *, +)
```

**If cleaning is too aggressive:**
- Comment out specific cleaning rules
- Test to see which rule breaks the format
- Adjust cleaning logic to preserve required format

### Issue 5: Context Data Format Mismatch

**Symptoms:**
- Prompt expects specific context format
- Context data doesn't match expected format
- LLM gets confused

**Check context format:**
```bash
# Check what context is being sent
sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -A 20 "Formatted prompt"
```

**Fix:**
- Check `main.py` lines 4916-4941 (context generation)
- Ensure context matches what prompt expects
- Adjust context format if needed

## Quick Diagnostic Script

```bash
#!/bin/bash
# diagnose_research_agent.sh {campaign_id} {agent_type}

CAMPAIGN_ID=$1
AGENT_TYPE=$2

echo "=== DATABASE PROMPT ==="
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT setting_value
  FROM system_settings
  WHERE setting_key = 'research_agent_${AGENT_TYPE}_prompt';
" | tail -n +2

echo ""
echo "=== BACKEND LOGS (last 5 minutes) ==="
sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -E "research.*${AGENT_TYPE}|${AGENT_TYPE}.*agent|prompt.*${AGENT_TYPE}|LLM.*${AGENT_TYPE}" | tail -20

echo ""
echo "=== CACHED INSIGHTS ==="
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "
  SELECT 
    LEFT(insights_text, 1000) as insights_preview,
    LENGTH(insights_text) as length,
    updated_at
  FROM campaign_research_insights
  WHERE campaign_id = '${CAMPAIGN_ID}' AND agent_type = '${AGENT_TYPE}';
"
```

**Usage:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true
chmod +x scripts/diagnose_research_agent.sh
./scripts/diagnose_research_agent.sh fad936de-8696-47c6-94ca-cf54da1813c2 keyword
```

## Example: Keyword Agent Debugging

**Expected Format (from prompt):**
```
iphone, features, camera, review, colors, performance, battery, specs, upgrade

Create an article that details the new features...
Develop a comparison piece that evaluates...
```

**If you see formatted paragraphs instead:**

1. **Check database prompt:**
   ```bash
   mysql ... -e "SELECT setting_value FROM system_settings WHERE setting_key = 'research_agent_keyword_prompt';"
   ```
   - Does it say "one word/phrase per line, then recommendations"?
   - Does it have examples?

2. **Check backend logs:**
   ```bash
   sudo journalctl -u vernal-agents -f | grep keyword
   ```
   - Does "📝 LLM response" show the correct format?
   - Or does it show paragraphs?

3. **Check frontend console:**
   - Does "📝 Raw ... response" match backend "📝 LLM response"?
   - Does "📝 Cleaned ... response" preserve the format?

4. **Fix based on where it breaks:**
   - **If LLM ignores format:** Strengthen prompt instructions
   - **If frontend breaks format:** Adjust cleaning logic
   - **If context is wrong:** Fix context generation

## Next Steps

1. Run the diagnostic script for the failing agent
2. Compare database prompt vs. LLM response
3. Check if issue is in prompt, LLM, or frontend cleaning
4. Fix the specific stage where format breaks
5. Test and verify end-to-end

