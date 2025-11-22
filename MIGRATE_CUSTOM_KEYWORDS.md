# 🚨 URGENT: Database Migration Required

## Issue
The backend is crashing with:
```
sqlalchemy.exc.OperationalError: (1054, "Unknown column 'campaigns.custom_keywords_json' in 'field list'")
```

This happens because the code expects a `custom_keywords_json` column that doesn't exist in the database yet.

## Quick Fix (Run on Backend Server)

**SSH into the backend server and run:**

```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
./scripts/add_custom_keywords_column.sh
```

The script will:
- ✅ Load database credentials from `.env`
- ✅ Check if column already exists (idempotent - safe to run multiple times)
- ✅ Add the column if it doesn't exist
- ✅ Verify the column was added

## What This Column Does

The `custom_keywords_json` column stores custom keywords/ideas that users add to campaigns. This replaces the previous localStorage-based storage with permanent database storage.

## After Migration

After running the script, restart the backend service:

```bash
sudo systemctl restart vernal-agents
sleep 3
sudo systemctl status vernal-agents --no-pager | head -5
```

## Verification

Check that the column exists:

```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "DESCRIBE campaigns;" | grep custom_keywords_json
```

You should see:
```
custom_keywords_json | text | YES | | NULL |
```

## Manual Alternative (If Script Fails)

If the script doesn't work, you can run the SQL directly:

```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
ALTER TABLE campaigns 
ADD COLUMN custom_keywords_json TEXT NULL;
EOF
```

**Note:** This manual method is NOT idempotent - it will fail if the column already exists. Use the script for safety.

