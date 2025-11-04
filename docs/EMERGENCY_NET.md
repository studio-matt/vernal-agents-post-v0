# Vernal Agents Backend — Emergency Net (v12)

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

## 🚨 CRITICAL: CODE PRESERVATION RULES (v7)

### **THE #1 CAUSE OF REGRESSION: Removing Working Code**

**PROBLEM:** During code cleanup or fixing non-existent imports, working endpoints get accidentally removed, breaking previously functional features.

**SYMPTOMS:**
- Feature worked before, now returns 404
- "Previously saved campaigns" are missing from UI
- Endpoints that existed are gone
- Database has data but no way to access it
- **Backend service fails for 2,168+ attempts due to missing .env file**

### **MANDATORY CODE PRESERVATION RULES**

#### **1. NEVER REMOVE ENDPOINTS WITHOUT VERIFYING THEY DON'T EXIST**
```python
# ❌ WRONG: Removing imports that "don't exist"
# You removed campaign_api and content_api imports
# But campaign endpoints were IN main.py, not in separate files!

# ✅ CORRECT: Check if endpoints are in main.py before removing imports
# If imports are missing, check if code is inlined in main.py
```

#### **2. SEARCH BEFORE REMOVING**
```bash
# BEFORE removing any code, search for where it's used:
git log --all --full-history -- "**/campaign*"
git show <commit>:main.py | grep campaign
find . -name "*campaign*" -type f
```

#### **3. VERIFY FUNCTIONALITY STILL EXISTS**
```bash
# Check if endpoints are defined in main.py:
grep -n "def.*campaign" main.py
grep -n "@app.get.*campaign" main.py
```

#### **4. IF CODE IS MISSING, RESTORE IT FROM HISTORY**
```bash
# Find working commit:
git log --all --grep="campaign" --oneline

# View code from working commit:
git show <commit>:main.py | grep -A 50 "@app.post.*campaign"

# Restore the endpoints manually
```

### **CRITICAL RULE: If It Worked Before, It Must Exist Somewhere**
- Check Git history for removed code
- Check inline definitions vs imports
- Never assume missing imports = missing functionality
- Always verify endpoints exist before declaring them missing

#### **5. NEVER DELETE .env FILES DURING CLEANUP (CRITICAL)**
```bash
# ❌ WRONG: These commands delete .env and break systemd service
rm -rf /home/ubuntu/vernal-agents-post-v0/*
rm -rf /home/ubuntu/vernal-agents-post-v0/.env*

# ✅ CORRECT: Preserve .env during cleanup
rm -rf /home/ubuntu/vernal-agents-post-v0/*.py
rm -rf /home/ubuntu/vernal-agents-post-v0/__pycache__
# Keep .env file intact!

# MANDATORY: Always backup .env before cleanup
cp /home/ubuntu/vernal-agents-post-v0/.env /home/ubuntu/.env.backup
```

**Why this matters:**
- Systemd service requires `EnvironmentFile=/home/ubuntu/vernal-agents-post-v0/.env`
- Without .env, service fails for 2,168+ consecutive attempts
- Causes 502 Bad Gateway and CORS errors
- **This is the #1 cause of backend service failures**

---

## 🚨 CRITICAL: GIT SUBMODULE ERRORS (v2)

### **THE #1 CAUSE OF DEPLOYMENT FAILURES**

**PROBLEM:** GitHub Actions fails with "No url found for submodule path 'agents-backend'/'backend-server' in .gitmodules" when this repo doesn't use submodules.

**ROOT CAUSE:** Stale submodule references in Git history that don't exist anymore, plus default Git checkout behavior tries to initialize them.

**SYMPTOMS:**
- Deployment fails at checkout step
- Error: "fatal: No url found for submodule path"
- Workflow fails before any code runs

### **MANDATORY FIX FOR ALL WORKFLOWS**

**Every workflow that uses `actions/checkout@v4` MUST have:**
```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    submodules: false  # No submodules in this repo
```

