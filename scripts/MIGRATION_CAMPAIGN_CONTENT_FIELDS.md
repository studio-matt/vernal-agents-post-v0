# Migration: Campaign Planning & Content Pre-population Fields

## Overview
This migration adds fields to support:
- Campaign planning with weeks, parent/children ideas, and knowledge graph locations
- Content pre-population with draft/editing capabilities
- Content queue integration

## What Gets Added

### Campaigns Table
- `scheduling_settings_json` (TEXT) - Stores scheduling configuration (weeks, posts per day, start date, etc.)
- `campaign_plan_json` (TEXT) - Stores generated campaign plan with parent/children structure
- `content_queue_items_json` (TEXT) - Stores checked items from content queue

### Content Table
- `campaign_id` (VARCHAR(255)) - Links content to campaign
- `is_draft` (BOOLEAN, default TRUE) - Marks content as draft until scheduled
- `can_edit` (BOOLEAN, default TRUE) - Allows editing until content is sent
- `knowledge_graph_location` (TEXT) - Knowledge graph node/location this content is based on
- `parent_idea` (TEXT) - Parent idea this content supports
- `landing_page_url` (VARCHAR(500)) - Landing page URL this content drives traffic to

## How to Run

### Step 1: Deploy Code First (Required)

**You must deploy the migration script to the server before running it.**

#### Option A: Quick Deploy (Code Only - Recommended)
```bash
# On your local machine or in the workspace, commit and push:
cd /home/runner/workspace/backend-repo
git add scripts/add_campaign_content_fields.sh scripts/add_campaign_content_fields.sql scripts/MIGRATION_CAMPAIGN_CONTENT_FIELDS.md
git commit -m "Add database migration for campaign planning and content fields"
git push origin main
```

Then on the backend server:
```bash
# SSH into the backend server first
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
sudo systemctl restart vernal-agents
```

#### Option B: Full Deploy (If you have other changes)
Follow the standard deployment process in `docs/EMERGENCY_NET.md` or use `scripts/bulletproof_deploy_backend.sh`

### Step 2: Run Migration

**After the code is deployed, run the migration on the backend server:**

```bash
# SSH into the backend server
cd /home/ubuntu/vernal-agents-post-v0
./scripts/add_campaign_content_fields.sh
```

The script:
- ✅ Loads database credentials from `.env`
- ✅ Checks if columns already exist (idempotent - safe to run multiple times)
- ✅ Adds columns only if they don't exist
- ✅ Provides clear success/error messages

### Alternative: Manual SQL (Not Recommended)
```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < scripts/add_campaign_content_fields.sql
```

**Note:** The SQL file is NOT idempotent - it will fail if columns already exist. Use the bash script for safety.

## Verification

After running the migration, verify the columns were added:

```bash
cd /home/ubuntu/vernal-agents-post-v0
source .env
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" <<EOF
DESCRIBE campaigns;
DESCRIBE content;
EOF
```

You should see the new columns in the output.

## Rollback (If Needed)

If you need to remove these columns (not recommended for production):

```sql
ALTER TABLE campaigns 
DROP COLUMN scheduling_settings_json,
DROP COLUMN campaign_plan_json,
DROP COLUMN content_queue_items_json;

ALTER TABLE content
DROP COLUMN campaign_id,
DROP COLUMN is_draft,
DROP COLUMN can_edit,
DROP COLUMN knowledge_graph_location,
DROP COLUMN parent_idea,
DROP COLUMN landing_page_url;
```

**⚠️ WARNING:** This will delete all data in these columns. Only use if absolutely necessary.

## Related Backend Changes

This migration supports the following new endpoints:
- `POST /campaigns/{campaign_id}/plan` - Create campaign plan
- `POST /campaigns/{campaign_id}/prepopulate-content` - Pre-populate content
- `POST /campaigns/{campaign_id}/generate-content` - Generate content with queue items

See `main.py` for endpoint documentation.


