# Vernal Agents Backend — Emergency Net

## TL;DR
- **App:** FastAPI served by Python (systemd)
- **Domain:** https://themachine.vernalcontentum.com → **nginx** → `127.0.0.1:8000`
- **Live dir:** `/home/ubuntu/vernal-agents-post-v0`
- **Repo:** https://github.com/studio-matt/vernal-agents-post-v0.git
- **DB:** MySQL (remote @ `50.6.198.220:3306`)
- **Service:** `vernal-agents.service` (systemd) ← **ONLY SERVICE - NO OTHERS**
- **Health:**  
  - Local:  `curl -s http://127.0.0.1:8000/health` → `{"ok":true,"version":"2.0.0","status":"debug"}` (Service running)
  - Public: `curl -s https://themachine.vernalcontentum.com/health` → `{"ok":true,"version":"2.0.0","status":"debug"}` (Service running)
- **Database:**  
  - Local:  `curl -s http://127.0.0.1:8000/mcp/enhanced/health` → Database connectivity test
  - Public: `curl -s https://themachine.vernalcontentum.com/mcp/enhanced/health` → Database connectivity test

---

## ⚠️ CRITICAL CONFIGURATION - NEVER CHANGE THESE ⚠️
- **Project:** `/home/ubuntu/vernal-agents-post-v0`
- **Virtualenv:** `/home/ubuntu/vernal-agents-post-v0/venv/`
- **Systemd unit:** `/etc/systemd/system/vernal-agents.service` ← **ONLY SERVICE**
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000` ← **MUST USE VENV + UVICORN**
- **WorkingDirectory:** `/home/ubuntu/vernal-agents-post-v0` ← **MUST BE THIS PATH**
- **nginx site:** `/etc/nginx/sites-enabled/themachine`  
  - Proxies → `http://127.0.0.1:8000`
  - TLS → `/etc/letsencrypt/live/themachine.vernalcontentum.com/`
- **Environment:** `.env` file in project root with DB credentials

## 🚨 CRITICAL ARCHITECTURE REQUIREMENTS - NEVER DEVIATE 🚨
- **100% DATABASE DEPENDENCY:** ALL persistent data MUST be stored in MySQL database
- **NO IN-MEMORY STORAGE:** Never use Python dictionaries, lists, or variables for persistent data
- **MULTI-TENANT ARCHITECTURE:** All data MUST be scoped to user accounts
- **PRODUCTION-READY:** No "temporary" or "mock" solutions that violate core requirements
- **AUTHENTICATION:** MUST use `auth_api.py` (database-backed), NEVER `auth_ultra_minimal.py`
- **USER DATA:** User accounts, OTPs, sessions MUST be in database tables
- **MCP INTEGRATION:** All MCP tools MUST be database-aware and user-scoped

### ⚠️ ARCHITECTURE VALIDATION CHECKLIST ⚠️
Before implementing ANY solution, ask:
1. **Does this store data in the database?** (Not in memory)
2. **Is this user-scoped/multi-tenant?** (Not global/shared)
3. **Is this production-ready?** (Not temporary/mock)
4. **Does this align with 100% DB dependency?** (No shortcuts)
5. **Will this persist across server restarts?** (Database only)

### 🚫 FORBIDDEN PATTERNS 🚫
- ❌ `users_db = {}` (in-memory dictionaries)
- ❌ `global_variable = []` (in-memory lists)
- ❌ Mock/temporary authentication systems
- ❌ "Just to get it working" solutions that violate architecture
- ❌ Any data storage outside the database

## 🔐 AUTHENTICATION SYSTEM - CRITICAL RULES 🔐
- **ONLY USE:** `auth_api.py` (database-backed authentication)
- **NEVER USE:** `auth_ultra_minimal.py` (in-memory storage)
- **USER STORAGE:** MySQL `user` table only
- **OTP STORAGE:** MySQL `otp` table only
- **SESSIONS:** JWT tokens with database user validation
- **EMAIL SERVICE:** Real SMTP integration, not mock

### Authentication Validation:
- ✅ All user data in database
- ✅ All OTPs in database with expiration
- ✅ Real email sending for verification
- ✅ Multi-tenant user scoping
- ✅ Production-ready security

### If Authentication Issues Arise:
1. **Check database connectivity first**
2. **Verify `auth_api.py` is loaded** (not ultra minimal)
3. **Check email service configuration**
4. **NEVER fall back to in-memory storage**