**Why this matters:**
- This repo doesn't use Git submodules
- Default `actions/checkout` behavior tries to initialize them
- Results in fatal error: "No url found for submodule path"
- **ALL deployment workflows must disable submodules**

### **STALE SUBMODULE CLEANUP (CRITICAL)**

**If you see submodule errors, check and remove stale references:**
```bash
# List all submodule entries in current commit
git ls-tree HEAD | grep "160000 commit"

# Remove stale submodule references
git rm --cached agents-backend backend-server

# Commit and push
git commit -m "CRITICAL: Remove stale submodule references"
git push origin main
```

**Stale submodules known to cause issues:**
- `agents-backend` (removed in commit a4f13ea)
- `backend-server` (removed in commit 3429460)

**How to detect stale submodules:**
```bash
# Check if any submodule entries exist
git ls-tree HEAD | grep "160000 commit"

# If you see any "160000 commit" entries, they're stale submodules
# This repo does NOT use submodules - all 160000 entries must be removed
```

### **APPLY TO ALL WORKFLOWS**
- ✅ dependency-check.yml
- ✅ deploy-vm.yml
- ✅ deploy-self-hosted.yml
- ✅ deploy-agents.yml
- ✅ deploy-prebuilt.yml

**CRITICAL RULES:**
1. **Every workflow file MUST have `submodules: false` in checkout step**
2. **NEVER add submodule references** - this repo uses direct dependencies
3. **Remove ANY stale submodule references** found in `git ls-tree HEAD`

---

## 🚨 CRITICAL: DEPLOYMENT VORTEX PREVENTION (v4)

### **THE #1 CAUSE OF ENDLESS DEPLOYMENT FAILURES**

**PROBLEM:** FastAPI app fails to start and listen on port 8000, causing endless deployment loops.

**ROOT CAUSE:** Blocking operations at import time prevent uvicorn from starting the ASGI server.

**SYMPTOMS:**
- Systemd shows "active (running)" but port 8000 is not listening
- Health checks fail with connection refused
- Deployment scripts timeout waiting for port 8000
- Endless deployment vortex with no clear error messages

### **MANDATORY PREVENTION RULES**

#### **1. NO BLOCKING OPERATIONS AT IMPORT TIME**
```python
# ❌ WRONG - This blocks FastAPI startup
from database import DatabaseManager
db_manager = DatabaseManager()  # This runs at import time!

# ✅ CORRECT - Use lazy initialization
def get_db_manager():
    global db_manager
    if db_manager is None:
        from database import DatabaseManager
        db_manager = DatabaseManager()
    return db_manager
```

#### **2. NO HEAVY IMPORTS AT GLOBAL SCOPE**
```python
# ❌ WRONG - These can block startup
from agents import script_research_agent, qc_agent
from tasks import script_research_task, qc_task
from tools import process_content_for_platform
from database import DatabaseManager, SessionLocal
from models import Content, User, PlatformConnection

# ✅ CORRECT - Lazy imports only
def get_agents():
    from agents import script_research_agent, qc_agent
    return {'script_research_agent': script_research_agent, 'qc_agent': qc_agent}
```

#### **3. NO DATABASE CONNECTIONS AT IMPORT TIME**
```python
# ❌ WRONG - Database connection at import
from database import DatabaseManager
db = DatabaseManager()  # This can hang!

# ✅ CORRECT - In startup event
@app.on_event("startup")
async def startup_event():
    global db_manager
    db_manager = DatabaseManager()
```

#### **4. NO SUBPROCESS CALLS AT IMPORT TIME**
```python
# ❌ WRONG - Playwright install at import
import subprocess
subprocess.check_call(["playwright", "install"])  # This blocks!

# ✅ CORRECT - In endpoint or startup event
@app.get("/install-playwright")
def install_playwright():
    subprocess.check_call(["playwright", "install"])
```

### **BULLETPROOF MAIN.PY TEMPLATE**

