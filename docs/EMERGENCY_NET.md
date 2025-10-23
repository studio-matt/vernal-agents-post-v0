# Vernal Agents Backend — Emergency Net (v3)

## TL;DR
- **App:** FastAPI served by Python (systemd)
- **Server:** `18.235.104.132` (Back End Server)
- **Domain:** https://themachine.vernalcontentum.com → nginx → 127.0.0.1:8000
- **Live directory:** `/home/ubuntu/vernal-agents-post-v0` (systemd cwd)
- **Repo checkout:** `/home/ubuntu/vernal-agents-post-v0`
- **Git repo:** `https://github.com/studio-matt/vernal-agents-post-v0.git`
- **Deploy flow:** Pull from repo → activate venv → restart systemd service
- **Verify:** Health endpoints, database connectivity, CORS, and auth flows.

---

## Key Paths
- **Live app dir:** `/home/ubuntu/vernal-agents-post-v0`
  - **Main app:** `main.py`
  - **Auth system:** `auth_api.py`
  - **Database:** `models.py`, `database.py`
  - **Email service:** `email_service.py`
  - **Config:** `requirements.txt`, `.env`
- **Systemd service:** `vernal-agents.service`
- **Virtual environment:** `/home/ubuntu/vernal-agents-post-v0/venv/`
- **Nginx config:** `/etc/nginx/sites-enabled/themachine`
  - **Proxies to:** `http://127.0.0.1:8000`
  - **TLS:** `/etc/letsencrypt/live/themachine.vernalcontentum.com/`
- **Database:** MySQL @ `50.6.198.220:3306`

---

## 🚀 Bulletproof Manual Deploy

### 1. **Pull Latest Code**
```bash
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
```

### 2. **Activate Virtual Environment**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. **Restart Systemd Service**
```bash
sudo systemctl restart vernal-agents
sudo systemctl status vernal-agents
```

### 4. **Verification (MANDATORY)**
```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .
curl -I https://themachine.vernalcontentum.com/health
curl -I https://themachine.vernalcontentum.com/auth/login
```

---

## 🔒 Nginx Routing/Proxy Health

**Critical:** Nginx must correctly proxy all requests to FastAPI. CORS must be handled by FastAPI, not nginx.

### **Sample Config**
```nginx
server {
    listen 443 ssl;
    server_name themachine.vernalcontentum.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # NO CORS HEADERS HERE - let FastAPI handle it!
    }
}
```

### **Validate Nginx**
```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I https://themachine.vernalcontentum.com/health
curl -I https://themachine.vernalcontentum.com/auth/login
```

---

## 🚨 Common Integration Issues

### **CORS Headers (CRITICAL)**
- **Error:** "Request header field content-type is not allowed by Access-Control-Allow-Headers"
- **Root Cause:** nginx intercepting OPTIONS requests, preventing FastAPI CORS handling
- **Fix:** Remove ALL nginx CORS headers, let FastAPI handle everything
- **Test:** `curl -i -X OPTIONS https://themachine.vernalcontentum.com/auth/signup`

### **422/500 Errors on Auth Endpoints**
- **422 Error:** Invalid request format or missing required fields
- **500 Error:** Server-side error (check logs: `sudo journalctl -u vernal-agents -f`)
- **Common Causes:** Missing environment variables, database connection issues, JWT token creation errors
- **Fix:** Check `.env` file, verify database connectivity, validate JWT implementation

### **JWT Token Creation Issues**
- **Error:** "create_access_token() got an unexpected keyword argument 'expires_delta'"
- **Fix:** Remove `expires_delta` parameter from `create_access_token()` calls
- **Correct Usage:** `create_access_token(data={"sub": str(user.id)})`

