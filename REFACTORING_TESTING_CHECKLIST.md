# Testing Checklist - Post Refactoring

**Date:** 2025-01-XX  
**Status:** Ready for Testing

---

## ✅ Pre-Testing Validation (Completed)

- [x] `main.py` exists and is properly structured (92 lines)
- [x] All 6 routers are included:
  - [x] `admin_router`
  - [x] `auth_router`
  - [x] `platforms_router`
  - [x] `content_router`
  - [x] `campaigns_research_router`
  - [x] `brand_personalities_router`
- [x] CORS middleware configured
- [x] Health and root endpoints defined
- [x] Refactoring guardrails documented

---

## 🧪 Server Testing Steps

### 1. Pull Latest Code
```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
```

### 2. Run Syntax Validation
```bash
bash find_all_syntax_errors.sh
```
**Expected:** All files pass syntax check, no errors

### 3. Validate main.py Structure
```bash
bash guardrails/validate_main_structure.sh
```
**Expected:** All checks pass ✅

### 4. Test Import
```bash
python3 -c "import main; print('✅ Import successful')"
```
**Expected:** `✅ Import successful`

### 5. Restart Service
```bash
sudo systemctl restart vernal-agents
sleep 3
sudo systemctl status vernal-agents
```
**Expected:** Service is `active (running)`

### 6. Test Health Endpoint
```bash
curl http://127.0.0.1:8000/health
```
**Expected:** `{"status":"ok","message":"Backend is running"}`

### 7. Test External Health Endpoint
```bash
curl https://themachine.vernalcontentum.com/health
```
**Expected:** `{"status":"ok","message":"Backend is running"}`

### 8. Test CORS Preflight
```bash
curl -X OPTIONS https://themachine.vernalcontentum.com/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  -v
```
**Expected:** Response includes `Access-Control-Allow-Origin: *`

### 9. Test Admin Settings Endpoint
```bash
# This should work without CORS errors in browser
# Navigate to: https://machine.vernalcontentum.com/admin/settings
# Check browser console for errors
```
**Expected:** No CORS errors, settings page loads

### 10. Test Router Endpoints
Test at least one endpoint from each router:

- **Admin:** `GET /admin/settings/{setting_key}` (requires auth)
- **Auth:** `POST /auth/login`
- **Platforms:** `GET /platforms/{platform}/credentials` (requires auth)
- **Content:** Check content-related endpoints
- **Campaigns Research:** Check research endpoints
- **Brand Personalities:** Check brand personality endpoints

---

## 🐛 Troubleshooting

### If Service Fails to Start

1. **Check logs:**
   ```bash
   sudo journalctl -u vernal-agents -n 50
   ```

2. **Common issues:**
   - Import errors → Check router imports in `main.py`
   - Syntax errors → Run `bash find_all_syntax_errors.sh`
   - Missing dependencies → Check `requirements.txt`

### If CORS Errors Persist

1. **Verify CORS middleware:**
   ```bash
   grep -A 5 "CORSMiddleware" main.py
   ```

2. **Check nginx (if applicable):**
   - Ensure nginx isn't stripping CORS headers
   - Verify nginx isn't handling CORS (FastAPI should handle it)

3. **Test preflight:**
   ```bash
   curl -X OPTIONS https://themachine.vernalcontentum.com/health \
     -H "Origin: https://machine.vernalcontentum.com" \
     -H "Access-Control-Request-Method: GET" \
     -v 2>&1 | grep -i "access-control"
   ```

### If Endpoints Return 404

1. **Verify router includes:**
   ```bash
   grep "app.include_router" main.py
   ```
   Should show 6 router includes

2. **Check router files exist:**
   ```bash
   ls -la app/routes/*.py
   ```

3. **Test router import:**
   ```bash
   python3 -c "from app.routes.admin import admin_router; print('✅ Admin router imports')"
   ```

---

## ✅ Success Criteria

- [ ] Service starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] No CORS errors in browser console
- [ ] Admin settings page loads
- [ ] At least one endpoint from each router works
- [ ] No 404 errors for expected endpoints
- [ ] No syntax errors in logs

---

## 📝 Notes

- All changes have been committed and pushed to `main` branch
- Refactoring guardrails are in place (`guardrails/REFACTORING.md`)
- Validation script available (`guardrails/validate_main_structure.sh`)
- Syntax checking script available (`find_all_syntax_errors.sh`)

---

**Ready for Testing:** ✅ Yes

