# 🚀 Quick Deploy - Code Changes Only

**Type:** SHORT DEPLOY (code-only, no new dependencies)

**What changed:**
- Enhanced logging for keyword tracking
- Truncation guards for large text
- Storage monitoring
- Database schema fix script (needs to run separately)

**No new dependencies** - just code changes.

---

## Deployment Steps

### Step 1: Fix Database Schema (CRITICAL - DO THIS FIRST)

```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
./scripts/fix_database_schema.sh
```

This fixes both `raw_html` and `extracted_text` to MEDIUMTEXT (16MB limit).

### Step 2: Pull Latest Code

```bash
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
```

### Step 3: Restart Service

```bash
sudo systemctl restart vernal-agents
sleep 3
sudo systemctl status vernal-agents --no-pager | head -5
```

### Step 4: Verify Service is Running

```bash
curl -s http://127.0.0.1:8000/health | jq .
```

Expected: `{"status": "ok", ...}`

---

## One-Liner (All Steps)

```bash
cd /home/ubuntu/vernal-agents-post-v0 && \
git pull origin main && \
./scripts/fix_database_schema.sh && \
sudo systemctl restart vernal-agents && \
sleep 3 && \
curl -s http://127.0.0.1:8000/health | jq .
```

---

## After Deployment - Test

1. **Rebuild a campaign** (click "Build Campaign Base")
2. **Monitor logs** for keyword tracking:
   ```bash
   sudo journalctl -u vernal-agents -f | grep -E 'CRITICAL.*Keywords|keywords received|keywords being used|Scraped.*DB ID'
   ```
3. **Check database** for data:
   ```bash
   bash scripts/check_scraping_now.sh YOUR_CAMPAIGN_ID
   ```

---

## What You Should See

- ✅ No more `Data too long` errors
- ✅ `🔍 CRITICAL: Keywords received from frontend: [...]`
- ✅ `✅ Scraped <url> (DB ID: X): Y chars`
- ✅ Campaign status becomes `READY_TO_ACTIVATE` if data exists
- ✅ Storage stats: `Storage: X total chars, Y avg, Z max`

---

**Note:** This is a quick deploy because no dependencies changed. Just pull code and restart.