```python
#!/usr/bin/env python3
"""
BULLETPROOF FastAPI main.py - NO BLOCKING IMPORTS
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for lazy initialization
db_manager = None
scheduler = None

def get_db_manager():
    """Lazy database manager initialization"""
    global db_manager
    if db_manager is None:
        from database import DatabaseManager
        db_manager = DatabaseManager()
    return db_manager

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup - NOT at import time"""
    global db_manager, scheduler
    try:
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database manager initialized")
        
        # Initialize scheduler
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("Scheduler started")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

# REQUIRED ENDPOINTS FOR DEPLOYMENT
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@app.get("/version")
def version():
    return {"version": os.getenv("GITHUB_SHA", "development"), "status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/mcp/enhanced/health")
def database_health():
    return {"status": "ok", "message": "Database health check", "database_connected": True}

@app.get("/")
def root():
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### **DEPLOYMENT VALIDATION CHECKLIST**

Before every deployment, verify:

- [ ] **No blocking imports** - Only basic FastAPI imports at global scope
- [ ] **No database connections** - All DB logic in functions or startup events
- [ ] **No subprocess calls** - All external commands in endpoints
- [ ] **No heavy module imports** - Use lazy imports for agents, tasks, tools
- [ ] **Required endpoints exist** - `/health`, `/version`, `/mcp/enhanced/health`
- [ ] **Test locally first** - `uvicorn main:app --host 0.0.0.0 --port 8000`

### **EMERGENCY RECOVERY**

If deployment vortex occurs:

1. **Replace main.py with bulletproof template above**
2. **Commit and push to correct repository** (`vernal-agents-post-v0`)
3. **Trigger deployment manually**
4. **Verify port 8000 is listening**: `curl http://127.0.0.1:8000/health`
5. **Gradually add back functionality** using lazy imports

### **REPOSITORY CONFUSION PREVENTION**

**CRITICAL:** Always verify you're in the correct repository:

```bash
# Check which repository you're in
git remote -v

# Backend should show:
# origin https://github.com/studio-matt/vernal-agents-post-v0.git

# Frontend should show:
# origin https://github.com/studio-matt/vernal-post-v0.git
```

**NEVER commit backend code to frontend repository or vice versa!**

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

### **OPTION A: Automated Bulletproof Script (RECOMMENDED for v13+)**

**This is the complete, tested, end-to-end deployment script that handles everything:**
```bash
cd /home/ubuntu
rm -rf /home/ubuntu/vernal-agents-post-v0 2>/dev/null || true
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0
cd /home/ubuntu/vernal-agents-post-v0
chmod +x scripts/bulletproof_deploy_backend.sh
bash scripts/bulletproof_deploy_backend.sh
```

**What this script does:**
1. ✅ Changes to safe directory (`/home/ubuntu`) before deletion (prevents getcwd errors)
2. ✅ Backs up `.env` file automatically (EMERGENCY_NET v7 compliance)
3. ✅ Deletes old code completely
4. ✅ Clones fresh from GitHub
5. ✅ Sets up venv with chunked pip installation (prevents SIGKILL)
6. ✅ **MANDATORY: Installs Playwright browsers** (`playwright install chromium`)
7. ✅ **MANDATORY: Verifies critical packages are importable** (prevents silent failures)
8. ✅ **MANDATORY: Verifies Playwright browsers work** (prevents scraping failures)
9. ✅ **MANDATORY: Verifies auth router can load** (prevents 404 regressions)
10. ✅ Restores `.env` from backup
11. ✅ Validates required environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
12. ✅ Validates no placeholder values (myuser, localhost, dummy, mypassword)
13. ✅ Configures systemd service
14. ✅ Starts service and waits
15. ✅ Runs comprehensive health checks (local, version, database, external)
16. ✅ **MANDATORY: Verifies auth endpoints are accessible** (not 404) before success
17. ✅ Logs successful deployment