### **JWT Authentication "Invalid credentials" on Protected Endpoints**
- **Error:** "Invalid authentication credentials" on protected endpoints (e.g., /campaigns)
- **Root Cause:** User not verified (`is_verified: false`) - many systems require verified users
- **Symptoms:** Login works and returns JWT, but protected endpoints reject the token
- **Fix:** Complete email verification OR manually set `is_verified = 1` in database
- **Quick Test:** `UPDATE user SET is_verified = 1 WHERE email = 'user@example.com';`

### **JWT String vs Integer Type Mismatch (CRITICAL)**
- **Error:** "Invalid authentication credentials" even with valid JWT tokens
- **Root Cause:** JWT payload `sub` field contains string user_id ("14"), but database `User.id` is integer (14)
- **Symptoms:** Login works, JWT created, but `get_current_user` fails with "User not found"
- **Fix:** Convert string to integer: `User.id == int(user_id)` instead of `User.id == user_id`
- **Code Fix:** `user = db.query(User).filter(User.id == int(user_id)).first()`

### **Frontend 401 Unauthorized Errors**
- **Error:** Frontend gets 401 errors on campaign endpoints despite successful login
- **Root Cause:** JWT token expired, not stored, or user not verified
- **Symptoms:** Console shows "Failed to load resource: 401" for /campaigns endpoints
- **Fix:** Log out and log back in to get fresh token, ensure user is verified
- **Debug:** Check browser dev tools → Network tab → Authorization header

### **Database Connection Issues**
- **Error:** Database connection timeouts or failures
- **Check:** `curl -s http://127.0.0.1:8000/mcp/enhanced/health`
- **Fix:** Verify database credentials in `.env`, check network connectivity to `50.6.198.220:3306`

### **Email Service Issues**
- **Error:** OTP emails not sending
- **Check:** SMTP configuration in `.env` file
- **Test:** Check email service logs in systemd journal
- **Fix:** Verify SMTP credentials and server settings

---

## 📧 Email/OTP Verification Flow

### **Email Service Configuration**
- **SMTP Settings:** Must be configured in `.env` file
- **OTP Storage:** MySQL `otp` table with expiration
- **Email Templates:** Include verification URL with OTP parameter

### **OTP Verification Process**
- **API Endpoint:** `/auth/verify-email`
- **Payload:** `{"email": "user@example.com", "otp_code": "123456"}`
- **Response:** `{"message": "Email verified successfully"}` or error
- **Database Update:** Set `is_verified = 1` in user table

### **Email Verification Testing**
```bash
# Test OTP verification
curl -X POST https://themachine.vernalcontentum.com/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","otp_code":"123456"}'

# Test email sending (check logs)
sudo journalctl -u vernal-agents -f | grep -i email
```

### **User Verification Requirements (CRITICAL)**
- **Protected Endpoints:** Campaign endpoints require `is_verified = true`
- **Login vs Protected:** Login works for unverified users, but protected endpoints fail
- **Verification Methods:**
  1. **Complete OTP Flow:** Signup → Check email → Enter OTP → Verified
  2. **Manual Database:** `UPDATE user SET is_verified = 1 WHERE email = 'user@example.com';`
- **Testing Workflow:**
```bash
# 1. Create user
curl -X POST https://themachine.vernalcontentum.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","email":"test@example.com","password":"testpass123","name":"Test User"}'

# 2. Verify user (use OTP from response)
curl -X POST https://themachine.vernalcontentum.com/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","otp_code":"123456"}'

# 3. Login and test protected endpoints
curl -X POST https://themachine.vernalcontentum.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass123"}'
```

---

## 🧹 Cache/CORS/Reset Procedures

### **When to Use**
- CORS errors persist after nginx config changes
- Database connection issues
- Service won't start or respond

### **System Reset Commands**
```bash
# Stop systemd service
sudo systemctl stop vernal-agents

# Kill any stuck processes
sudo pkill -f "python.*main.py"
sudo pkill -f "uvicorn"
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# Clear Python cache
find /home/ubuntu/vernal-agents-post-v0 -name "*.pyc" -delete
find /home/ubuntu/vernal-agents-post-v0 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Restart service
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents
```

