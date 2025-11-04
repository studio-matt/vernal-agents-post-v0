# Scraping Failure Diagnostic & Fix Plan

## Problem Summary
- Campaigns build, show "READY_TO_ACTIVATE" briefly, then revert to "INCOMPLETE"
- No scraped data appears in database
- Frontend shows empty data tab

## Root Cause Analysis

### Suspect #1: Scraping Never Runs (Most Likely)
**Symptoms:**
- Backend logs show `❌ CRITICAL: Scraping returned 0 results`
- No valid rows in `campaign_raw_data` table
- Only error rows exist (`error:no_results`, `error:scrape_failed`)

**Possible Causes:**
1. Playwright not installed/available
2. DuckDuckGo search failing (`ddgs` package issue)
3. Keywords empty or invalid
4. Network/firewall blocking scraping

### Suspect #2: Scraping Runs But Fails Silently
**Symptoms:**
- Scraping attempts logged but all return errors
- Error rows exist but no valid data
- Backend logs show `❌ CRITICAL: All X scraping attempts failed!`

**Possible Causes:**
1. All URLs return errors (timeouts, 404s, etc.)
2. Playwright browser crashes
3. Content extraction fails

### Suspect #3: Database Commit Issue
**Symptoms:**
- Scraping succeeds but rows not persisted
- Logs show "✅ Stored scraped data" but DB query returns 0 rows

**Possible Causes:**
1. Transaction rollback
2. Wrong `campaign_id` used
3. Database connection issues

## Immediate Diagnostic Steps

### Step 1: Check Database for Campaign Data
```sql
-- Replace CAMPAIGN_ID with actual campaign ID
SELECT 
    campaign_id,
    source_url,
    CASE 
        WHEN source_url LIKE 'error:%' THEN 'ERROR'
        WHEN source_url LIKE 'placeholder:%' THEN 'PLACEHOLDER'
        ELSE 'VALID'
    END as row_type,
    LENGTH(extracted_text) as text_length,
    fetched_at
FROM campaign_raw_data
WHERE campaign_id = 'CAMPAIGN_ID'
ORDER BY fetched_at DESC;
```

**Expected:**
- If 0 rows: Scraping never ran
- If only ERROR rows: Scraping failed
- If VALID rows with text_length > 10: Data exists, status issue is elsewhere

### Step 2: Check Backend Logs for Campaign
```bash
# Replace CAMPAIGN_ID and TASK_ID with actual values
sudo journalctl -u vernal-agents --since "30 minutes ago" | \
  grep -E "CAMPAIGN_ID|TASK_ID" -A 5 -B 5
```

**Look for:**
- `🚀 Starting web scraping for campaign`
- `✅ Web scraping completed: X pages scraped`
- `📊 Summary: X successful, Y errors`
- `❌ CRITICAL: Scraping returned 0 results`
- `📊 Data validation: X valid rows, Y with text, Z error rows`

### Step 3: Test Playwright and DuckDuckGo Availability
```bash
# On backend server
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

# Test Playwright
python -m playwright --version
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print('✅ Playwright works'); p.stop()"

# Test DuckDuckGo
python -c "from duckduckgo_search import DDGS; ddgs = DDGS(); results = list(ddgs.text('test', max_results=1)); print(f'✅ DuckDuckGo works: {len(results)} results')"
```

### Step 4: Manual Scraping Test
```python
# On backend server, in venv
python3 -c "
from web_scraping import scrape_campaign_data
results = scrape_campaign_data(
    keywords=['test'],
    urls=[],
    query='test query',
    max_pages=3
)
print(f'Scraped {len(results)} results')
for i, r in enumerate(results[:3]):
    print(f'  [{i+1}] {r.get(\"url\", \"unknown\")}: {len(r.get(\"text\", \"\"))} chars, error={r.get(\"error\")}')
"
```

## Fix Strategy

### Fix 1: Add Pre-Commit Status Lock (Prevent False READY)
**Problem:** Status might be set to READY before validation completes

**Solution:** Add status lock during scraping/finalization
```python
# In main.py, before setting status
camp.status = "PROCESSING"  # Lock status during validation
session.commit()

# ... validation logic ...

if valid_data_count > 0:
    camp.status = "READY_TO_ACTIVATE"
else:
    camp.status = "INCOMPLETE"
session.commit()
```

### Fix 2: Add Error State to Campaign
**Problem:** No way to distinguish "not started" from "failed"

**Solution:** Add `FAILED` status with error message
```python
# Add to Campaign model
status: Optional[str] = "INCOMPLETE"  # INCOMPLETE, PROCESSING, READY_TO_ACTIVATE, FAILED

# In finalization
if valid_data_count == 0 and error_count > 0:
    camp.status = "FAILED"
    camp.error_message = f"Scraping failed: {error_count} error(s). Check logs for details."
```

### Fix 3: Improve Error Logging
**Problem:** Errors not visible in logs

**Solution:** Add structured error logging
```python
# Log scraping errors with full context
if len(scraped_results) == 0:
    logger.error(f"❌ SCRAPING FAILED FOR CAMPAIGN {cid}")
    logger.error(f"   Keywords: {keywords}")
    logger.error(f"   URLs: {urls}")
    logger.error(f"   Query: {data.query or '(empty)'}")
    logger.error(f"   Check: Playwright installed? DuckDuckGo available? Network OK?")
    
    # Store error in campaign for UI display
    camp.error_message = f"Scraping returned 0 results. Check Playwright/DuckDuckGo availability."
```

### Fix 4: Add Health Check Endpoint
**Problem:** Can't verify scraping infrastructure without running full campaign

**Solution:** Add `/health/scraping` endpoint
```python
@app.get("/health/scraping")
def health_scraping():
    """Check if scraping infrastructure is available"""
    checks = {
        "playwright": False,
        "duckduckgo": False,
        "browsers_installed": False
    }
    
    try:
        from playwright.sync_api import sync_playwright
        checks["playwright"] = True
        p = sync_playwright().start()
        checks["browsers_installed"] = len(p.chromium.executable_path) > 0
        p.stop()
    except Exception as e:
        checks["playwright_error"] = str(e)
    
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        results = list(ddgs.text("test", max_results=1))
        checks["duckduckgo"] = len(results) > 0
    except Exception as e:
        checks["duckduckgo_error"] = str(e)
    
    all_ok = checks["playwright"] and checks["duckduckgo"] and checks["browsers_installed"]
    
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks
    }
```

## Implementation Priority

1. **HIGH:** Run diagnostics (Steps 1-4 above) to identify root cause
2. **HIGH:** Fix 3 - Improve error logging (helps diagnose future issues)
3. **MEDIUM:** Fix 2 - Add FAILED status (better UX)
4. **MEDIUM:** Fix 4 - Add health check endpoint (prevent issues)
5. **LOW:** Fix 1 - Status lock (defensive, but validation should prevent this)

## Next Steps

1. Run diagnostic queries on database
2. Check backend logs for campaign ID
3. Test Playwright/DuckDuckGo manually
4. Share results to pinpoint exact failure point
5. Apply targeted fix based on root cause