---

## Current Working Configuration (MCP Migration State)
- **Service:** `vernal-agents.service` (NOT `fastapi.service`)
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`
- **Database:** Connected and working (MySQL @ 50.6.198.220:3306)
- **Status:** Backend running, database connected, some methods missing
- **GitHub Actions Deployment:**
  - **Workflow:** `.github/workflows/agents-deploy-workflow.yml`
  - **Strategy:** Direct SSH deployment (pulls code, restarts service)
  - **GitHub Secrets Required:**
    - `EC2_HOST` = `18.235.104.132`
    - `EC2_USER` = `ubuntu`
    - `EC2_PRIVATE_KEY` = SSH private key for backend server
- **Known Issues:** 
  - Missing `get_all_campaigns` method in DatabaseManager
  - Auth endpoints (`/auth/signup`, `/auth/login`) - **WORKING** with CORS fixes
  - `db_manager.create_tables()` commented out (method doesn't exist)
- **CORS Configuration:**
  - **CRITICAL:** nginx must NOT handle CORS - let FastAPI handle it
  - **nginx config:** `/etc/nginx/sites-enabled/themachine` - NO `add_header` CORS directives
  - **FastAPI handles:** All CORS headers including `Access-Control-Allow-Headers`
  - **Fixed:** `content-type` header issue with explicit `allow_headers` list
  - **Manual handler:** Added `@app.options("/{path:path}")` as backup
  - **Headers allowed:** `["content-type", "authorization", "accept", "ngrok-skip-browser-warning"]`

---

## 🚨 CORS TROUBLESHOOTING - CRITICAL LESSONS LEARNED 🚨

### The Multi-Day CORS Nightmare (RESOLVED)
**Problem:** `Request header field content-type is not allowed by Access-Control-Allow-Headers in preflight response`

**Root Cause:** nginx was intercepting OPTIONS requests and returning incomplete CORS headers, preventing FastAPI from handling CORS properly.

**Solution:** 
1. **Remove ALL nginx CORS handling** - no `add_header` directives for CORS
2. **Let FastAPI handle ALL CORS** - proxy everything including OPTIONS requests
3. **nginx config must be clean proxy only:**

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    # NO CORS HEADERS HERE - let FastAPI handle it!
}
```

**Test CORS fix:**
```bash
curl -i -X OPTIONS https://themachine.vernalcontentum.com/auth/signup
# Should return FastAPI CORS headers including Access-Control-Allow-Headers
```

**NEVER AGAIN:** Don't let nginx handle CORS - always proxy to FastAPI!

---

## 🚨 SINGLE SOURCE OF TRUTH - USE THESE EXACT COMMANDS 🚨
```bash
# FIRST: Create virtual environment and install dependencies
cd /home/ubuntu/vernal-agents-post-v0
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# THEN: THE ONLY systemd service configuration that works:
sudo tee /etc/systemd/system/vernal-agents.service > /dev/null << 'EOF'
[Unit]
Description=Vernal Agents Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vernal-agents-post-v0
ExecStart=/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/ubuntu/vernal-agents-post-v0

[Install]
WantedBy=multi-user.target
EOF

# Apply and start
sudo systemctl daemon-reload
sudo systemctl restart vernal-agents
```

## 🧹 CLEANUP COMMANDS - USE WHEN PORT 8000 IS BLOCKED
```bash
# Kill ALL competing processes on port 8000
sudo pkill -f "python.*main.py"
sudo pkill -f "uvicorn"
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# Verify port 8000 is free
sudo lsof -i :8000

# Start ONLY the systemd service
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents
curl http://localhost:8000/health
```

## 🔒 BULLETPROOF DEPLOYMENT PROCESS

### CRITICAL CODE VALIDATION
```bash
# Verify main.py exists and defines FastAPI app
test -f main.py || { echo "ERROR: main.py not found!"; exit 1; }
grep -q "app = FastAPI" main.py || { echo "ERROR: main.py must define app = FastAPI()!"; exit 1; }
grep -q "from fastapi import FastAPI" main.py || { echo "ERROR: main.py must import FastAPI!"; exit 1; }
echo "✅ main.py validation passed"
```