### **Database Reset (If Needed)**
```bash
# Connect to database and reset tables
mysql -h 50.6.198.220 -u [username] -p[password] [database_name]
# Then run: DROP TABLE IF EXISTS users, otps; CREATE TABLE users (...);
```

### **Database Cleanup - Foreign Key Constraints**
- **Error:** "Cannot delete or update a parent row: a foreign key constraint fails"
- **Root Cause:** Foreign key constraints prevent deleting users with related records
- **Solution 1 - Proper Order:**
```sql
-- Delete related records first, then users
DELETE FROM otp WHERE user_id IN (14, 15, 16);
DELETE FROM campaigns WHERE user_id IN (14, 15, 16);
DELETE FROM platform_connection WHERE user_id IN (14, 15, 16);
DELETE FROM content WHERE user_id IN (14, 15, 16);
DELETE FROM state_tokens WHERE user_id IN (14, 15, 16);
DELETE FROM user WHERE id IN (14, 15, 16);
```
- **Solution 2 - Nuclear Option:**
```sql
-- Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;
DELETE FROM user WHERE id IN (14, 15, 16);
SET FOREIGN_KEY_CHECKS = 1;
```

---

## 🛡️ PRE-DEPLOYMENT CHECKS

### **Environment Variables Validation (CRITICAL - PREVENTS DATABASE WORMHOLE)**
- **Verify .env file exists** (`ls -la .env`)
- **Check for real database credentials** (`grep -E "DB_HOST|DB_USER|DB_PASSWORD|DB_NAME" .env`)
- **Validate NO default/placeholder values** (`grep -v "myuser\|localhost\|dummy\|mypassword" .env`)
- **Test environment loading** (`python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print('DB_HOST:', os.getenv('DB_HOST')); print('DB_USER:', os.getenv('DB_USER')); print('DB_NAME:', os.getenv('DB_NAME'))"`)
- **Verify database connectivity** (`python3 -c "from database import DatabaseManager; db = DatabaseManager(); print('✅ Database connection successful')"`)

### **Python/Backend Dependency Validation (CRITICAL)**
- **Test all critical imports** (`python3 -c "import main; print('✅ All imports successful')"`)
- **Verify no missing dependencies** (`python3 -c "from database import db_manager; print('✅ Database import successful')"`)
- **Check virtual environment** (`which python3` should show `/home/ubuntu/vernal-agents-post-v0/venv/bin/python3`)
- **Verify all packages installed** (`pip list | grep -E "fastapi|uvicorn|sqlalchemy|pymysql"`)

### **Standard Pre-Deployment Checks**
- Confirm repo is up-to-date and clean (`git status`)
- Verify Python version (`python3 --version`)
- Check virtual environment is activated (`which python`)
- Ensure `.env` file exists with all required variables
- Verify database connectivity (`curl -s http://127.0.0.1:8000/mcp/enhanced/health`)
- Check systemd service status (`sudo systemctl status vernal-agents`)
- **Test auth endpoints locally** (`curl -X POST http://127.0.0.1:8000/auth/login`)

---

## 🩺 POST-DEPLOYMENT HEALTHCHECKS
- Local and public health endpoints respond (200 OK)
- Database connectivity test passes
- CORS headers present in OPTIONS requests
- Auth endpoints work (signup, login, verify-email)
- No errors in systemd logs (`sudo journalctl -u vernal-agents -f`)
- **Test full auth flow:** Registration → Email verification → Login
- **Verify API endpoints:** `/health`, `/mcp/enhanced/health`, `/auth/*`

---

## 🔄 ROLLBACK PROCEDURE
```bash
git log --oneline -10  # Find last working commit
git reset --hard <last-working-commit-hash>
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart vernal-agents
curl -f http://localhost:8000/health || echo "Rollback failed - manual intervention needed"
```

---

## 📋 TROUBLESHOOTING MATRIX