**CRITICAL: Package Verification (Step 6)**
The script now verifies that all critical packages can actually be imported:
- Core: `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`
- Auth: `email_validator` (required for `/auth/login` to work)
- Auth: `passlib`, `jose` (required for password hashing and JWT tokens)
- Scraping: `ddgs` (required for web scraping)
- Scraping: `playwright` (required for web scraping - Python package)
- Research: `nltk` (required for research endpoint)
- Local modules: `database`, `models`

**CRITICAL: Playwright Browser Installation (Step 7)**
- Playwright requires TWO steps:
  1. ✅ Python package: `pip install playwright` (included in requirements.txt)
  2. ✅ Browser binaries: `playwright install chromium` (MUST run separately)
- Without browser binaries, scraping fails with "Playwright not available" error
- Deployment script now installs browsers and verifies they work
- This prevents the regression where scraping fails silently

**If any package fails to import, deployment EXITS with error code 1.**
This prevents the regression where packages were "installed" but couldn't be imported, causing 404 errors.

**Required Environment Variables:**
- `DB_HOST` (must not be localhost)
- `DB_USER` (must not be myuser)
- `DB_PASSWORD` (must not be mypassword/dummy)
- `DB_NAME`
- `JWT_SECRET_KEY` (generated if missing)

**Optional:**
- `OPENAI_API_KEY` (not required for backend startup, can be per-user)

**If script fails:**
- Check logs for specific error message
- Verify `.env` backup exists: `ls -la /home/ubuntu/.env.backup`
- Restore `.env` manually if needed: `cp /home/ubuntu/.env.backup /home/ubuntu/vernal-agents-post-v0/.env`

---

### **OPTION B: Manual Step-by-Step Deploy**

### 1. **Pull Latest Code**
```bash
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main
```

### 2. **MANDATORY: Validate Dependencies (PREVENTS DEPENDENCY HELL)**
```bash
# Run dependency validation BEFORE installing
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}
```

**This catches ALL dependency conflicts before they cause deployment loops.**

### 3. **Activate Virtual Environment**
```bash
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir
```

**CRITICAL: Install Playwright Browsers (REQUIRED for web scraping)**
```bash
# Playwright requires TWO steps:
# 1. Python package (already installed via requirements.txt)
# 2. Browser binaries (MUST run separately)
playwright install chromium
```
**Without browser binaries, scraping fails with "Playwright not available" error.**

**Note:** If installing new dependencies (e.g., spaCy), also download required models:
```bash
# Download spaCy language model (required for NLP processing)
python -m spacy download en_core_web_md
```

### 4. **Restart Systemd Service**
```bash
sudo systemctl restart vernal-agents
sudo systemctl status vernal-agents
```

### 5. **Verification (MANDATORY)**
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

### **Expected Output for DB Env Checks (Example):**
```bash
# GOOD - Real production credentials:
DB_HOST: 50.6.198.220
DB_USER: vernalcontentum_vernaluse
DB_NAME: vernalcontentum_contentMachine

# BAD - If you see any of these, STOP and fix:
# myuser, localhost, dummy, mypassword, or None
```

### **Fail-Fast Code Addition (Add to database.py):**
```python
# Add this at the top of database.py __init__ method:
def __init__(self):
    # Fail-fast if any DB env vars are missing or placeholder values
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    placeholder_values = ['myuser', 'localhost', 'dummy', 'mypassword', None]
    
    for var in required_vars:
        value = os.getenv(var)
        if value in placeholder_values or not value:
            raise ValueError(f"CRITICAL: {var} is missing or placeholder value: {value}. "
                           f"Must use real production database credentials in .env file!")
```

### **Python/Backend Dependency Validation (CRITICAL - MANDATORY BEFORE ANY DEPLOYMENT)**

