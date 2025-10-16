#!/usr/bin/env python3
"""
Debug Database Auth API Imports
Test each import to identify the issue
"""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module"""
    try:
        __import__(module_name)
        print(f"✅ {description}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {description}: FAILED - {str(e)}")
        traceback.print_exc()
        return False

def main():
    print("🔍 Debugging Database Auth API Imports...")
    print("=" * 50)
    
    # Test basic imports
    test_import("fastapi", "FastAPI")
    test_import("pydantic", "Pydantic")
    test_import("sqlalchemy", "SQLAlchemy")
    test_import("sqlalchemy.orm", "SQLAlchemy ORM")
    
    print()
    
    # Test project imports
    test_import("database", "Database module")
    test_import("models", "Models module")
    test_import("utils", "Utils module")
    test_import("email_service", "Email service module")
    
    print()
    
    # Test specific classes
    try:
        from models import User, OTP
        print("✅ User and OTP models: SUCCESS")
    except Exception as e:
        print(f"❌ User and OTP models: FAILED - {str(e)}")
        traceback.print_exc()
    
    try:
        from database import db_manager
        print("✅ Database manager: SUCCESS")
    except Exception as e:
        print(f"❌ Database manager: FAILED - {str(e)}")
        traceback.print_exc()
    
    try:
        from utils import hash_password, verify_password, create_access_token, verify_token
        print("✅ Utils functions: SUCCESS")
    except Exception as e:
        print(f"❌ Utils functions: FAILED - {str(e)}")
        traceback.print_exc()
    
    print()
    print("🎯 Import debugging completed!")

if __name__ == "__main__":
    main()
