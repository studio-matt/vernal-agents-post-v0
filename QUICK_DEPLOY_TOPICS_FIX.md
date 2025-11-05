# 🚀 Quick Deploy - Topics & Entities Fix

**Type:** SHORT DEPLOY (code-only, no new dependencies)

**What changed:**
- Research endpoint now uses `extract_topics` for phrase-based topics
- Added detailed logging for topic extraction debugging
- Added detailed logging for entity extraction debugging
- Improved campaign refresh after completion

**No new dependencies** - just code changes.

---

## EMERGENCY_NET.md Compliant Deployment Steps

### Step 1: Pre-Deployment Validation (MANDATORY)

```bash
cd /home/ubuntu/vernal-agents-post-v0

# 1. Verify .env file exists and has real credentials
ls -la .env
grep -E "DB_HOST|DB_USER|DB_PASSWORD|DB_NAME" .env
# Must show: DB_HOST=50.6.198.220 (NOT localhost), DB_USER=vernalcontentum_vernaluse (NOT myuser)

# 2. MANDATORY: Validate dependencies (PREVENTS DEPENDENCY HELL)
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}
```

### Step 2: Pull Latest Code

```bash
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
```

### Step 3: Verify Code Changes

```bash
# Check that extract_topics is imported
grep -n "from text_processing import.*extract_topics" main.py

# Check that research endpoint uses extract_topics
grep -n "extract_topics" main.py | head -5
```

### Step 4: Restart Service

```bash
sudo systemctl restart vernal-agents
sleep 5
sudo systemctl status vernal-agents --no-pager | head -10
```

### Step 5: Verification (MANDATORY)

```bash
# Health check
curl -s http://127.0.0.1:8000/health | jq .

# Database health
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .

# External health
curl -I https://themachine.vernalcontentum.com/health
```

---

## One-Liner (All Steps - EMERGENCY_NET Compliant)

```bash
cd /home/ubuntu/vernal-agents-post-v0 && \
python3 validate_dependencies.py && \
git fetch origin && git switch main && git pull --ff-only origin main && \
sudo systemctl restart vernal-agents && \
sleep 5 && \
curl -s http://127.0.0.1:8000/health | jq . && \
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .
```

---

## After Deployment - Test & Debug

### Test Topic Phrases

1. **Rebuild a campaign** (or use existing campaign)
2. **Check backend logs** for topic extraction:
   ```bash
   sudo journalctl -u vernal-agents -f | grep -E "extract_topics|topic phrases|Generated.*topics|Error extracting topics"
   ```
3. **Check research endpoint** returns phrases:
   ```bash
   curl -s "https://themachine.vernalcontentum.com/campaigns/YOUR_CAMPAIGN_ID/research" \
     -H "Authorization: Bearer YOUR_TOKEN" | jq '.topics'
   ```

### Debug Entity Extraction

```bash
sudo journalctl -u vernal-agents -f | grep -E "Entity extraction|📝 Text|No entities found|Error extracting entities|Sample text"
```

---

## What You Should See

### In Logs:
- ✅ `🔍 Calling extract_topics with X texts, tool=llm, num_topics=10`
- ✅ `✅ Generated X topic phrases: ['phrase one', 'phrase two', ...]`
- ✅ `📄 Sample text (first 200 chars): ...`
- ✅ `📝 Text 1: Found {'persons': 2, 'locations': 3, ...}`

### In Frontend:
- ✅ Topics show as 2-3 word phrases (e.g., "vietnam war", "american military")
- ✅ Entities show counts > 0 (persons, organizations, locations, dates)
- ✅ Campaign automatically refreshes when complete (no manual refresh needed)

---

## Troubleshooting

### If topics are still single words:
```bash
# Check if extract_topics is being called
sudo journalctl -u vernal-agents -f | grep "extract_topics"

# Check for errors
sudo journalctl -u vernal-agents -f | grep "Error extracting topics"

# Check if LLM is available
grep OPENAI_API_KEY /home/ubuntu/vernal-agents-post-v0/.env
```

### If entities are still zero:
```bash
# Check entity extraction logs
sudo journalctl -u vernal-agents -f | grep -E "Entity extraction|📝 Text|No entities found"

# Check if texts are being processed
sudo journalctl -u vernal-agents -f | grep "Sample text"
```

---

**Note:** This is a quick deploy because no dependencies changed. Just pull code and restart.