### PRE-DEPLOYMENT VALIDATION CHECKS
```bash
# Verify correct repo and path
if [ "$PWD" != "/home/ubuntu/vernal-agents-post-v0" ]; then
    echo "ERROR: Wrong working directory! Expected: /home/ubuntu/vernal-agents-post-v0"
    exit 1
fi

# Check git status
git remote -v | grep "vernal-agents-post-v0"
git status --porcelain | wc -l | xargs -I {} test {} -eq 0 || echo "WARNING: Uncommitted changes"

# Verify Python environment
source venv/bin/activate
python --version | grep "3.12" || echo "WARNING: Wrong Python version"

# Check for conflicting processes
sudo lsof -i :8000 && echo "WARNING: Port 8000 in use" || echo "Port 8000 free"

# Verify systemd service exists
sudo systemctl list-unit-files | grep vernal-agents || echo "ERROR: Service not found"

# Verify .env file exists and has required keys
test -f .env || { echo "ERROR: .env file not found!"; exit 1; }
grep DB_HOST .env || echo "WARNING: DB_HOST not set in .env"
grep OPENAI_API_KEY .env || echo "WARNING: OPENAI_API_KEY not set in .env"

# Check critical environment variables
echo "🔍 Checking critical environment variables..."
test -n "$DB_HOST" && echo "✅ DB_HOST set" || echo "WARNING: DB_HOST not set"
test -n "$DB_USER" && echo "✅ DB_USER set" || echo "WARNING: DB_USER not set"
test -n "$DB_PASSWORD" && echo "✅ DB_PASSWORD set" || echo "WARNING: DB_PASSWORD not set"
test -n "$DB_NAME" && echo "✅ DB_NAME set" || echo "WARNING: DB_NAME not set"
test -n "$OPENAI_API_KEY" && echo "✅ OPENAI_API_KEY set" || echo "WARNING: OPENAI_API_KEY not set"

# Disable any competing services
sudo systemctl disable fastapi.service 2>/dev/null || true
sudo systemctl stop fastapi.service 2>/dev/null || true
```

### AUTOMATIC KILL & CLEANUP (BACKEND ONLY)
```bash
# Kill ALL backend processes before deployment
sudo pkill -f "python.*main.py"
sudo pkill -f "uvicorn"
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# Verify port 8000 is completely free
sudo lsof -i :8000 || echo "Port 8000 is free"

# Stop systemd service
sudo systemctl stop vernal-agents
```

### POST-DEPLOYMENT VALIDATION
```bash
# Start service
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents

# Health checks (MANDATORY - deployment not complete until these pass)
curl -f http://localhost:8000/health || { echo "ERROR: Health check failed!"; exit 1; }

# Test version endpoint and validate response
echo "🔍 Testing version endpoint..."
VERSION_RESPONSE=$(curl -s http://localhost:8000/version)
echo "$VERSION_RESPONSE" | jq . || { echo "ERROR: Version endpoint returned invalid JSON!"; exit 1; }

# Validate version endpoint contains required fields
echo "$VERSION_RESPONSE" | jq -e '.commit' || { echo "ERROR: Version endpoint missing commit!"; exit 1; }
echo "$VERSION_RESPONSE" | jq -e '.build_time' || { echo "ERROR: Version endpoint missing build_time!"; exit 1; }
echo "$VERSION_RESPONSE" | jq -e '.version' || { echo "ERROR: Version endpoint missing version!"; exit 1; }

# Verify external access
curl -f https://themachine.vernalcontentum.com/health || { echo "ERROR: External health check failed!"; exit 1; }
curl -f https://themachine.vernalcontentum.com/version || { echo "ERROR: External version check failed!"; exit 1; }

# Log monitoring
echo "📋 Recent logs:"
sudo journalctl -u vernal-agents -n 20 --no-pager | tail -10

# Verify no competing processes on port 8000
sudo lsof -i :8000 | grep -v systemd && echo "WARNING: Non-systemd process on port 8000" || echo "✅ Only systemd on port 8000"

# CRITICAL: If port 8000 is not open, check systemd logs for errors
if ! sudo lsof -i :8000 >/dev/null 2>&1; then
    echo "❌ Port 8000 is not listening!"
    echo "🔍 Checking systemd logs for errors..."
    sudo journalctl -u vernal-agents -n 50 --no-pager
    echo "🔍 Verifying main.py defines app = FastAPI()..."
    grep -q "app = FastAPI" main.py || echo "❌ main.py does not define app = FastAPI()!"
    echo "🔍 Common causes: code bug, missing dependency, or main.py does not define app = FastAPI()"
    exit 1
fi
```

