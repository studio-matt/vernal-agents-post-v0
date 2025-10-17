#!/usr/bin/env python3
"""
Test bcrypt hashing directly to debug the 72-byte issue
"""

from passlib.context import CryptContext
import bcrypt

# Test 1: Using passlib (our current method)
print("=== Testing passlib ===")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

test_passwords = ["1", "123456", "a" * 100]  # Short, medium, long

for pwd in test_passwords:
    try:
        print(f"Testing password: '{pwd}' (length: {len(pwd)}, bytes: {len(pwd.encode('utf-8'))})")
        hash_result = pwd_context.hash(pwd)
        print(f"✅ Success: {hash_result[:20]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n=== Testing raw bcrypt ===")
# Test 2: Using raw bcrypt
for pwd in test_passwords:
    try:
        print(f"Testing password: '{pwd}' (length: {len(pwd)}, bytes: {len(pwd.encode('utf-8'))})")
        hash_result = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt())
        print(f"✅ Success: {hash_result[:20]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n=== Testing our current method ===")
# Test 3: Our current method
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    password_to_hash = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password_to_hash)

for pwd in test_passwords:
    try:
        print(f"Testing password: '{pwd}' (length: {len(pwd)}, bytes: {len(pwd.encode('utf-8'))})")
        hash_result = hash_password(pwd)
        print(f"✅ Success: {hash_result[:20]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
