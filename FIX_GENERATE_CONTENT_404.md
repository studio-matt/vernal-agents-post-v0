# Fix for 404 Error on `/campaigns/{campaign_id}/generate-content`

## Problem
The endpoint was returning 404 because FastAPI couldn't parse the request body when path parameters are present.

## Solution Applied
Added `Body(...)` wrapper to the `request_data` parameter in:
- `/campaigns/{campaign_id}/generate-content` endpoint
- `/campaigns/{campaign_id}/plan` endpoint (preventive fix)

## Changes Made
**File:** `app/routes/brand_personalities.py`

1. Added `Body` to imports:
```python
from fastapi import APIRouter, HTTPException, Depends, status, Body
```

2. Updated endpoint signature:
```python
# Before:
async def generate_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any],
    ...

# After:
async def generate_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any] = Body(...),
    ...
```

## Next Steps - REQUIRED

**You must restart the backend service for the changes to take effect:**

### On your server (Ubuntu):
```bash
# SSH into your server
ssh ubuntu@your-server-ip

# Navigate to backend directory
cd /home/ubuntu/vernal-agents-post-v0

# Pull latest changes
git pull origin main

# Restart the service
sudo systemctl restart vernal-backend

# Check service status
sudo systemctl status vernal-backend

# Check logs to verify it started correctly
sudo journalctl -u vernal-backend -n 50 --no-pager
```

### Verify the fix:
1. Check that the service restarted successfully
2. Look for this log line: `✅ Brand personalities router included successfully`
3. Test the regenerate button in the UI
4. The endpoint should now return 200 instead of 404

## Why This Was Needed

In FastAPI, when you have:
- Path parameters (like `{campaign_id}`)
- A request body parameter

FastAPI needs explicit `Body()` to distinguish the body parameter from path/query parameters. Without it, FastAPI may not correctly parse the JSON body, causing routing issues.

## Verification Script

After restarting, you can verify the route is registered by checking the OpenAPI docs:
```bash
curl https://themachine.vernalcontentum.com/openapi.json | grep -A 5 "generate-content"
```

Or check the route directly:
```bash
curl -X POST https://themachine.vernalcontentum.com/campaigns/{campaign_id}/generate-content \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"platform": "wordpress", "week": 1, "day": "Monday"}'
```

