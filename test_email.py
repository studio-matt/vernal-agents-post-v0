#!/usr/bin/env python3
"""
Test Email Configuration
Tests SMTP connection and email sending before deployment
"""

import os
import asyncio
import sys
from email_service import get_email_service

async def test_email_config():
    """Test email configuration"""
    print("🧪 Testing Email Configuration...")
    print("=" * 50)
    
    # Check environment variables
    print("📋 Checking Environment Variables:")
    required_vars = ["MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM", "MAIL_SERVER", "MAIL_PORT"]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == "MAIL_PASSWORD":
                print(f"  ✅ {var}: {'*' * len(value)}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")
    
    print()
    
    # Test email service
    print("📧 Testing Email Service:")
    email_service = get_email_service()
    
    # Test OTP email
    print("  🔄 Testing OTP email...")
    try:
        success = await email_service.send_otp_email(
            email="test@example.com",
            otp_code="123456",
            user_name="Test User"
        )
        if success:
            print("  ✅ OTP email test: SUCCESS")
        else:
            print("  ❌ OTP email test: FAILED")
    except Exception as e:
        print(f"  ❌ OTP email test: ERROR - {str(e)}")
    
    # Test password reset email
    print("  🔄 Testing password reset email...")
    try:
        success = await email_service.send_password_reset_email(
            email="test@example.com",
            otp_code="789012",
            user_name="Test User"
        )
        if success:
            print("  ✅ Password reset email test: SUCCESS")
        else:
            print("  ❌ Password reset email test: FAILED")
    except Exception as e:
        print(f"  ❌ Password reset email test: ERROR - {str(e)}")
    
    print()
    print("🎯 Email test completed!")

if __name__ == "__main__":
    # Set test environment variables if not set
    if not os.getenv("MAIL_USERNAME"):
        print("⚠️  No email environment variables found.")
        print("   Set them manually or run with:")
        print("   MAIL_USERNAME=seed@vernalcontentum.com MAIL_PASSWORD=yourpass python test_email.py")
        print()
    
    asyncio.run(test_email_config())
