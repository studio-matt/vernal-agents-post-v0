# Run Diagnostics for Campaign: 31dfec2f-cce2-442a-b773-bf690074e2b0

## Quick Command (Copy & Paste)

```bash
# Navigate to repo and pull latest
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main

# Make script executable (if needed)
chmod +x scripts/diagnose_scraping_failure.sh

# Run diagnostic with your campaign ID
./scripts/diagnose_scraping_failure.sh 31dfec2f-cce2-442a-b773-bf690074e2b0
```

## What You'll See

The script will output:
1. **Database rows** - Shows if any data was saved (valid vs error rows)
2. **Campaign status** - Current status in database
3. **Backend logs** - Recent log entries for this campaign
4. **Scraping errors** - Any critical errors from scraping
5. **Playwright test** - Verifies Playwright is working
6. **DuckDuckGo test** - Verifies DuckDuckGo search is working

## After Running

**Copy the entire output** and share it - I'll help interpret:
- What failed (Playwright, DuckDuckGo, network, etc.)
- Why it failed (specific error messages)
- How to fix it (exact commands)

## Alternative: Quick Database Check

If you can't run the full script right now, at least check the database:

```bash
# Load environment (if needed)
cd /home/ubuntu/vernal-agents-post-v0
source .env 2>/dev/null || true

# Quick database check
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN source_url LIKE 'error:%' THEN 1 ELSE 0 END) as error_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' THEN 1 ELSE 0 END) as valid_rows
FROM campaign_raw_data
WHERE campaign_id = '31dfec2f-cce2-442a-b773-bf690074e2b0';
EOF
```

This tells us immediately:
- If `total_rows = 0`: Scraping never ran
- If `error_rows > 0` and `valid_rows = 0`: Scraping failed
- If `valid_rows > 0`: Data exists, status issue is elsewhere

