#!/usr/bin/env python3
"""
Set a user as admin in the database (same DB as the app).
Run from backend repo root: python scripts/ensure_admin.py matt@envoydesign.com
Uses .env for DB credentials.
"""
import os
import sys

# Run from repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(REPO_ROOT)

# Load .env
from dotenv import load_dotenv
load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ensure_admin.py <email>")
        print("Example: python scripts/ensure_admin.py matt@envoydesign.com")
        sys.exit(1)
    email = sys.argv[1].strip()

    from database import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ No user found with email: {email}")
            sys.exit(1)
        old_val = getattr(user, 'is_admin', None)
        user.is_admin = True
        db.commit()
        db.refresh(user)
        print(f"✅ Set is_admin=True for: {email} (id={user.id})")
        print(f"   (previous value: {old_val})")
        print(f"   Verify: is_admin={user.is_admin}")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
