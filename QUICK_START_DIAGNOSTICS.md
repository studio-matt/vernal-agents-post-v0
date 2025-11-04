# Quick Start: Diagnose Scraping Failure

## Get Your Campaign ID

**Option 1: From Frontend**
- Go to campaign listing page
- Right-click on the failed campaign → Inspect
- Look for `campaign_id` in the HTML/data attributes

**Option 2: From Database**
```bash
# SSH to backend server
ssh ubuntu@18.235.104.132

# Get most recent campaign ID
mysql -h 50.6.198.220 -u [DB_USER] -p[DB_PASSWORD] [DB_NAME] -e "
  SELECT campaign_id, campaign_name, status, created_at 
  FROM campaign 
  ORDER BY created_at DESC 
  LIMIT 5;
"
```

**Option 3: From Backend Logs**
```bash
# SSH to backend server
sudo journalctl -u vernal-agents --since "1 hour ago" | \
  grep -E "campaign.*marked|Campaign.*created" | \
  tail -10
```

## Run Diagnostic Script

```bash
# SSH to backend server
ssh ubuntu@18.235.104.132

# Navigate to repo
cd /home/ubuntu/vernal-agents-post-v0

# Pull latest (to get diagnostic script)
git pull origin main

# Run diagnostic (replace CAMPAIGN_ID with your actual ID)
./scripts/diagnose_scraping_failure.sh CAMPAIGN_ID
```

**Example:**
```bash
./scripts/diagnose_scraping_failure.sh 31dfec2f-cce2-442a-b773-bf690074e2b0
```

## What to Look For

### ✅ Good Signs (Scraping Working)
- `valid_text_rows > 0` in database summary
- `✅ Web scraping completed: X pages scraped` in logs
- `📊 Summary: X successful, Y errors` with X > 0

### ❌ Bad Signs (Scraping Failing)
- `valid_text_rows = 0` in database summary
- `❌ CRITICAL: Scraping returned 0 results` in logs
- `❌ Playwright error` or `❌ DuckDuckGo error` in tests
- Only `ERROR` rows in database

## Quick Fixes Based on Results

### If Playwright Test Fails:
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
python -m playwright install chromium
```

### If DuckDuckGo Test Fails:
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
pip install --upgrade duckduckgo-search
```

### If Database Shows 0 Rows:
- Scraping never ran → Check logs for exceptions
- Look for "Web scraping failed" or "scrape_campaign_data" errors

### If Database Shows Only Error Rows:
- Scraping ran but all attempts failed
- Check logs for specific URL errors
- Might be network/firewall blocking

## Next Steps After Diagnosis

1. **Share the diagnostic output** - I can help interpret results
2. **Apply fixes** based on what failed (Playwright/DuckDuckGo/network)
3. **Re-run campaign** and check logs again

