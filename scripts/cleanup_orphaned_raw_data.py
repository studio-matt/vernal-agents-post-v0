#!/usr/bin/env python3
"""
Clean up orphaned campaign_raw_data records
Removes all raw data records not associated with existing campaigns
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import CampaignRawData, Campaign
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

def cleanup_orphaned_raw_data():
    """Remove all campaign_raw_data records not associated with existing campaigns"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all existing campaign IDs
        existing_campaigns = db.query(Campaign.campaign_id).all()
        existing_campaign_ids = {c[0] for c in existing_campaigns}
        
        logger.info(f"Found {len(existing_campaign_ids)} existing campaigns")
        
        # Find orphaned raw data records
        all_raw_data = db.query(CampaignRawData).all()
        orphaned = [rd for rd in all_raw_data if rd.campaign_id not in existing_campaign_ids]
        
        logger.info(f"Found {len(orphaned)} orphaned raw data records out of {len(all_raw_data)} total")
        
        if orphaned:
            # Delete orphaned records
            for rd in orphaned:
                db.delete(rd)
            
            db.commit()
            logger.info(f"✅ Deleted {len(orphaned)} orphaned raw data records")
        else:
            logger.info("✅ No orphaned records found")
            
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error cleaning up orphaned raw data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_orphaned_raw_data()

