#!/bin/bash
# bulletproof_deploy_backend.sh - Complete nuke-and-replace deployment

set -e

echo "🔒 BULLETPROOF BACKEND DEPLOYMENT STARTING..."

# 1. Nuke old code completely
echo "🧹 Nuking old code..."

# CRITICAL: Change to safe directory BEFORE deleting (prevents "getcwd() failed" errors)
cd /home/ubuntu || exit 1

# CRITICAL: Backup .env file before deletion (EMERGENCY_NET.md v7)
echo "🔐 Backing up .env file before cleanup..."
if [ -f /home/ubuntu/vernal-agents-post-v0/.env ]; then
  sudo cp /home/ubuntu/vernal-agents-post-v0/.env /home/ubuntu/.env.backup
  sudo chown ubuntu:ubuntu /home/ubuntu/.env.backup
  chmod 600 /home/ubuntu/.env.backup
  echo "✅ .env file backed up to /home/ubuntu/.env.backup"
else
  echo "⚠️ No existing .env file found to backup"
fi

sudo systemctl stop vernal-agents || true
rm -rf /home/ubuntu/vernal-agents-post-v0

# Clean up old backup directories
echo "🧹 Cleaning up old backup directories..."
find /home/ubuntu -maxdepth 1 -name "vernal-agents*backup*" -type d -exec rm -rf {} + 2>/dev/null || true
find /home/ubuntu -maxdepth 1 -name "vernal-agents*corrupted*" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ Backup directories cleaned up"

# 2. Clone fresh from GitHub
echo "📦 Cloning fresh from GitHub..."
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0
cd /home/ubuntu/vernal-agents-post-v0

# 3. Setup venv from scratch with memory optimization
echo "🐍 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Memory monitoring and optimization
echo "📊 Memory status before pip install:"
free -h