| Error/Symptom           | Likely Cause         | Fix Command/Step |
|-------------------------|----------------------|------------------|
| 502 from nginx          | Service not running  | `sudo systemctl restart vernal-agents` |
| CORS errors             | nginx handling CORS  | Remove nginx CORS headers, let FastAPI handle |
| 422 on auth endpoints   | Invalid payload      | Check request format, required fields |
| 500 on auth endpoints   | Server error         | Check systemd logs, database connectivity |
| **Database connection failed** | **DB credentials/network** | **Check `.env`, test DB connectivity** |
| **Access denied for user 'myuser'** | **Wrong DB credentials** | **Fix .env with real credentials** |
| **ModuleNotFoundError: No module named 'browser_use'** | **Missing dependencies** | **pip install browser-use** |
| **SyntaxError: invalid syntax** | **Code syntax error** | **Check database.py line 928 for missing newline** |
| Email not sending       | SMTP configuration   | Check `.env` SMTP settings |
| Service won't start     | Port conflict        | Kill processes on port 8000 |
| **JWT creation error**  | **expires_delta param** | **Remove expires_delta from create_access_token** |
| **OTP verification fails** | **Missing DB table** | **Check otp table exists and accessible** |

---

## 🔧 ADDITIONAL TROUBLESHOOTING (Lessons Learned)

| Error/Symptom | Root Cause | Fix Command/Step |
|---------------|------------|------------------|
| **JWT "Invalid credentials"** | **String vs integer mismatch** | **Convert user_id to int: `int(user_id)`** |
| **JWT "Invalid credentials"** | **User not verified** | **Set `is_verified = 1` or complete OTP verification** |
| **Frontend 401 errors** | **Token expired/not stored** | **Log out and log back in, check user verification** |
| **Database delete fails** | **Foreign key constraints** | **Delete related records first, or disable FK checks** |

---

## 🚨 EMERGENCY RESET PROCEDURE

### **When Everything Goes Wrong**
```bash
# 1. Stop everything
sudo systemctl stop vernal-agents
sudo pkill -f "python.*main.py"
sudo pkill -f "uvicorn"
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# 2. Clear caches
find /home/ubuntu/vernal-agents-post-v0 -name "*.pyc" -delete
find /home/ubuntu/vernal-agents-post-v0 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 3. Verify nginx config
sudo nginx -t
sudo systemctl reload nginx

# 4. Rebuild from scratch
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart service
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents

# 6. Test everything
curl -I http://127.0.0.1:8000/health
curl -I https://themachine.vernalcontentum.com/health
curl -s https://themachine.vernalcontentum.com/mcp/enhanced/health | jq .
```

---

## Team Quick Start

1. **SSH to backend server:** `ssh ubuntu@18.235.104.132`
2. **Navigate to repo:** `cd /home/ubuntu/vernal-agents-post-v0`
3. **Pull latest code:** `git fetch origin && git switch main && git pull --ff-only origin main`
4. **Activate environment:** `source venv/bin/activate`
5. **Install dependencies:** `pip install -r requirements.txt`
6. **Restart service:** `sudo systemctl restart vernal-agents`
7. **Run health check:** `./full_health_check.sh` (see script below)
8. **Verify endpoints:** `curl -I https://themachine.vernalcontentum.com/health`

---

## 🖥️ Server and Repository Addresses

- **Back End Server**
  - Hostname/IP: `18.235.104.132`
  - Git repo: `https://github.com/studio-matt/vernal-agents-post-v0.git`
  - Reference as: "back end"

- **Front End Server**
  - Hostname/IP: `98.87.57.133`
  - Git repo: `https://github.com/studio-matt/vernal-post-v0.git`
  - Reference as: "front end"

---

## 🚨 CRITICAL: Environment Restoration (PREVENTS DATABASE WORMHOLE)

