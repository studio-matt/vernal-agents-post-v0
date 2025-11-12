#!/usr/bin/env python3
"""
Verify visualizer settings are in the database and show their values.
Uses .env file for database credentials - no password required.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from database import SessionLocal
from models import SystemSettings

def verify_visualizer_settings():
    """Check if visualizer settings exist in database."""
    db = SessionLocal()
    try:
        # Get all visualizer settings
        settings = db.query(SystemSettings).filter(
            SystemSettings.setting_key.like("visualizer_%")
        ).order_by(SystemSettings.setting_key).all()
        
        print("=" * 70)
        print("📊 VISUALIZER SETTINGS IN DATABASE")
        print("=" * 70)
        
        if len(settings) == 0:
            print("❌ NO VISUALIZER SETTINGS FOUND!")
            print("\n💡 Run: python3 scripts/insert_visualizer_settings.py")
            return False
        
        print(f"\n✅ Found {len(settings)} visualizer settings:\n")
        
        for setting in settings:
            print(f"  {setting.setting_key:40} = {setting.setting_value}")
        
        # Check for critical settings
        critical_keys = [
            "visualizer_visualization_type",
            "visualizer_color_scheme",
            "visualizer_size_scaling"
        ]
        
        print("\n" + "=" * 70)
        print("🔍 CRITICAL SETTINGS CHECK")
        print("=" * 70)
        
        found_keys = {s.setting_key for s in settings}
        all_present = True
        
        for key in critical_keys:
            if key in found_keys:
                value = next(s.setting_value for s in settings if s.setting_key == key)
                print(f"  ✅ {key:40} = {value}")
            else:
                print(f"  ❌ {key:40} = MISSING")
                all_present = False
        
        print("\n" + "=" * 70)
        if all_present:
            print("✅ All critical settings present!")
        else:
            print("⚠️  Some settings missing - run insert_visualizer_settings.py")
        print("=" * 70)
        
        return all_present
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = verify_visualizer_settings()
    sys.exit(0 if success else 1)