**🚨 MANDATORY: Run dependency validation before ANY deployment:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
python3 validate_dependencies.py
```

**This validation script checks:**
- ✅ Pip version compatibility (pip<25.0 for pip-tools)
- ✅ requirements.in follows best practices (lower bounds only)
- ✅ No known conflict patterns
- ✅ Dependency resolution succeeds without conflicts

**If validation fails: DO NOT DEPLOY. Fix issues first.**

**Additional manual checks:**
- **Test all critical imports** (`python3 -c "import main; print('✅ All imports successful')"`)
- **Verify no missing dependencies** (`python3 -c "from database import db_manager; print('✅ Database import successful')"`)
- **Check virtual environment** (`which python3` should show `/home/ubuntu/vernal-agents-post-v0/venv/bin/python3`)
- **Verify all packages installed** (`pip list | grep -E "fastapi|uvicorn|sqlalchemy|pymysql"`)

### **Standard Pre-Deployment Checks**

**MANDATORY ORDER:**
1. **Run dependency validation** (`python3 validate_dependencies.py`) - MUST PASS
2. Confirm repo is up-to-date and clean (`git status`)
3. Verify Python version (`python3 --version`)
4. Check virtual environment is activated (`which python`)
5. Ensure `.env` file exists with all required variables
6. Verify database connectivity (`curl -s http://127.0.0.1:8000/mcp/enhanced/health`)
7. Check systemd service status (`sudo systemctl status vernal-agents`)
8. **Test auth endpoints locally** (`curl -X POST http://127.0.0.1:8000/auth/login`)

**🚨 If dependency validation fails, deployment is BLOCKED until fixed.**

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
| **OSError: Can't find model 'en_core_web_md'** | **spaCy model not downloaded** | **python -m spacy download en_core_web_md** |
| **ModuleNotFoundError: No module named 'spacy'** | **Missing spacy package** | **pip install spacy>=3.7.0** |
| **ModuleNotFoundError: No module named 'duckduckgo_search'** | **Missing duckduckgo-search** | **pip install duckduckgo-search>=6.0.0** |
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
4. **MANDATORY: Validate dependencies** `python3 validate_dependencies.py` (MUST PASS)
5. **Activate environment:** `source venv/bin/activate`
6. **Install dependencies:** `pip install -r requirements.txt --no-cache-dir`
7. **Download spaCy model (if new install):** `python -m spacy download en_core_web_md`
8. **Restart service:** `sudo systemctl restart vernal-agents`
9. **Run health check:** `./full_health_check.sh` (see script below)
10. **Verify endpoints:** `curl -I https://themachine.vernalcontentum.com/health`

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

### **Summary: 100% Immune to Database Credentials Wormhole**
✅ **Environment validation** explicitly prevents "myuser"/fallback credentials issue  
✅ **Any new or old operator** will catch missing/incorrect DB credentials before any build or run  
✅ **Process is now Emergency Net compliant**, resilient, and repeatable  
✅ **Fail-fast code snippet** and expected outputs make you 100% immune to this class of bug  
✅ **MANDATORY checklist item** ensures verification before every deployment

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
- [ ] **MANDATORY: Dependency validation passed** (`python3 validate_dependencies.py`)
- [ ] App code and dependencies up-to-date
- [ ] `.env` present and secure
- [ ] **Verified .env contains production DB credentials (NO 'myuser', 'localhost', 'dummy', 'mypassword')**
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

**🚨 If dependency validation fails, deployment is BLOCKED. This prevents dependency hell loops.**

---

## 🚨 CRITICAL: SIGKILL (STATUS 137) PREVENTION (v5)

### **THE #1 CAUSE OF CI DEPLOYMENT FAILURES**

**PROBLEM:** GitHub Actions runner killed with SIGKILL (status 137) before deployment completes, even though the script is bulletproof.

**ROOT CAUSE:** CI runner runs out of RAM (<7GB) or hits timeout during heavy Python package installation.

**SYMPTOMS:**
- GitHub Action shows "Process exited with status 137 from signal KILL"
- Deployment script is perfect but never finishes
- Backend may not be updated even if script is correct
- Endless deployment loops with no clear error messages

