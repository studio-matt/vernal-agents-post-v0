# OpenAI API Key Fix - Summary

## Problem
The system was failing because:
1. API key was only being read from environment variables
2. Global API key stored in `system_settings.openai_api_key` was not being used
3. User's personal API keys were not being checked
4. Research agent recommendations (keyword, topical, hashtag insights) were failing
5. Admin users endpoint was timing out

## Solution Implemented

### 1. Created Helper Function
Added `get_openai_api_key()` helper function that checks API keys in priority order:
1. **User's personal key** (`current_user.openai_key`) - if user has one
2. **Global key** (`system_settings.openai_api_key`) - from database
3. **Environment variable** (`OPENAI_API_KEY`) - fallback

**Location:** `main.py` line 74

### 2. Updated All LLM Call Sites
Updated the following endpoints to use the new helper:
- ✅ Research Agent Recommendations (`/campaigns/{campaign_id}/research-agent-recommendations`) - line 5327
- ✅ Topic Extraction (research endpoint) - line 3460
- ✅ Topic Comparison (`/campaigns/{campaign_id}/compare-topics`) - line 3899
- ✅ Topic Extraction (research agent) - line 5316
- ✅ Generate Ideas (`/generate-ideas`) - line 5476
- ✅ Generate Campaign Plan (`/campaigns/{campaign_id}/generate-plan`) - line 7018

### 3. Files Still Using Direct Environment Variable
These files still use `os.getenv("OPENAI_API_KEY")` directly:
- `tasks.py` line 110 - Used in background tasks
- `machine_agent.py` line 14 - Used in machine agent
- `tools.py` line 39 - Used in tools

**Note:** These may need updating if they need access to user/global keys. However, background tasks and agents may need to use global keys only.

## Next Steps

### 1. Restart Backend Service
After deploying these changes, restart the backend service:
```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
sudo systemctl restart vernal-agents
sudo systemctl status vernal-agents
```

### 2. Set Global API Key in Admin Panel
1. Go to Admin Settings > System > Platform Keys
2. Enter the global OpenAI API key in the "OpenAI (Global Default)" field
3. Click "Save OpenAI Key"
4. The key will be stored in `system_settings.openai_api_key`

### 3. Verify API Key is Working
1. Test research agent recommendations (keyword insights, topical insights, hashtag insights)
2. Check backend logs for messages like:
   - `✅ Using global OpenAI API key from system_settings`
   - `✅ Using user's personal OpenAI API key (user_id: X)`
   - `✅ Using OpenAI API key from environment variable`

### 4. Admin Users Endpoint Timeout
The `/admin/users` endpoint timeout is likely a separate issue:
- Check database connectivity
- Check if the User table query is slow
- Verify service is running: `sudo systemctl status vernal-agents`
- Check logs: `sudo journalctl -u vernal-agents -n 50 --no-pager`

## Testing Checklist

- [ ] Global API key can be set in Admin Settings
- [ ] Research agent recommendations work with global key
- [ ] User's personal key overrides global key (if set)
- [ ] Environment variable works as fallback
- [ ] Admin users endpoint loads (if timeout is fixed)
- [ ] Keyword insights generate successfully
- [ ] Topical insights generate successfully
- [ ] Hashtag insights generate successfully
- [ ] Content generation works with API key

## Error Messages

If API key is not found, users will see:
- "OpenAI API key not configured. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings."

This is more helpful than the previous generic error.

