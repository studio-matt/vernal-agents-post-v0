#!/usr/bin/env python3
"""
Create campaign_research_data table using existing database connection.
This script uses the same database credentials from .env file.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database import DatabaseManager

# Load environment variables
load_dotenv()

def create_research_data_table():
    """Create the campaign_research_data table if it doesn't exist"""
    try:
        # Use existing database connection
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # SQL to create the table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS campaign_research_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            campaign_id VARCHAR(255) NOT NULL UNIQUE,
            word_cloud_json TEXT,
            topics_json TEXT,
            hashtags_json TEXT,
            entities_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_campaign_id (campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        print("✅ Successfully created campaign_research_data table")
        return True
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Creating campaign_research_data table...")
    success = create_research_data_table()
    sys.exit(0 if success else 1)


