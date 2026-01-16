# CORS Emergency Net - Complete Fix Documentation

## 🚨 CRITICAL: The CORS Fix That Works

### The Problem
Frontend receives CORS errors:
- `No 'Access-Control-Allow-Origin' header is present`
- `The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'`

### The Root Cause
**When `allow_credentials=True`, you CANNOT use `allow_origins=["*"]`**

This is a browser security restriction. If credentials are included, the origin must be explicitly specified.

### The Fix (main.py lines 27-38)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://machine.vernalcontentum.com",
        "https://themachine.vernalcontentum.com",
        "http://localhost:3000",  # For local development
        "http://localhost:3001",  # Alternative local port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Key Points:**
- ✅ Specific origins (not wildcard)
- ✅ `allow_credentials=True` (required for cookies/auth)
- ✅ All methods and headers allowed

---

## 🔍 Diagnostic Checklist

### Step 1: Is the Service Running?

```bash
sudo systemctl status vernal-agents
```

**If not running:**
- Check logs: `sudo journalctl -u vernal-agents --since "5 minutes ago" | tail -50`
- Common causes:
  - Syntax errors in `main.py` or route files
  - Missing imports
  - Python import errors

**Fix:** See `guardrails/SYNTAX_CHECKING.md`

### Step 2: Is Port 8000 Listening?

```bash
sudo lsof -i :8000
```

**If not listening:**
- Service is crashing on startup
- Check logs for Python errors
- Run: `bash scripts/check_service_startup.sh`

### Step 3: Can We Reach FastAPI Directly?

```bash
curl -v http://127.0.0.1:8000/health
```

**If connection refused:**
- Service not running (see Step 1)
- Wrong port or host binding

### Step 4: Check CORS Configuration

```bash
# Test CORS preflight
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  2>&1 | grep -i "access-control"
```

**Expected output:**
```
< access-control-allow-origin: https://machine.vernalcontentum.com
< access-control-allow-credentials: true
< access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
```

**If missing or wildcard:**
- Check `main.py` CORS configuration
- Verify specific origins (not `["*"]`)
- Restart service: `sudo systemctl restart vernal-agents`

### Step 5: Verify main.py Configuration

```bash
cd /home/ubuntu/vernal-agents-post-v0
grep -A 10 "CORSMiddleware" main.py
```

**Must see:**
- `allow_origins=[` (not `allow_origins=["*"]`)
- Specific domain URLs listed
- `allow_credentials=True`

**If wrong:**
- Fix `main.py` (see fix above)
- Restart service

### Step 6: Check Nginx Configuration

```bash
sudo nginx -t
sudo grep -i "access-control" /etc/nginx/sites-enabled/themachine
```

**Nginx should NOT set CORS headers** - FastAPI handles CORS.

**If nginx has CORS headers:**
- Remove them (they interfere with FastAPI CORS)
- Reload nginx: `sudo nginx -s reload`

---

## 🛠️ Quick Fix Script

Run this to diagnose and fix common CORS issues:

```bash
cd /home/ubuntu/vernal-agents-post-v0
bash scripts/diagnose_cors.sh
```

This script checks:
1. Service status
2. Port 8000 listening
3. Health endpoint
4. CORS headers
5. main.py configuration
6. Nginx configuration
7. Recent errors

---

## 📋 Common Issues & Solutions

### Issue 1: Service Won't Start

**Symptoms:**
- `systemctl status` shows `failed` or `activating`
- Port 8000 not listening

**Diagnosis:**
```bash
sudo journalctl -u vernal-agents --since "5 minutes ago" | tail -50
```

**Common Causes:**
1. **Syntax Error** - Check for `SyntaxError` in logs
   - Fix: Run `bash find_all_syntax_errors.sh`
2. **Import Error** - Check for `ImportError` or `NameError`
   - Fix: Check imports in `main.py` and route files
3. **Missing Module** - Check for `ModuleNotFoundError`
   - Fix: Install missing package in venv

**Solution:**
```bash
# Check syntax
cd /home/ubuntu/vernal-agents-post-v0
bash find_all_syntax_errors.sh

# If errors found, fix them, then:
sudo systemctl restart vernal-agents
```