# Aggressive memory cleanup
echo "🧹 Cleaning up memory..."
sudo apt-get clean
sudo apt-get autoremove -y 2>/dev/null || true
sudo rm -rf /var/cache/apt/archives/* 2>/dev/null || true
sudo rm -rf /tmp/* 2>/dev/null || true
echo "📊 Memory after cleanup:"
free -h

# Memory optimization: upgrade pip and install with no cache
echo "⬆️ Upgrading pip..."
pip install --upgrade pip --no-cache-dir

# Install packages in chunks to reduce memory pressure (prevents SIGKILL)
echo "📦 Installing core dependencies..."
pip install fastapi uvicorn sqlalchemy pymysql python-multipart python-dotenv pydantic --no-cache-dir --progress-bar off || { echo "❌ Core dependencies failed!"; exit 1; }

echo "📦 Installing AI/ML dependencies (this may take 5-10 minutes)..."
pip install openai anthropic transformers torch --no-cache-dir --progress-bar off || { echo "❌ AI packages installation FAILED!"; exit 1; }

echo "📦 Installing remaining dependencies..."
pip install -r requirements.txt --no-cache-dir --progress-bar off || { echo "❌ Package installation FAILED! Check requirements.txt for issues."; exit 1; }

# CRITICAL: Verify critical packages are actually importable (prevents silent failures)
echo "🔍 Verifying critical package imports (MANDATORY)..."
python3 << 'VERIFY_EOF'
import sys
critical_packages = {
    "fastapi": "FastAPI web framework",
    "uvicorn": "ASGI server",
    "sqlalchemy": "Database ORM",
    "pymysql": "MySQL driver",
    "pydantic": "Data validation",
    "email_validator": "Email validation (required for auth)",
    "ddgs": "DuckDuckGo search (required for scraping)",
    "nltk": "NLTK text processing (required for research)",
    "database": "Database manager (local module)",
    "models": "Database models (local module)",
}

failed_imports = []
for package, description in critical_packages.items():
    try:
        __import__(package)
        print(f"✅ {package} - OK")
    except ImportError as e:
        print(f"❌ {package} - FAILED: {e}")
        print(f"   Required for: {description}")
        failed_imports.append((package, description, str(e)))

if failed_imports:
    print("\n❌ CRITICAL PACKAGES FAILED TO IMPORT!")
    print("   This deployment will FAIL if service starts.")
    print("   Missing packages:")
    for pkg, desc, err in failed_imports:
        print(f"   - {pkg}: {desc} ({err})")
    sys.exit(1)

print("\n✅ All critical packages verified successfully!")
VERIFY_EOF

if [ $? -ne 0 ]; then
    echo "❌ Package verification FAILED! Fix missing packages before deploying."
    exit 1
fi

# Verify auth router can load (catches email-validator issues early)
echo "🔍 Verifying auth router can load..."
python3 << 'AUTH_VERIFY_EOF'
import sys
try:
    from auth_api import auth_router
    print("✅ Auth router loaded successfully")
except Exception as e:
    print(f"❌ Auth router failed to load: {e}")
    print("   This will cause 404 errors on /auth/login and /auth/signup")
    sys.exit(1)
AUTH_VERIFY_EOF

if [ $? -ne 0 ]; then
    echo "❌ Auth router verification FAILED! Fix dependencies before deploying."
    exit 1
fi

# 4. Restore and validate environment variables (EMERGENCY_NET.md v7)
echo "🔐 Setting up environment..."

# CRITICAL: Restore .env from backup if it exists, otherwise use /etc/environment
if [ -f /home/ubuntu/.env.backup ]; then
  echo "✅ Restoring .env from backup..."
  sudo cp /home/ubuntu/.env.backup .env
  sudo chown ubuntu:ubuntu .env
  chmod 600 .env
  echo "✅ .env file restored from backup with preserved credentials"
else
  echo "⚠️ No .env backup found, creating from /etc/environment..."
  sudo cp /etc/environment .env
  sudo chown ubuntu:ubuntu .env
  chmod 600 .env
  echo "⚠️ WARNING: .env created from /etc/environment - DB and JWT credentials may be missing!"
  echo "⚠️ Please verify .env contains DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, and JWT_SECRET_KEY"
fi

# Validate critical environment variables (EMERGENCY_NET.md v7)
echo "🔍 Validating environment variables..."
REQUIRED_VARS=("DB_HOST" "DB_USER" "DB_PASSWORD" "DB_NAME")
MISSING_VARS=()

# Check for presence of required variables
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo "Please restore .env from backup or manually configure with real credentials"
    exit 1
fi

# CRITICAL: Validate no placeholder values (EMERGENCY_NET.md)
echo "🔍 Validating no placeholder values..."
if grep -E "myuser|localhost|dummy|mypassword" .env > /dev/null; then
    echo "❌ CRITICAL: Placeholder values detected in .env file!"
    echo "❌ Detected placeholders:"
    grep -E "myuser|localhost|dummy|mypassword" .env || true
    echo "❌ This will cause database connection failures!"
    echo "❌ Please restore .env from backup or manually configure with real credentials"
    exit 1
fi

echo "✅ All required environment variables present with real values"

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
EnvironmentFile=/home/ubuntu/vernal-agents-post-v0/.env

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

# Database test (using health endpoint that checks DB)
echo "🔍 Testing database connectivity..."
curl -f http://localhost:8000/mcp/enhanced/health || { echo "❌ Database health check failed!"; exit 1; }
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

# CRITICAL: Verify auth endpoints are accessible (prevents 404 regressions)
echo "🔍 Testing auth endpoints (CRITICAL - prevents 404 regressions)..."
AUTH_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://themachine.vernalcontentum.com/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"test","password":"test"}')
if [ "$AUTH_HEALTH" = "404" ]; then
    echo "❌ Auth endpoint returned 404 - router not loaded!"
    echo "   Check backend logs for 'Failed to include authentication router'"
    exit 1
elif [ "$AUTH_HEALTH" = "422" ] || [ "$AUTH_HEALTH" = "401" ]; then
    echo "✅ Auth endpoint accessible (returned $AUTH_HEALTH - expected for invalid credentials)"
else
    echo "⚠️  Auth endpoint returned unexpected status: $AUTH_HEALTH"
    echo "   Endpoint exists but may have issues"
fi

echo "✅ External access working"

# 9. Log successful deployment
COMMIT_HASH=$(git rev-parse HEAD)
PYTHON_VERSION=$(python --version)
echo "$(date) - BULLETPROOF Backend deployed successfully, commit: $COMMIT_HASH, Python: $PYTHON_VERSION" >> ~/vernal_agents_deploy.log

echo "🎉 BULLETPROOF BACKEND DEPLOYMENT SUCCESSFUL!"
echo "📝 Deployment logged to ~/vernal_agents_deploy.log"
