# Deployment Guide: Topic Extraction Prompt Feature

## Overview
This feature adds a configurable LLM prompt for topic extraction that can be edited from the admin page.

## Changes Made
- **Frontend**: Admin page UI for editing prompt (`app/admin/page.tsx`)
- **Backend**: SystemSettings model, API endpoints, and database migration
- **Database**: New `system_settings` table

## Deployment Steps (Following EMERGENCY_NET.md)

### 1. Backend Deployment (SSH to backend server)

```bash
# SSH to backend server
ssh ubuntu@18.235.104.132

# Navigate to backend directory
cd /home/ubuntu/vernal-agents-post-v0

# Pull latest code
git fetch origin && git switch main && git pull --ff-only origin main

# MANDATORY: Activate venv and validate dependencies
source venv/bin/activate
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}

# Run database migration to create system_settings table
bash scripts/add_system_settings_table.sh

# Restart backend service
sudo systemctl restart vernal-agents
sleep 5

# Verification (MANDATORY per EMERGENCY_NET.md)
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .
curl -I https://themachine.vernalcontentum.com/health
curl -I https://themachine.vernalcontentum.com/auth/login

# Test the new endpoints
curl -s http://127.0.0.1:8000/admin/settings/topic_extraction_prompt | jq .
```

### 2. Frontend Deployment

The frontend changes have been committed and pushed. The frontend will automatically rebuild on the next deployment trigger.

**If manual deployment is needed:**
- Follow your standard frontend deployment process
- The changes are in `app/admin/page.tsx` and `components/Service.tsx`

### 3. Verify Feature Works

1. **Navigate to admin page**: https://machine.vernalcontentum.com/admin
2. **You should see**: "Topic Extraction Prompt" section above "Script Regenerator"
3. **Test loading**: The prompt should load from database (or show empty if not set yet)
4. **Test saving**: Edit the prompt and click "Save Topic Extraction Prompt"
5. **Verify**: Check that the prompt is saved and used in next topic extraction

### 4. Database Migration Details

The migration script (`scripts/add_system_settings_table.sh`) will:
- Create `system_settings` table if it doesn't exist
- Insert default topic extraction prompt
- Set up proper indexes

**If migration fails:**
```bash
# Check database connection
mysql -h 50.6.198.220 -u [DB_USER] -p[DB_PASSWORD] [DB_NAME] -e "SHOW TABLES LIKE 'system_settings';"

# Manual migration if needed
mysql -h 50.6.198.220 -u [DB_USER] -p[DB_PASSWORD] [DB_NAME] < scripts/add_system_settings_table.sql
```

### 5. Troubleshooting

**Admin page not showing prompt editor:**
- Check browser console for errors
- Verify frontend is deployed with latest code
- Check API endpoint: `curl -s https://themachine.vernalcontentum.com/admin/settings/topic_extraction_prompt`

**Prompt not saving:**
- Check backend logs: `sudo journalctl -u vernal-agents -f | grep "system_setting"`
- Verify database table exists: `mysql -h 50.6.198.220 -u [user] -p [db] -e "SELECT * FROM system_settings;"`
- Check API response: `curl -X PUT https://themachine.vernalcontentum.com/admin/settings/topic_extraction_prompt -H "Content-Type: application/json" -d '{"setting_value":"test"}'`

**Prompt not being used in topic extraction:**
- Check backend logs for "✅ Loaded topic extraction prompt from database"
- Verify cache is cleared after updates (check logs for "✅ Cleared topic extraction prompt cache")
- Wait 5 minutes for cache TTL or restart backend service

## Rollback Procedure

If issues occur:

```bash
# Backend rollback
cd /home/ubuntu/vernal-agents-post-v0
git log --oneline -10  # Find last working commit
git reset --hard <last-working-commit-hash>
sudo systemctl restart vernal-agents

# Frontend rollback
# Follow your standard frontend rollback procedure
```

## Success Criteria

- [x] Frontend changes committed and pushed
- [ ] Backend changes committed and pushed
- [ ] Database migration run successfully
- [ ] Backend service restarted
- [ ] Admin page shows "Topic Extraction Prompt" section
- [ ] Prompt can be loaded from database
- [ ] Prompt can be saved to database
- [ ] Prompt is used in topic extraction (check logs)