## 🚀 BULLETPROOF DEPLOYMENT SCRIPT (BACKEND)

**Script Location:** `scripts/bulletproof_deploy_backend.sh` (in repository)

**Usage:**
```bash
# Download and run the bulletproof deployment
curl -s https://raw.githubusercontent.com/studio-matt/vernal-agents-post-v0/main/scripts/bulletproof_deploy_backend.sh | bash
```

**Or run locally:**
```bash
cd /home/ubuntu
wget https://raw.githubusercontent.com/studio-matt/vernal-agents-post-v0/main/scripts/bulletproof_deploy_backend.sh
chmod +x bulletproof_deploy_backend.sh
./bulletproof_deploy_backend.sh
```

**Script Contents:**
```bash
#!/bin/bash
# bulletproof_deploy_backend.sh - Complete nuke-and-replace deployment

set -e

echo "🔒 BULLETPROOF BACKEND DEPLOYMENT STARTING..."

# 1. Nuke old code completely
echo "🧹 Nuking old code..."
sudo systemctl stop vernal-agents || true

# Let systemd handle process management - don't kill processes manually
echo "⏳ Allowing systemd to manage processes..."
sleep 2

# More aggressive cleanup for stubborn files
echo "🧹 Force removing stubborn files..."
sudo find /home/ubuntu/vernal-agents-post-v0 -type f -exec rm -f {} + 2>/dev/null || true
sudo find /home/ubuntu/vernal-agents-post-v0 -type d -exec rmdir {} + 2>/dev/null || true
sudo rm -rf /home/ubuntu/vernal-agents-post-v0

# Try harder removal loop for stuck files
echo "🔄 Trying harder to remove directory..."
for i in {1..3}; do
  if [ -d /home/ubuntu/vernal-agents-post-v0 ]; then
    echo "❌ Directory still exists, trying harder to remove it (attempt $i)..."
    sudo rm -rf /home/ubuntu/vernal-agents-post-v0
    sleep 2
  fi
done

# Log remaining files if still stuck
if [ -d /home/ubuntu/vernal-agents-post-v0 ]; then
  echo "❌ Directory could not be fully deleted. Showing contents:"
  sudo find /home/ubuntu/vernal-agents-post-v0
  exit 1
fi

# Clean up old backup directories
echo "🧹 Cleaning up old backup directories..."
find /home/ubuntu -maxdepth 1 -name "vernal-agents*backup*" -type d -exec sudo rm -rf {} + 2>/dev/null || true
find /home/ubuntu -maxdepth 1 -name "vernal-agents*corrupted*" -type d -exec sudo rm -rf {} + 2>/dev/null || true
echo "✅ Backup directories cleaned up"

# 2. Clone fresh from GitHub
echo "📦 Cloning fresh from GitHub..."
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0
cd /home/ubuntu/vernal-agents-post-v0

# 3. Setup venv from scratch
echo "🐍 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Copy and validate environment variables
echo "🔐 Setting up environment..."
sudo cp /etc/environment .env
sudo chown ubuntu:ubuntu .env
chmod 600 .env

# Validate critical environment variables
echo "🔍 Validating environment variables..."
REQUIRED_VARS=("DB_HOST" "DB_USER" "DB_PASSWORD" "DB_NAME" "OPENAI_API_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo "Please update /etc/environment or provide a complete .env file"
    exit 1
fi

echo "✅ All required environment variables present"

# 5. Overwrite systemd unit (always)
echo "⚙️ Configuring systemd service..."
sudo tee /etc/systemd/system/vernal-agents.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Vernal Agents Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vernal-agents-post-v0
ExecStart=/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/ubuntu/vernal-agents-post-v0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# 6. Reload and start service
echo "🔄 Starting service..."
sudo systemctl daemon-reload
sudo systemctl start vernal-agents

# 7. Wait for startup
echo "⏳ Waiting for service startup..."
sleep 5

# 8. Automated post-deploy validation (MANDATORY)
echo "✅ Running post-deploy validation..."

# Health check
echo "🔍 Testing health endpoint..."
curl -f http://localhost:8000/health || { echo "❌ Health check failed!"; exit 1; }
echo "✅ Health check passed"

# Version check
echo "🔍 Testing version endpoint..."
VERSION_RESPONSE=$(curl -s http://localhost:8000/version)
echo "$VERSION_RESPONSE" | jq . || { echo "❌ Version endpoint returned invalid JSON!"; exit 1; }
echo "✅ Version check passed"

# Database test
echo "🔍 Testing database connectivity..."
curl -f http://localhost:8000/mcp/enhanced/health || { echo "❌ Database test failed!"; exit 1; }
echo "✅ Database test passed"

# Systemd status
echo "🔍 Checking systemd status..."
sudo systemctl status vernal-agents --no-pager || { echo "❌ Service not running!"; exit 1; }
echo "✅ Service is running"

# Port check
echo "🔍 Checking port 8000..."
sudo lsof -i :8000 || { echo "❌ Nothing listening on port 8000!"; exit 1; }
echo "✅ Port 8000 is listening"

# External access test
echo "🔍 Testing external access..."
curl -f https://themachine.vernalcontentum.com/health || { echo "❌ External health check failed!"; exit 1; }
curl -f https://themachine.vernalcontentum.com/version || { echo "❌ External version check failed!"; exit 1; }
curl -f https://themachine.vernalcontentum.com/mcp/enhanced/health || { echo "❌ External database test failed!"; exit 1; }
echo "✅ External access working"

# 9. Log successful deployment
COMMIT_HASH=$(git rev-parse HEAD)
PYTHON_VERSION=$(python --version)
echo "$(date) - BULLETPROOF Backend deployed successfully, commit: $COMMIT_HASH, Python: $PYTHON_VERSION" >> ~/vernal_agents_deploy.log

echo "🎉 BULLETPROOF BACKEND DEPLOYMENT SUCCESSFUL!"
echo "📝 Deployment logged to ~/vernal_agents_deploy.log"
```

