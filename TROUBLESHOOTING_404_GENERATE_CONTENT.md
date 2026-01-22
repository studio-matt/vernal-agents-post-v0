# Troubleshooting 404 Error on `/campaigns/{campaign_id}/generate-content`

## Current Status
✅ Code fix applied: Added `Body(...)` to `request_data` parameter
❌ Still getting 404 - Backend needs restart OR there's another issue

## Step-by-Step Troubleshooting

### Step 1: Verify Code Changes Are Present

SSH into your server and run:
```bash
cd /home/ubuntu/vernal-agents-post-v0
bash scripts/check_route_registration.sh
```

This will verify:
- Route definition exists
- `Body` is imported
- `Body(...)` is used in endpoint
- Router is included in main.py

### Step 2: Pull Latest Changes

```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
```

### Step 3: Check for Syntax Errors

```bash
# Check Python syntax
python3 -m py_compile app/routes/brand_personalities.py

# Check if router can be imported
python3 -c "from app.routes.brand_personalities import brand_personalities_router; print('OK')"
```

If you get import errors, check the logs:
```bash
sudo journalctl -u vernal-backend -n 100 --no-pager | grep -i error
```

### Step 4: Restart Backend Service

```bash
# Restart the service
sudo systemctl restart vernal-backend

# Wait a few seconds, then check status
sleep 3
sudo systemctl status vernal-backend
```

### Step 5: Verify Service Started Successfully

Check the logs for:
- ✅ `Brand personalities router included successfully`
- ❌ Any import errors or syntax errors

```bash
sudo journalctl -u vernal-backend -n 50 --no-pager
```

### Step 6: Test the Endpoint Directly

```bash
# Get your auth token first, then:
curl -X POST https://themachine.vernalcontentum.com/campaigns/87165cd0-5c27-4c68-95d3-6984133de8a4/generate-content \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "platform": "wordpress",
    "week": 1,
    "day": "Monday"
  }'
```

### Step 7: Check OpenAPI Docs

The route should appear in the OpenAPI schema:
```bash
curl https://themachine.vernalcontentum.com/openapi.json | grep -A 10 "generate-content"
```

## Common Issues

### Issue 1: Service Not Restarted
**Symptom:** Code changes are present but endpoint still returns 404
**Solution:** Restart the service (Step 4)

### Issue 2: Import Error Preventing Router Load
**Symptom:** Service starts but router isn't included
**Solution:** Check logs for import errors, fix missing dependencies

### Issue 3: Syntax Error
**Symptom:** Service fails to start
**Solution:** Run syntax check (Step 3), fix any errors

### Issue 4: Route Conflict
**Symptom:** Route exists but returns 404
**Solution:** Check if another route is matching first (unlikely but possible)

## Expected Log Output After Fix

When the endpoint is called, you should see:
```
📝 generate_campaign_content called for campaign_id: 87165cd0-5c27-4c68-95d3-6984133de8a4
📝 request_data keys: ['platform', 'week', 'day', ...]
📝 Created content generation task: <task_id> for campaign <campaign_id>
```

If you don't see these logs, the endpoint isn't being hit (still 404).

## Still Not Working?

If after all these steps it's still not working:

1. **Check if the route is actually registered:**
   ```bash
   # On the server, create a test script
   cat > /tmp/test_routes.py << 'EOF'
   import sys
   sys.path.insert(0, '/home/ubuntu/vernal-agents-post-v0')
   from main import app
   for route in app.routes:
       if hasattr(route, 'path') and 'generate-content' in route.path:
           print(f"Found: {route.methods} {route.path}")
   EOF
   python3 /tmp/test_routes.py
   ```

2. **Check nginx configuration** (if using reverse proxy):
   - Ensure `/campaigns/` routes are proxied correctly
   - Check for any route rewriting that might interfere

3. **Check FastAPI route order:**
   - Routes are matched in order
   - Ensure no earlier route is catching this path