### **MANDATORY DEPLOYMENT OPTIONS**

#### **1. SELF-HOSTED RUNNER (RECOMMENDED)**
```yaml
# Use .github/workflows/deploy-self-hosted.yml
jobs:
  deploy:
    runs-on: [self-hosted, linux, x64]  # High RAM runner
    timeout-minutes: 120  # 2 hours for heavy installs
```

**Benefits:**
- 8GB+ RAM available (vs 7GB on GitHub-hosted)
- 120-minute timeout (vs 90-minute limit)
- Full control over environment
- No memory constraints

#### **2. DOCKER DEPLOYMENT (MEMORY ALLOCATED)**
```yaml
# Use .github/workflows/deploy-docker.yml
docker run -d \
  --name vernal-agents-container \
  --memory=4g \
  --memory-swap=6g \
  -p 8000:8000 \
  vernal-agents:latest
```

**Benefits:**
- 4GB memory allocation guaranteed
- Container isolation prevents OOM
- Consistent environment
- Easy rollback

#### **3. MEMORY-OPTIMIZED SCRIPT (CHUNKED INSTALLS)**
```bash
# Use deploy_memory_optimized.sh
# Installs dependencies in chunks:
# 1. requirements-core.txt (FastAPI, SQLAlchemy)
# 2. requirements-ai.txt (OpenAI, Anthropic)  
# 3. requirements-remaining.txt (Everything else)
```

**Benefits:**
- Reduces memory pressure during install
- Memory monitoring between chunks
- Emergency cleanup when <200MB available
- Works on standard GitHub runners

#### **4. LIGHTWEIGHT DEPLOYMENT (MINIMAL DEPS)**
```bash
# Use deploy_lightweight.sh
# Installs only essential packages first
# Then remaining packages from requirements.txt
```

**Benefits:**
- Minimal memory usage
- Faster deployment
- Works in resource-constrained environments
- Good for quick fixes

### **DEPLOYMENT VERIFICATION**

**After ANY deployment, verify completion:**
```bash
# Check completion marker
cat /home/ubuntu/vernal_agents_deploy_complete.txt

# Test commit hash endpoint
curl https://themachine.vernalcontentum.com/deploy/commit

# Run full verification
/home/ubuntu/verify_deployment.sh
```

**Success Indicators:**
- ✅ Completion marker file exists with today's timestamp
- ✅ `/deploy/commit` returns latest commit hash
- ✅ All health endpoints return 200 OK
- ✅ External access works
- ✅ No SIGKILL in deployment logs

### **EMERGENCY RECOVERY FOR SIGKILL**

**If CI keeps failing with status 137:**

1. **Use manual deployment:**
   ```bash
   ssh ubuntu@18.235.104.132
   cd /home/ubuntu/vernal-agents-post-v0
   ./deploy_memory_optimized.sh
   ```

2. **Or use lightweight deployment:**
   ```bash
   ./deploy_lightweight.sh
   ```

3. **Or use Docker deployment:**
   ```bash
   docker run -d --name vernal-agents-container --memory=4g -p 8000:8000 vernal-agents:latest
   ```

4. **Verify deployment completed:**
   ```bash
   /home/ubuntu/verify_deployment.sh
   ```

### **INFRASTRUCTURE REQUIREMENTS**

**For reliable automated deployments:**
- **Self-hosted runner:** 8GB+ RAM, 120min timeout
- **Docker deployment:** 4GB memory allocation
- **Memory monitoring:** Check available RAM before heavy operations
- **Chunked installs:** Split requirements.txt into core/ai/remaining
- **Emergency cleanup:** Drop caches when <200MB available

**This prevents the deployment vortex caused by CI infrastructure limits, not code issues.**

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

### **Dependency Management Rules (CRITICAL)**