## 🚀 AUTOMATED RECOVERY SCRIPT (BACKEND) - LEGACY
```bash
#!/bin/bash
# deploy_backend.sh - Bulletproof backend deployment

set -e

echo "🔒 BACKEND DEPLOYMENT STARTING..."

# Pre-deployment validation
echo "📋 Running pre-deployment checks..."
if [ "$PWD" != "/home/ubuntu/vernal-agents-post-v0" ]; then
    echo "ERROR: Wrong working directory! Expected: /home/ubuntu/vernal-agents-post-v0"
    exit 1
fi

git remote -v | grep "vernal-agents-post-v0" || { echo "ERROR: Wrong repo!"; exit 1; }
source venv/bin/activate
python --version | grep "3.12" || { echo "ERROR: Wrong Python version!"; exit 1; }

# Kill all competing processes
echo "🧹 Cleaning up competing processes..."
sudo pkill -f "python.*main.py" 2>/dev/null || true
sudo pkill -f "uvicorn" 2>/dev/null || true
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# Verify port is free
sudo lsof -i :8000 && { echo "ERROR: Port 8000 still in use!"; exit 1; } || echo "✅ Port 8000 is free"

# Deploy
echo "📦 Deploying backend..."
git pull origin main
pip install -r requirements.txt

# Restart service
echo "🔄 Restarting service..."
sudo systemctl stop vernal-agents
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents

# Post-deployment validation
echo "✅ Running post-deployment checks..."
curl -f http://localhost:8000/health || { echo "ERROR: Health check failed!"; exit 1; }
curl -f http://localhost:8000/version || { echo "ERROR: Version check failed!"; exit 1; }
curl -f https://themachine.vernalcontentum.com/health || { echo "ERROR: External health check failed!"; exit 1; }
curl -f https://themachine.vernalcontentum.com/version || { echo "ERROR: External version check failed!"; exit 1; }

# Show recent logs
echo "📋 Recent logs:"
sudo journalctl -u vernal-agents -n 10 --no-pager | tail -5

# Verify no competing processes
sudo lsof -i :8000 | grep -v systemd && echo "WARNING: Non-systemd process on port 8000" || echo "✅ Only systemd on port 8000"

# Log successful deployment (consistent format with frontend)
COMMIT_HASH=$(git rev-parse HEAD)
PYTHON_VERSION=$(python --version)
echo "$(date) - Backend deployed successfully, commit: $COMMIT_HASH, Python: $PYTHON_VERSION" >> ~/vernal_agents_deploy.log
echo "📝 Deployment logged to ~/vernal_agents_deploy.log"

echo "🎉 BACKEND DEPLOYMENT SUCCESSFUL!"
```

