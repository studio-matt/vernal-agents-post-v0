# 🚨 COMPLETE FIX GUIDE - All Issues

## Issues Found
1. **Wrong keyword**: Campaign built with "pug" but scraped "looking"
2. **Database schema**: `raw_html` column too small (TEXT vs MEDIUMTEXT)
3. **Missing apscheduler**: Startup error (already in requirements.txt)
4. **Script execution**: Running bash script with python3

## Step 1: Fix Database Schema (CRITICAL - DO THIS FIRST)

**This is blocking all data saves!**

**RECOMMENDED: Use the automated script (reads password from .env):**

```bash
cd /home/ubuntu/vernal-agents-post-v0
./scripts/fix_database_schema.sh
```

**OR manually (you'll be prompted for password):**

```bash
cd /home/ubuntu/vernal-agents-post-v0
# Get password from .env file
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE campaign_raw_data
MODIFY COLUMN raw_html MEDIUMTEXT;
EOF
```

**OR if you prefer to type password interactively:**

```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p "$DB_NAME" <<EOF
ALTER TABLE campaign_raw_data
MODIFY COLUMN raw_html MEDIUMTEXT;
EOF
# (it will prompt for password - paste from .env file)
```

## Step 2: Pull Latest Code and Install Dependencies

```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main

# Install missing dependencies
source venv/bin/activate
pip install apscheduler>=3.10.4

# Verify all dependencies
python -c "import bs4; import gensim; import apscheduler; print('✅ All dependencies installed')"

# Restart service
sudo systemctl restart vernal-agents
```

## Step 3: Diagnose Keyword Issue

The enhanced logging will now show exactly what keywords are being used. 

**Run a campaign rebuild and check logs:**

```bash
# Monitor logs for keyword information
sudo journalctl -u vernal-agents -f | grep -E 'CRITICAL.*Keywords|keywords received|keywords being used|First keyword'
```

**Expected output:**
- `🔍 CRITICAL: Keywords received from frontend: ['pug']`
- `🔍 CRITICAL: Keywords being used for scraping: ['pug']`
- `🔍 First keyword: 'pug'`

**If you see "looking" instead of "pug":**
- Check the campaign in the database: `SELECT campaign_id, campaign_name, keywords FROM campaigns WHERE campaign_id='a298b592-411c-4a48-9ea3-10d397d3d84c'`
- Check frontend console logs for what keywords are being sent

## Step 4: Fix Script Execution

The script is bash, not Python:

```bash
# Correct way to run the diagnostic script:
bash scripts/check_scraping_now.sh a298b592-411c-4a48-9ea3-10d397d3d84c

# NOT: python3 scripts/check_scraping_now.sh
```

## Step 5: Verify Everything Works

After applying all fixes:

1. **Rebuild campaign** with "pug" keyword
2. **Check logs** for:
   - `🔍 CRITICAL: Keywords received from frontend: ['pug']`
   - `✅ Scraped <url> (DB ID: X): Y chars`
   - No database errors
3. **Check database** for valid rows:
   ```sql
   SELECT COUNT(*) FROM campaign_raw_data 
   WHERE campaign_id='a298b592-411c-4a48-9ea3-10d397d3d84c' 
   AND source_url NOT LIKE 'error:%';
   ```

## Troubleshooting

### If keywords still wrong:
1. Check campaign in database: `SELECT * FROM campaigns WHERE campaign_id='...'`
2. Check frontend console for `🔍 CRITICAL: Keywords being sent:`
3. Check backend logs for `🔍 CRITICAL: Keywords received from frontend:`

### If database errors persist:
1. Verify schema change: `DESCRIBE campaign_raw_data;` (should show `MEDIUMTEXT` for `raw_html`)
2. Check if column was updated: `SHOW COLUMNS FROM campaign_raw_data LIKE 'raw_html';`

### If scraping still fails:
1. Check dependencies: `python -c "import bs4, gensim, apscheduler; print('OK')"`
2. Check Playwright: `python -m playwright --version`
3. Check DuckDuckGo: Look for `DDGS is None` errors in logs