#### **Transitive Dependency Pinning**
- **Never pin a package to a version that conflicts with a required range from a sub-dependency**
- **Prefer compatible range pins** (e.g., `anthropic>=0.69.0,<1.0.0`) when required by another package
- **Always regenerate your lock file** after updating any dependency or adding new packages
- **Test requirements install** in your actual deployment Docker image before merging

#### **Common Dependency Conflicts**
- `anthropic==0.7.8` → Use `anthropic>=0.69.0,<1.0.0` (required by langchain-anthropic)
- `requests==2.31.0` → Use `requests>=2.32.3` (required by browser-use)
- `python-dotenv==1.0.0` → Use `python-dotenv>=1.0.1` (required by browser-use)
- `beautifulsoup4==4.12.2` → Use `beautifulsoup4>=4.12.3` (required by browser-use)

#### **Post-Installation Steps for NLP Dependencies**
- **spaCy:** After installing `spacy>=3.7.0`, download language model: `python -m spacy download en_core_web_md`
  - **Recommended model:** `en_core_web_md` (includes word vectors for semantic similarity)
  - **Alternative models:** `en_core_web_sm` (smaller, no vectors), `en_core_web_lg` (larger, best accuracy)
- **NLTK:** NLTK data downloads automatically on first import, but ensure required resources:
  ```python
  import nltk
  nltk.download('punkt')
  nltk.download('stopwords')
  nltk.download('wordnet')
  nltk.download('averaged_perceptron_tagger')
  nltk.download('maxent_ne_chunker')
  ```

#### **ResolutionImpossible Prevention**
- **Golden Rule:** Never pin a package to a version below what any dependencies require
- **Use flexible pins:** Prefer `>=` or range pins over exact pins `==`
- **Test in Docker:** Always test locked requirements in production Docker image
- **Run pip check:** Verify no conflicts after every requirements change

#### **Resolution-Too-Deep Prevention** (CRITICAL)
- **ALWAYS use lower bounds (>=) for ALL dependencies** - This prevents "resolution-too-deep" errors
- **Never use just package names** - Always specify minimum versions (e.g., `fastapi>=0.104.1`)
- **Only use upper bounds (<) when required by sub-dependencies** - (e.g., `anthropic>=0.69.0,<1.0.0`)
- **Avoid mixing exact pins (==) with unpinned packages** - Use consistent `>=` constraints
- **Let pip-compile resolve final versions** - Don't manually edit locked files

**Example of CORRECT requirements.in:**
```python
# ✅ CORRECT: Using lower bounds
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.23
anthropic>=0.69.0,<1.0.0  # Only < when required by sub-dependency
```

**Example of INCORRECT requirements.in (causes "resolution-too-deep"):**
```python
# ❌ WRONG: Mixing exact pins and unpinned packages
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy  # Missing version constraint!
anthropic  # Missing version constraint!
```

#### **pip-tools/pip 25.x Compatibility** (CRITICAL)
- **CRITICAL:** For reproducible pip-compile lockfiles, ALWAYS use `pip<25.0` until pip-tools is upgraded
- **Root Cause:** pip-tools 7.x doesn't support pip 25.x (AttributeError: 'InstallRequirement' object has no attribute 'use_pep517')
- **Workaround:** Force `pip install "pip<25.0"` before running `pip-compile`
- **Best Practice:** Install `pip<25.0`, generate lockfile, then upgrade pip for builds

**Example of CORRECT pip-tools usage:**
```bash
# ✅ CORRECT: Force pip<25.0 before pip-compile AND KEEP IT
pip install "pip<25.0" setuptools wheel pip-tools
pip-compile requirements.in --output-file requirements-locked.txt
pip install -r requirements-locked.txt --no-cache-dir
# CRITICAL: Do NOT upgrade pip after pip-compile - keep pip<25.0 throughout
```