## 🔄 ROLLBACK PROCEDURE
```bash
# If deployment fails, rollback to last known working commit
git log --oneline -10  # Find last working commit
git reset --hard <last-working-commit-hash>
sudo systemctl restart vernal-agents
curl -f http://localhost:8000/health || echo "Rollback failed - manual intervention needed"
```

## Quick Recovery Commands
```bash
# Check service status
sudo systemctl status vernal-agents

# Restart if needed
sudo systemctl restart vernal-agents

# Check logs
sudo journalctl -u vernal-agents -n 20 --no-pager

# Test database connectivity
curl http://localhost:8000/mcp/enhanced/health
curl https://themachine.vernalcontentum.com/mcp/enhanced/health

# Check deployment history
tail -10 ~/vernal_agents_deploy.log

# Check current version info
curl -s http://localhost:8000/version | jq .

# CRITICAL: If backend is not listening, check these:
echo "🔍 Checking if port 8000 is listening..."
sudo lsof -i :8000 || echo "❌ Nothing listening on port 8000"

echo "🔍 Checking main.py defines FastAPI app..."
grep -q "app = FastAPI" main.py && echo "✅ main.py defines app = FastAPI()" || echo "❌ main.py missing app = FastAPI()"

echo "🔍 Common causes if backend not listening:"
echo "  - Code bug in main.py"
echo "  - Missing dependency (check pip install -r requirements.txt)"
echo "  - main.py does not define app = FastAPI()"
echo "  - Environment variables missing"
echo "  - Database connection issues"

# CORS troubleshooting
echo "🔍 CORS troubleshooting:"
echo "  - Check if content-type header is allowed in CORS config"
echo "  - Verify allow_headers includes 'content-type' explicitly"
echo "  - Test preflight OPTIONS request manually"
echo "  - Check browser console for CORS errors"
```

---

## Database Connectivity Test
- **Working:** Database connection, basic queries
- **Available methods:** `create_agent`, `create_task`, `get_agent_by_name`, `get_task_by_name`
- **Missing methods:** `get_all_campaigns`, `create_tables`
- **Test endpoint:** `PUT /agents/{agent_name}` (updates work)

---

## Previous Configuration (Pre-MCP Status) - COMMENTED OUT
<!-- 
PRE MCP STATUS - This was the working configuration before MCP migration:

- **Service:** `fastapi.service` (systemd) - INACTIVE
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`
- **EnvironmentFile:** `/etc/fastapi/vernal.env`
- **Health:** `curl -s http://127.0.0.1:8000/health` → `{"ok":true}`
- **Status:** Stopped 3 days ago, replaced by vernal-agents.service
- **Logs:** `sudo journalctl -u fastapi.service -n 120 --no-pager`

PRE MCP STATUS END
-->

---

## Migration Notes
- **Date:** October 2025
- **Reason:** MCP migration required direct Python execution instead of uvicorn
- **Change:** Switched from `fastapi.service` to `vernal-agents.service`
- **Database:** Same MySQL connection, different service configuration

## System Requirements
- **OS:** Ubuntu 24.04 LTS
- **Python:** 3.12+ with venv support
- **Required packages:** `python3-venv`, `python3-pip`, `git`
- **Database client:** `mysqlclient` (via pip)
- **Memory:** Minimum 2GB RAM (4GB recommended)
- **Storage:** 8GB+ free space for dependencies

## Security Notes
- **NEVER** commit `.env` files to version control
- **NEVER** commit database credentials or API keys
- **NEVER** commit SSH private keys
- **ALWAYS** use environment variables for sensitive data
- **VERIFY** `.env` file permissions: `chmod 600 .env`

---

## Runtime & Pinning (why gensim/scipy worked)
- **Python:** 3.12 (Ubuntu 24.04 LTS)
- **Pins that matter:**  
  - `numpy==1.26.4`  
  - `scipy==1.12.0`  ← required so `scipy.linalg.triu` exists (gensim compat)  
  - `gensim==4.3.2`  
  - `bertopic==0.16.3`  
  - `torch==2.2.2+cpu` / `torchvision==0.17.2+cpu`  
  - `smart-open>=6` (installed as `smart_open`)
- **Quick import check (optional):**
  ```bash
  /home/ubuntu/vernal-agents-post-v0/venv/bin/python - <<'PY'
import numpy, scipy, gensim; from bertopic import BERTopic
from scipy.linalg import triu
print("OK:", numpy.__version__, scipy.__version__, gensim.__version__)
PY