### **MANDATORY First Steps After Git Clone**
```bash
# 1. Navigate to backend directory
cd /home/ubuntu/vernal-agents-post-v0

# 2. VERIFY .env file exists (CRITICAL)
ls -la .env
# If missing: STOP - DO NOT PROCEED

# 3. CHECK for real database credentials (CRITICAL)
grep -E "DB_HOST|DB_USER|DB_PASSWORD|DB_NAME" .env
# Must show: DB_HOST=50.6.198.220, DB_USER=vernalcontentum_vernaluse, etc.
# If shows: myuser, localhost, dummy, mypassword - STOP - DO NOT PROCEED

# 4. VALIDATE no placeholder values (CRITICAL)
grep -v "myuser\|localhost\|dummy\|mypassword" .env
# Should show only real credentials

# 5. TEST environment loading (CRITICAL)
python3 -c "
from dotenv import load_dotenv
load_dotenv()
import os
print('DB_HOST:', os.getenv('DB_HOST'))
print('DB_USER:', os.getenv('DB_USER'))
print('DB_NAME:', os.getenv('DB_NAME'))
"
# Must show real values, not None or placeholders

# 6. TEST database connection (CRITICAL)
python3 -c "
from database import DatabaseManager
db = DatabaseManager()
print('✅ Database connection successful')
"
# Must succeed without errors
```

### **Why This Prevents the Wormhole**
- **Forces env restoration** as the FIRST steps after git clone
- **Requires explicit checking** for real DB credentials before any build or run
- **App will fail-fast** with a clear error if env is missing or defaults are used
- **No fallback to 'myuser'** or 'localhost' is possible
- **Ensures .env is actually loaded**, even under systemd or PM2

**See also:** [Vernal Machine Frontend — Emergency Net (v3)](../frontend/docs/EMERGENCY_NET.md)

---

## 🔬 Full System Health Check Script

### **Complete Integration Test**
```bash
#!/bin/bash
# full_health_check.sh - Comprehensive backend health check

echo "🔍 Starting Full System Health Check..."

# 1. Service Status
echo "📋 Checking systemd service..."
sudo systemctl is-active vernal-agents || { echo "❌ Service not active"; exit 1; }
echo "✅ Service is active"

# 2. Local Health Endpoints
echo "📋 Testing local health endpoints..."
curl -f http://127.0.0.1:8000/health || { echo "❌ Local health failed"; exit 1; }
curl -f http://127.0.0.1:8000/mcp/enhanced/health || { echo "❌ Database health failed"; exit 1; }
echo "✅ Local endpoints working"

# 3. Public Health Endpoints
echo "📋 Testing public health endpoints..."
curl -f https://themachine.vernalcontentum.com/health || { echo "❌ Public health failed"; exit 1; }
curl -f https://themachine.vernalcontentum.com/mcp/enhanced/health || { echo "❌ Public database health failed"; exit 1; }
echo "✅ Public endpoints working"

# 4. CORS Testing
echo "📋 Testing CORS headers..."
CORS_RESPONSE=$(curl -i -X OPTIONS https://themachine.vernalcontentum.com/auth/signup 2>/dev/null)
echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Headers" || { echo "❌ CORS headers missing"; exit 1; }
echo "✅ CORS headers present"

# 5. Auth Flow Testing
echo "📋 Testing auth flow..."
# Test signup
SIGNUP_RESPONSE=$(curl -s -X POST https://themachine.vernalcontentum.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","name":"Test User"}')
echo "$SIGNUP_RESPONSE" | grep -q "successfully" || { echo "❌ Signup failed"; exit 1; }
echo "✅ Signup working"

# Test login
LOGIN_RESPONSE=$(curl -s -X POST https://themachine.vernalcontentum.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}')
echo "$LOGIN_RESPONSE" | grep -q "token" || { echo "❌ Login failed"; exit 1; }
echo "✅ Login working"

# 6. Database Connectivity
echo "📋 Testing database connectivity..."
DB_RESPONSE=$(curl -s https://themachine.vernalcontentum.com/mcp/enhanced/health)
echo "$DB_RESPONSE" | jq -e '.database_connected' || { echo "❌ Database not connected"; exit 1; }
echo "✅ Database connected"

# 7. Service Logs Check
echo "📋 Checking service logs for errors..."
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "5 minutes ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT errors in logs (check manually)"
else
    echo "✅ No recent errors in logs"
fi

echo "🎉 Full System Health Check PASSED!"
```

