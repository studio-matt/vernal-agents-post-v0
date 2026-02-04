# Finding the Backend Repo on AWS Server

## Step 1: Find the Repository Location

Try these commands to locate the backend repository:

```bash
# Check common locations
ls -la ~/
ls -la /home/ubuntu/
ls -la /opt/
ls -la /var/www/

# Or search for the repo
find ~ -name "backend-repo-git" -type d 2>/dev/null
find /home -name "campaigns.py" -type f 2>/dev/null | head -1

# Check where the service is running from
sudo systemctl status vernal-agents | grep -i "working\|directory"

# Or check the service file directly
sudo cat /etc/systemd/system/vernal-agents.service | grep -i "working\|directory\|execstart"
```

## Step 2: Once You Find It, Navigate There

```bash
# Example (adjust path as needed):
cd /home/ubuntu/vernal-agents-post-v0
# OR
cd /opt/vernal-agents-post-v0
# OR wherever it's located

# Then run the script
bash scripts/check_campaigns_db.sh
```

## Alternative: Run Commands Directly Without Script

If you can't find the repo, you can run the database checks directly:

```bash
# Connect to database
mysql -u vernalcontentum_vernaluse -p vernalcontentum_contentMachine

# Then run these queries:
SELECT COUNT(*) as total_campaigns FROM campaigns;
SELECT user_id, COUNT(*) as count FROM campaigns GROUP BY user_id ORDER BY count DESC;
SHOW INDEXES FROM campaigns;
EXPLAIN SELECT * FROM campaigns WHERE user_id = 1 LIMIT 1;
```
