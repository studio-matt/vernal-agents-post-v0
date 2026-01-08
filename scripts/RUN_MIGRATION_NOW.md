# 🔴 URGENT: Run Database Migration for Writing Samples

## Problem
The `writing_samples_json` column is currently `TEXT` (64KB limit) and needs to be `LONGTEXT` (4GB limit) to support large writing samples.

## Error You're Seeing
```
(pymysql.err.DataError) (1406, "Data too long for column 'writing_samples_json' at row 1")
```

## Solution: Run Migration on Backend Server

### Step 1: SSH to Backend Server
```bash
ssh ubuntu@18.235.104.132
```

### Step 2: Navigate to Backend Directory
```bash
cd /home/ubuntu/vernal-agents-post-v0
```

### Step 3: Pull Latest Code (if not already done)
```bash
git pull origin main
```

### Step 4: Run Migration Script

**Option A: Python Script (Recommended)**
```bash
source venv/bin/activate
python3 scripts/migrate_writing_samples_to_longtext.py
```

**Option B: SQL Script (Alternative)**
```bash
mysql -u your_db_user -p your_database_name < scripts/migrate_writing_samples_to_longtext.sql
```

**Option C: Manual SQL (If you have MySQL access)**
```sql
USE your_database_name;
ALTER TABLE author_personalities 
MODIFY COLUMN writing_samples_json LONGTEXT NULL;
```

### Step 5: Verify Migration
```bash
mysql -u your_db_user -p your_database_name -e "SHOW COLUMNS FROM author_personalities LIKE 'writing_samples_json';"
```

You should see `LONGTEXT` in the Type column.

### Step 6: Restart Backend Service (if needed)
```bash
sudo systemctl restart vernal-agents
```

## Expected Output
When running the Python script, you should see:
```
🔄 Migrating writing_samples_json column from TEXT to LONGTEXT...
📊 Current column type: text
🔧 Altering column type...
✅ Successfully migrated writing_samples_json to LONGTEXT!
✅ Verified new column type: longtext
```

## Important Notes
- This migration is **safe** - it only changes the column type, not the data
- The migration is **backward compatible** - existing data will work fine
- No downtime required - the column can be altered while the service is running
- After migration, you can upload much larger writing samples (up to 4GB total)







