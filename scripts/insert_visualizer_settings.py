#!/usr/bin/env python3
"""
Insert default visualizer settings into the database.
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

def insert_visualizer_settings():
    """Insert default visualizer settings if they don't exist."""
    db = SessionLocal()
    try:
        # Default visualizer settings
        default_settings = [
            ("visualizer_max_documents", "100"),
            ("visualizer_top_words_per_topic", "10"),
            ("visualizer_grid_columns", "0"),
            ("visualizer_sort_order", "coverage"),
            ("visualizer_show_coverage", "true"),
            ("visualizer_show_top_weights", "false"),
            ("visualizer_visualization_type", "scatter"),
            ("visualizer_color_scheme", "rainbow"),
            ("visualizer_size_scaling", "true"),
            ("visualizer_show_title", "false"),
            ("visualizer_show_info_box", "false"),
            ("visualizer_background_color", "#ffffff"),
            ("visualizer_min_size", "20"),
            ("visualizer_max_size", "100"),
        ]
        
        inserted_count = 0
        updated_count = 0
        
        for setting_key, setting_value in default_settings:
            # Check if setting exists
            existing = db.query(SystemSettings).filter(
                SystemSettings.setting_key == setting_key
            ).first()
            
            if existing:
                # Update if value is different
                if existing.setting_value != setting_value:
                    existing.setting_value = setting_value
                    updated_count += 1
                    print(f"✓ Updated: {setting_key} = {setting_value}")
                else:
                    print(f"○ Already set: {setting_key} = {setting_value}")
            else:
                # Insert new setting
                new_setting = SystemSettings(
                    setting_key=setting_key,
                    setting_value=setting_value
                )
                db.add(new_setting)
                inserted_count += 1
                print(f"✓ Inserted: {setting_key} = {setting_value}")
        
        db.commit()
        print(f"\n✅ Success! Inserted {inserted_count} new settings, updated {updated_count} existing settings")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Inserting default visualizer settings...")
    print("=" * 60)
    success = insert_visualizer_settings()
    sys.exit(0 if success else 1)

