"""
Test script for ultra minimal auth system
"""

import requests
import json

def test_auth_system():
    base_url = "https://themachine.vernalcontentum.com"
    
    print("🧪 Testing Ultra Minimal Auth System")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Auth health check
    print("\n2. Testing auth health endpoint...")
    try:
        response = requests.get(f"{base_url}/auth/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: User signup
    print("\n3. Testing user signup...")
    try:
        signup_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "contact": "1234567890"
        }
        response = requests.post(f"{base_url}/auth/signup", json=signup_data, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: User login
    print("\n4. Testing user login...")
    try:
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_auth_system()
