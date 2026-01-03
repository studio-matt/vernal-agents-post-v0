#!/usr/bin/env python3
"""
Cleanup script to remove all campaign_raw_data NOT associated with the Demo Vernal Campaign.
This ensures only raw data for the Demo Campaign exists in the database.
"""

import sys
import os

# Add parent directory to path to import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import CampaignRawData, Campaign
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_CAMPAIGN_ID = "9aaa2de6-ac2c-4bd1-8cd2-44f8cbc66f2a"

def cleanup_non_demo_raw_data():
    """Remove all campaign_raw_data not associated with the Demo Campaign"""
    session = next(get_db())
    try:
        # Get all unique campaign_ids from CampaignRawData
        raw_data_campaign_ids = session.query(CampaignRawData.campaign_id).distinct().all()
        raw_data_campaign_ids = [cid[0] for cid in raw_data_campaign_ids if cid[0]]
        
        logger.info(f"📋 Found {len(raw_data_campaign_ids)} unique campaign_ids in CampaignRawData")
        
        # Find campaign_ids that are NOT the Demo Campaign
        non_demo_campaign_ids = [cid for cid in raw_data_campaign_ids if cid != DEMO_CAMPAIGN_ID]
        
        if not non_demo_campaign_ids:
            logger.info("✅ No non-demo campaign raw data found. All data is for Demo Campaign.")
            return
        
        logger.info(f"🗑️ Found {len(non_demo_campaign_ids)} non-demo campaign_ids: {non_demo_campaign_ids}")
        
        total_deleted = 0
        for campaign_id in non_demo_campaign_ids:
            # Count records for this campaign
            count = session.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == campaign_id
            ).count()
            
            # Delete all records for this campaign
            deleted = session.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == campaign_id
            ).delete(synchronize_session=False)
            
            total_deleted += deleted
            logger.info(f"🗑️ Deleted {deleted} raw data records for campaign_id: {campaign_id}")
        
        session.commit()
        logger.info(f"✅ Cleaned up {total_deleted} raw data entries not associated with Demo Campaign.")
        
        # Also verify Demo Campaign data exists
        demo_count = session.query(CampaignRawData).filter(
            CampaignRawData.campaign_id == DEMO_CAMPAIGN_ID
        ).count()
        logger.info(f"📊 Demo Campaign ({DEMO_CAMPAIGN_ID}) now has {demo_count} raw data records")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error during raw data cleanup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("🧹 Starting cleanup of non-demo campaign_raw_data...")
    cleanup_non_demo_raw_data()
    logger.info("✅ Cleanup complete!")