### Issue 2: CORS Headers Missing

**Symptoms:**
- Browser console shows CORS errors
- `curl` shows no `access-control-allow-origin` header

**Diagnosis:**
```bash
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

**Common Causes:**
1. **Wildcard with credentials** - `allow_origins=["*"]` with `allow_credentials=True`
   - Fix: Use specific origins (see fix above)
2. **Service not running** - FastAPI not responding
   - Fix: Restart service
3. **Nginx interference** - Nginx stripping or overriding headers
   - Fix: Remove CORS headers from nginx config

**Solution:**
```bash
# Check main.py
grep -A 10 "CORSMiddleware" main.py

# If wrong, fix it:
# Change allow_origins=["*"] to specific origins list

# Restart service
sudo systemctl restart vernal-agents

# Verify
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

### Issue 3: Wrong Origin in Response

**Symptoms:**
- CORS headers present but wrong origin
- Browser rejects preflight

**Diagnosis:**
```bash
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep "access-control-allow-origin"
```

**Should show:**
```
access-control-allow-origin: https://machine.vernalcontentum.com
```

**If shows `*` or different origin:**
- Check `main.py` - must have specific origins
- Restart service

### Issue 4: Credentials Not Working

**Symptoms:**
- CORS preflight succeeds
- Actual request fails with credentials error

**Diagnosis:**
```bash
# Check if credentials header is set
curl -v http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Cookie: session=..." \
  2>&1 | grep -i "access-control"
```

**Common Causes:**
1. **Wildcard origin** - Cannot use `["*"]` with credentials
   - Fix: Use specific origins
2. **Missing credentials flag** - `allow_credentials=False`
   - Fix: Set `allow_credentials=True`

**Solution:**
- Ensure `allow_credentials=True` in `main.py`
- Ensure specific origins (not wildcard)
- Restart service

---

## 🔄 Complete Fix Procedure

If CORS is completely broken, follow this procedure:

### 1. Stop Service
```bash
sudo systemctl stop vernal-agents
```

### 2. Check main.py
```bash
cd /home/ubuntu/vernal-agents-post-v0
cat main.py | grep -A 15 "CORSMiddleware"
```

### 3. Fix main.py (if needed)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://machine.vernalcontentum.com",
        "https://themachine.vernalcontentum.com",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Check for Syntax Errors
```bash
bash find_all_syntax_errors.sh
```

### 5. Fix Any Errors Found
- Syntax errors
- Import errors
- Missing modules

### 6. Restart Service
```bash
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents
```

### 7. Verify CORS
```bash
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  -H "Access-Control-Request-Method: GET" \
  2>&1 | grep -i "access-control"
```

### 8. Test External
```bash
curl -v https://themachine.vernalcontentum.com/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

---

## 📚 Related Documentation

- **`guardrails/SYNTAX_CHECKING.md`** - Fix syntax errors that prevent service startup
- **`guardrails/REFACTORING.md`** - Avoid breaking main.py during refactoring
- **`scripts/diagnose_cors.sh`** - Comprehensive CORS diagnostic script
- **`scripts/check_service_startup.sh`** - Service startup diagnostics

---

## 🎯 Key Principles

1. **Never use `allow_origins=["*"]` with `allow_credentials=True`**
2. **Always specify exact origins** - Browser security requirement
3. **FastAPI handles CORS** - Nginx should not set CORS headers
4. **Service must be running** - CORS errors often mean service crashed
5. **Check logs first** - Most issues are Python errors preventing startup

---

## ⚡ Quick Reference

```bash
# Diagnose CORS
bash scripts/diagnose_cors.sh

# Check service
sudo systemctl status vernal-agents

# Check logs
sudo journalctl -u vernal-agents --since "5 minutes ago" | tail -50

# Test CORS
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"

# Restart service
sudo systemctl restart vernal-agents
```

---

## 🔗 The Fix Commit

The CORS fix was implemented in commit that changed:
- `allow_origins=["*"]` → specific origins list
- Kept `allow_credentials=True`
- Added production domains

**This fix is CRITICAL** - any changes to CORS configuration must maintain this pattern.

