# Database Credentials Reference

## Production Database

- **Database Name:** `vernalcontentum_contentMachine`
- **Username:** `vernalcontentum_vernaluse`
- **Password:** (stored securely, ask admin)

## Quick Connection Command

```bash
mysql -u vernalcontentum_vernaluse -p vernalcontentum_contentMachine
```

## Quick Database Check Script

On the AWS server (backend path: `/home/ubuntu/vernal-agents-post-v0`):
```bash
cd /home/ubuntu/vernal-agents-post-v0
bash scripts/check_campaigns_db.sh
```

## Common Queries

### Count campaigns
```sql
SELECT COUNT(*) FROM campaigns;
```

### Check indexes
```sql
SHOW INDEXES FROM campaigns;
```

### Add missing index (if needed)
```sql
CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_campaign_id ON campaigns(campaign_id);
```

### Check campaigns per user
```sql
SELECT user_id, COUNT(*) as count 
FROM campaigns 
GROUP BY user_id 
ORDER BY count DESC;
```