**💡 Save this script:** Copy the script above and save as `/home/ubuntu/vernal-agents-post-v0/full_health_check.sh`, then make it executable with `chmod +x full_health_check.sh`

---

## 📊 API Integration Matrix

| Endpoint | Method | Payload | Expected Response | Notes |
|----------|--------|---------|-------------------|-------|
| `/health` | GET | None | `{"ok":true,"version":"2.0.0","status":"debug"}` | Service health check |
| `/mcp/enhanced/health` | GET | None | `{"database_connected":true}` | Database connectivity |
| `/auth/signup` | POST | `{"username":"user@example.com","email":"user@example.com","password":"pass123","name":"User"}` | `{"message":"User created successfully"}` | User registration |
| `/auth/login` | POST | `{"username":"user@example.com","password":"pass123"}` | `{"token":"jwt_token_here"}` | User authentication |
| `/auth/verify-email` | POST | `{"email":"user@example.com","otp_code":"123456"}` | `{"message":"Email verified successfully"}` | OTP verification |
| `/auth/reset-password` | POST | `{"email":"user@example.com"}` | `{"message":"Reset email sent"}` | Password reset |
| `/campaigns` | GET | None | `{"status":"success","campaigns":[...]}` | Get user campaigns |
| `/campaigns` | POST | `{"name":"Campaign","description":"...","keywords":["tag1"]}` | `{"status":"success","message":{...}}` | Create campaign |
| `/campaigns/{id}` | GET | None | `{"status":"success","campaign":{...}}` | Get specific campaign |

### **CORS Headers Required**
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: content-type, authorization, accept, ngrok-skip-browser-warning`

---

## 🔐 Security, Performance & Maintenance
- **Environment:** Never expose secrets in logs or responses
- **Database:** Regular backups of MySQL database
- **Monitoring:** Use systemd logs for troubleshooting (`sudo journalctl -u vernal-agents -f`)
- **Clean:** Regularly clear Python cache files
- **Audit:** Review auth logs for suspicious activity

---

## ☑️ FINAL CHECKLIST
- [ ] App code and dependencies up-to-date
- [ ] `.env` present and secure
- [ ] Database connectivity verified
- [ ] Systemd service running, port 8000 open
- [ ] Health endpoints return correct data
- [ ] CORS headers present in OPTIONS requests
- [ ] Auth flow tested: signup → verify → login
- [ ] No lingering processes or port conflicts
- [ ] Rollback steps documented and tested
- [ ] **JWT token creation working correctly**
- [ ] **Email service configured and tested**
- [ ] **Database tables exist and accessible**

---

## 🚨 CRITICAL ARCHITECTURE REQUIREMENTS

### **100% Database Dependency**
- **ALL persistent data MUST be stored in MySQL database**
- **NO IN-MEMORY STORAGE:** Never use Python dictionaries, lists, or variables for persistent data
- **MULTI-TENANT ARCHITECTURE:** All data MUST be scoped to user accounts
- **PRODUCTION-READY:** No "temporary" or "mock" solutions

### **Authentication System**
- **ONLY USE:** `auth_api.py` (database-backed authentication)
- **NEVER USE:** `auth_ultra_minimal.py` (in-memory storage)
- **USER STORAGE:** MySQL `user` table only
- **OTP STORAGE:** MySQL `otp` table only
- **SESSIONS:** JWT tokens with database user validation

### **Forbidden Patterns**
- ❌ `users_db = {}` (in-memory dictionaries)
- ❌ `global_variable = []` (in-memory lists)
- ❌ Mock/temporary authentication systems
- ❌ Any data storage outside the database

---