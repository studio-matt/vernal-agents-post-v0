#!/usr/bin/env python3
"""
Migration script to change writing_samples_json column from TEXT to LONGTEXT.

This fixes the "Data too long for column" error when storing large writing samples.

Run this script on the backend server:
    python3 scripts/migrate_writing_samples_to_longtext.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from sqlalchemy import text

def migrate_writing_samples_column():
    """Change writing_samples_json from TEXT to LONGTEXT."""
    db = next(get_db())
    
    try:
        print("🔄 Migrating writing_samples_json column from TEXT to LONGTEXT...")
        
        # Check current column type
        result = db.execute(text("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'author_personalities' 
            AND COLUMN_NAME = 'writing_samples_json'
        """))
        
        current_type = result.fetchone()
        if current_type:
            print(f"📊 Current column type: {current_type[0]}")
            if 'longtext' in current_type[0].lower():
                print("✅ Column is already LONGTEXT, no migration needed.")
                return
        
        # Alter column to LONGTEXT
        print("🔧 Altering column type...")
        db.execute(text("""
            ALTER TABLE author_personalities 
            MODIFY COLUMN writing_samples_json LONGTEXT NULL
        """))
        
        db.commit()
        print("✅ Successfully migrated writing_samples_json to LONGTEXT!")
        
        # Verify the change
        result = db.execute(text("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'author_personalities' 
            AND COLUMN_NAME = 'writing_samples_json'
        """))
        
        new_type = result.fetchone()
        if new_type:
            print(f"✅ Verified new column type: {new_type[0]}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_writing_samples_column()

