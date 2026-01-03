#!/usr/bin/env python3
"""
Cleanup script to remove orphaned campaign_raw_data (data for campaigns that no longer exist).
This ensures only raw data for existing campaigns remains in the database.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import CampaignRawData, Campaign
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def cleanup_orphaned_raw_data():
    """Remove all campaign_raw_data not associated with existing campaigns"""
    # Create database connection
    db_config = {
        "host": os.getenv('DB_HOST'),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD'),
        "database": os.getenv('DB_NAME'),
    }
    
    encoded_password = quote_plus(str(db_config["password"]))
    DATABASE_URL = f"mysql+pymysql://{db_config['user']}:{encoded_password}@{db_config['host']}/{db_config['database']}?charset=utf8mb4"
    
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all existing campaign_ids from Campaign table
        existing_campaigns = session.query(Campaign.campaign_id).all()
        existing_campaign_ids = {c[0] for c in existing_campaigns if c[0]}
        
        logger.info(f"📋 Found {len(existing_campaign_ids)} existing campaigns in database")
        
        # Get all unique campaign_ids from CampaignRawData
        raw_data_campaign_ids = session.query(CampaignRawData.campaign_id).distinct().all()
        raw_data_campaign_ids = [cid[0] for cid in raw_data_campaign_ids if cid[0]]
        
        logger.info(f"📋 Found {len(raw_data_campaign_ids)} unique campaign_ids in CampaignRawData")
        
        # Find campaign_ids in raw_data that don't exist in campaigns table (orphaned)
        orphaned_campaign_ids = [cid for cid in raw_data_campaign_ids if cid not in existing_campaign_ids]
        
        if not orphaned_campaign_ids:
            logger.info("✅ No orphaned campaign raw data found. All data is associated with existing campaigns.")
            return
        
        logger.info(f"🗑️ Found {len(orphaned_campaign_ids)} orphaned campaign_ids: {orphaned_campaign_ids}")
        
        total_deleted = 0
        for campaign_id in orphaned_campaign_ids:
            # Count records for this orphaned campaign
            count = session.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == campaign_id
            ).count()
            
            # Delete all records for this orphaned campaign
            deleted = session.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == campaign_id
            ).delete(synchronize_session=False)
            
            total_deleted += deleted
            logger.info(f"🗑️ Deleted {deleted} orphaned raw data records for campaign_id: {campaign_id}")
        
        session.commit()
        logger.info(f"✅ Cleaned up {total_deleted} orphaned raw data entries.")
        
        # Report remaining data by campaign
        remaining_campaign_ids = session.query(CampaignRawData.campaign_id).distinct().all()
        remaining_campaign_ids = [cid[0] for cid in remaining_campaign_ids if cid[0]]
        logger.info(f"📊 Remaining raw data for {len(remaining_campaign_ids)} campaigns:")
        for cid in remaining_campaign_ids:
            count = session.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == cid
            ).count()
            logger.info(f"   - Campaign {cid}: {count} records")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error during raw data cleanup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()
        engine.dispose()

if __name__ == "__main__":
    logger.info("🧹 Starting cleanup of orphaned campaign_raw_data...")
    cleanup_orphaned_raw_data()
    logger.info("✅ Cleanup complete!")

