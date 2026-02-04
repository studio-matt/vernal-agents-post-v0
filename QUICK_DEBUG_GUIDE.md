# Quick Debug Guide for Slow Campaigns Endpoint

## Run These Commands on AWS Server (SSH)

### Step 1: Run the Debug Script
```bash
cd /path/to/backend-repo-git
bash scripts/debug_campaigns_slow.sh
```

### Step 2: Check Logs in Real-Time
```bash
# Watch logs as requests come in
sudo journalctl -u vernal-agents -f | grep -i campaigns
```

### Step 3: Test Endpoint Directly
```bash
# Get your auth token (from browser localStorage or previous API call)
TOKEN="your_token_here"

# Test with detailed timing
time curl -v \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/campaigns \
  -o /tmp/campaigns.json \
  2>&1 | tee /tmp/curl_output.txt

# Check response
cat /tmp/campaigns.json | python3 -m json.tool | head -50
```

### Step 4: Check Database Directly
```bash
# Connect to MySQL with correct credentials
mysql -u vernalcontentum_vernaluse -p vernalcontentum_contentMachine

# Then run:
# Count campaigns
SELECT COUNT(*) as total_campaigns FROM campaigns;

# Count campaigns per user
SELECT user_id, COUNT(*) as count FROM campaigns GROUP BY user_id;

# Check table size
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
    table_rows
FROM information_schema.TABLES
WHERE table_schema = DATABASE()
AND table_name = 'campaigns';

# Check indexes
SHOW INDEXES FROM campaigns;

# Test query performance
EXPLAIN SELECT * FROM campaigns WHERE user_id = 1;
```

### Step 5: Check for Missing Indexes
```sql
-- Check if user_id has an index (CRITICAL for performance)
SHOW INDEXES FROM campaigns WHERE Column_name = 'user_id';

-- If missing, add it:
CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);

-- Check campaign_id index
SHOW INDEXES FROM campaigns WHERE Column_name = 'campaign_id';
CREATE INDEX idx_campaigns_campaign_id ON campaigns(campaign_id) IF NOT EXISTS;
```

### Step 6: Check Application Code Performance
The endpoint does several things that could be slow:
1. Main query with defer() options
2. Demo campaign check/creation
3. Multiple fallback queries if main query fails
4. JSON serialization of all campaigns

**To add timing logs, edit `app/routes/campaigns.py`:**

```python
import time

@campaigns_router.get("/campaigns")
def get_campaigns(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    start_time = time.time()
    logger.info("🔍 /campaigns GET endpoint called")
    
    try:
        # ... existing code ...
        
        query_start = time.time()
        campaigns = db.query(Campaign).filter(...).all()
        query_time = time.time() - query_start
        logger.info(f"⏱️ Main query took {query_time:.2f}s, returned {len(campaigns)} campaigns")
        
        # Demo campaign check
        demo_start = time.time()
        # ... demo campaign logic ...
        demo_time = time.time() - demo_start
        logger.info(f"⏱️ Demo campaign check took {demo_time:.2f}s")
        
        # Serialization
        serial_start = time.time()
        # ... serialization code ...
        serial_time = time.time() - serial_start
        logger.info(f"⏱️ Serialization took {serial_time:.2f}s")
        
        total_time = time.time() - start_time
        logger.info(f"⏱️ Total endpoint time: {total_time:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Error in get_campaigns: {e}")
        # ... error handling ...
```

### Step 7: Common Issues to Check

1. **Missing Database Indexes** (MOST COMMON)
   ```sql
   -- Check if these indexes exist
   SHOW INDEXES FROM campaigns;
   
   -- Add if missing:
   CREATE INDEX idx_user_id ON campaigns(user_id);
   CREATE INDEX idx_campaign_id ON campaigns(campaign_id);
   ```

2. **Too Many Campaigns**
   ```sql
   -- Check how many campaigns exist
   SELECT COUNT(*) FROM campaigns;
   SELECT user_id, COUNT(*) FROM campaigns GROUP BY user_id;
   
   -- If > 1000 campaigns, consider pagination
   ```

3. **Large JSON Fields**
   ```sql
   -- Check size of JSON columns
   SELECT 
       campaign_id,
       LENGTH(extraction_settings_json) as extraction_size,
       LENGTH(preprocessing_settings_json) as preprocessing_size,
       LENGTH(campaign_plan_json) as plan_size
   FROM campaigns
   ORDER BY (extraction_size + preprocessing_size + plan_size) DESC
   LIMIT 10;
   ```

4. **Database Connection Pool**
   - Check if connection pool is exhausted
   - Look for "pool" or "connection" errors in logs

5. **N+1 Query Problem**
   - Check if endpoint makes multiple queries per campaign
   - Use SQLAlchemy eager loading if needed

### Step 8: Quick Fixes

**If missing indexes:**
```sql
CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_campaign_id ON campaigns(campaign_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
```

**If too many campaigns:**
- Add pagination to the endpoint
- Or filter by status/date

**If large JSON fields:**
- Consider lazy loading JSON fields
- Or compress JSON data

## Share Results

After running diagnostics, share:
1. Output of debug script
2. Database query counts and sizes
3. Index status
4. Any errors from logs
5. Response time from curl test

This will help identify the exact bottleneck.
