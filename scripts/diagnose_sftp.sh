#!/bin/bash
echo "🔍 SFTP Diagnostic"
echo "=================="
echo ""

echo "1. Checking .env file..."
if [ -f ".env" ]; then
    echo "✅ .env exists"
    echo ""
    echo "2. Checking SFTP variables..."
    grep -E "^SFTP_" .env || echo "❌ No SFTP variables found"
else
    echo "❌ .env not found"
    exit 1
fi

echo ""
echo "3. Testing paramiko..."
source venv/bin/activate
python3 -c "import paramiko; print('✅ paramiko installed')" || echo "❌ paramiko missing - run: pip install paramiko"

echo ""
echo "4. Testing SFTP connection..."
python3 << 'PYEOF'
import os
import paramiko
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("SFTP_HOST")
user = os.getenv("SFTP_USER")
pwd = os.getenv("SFTP_PASS")
port = int(os.getenv("SFTP_PORT", "22"))

if not all([host, user, pwd]):
    print("❌ Missing SFTP credentials in .env")
    print("   Add: SFTP_HOST, SFTP_USER, SFTP_PASS")
    exit(1)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=pwd, timeout=10)
    print(f"✅ Connected to {host}")
    
    sftp = ssh.open_sftp()
    print("✅ SFTP session opened")
    
    # Test directory
    remote_dir = os.getenv("SFTP_REMOTE_DIR") or f"/home/{user}/public_html/nishant"
    try:
        sftp.listdir(remote_dir)
        print(f"✅ Directory exists: {remote_dir}")
    except:
        print(f"❌ Directory missing: {remote_dir}")
        print(f"   Create it on SFTP server")
    
    sftp.close()
    ssh.close()
    print("✅ Connection test passed")
except Exception as e:
    print(f"❌ Connection failed: {e}")
PYEOF
