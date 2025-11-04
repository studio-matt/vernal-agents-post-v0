#!/bin/bash
# diagnose_auth_500.sh - Diagnose 500 errors in auth/login endpoint

set -e

echo "🔍 Diagnosing Auth 500 Error"
echo "============================="

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

echo ""
echo "1️⃣ Checking backend logs for auth/login errors..."
echo "---------------------------------------------------"
sudo journalctl -u vernal-agents --since "10 minutes ago" --no-pager | grep -i -A 10 "login\|auth\|error\|exception\|traceback" | tail -50

echo ""
echo "2️⃣ Testing critical auth dependencies..."
echo "------------------------------------------"
python3 << 'PYEOF'
import sys
deps = {
    "passlib": "Password hashing (bcrypt)",
    "python-jose": "JWT token creation",
    "bcrypt": "Password hashing backend",
    "email_validator": "Email validation",
    "database": "Database connection (local)",
    "models": "User model (local)",
    "utils": "Auth utilities (local)"
}

failed = []
for dep, desc in deps.items():
    try:
        __import__(dep)
        print(f"✅ {dep} - OK ({desc})")
    except ImportError as e:
        print(f"❌ {dep} - FAILED: {e} ({desc})")
        failed.append((dep, desc, str(e)))

if failed:
    print("\n❌ Missing dependencies:")
    for dep, desc, err in failed:
        print(f"   - {dep}: {desc}")
    sys.exit(1)
else:
    print("\n✅ All dependencies available")
PYEOF

echo ""
echo "3️⃣ Testing database connection..."
echo "-----------------------------------"
python3 << 'PYEOF'
try:
    from database import DatabaseManager
    db = DatabaseManager()
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "4️⃣ Testing auth router import..."
echo "---------------------------------"
python3 << 'PYEOF'
try:
    from auth_api import auth_router
    print("✅ Auth router imports successfully")
except Exception as e:
    print(f"❌ Auth router import failed: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "5️⃣ Testing auth utilities..."
echo "-----------------------------"
python3 << 'PYEOF'
try:
    from utils import hash_password, verify_password, create_access_token
    print("✅ Auth utilities available")
    
    # Test password hashing
    test_hash = hash_password("test")
    print(f"✅ Password hashing works: {test_hash[:20]}...")
    
    # Test password verification
    if verify_password("test", test_hash):
        print("✅ Password verification works")
    else:
        print("❌ Password verification failed")
    
    # Test token creation
    token = create_access_token(data={"sub": "1"})
    print(f"✅ Token creation works: {token[:30]}...")
    
except Exception as e:
    print(f"❌ Auth utilities failed: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "✅ Diagnosis complete!"
echo ""
echo "If any checks failed above, install missing packages:"
echo "  pip install passlib[bcrypt] python-jose[cryptography] bcrypt"

