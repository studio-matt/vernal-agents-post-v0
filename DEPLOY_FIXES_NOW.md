# 🚨 IMMEDIATE DEPLOYMENT CHECKLIST

## Current Issue
Campaigns complete progress (100%) but end up INCOMPLETE with 0 data rows because:
- `beautifulsoup4` (bs4) is missing → scraping fails silently
- `gensim` is missing → topic processing warnings

## Step 1: Pull Latest Code (with fixes)
```bash
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
```

## Step 2: Install Missing Dependencies (CRITICAL)
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
pip install beautifulsoup4>=4.12.3 gensim>=4.3.2
```

**OR use the fix script:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
./scripts/fix_missing_deps_now.sh
```

## Step 3: Verify Dependencies Installed
```bash
source venv/bin/activate
python -c "import bs4; import gensim; print(f'✅ bs4 {bs4.__version__}'); print(f'✅ gensim {gensim.__version__}')"
```

Expected output:
```
✅ bs4 4.12.3
✅ gensim 4.3.2
```

## Step 4: Restart Backend Service
```bash
sudo systemctl restart vernal-agents
sleep 3
sudo systemctl status vernal-agents --no-pager | head -5
```

## Step 5: Verify Service is Running
```bash
curl -s http://127.0.0.1:8000/health | jq .
```

Expected: `{"status": "ok", ...}`

## Step 6: Test Campaign Rebuild
1. Go to campaign edit page
2. Click "Build Campaign Base"
3. Monitor logs: `sudo journalctl -u vernal-agents -f | grep -E 'bs4|gensim|ImportError|CRITICAL|Scraped.*DB ID'`

**You should now see:**
- ✅ `✅ Scraped <url> (DB ID: X): Y chars, Z links, W images`
- ❌ NO MORE `No module named 'bs4'` errors
- ❌ NO MORE `No module named 'gensim'` warnings

## Step 7: Verify Data Was Saved
```bash
# Connect to database
mysql -h 50.6.198.220 -u [user] -p [database] -e "
  SELECT COUNT(*) AS cnt 
  FROM campaign_raw_data 
  WHERE campaign_id='31dfec2f-cce2-442a-b773-bf690074e2b0';
"
```

Expected: `cnt > 0` (should have valid rows)

## What Changed in This Deployment

### 1. Fail-Fast Dependency Checks (`web_scraping.py`)
- Checks for `beautifulsoup4` at module load
- Logs CRITICAL errors if missing
- Prevents silent failures

### 2. Enhanced Error Logging (`main.py`)
- Detects missing dependency errors
- Logs full tracebacks
- Stores error details in database

### 3. Post-Task Persistence Guard (`main.py`)
- Verifies data was actually saved before finalizing
- Counts valid vs error rows
- Logs DB row IDs for each URL

### 4. Improved Per-URL Logging (`main.py`)
- Logs each URL with DB row ID
- Shows text length, link count, image count
- Makes debugging much easier

## If Still Failing After Deployment

1. **Check backend logs for dependency errors:**
   ```bash
   sudo journalctl -u vernal-agents -f | grep -E 'bs4|gensim|ImportError|CRITICAL'
   ```

2. **Run dependency checker:**
   ```bash
   cd /home/ubuntu/vernal-agents-post-v0
   source venv/bin/activate
   python3 scripts/check_all_dependencies.py
   ```

3. **Check database for error rows:**
   ```bash
   mysql -h 50.6.198.220 -u [user] -p [database] -e "
     SELECT source_url, LEFT(extracted_text, 100) as error_msg
     FROM campaign_raw_data
     WHERE campaign_id='31dfec2f-cce2-442a-b773-bf690074e2b0'
     AND source_url LIKE 'error:%';
   "
   ```

## Expected Behavior After Fix

✅ Campaigns will show progress steps  
✅ Scraping will actually save data to database  
✅ Each URL will be logged with DB ID  
✅ Campaign will be marked READY_TO_ACTIVATE if valid data exists  
✅ Clear error messages if dependencies are missing  
✅ No more silent failures