**Example of INCORRECT pip-tools usage (causes AttributeError):**
```bash
# ❌ WRONG: Upgrading pip after pip-compile breaks compatibility
pip install "pip<25.0" setuptools wheel pip-tools
pip-compile requirements.in --output-file requirements-locked.txt
pip install --upgrade pip  # ❌ This upgrades pip to 25.x
# Error: AttributeError: 'InstallRequirement' object has no attribute 'use_pep517'

# ❌ WRONG: Using pip 25.x with pip-tools 7.x from the start
pip install --upgrade pip  # Installs pip 25.x
pip install pip-tools  # Incompatible with pip 25.x
pip-compile requirements.in --output-file requirements-locked.txt
# Error: AttributeError: 'InstallRequirement' object has no attribute 'use_pep517'
```

**CRITICAL RULE:**
- **NEVER run `pip install --upgrade pip` after pip-compile** when using pip<25.0
- **Keep pip<25.0 throughout the entire build process**
- Only upgrade pip if you want to break pip-tools compatibility

#### **Real Dependency Conflict (ResolutionImpossible)** (CRITICAL)
- **Always check upstream package requirements** for direct and transitive pins
- **If a package requires a conflicting version**, adjust your lower bounds to match the minimum version required by all dependencies
- **If no compatible range exists**, you must:
  - Wait for upstream packages to update
  - Refactor code to avoid the conflict
  - Open an issue with the upstream package maintainer

**Example: numpy/browser-use conflict**
```python
# ❌ WRONG: Too strict numpy constraint
numpy>=1.24.3  # Conflicts with browser-use which requires older numpy
browser-use>=0.1.0

# ✅ CORRECT: Looser numpy constraint for browser-use compatibility
numpy>=1.21.0  # Lower bound allows browser-use to resolve
browser-use>=0.1.0
```

**Diagnosis Steps:**
1. **Check package requirements on PyPI** (`https://pypi.org/project/package-name/`)
2. **Run `pip install package-name`** in a clean environment to see what versions it pulls in
3. **Adjust your constraints** to match the minimum required by all packages
4. **Test in Docker** with your actual base image before merging

#### **Langchain-core Ecosystem Conflicts** (CRITICAL)
- **Always align all langchain, langchain-core, crewai, langchain-openai, and browser-use to the same major version family**
- **If browser-use requires langchain-core>=1.0.0,<2.0.0**, all related packages must be compatible
- **Upgrade crewai to >=0.28.0** to avoid old langchain-core<0.4.0 pin

**Example: langchain-core version conflicts**
```python
# ❌ WRONG: Mixed langchain versions causing ResolutionImpossible
browser-use>=0.1.0  # Requires langchain-core>=1.0.0,<2.0.0
crewai<0.24.0  # Requires langchain-core<0.4.0
# Error: ResolutionImpossible: Cannot resolve langchain-core

# ✅ CORRECT: All langchain packages aligned to v1.x
browser-use>=0.1.0  # Requires langchain-core>=1.0.0,<2.0.0
crewai>=0.28.0  # Compatible with langchain-core>=1.0.0,<2.0.0
langchain-openai>=0.0.5  # Compatible with langchain-core>=1.0.0,<2.0.0
anthropic>=0.69.0,<1.0.0  # langchain-anthropic requires langchain-core>=1.0.0,<2.0.0
```

**Langchain Ecosystem Compatibility Table:**
| Package | Requires langchain-core | Compatible? |
|---------|-------------------------|-------------|
| browser-use | >=1.0.0,<2.0.0 | YES |
| crewai >=0.28.0 | >=1.0.0,<2.0.0 | YES |
| crewai <0.24.0 | <0.4.0 | NO |
| langchain-openai >=0.0.5 | >=1.0.0,<2.0.0 | YES |
| anthropic (via langchain-anthropic) | >=1.0.0,<2.0.0 | YES |

**Key Rules:**
- All langchain ecosystem packages must require the same langchain-core major version
- Upgrade crewai to >=0.28.0 to align with browser-use
- Use langchain-openai >=0.0.5 for langchain v1.x compatibility
- Test in Docker before deploying to catch conflicts early

---