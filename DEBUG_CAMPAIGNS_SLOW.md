# Debugging Slow Campaigns Endpoint

## Quick Diagnostic Commands (Run on AWS Server)

### 1. Check Service Status
```bash
# Check if service is running
sudo systemctl status vernal-agents

# Check recent logs for errors
sudo journalctl -u vernal-agents -n 100 --no-pager | grep -i error
```

### 2. Check Recent Campaigns Endpoint Logs
```bash
# See all recent requests to /campaigns
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -A 10 "campaigns GET\|/campaigns"

# Check for slow queries
sudo journalctl -u vernal-agents -n 200 --no-pager | grep -i "slow\|timeout\|taking"
```

### 3. Test Endpoint Directly (with timing)
```bash
# Get your auth token first (from browser localStorage or API)
TOKEN="your_token_here"

# Test with timing
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/campaigns \
  -w "\nTime: %{time_total}s\n" \
  -o /tmp/campaigns_response.json

# Check response size
ls -lh /tmp/campaigns_response.json
cat /tmp/campaigns_response.json | jq '.campaigns | length' 2>/dev/null || echo "Not JSON or jq not installed"
```

### 4. Check Database Performance
```bash
# Connect to MySQL with correct credentials
mysql -u vernalcontentum_vernaluse -p vernalcontentum_contentMachine

# Then run these queries:
# Check table sizes
SELECT 
    table_name AS 'Table',
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE table_schema = 'vernalcontentum_contentMachine'
ORDER BY (data_length + index_length) DESC;

# Check if campaigns table has indexes
SHOW INDEXES FROM campaigns;

# Check slow query log (if enabled)
sudo tail -f /var/log/mysql/slow-query.log

# Check current MySQL processes
mysql -u vernalcontentum_vernaluse -p -e "SHOW PROCESSLIST;" vernalcontentum_contentMachine
```

### 5. Check Server Resources
```bash
# CPU and Memory usage
top -bn1 | head -20
htop  # if available

# Disk I/O
iostat -x 1 5

# Check if MySQL is using too much memory
ps aux | grep mysql

# Check system load
uptime
```

### 6. Enable Detailed Logging (Temporary)
```bash
# Edit the campaigns endpoint to add timing logs
cd /path/to/backend-repo-git
# Add timing logs around database queries in app/routes/campaigns.py

# Or check current logs with more detail
sudo journalctl -u vernal-agents -f
```

### 7. Check for Database Locks
```bash
mysql -u vernalcontentum_vernaluse -p -e "
SELECT * FROM information_schema.INNODB_LOCKS;
SELECT * FROM information_schema.INNODB_LOCK_WAITS;
" vernalcontentum_contentMachine
```

### 8. Profile the Endpoint Code
```bash
# Add profiling to campaigns.py endpoint:
import time
import logging

@campaigns_router.get("/campaigns")
def get_campaigns(...):
    start_time = time.time()
    logger.info("🔍 /campaigns GET endpoint called")
    
    # ... existing code ...
    
    query_start = time.time()
    campaigns = db.query(Campaign).filter(...).all()
    query_time = time.time() - query_start
    logger.info(f"⏱️ Database query took {query_time:.2f}s")
    
    # ... rest of code ...
    
    total_time = time.time() - start_time
    logger.info(f"⏱️ Total endpoint time: {total_time:.2f}s")
```

## Common Issues to Check

1. **Missing Database Indexes**
   - Check if `user_id` and `campaign_id` columns have indexes
   - Large table scans can be very slow

2. **N+1 Query Problem**
   - Check if the endpoint is making multiple queries per campaign
   - Use SQLAlchemy eager loading if needed

3. **Large Result Sets**
   - Check how many campaigns are being returned
   - Consider pagination if there are many campaigns

4. **Database Connection Pool Exhaustion**
   - Check database connection pool settings
   - Too few connections can cause queuing

5. **Slow Joins**
   - If joining with other tables, check join performance
   - Add indexes on foreign keys

6. **Network Issues**
   - Check if there's network latency between app and database
   - Check database server location

## Quick Fixes to Try

### Add Indexes (if missing)
```sql
CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_campaign_id ON campaigns(campaign_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
```

### Check Query Execution Plan
```sql
EXPLAIN SELECT * FROM campaigns WHERE user_id = ?;
```

### Optimize Query (if using ORM)
```python
# Instead of:
campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()

# Try:
campaigns = db.query(Campaign).filter(
    Campaign.user_id == current_user.id
).options(
    # Add eager loading if needed
    # joinedload(Campaign.some_relation)
).all()
```

## Next Steps

1. Run the diagnostic commands above
2. Share the output to identify the bottleneck
3. Apply appropriate fix based on findings
