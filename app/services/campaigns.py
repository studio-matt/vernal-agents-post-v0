"""
Campaign service functions extracted from main.py
Moved from main.py to preserve behavior
"""
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Demo campaign template ID
DEMO_CAMPAIGN_ID = "9aaa2de6-ac2c-4bd1-8cd2-44f8cbc66f2a"


def create_user_demo_campaign(user_id: int, db: Session):
    """
    Create a user-specific copy of the demo campaign.
    Each user gets their own independent demo campaign with unique campaign_id.
    """
    try:
        from models import Campaign, CampaignRawData
        import json
        from app.utils.helpers import _safe_getattr
        
        logger.info(f"📋 Creating user-specific demo campaign for user {user_id}")
        
        # Get the template demo campaign (regardless of user_id - template should exist)
        template_campaign = db.query(Campaign).filter(Campaign.campaign_id == DEMO_CAMPAIGN_ID).first()
        if not template_campaign:
            logger.error(f"❌ Template demo campaign {DEMO_CAMPAIGN_ID} not found in database!")
            logger.error(f"❌ Cannot create user copy - template campaign must exist first")
            logger.error(f"❌ Please ensure a campaign with campaign_id={DEMO_CAMPAIGN_ID} exists in the database")
            return None
        
        logger.info(f"✅ Found template demo campaign: {template_campaign.campaign_name} (user_id: {template_campaign.user_id})")
        
        # Check if user already has a demo campaign
        # We'll use a naming convention: demo campaigns have name starting with "Demo Campaign"
        existing_demo = db.query(Campaign).filter(
            Campaign.user_id == user_id,
            Campaign.campaign_name.like("Demo Campaign%")
        ).first()
        
        if existing_demo:
            logger.info(f"✅ User {user_id} already has demo campaign: {existing_demo.campaign_id}")
            return existing_demo.campaign_id
        
        # Create new campaign_id for user's copy
        user_demo_campaign_id = str(uuid.uuid4())
        
        # Copy campaign data
        user_campaign = Campaign(
            campaign_id=user_demo_campaign_id,
            campaign_name=template_campaign.campaign_name,
            description=template_campaign.description,
            query=template_campaign.query,
            type=template_campaign.type,
            keywords=template_campaign.keywords,
            urls=template_campaign.urls,
            trending_topics=template_campaign.trending_topics,
            topics=template_campaign.topics,
            status=template_campaign.status,
            user_id=user_id,  # Set to current user
            extraction_settings_json=template_campaign.extraction_settings_json,
            preprocessing_settings_json=template_campaign.preprocessing_settings_json,
            entity_settings_json=template_campaign.entity_settings_json,
            modeling_settings_json=template_campaign.modeling_settings_json,
            site_base_url=_safe_getattr(template_campaign, 'site_base_url'),
            target_keywords_json=_safe_getattr(template_campaign, 'target_keywords_json'),
            top_ideas_count=_safe_getattr(template_campaign, 'top_ideas_count'),
            image_settings_json=_safe_getattr(template_campaign, 'image_settings_json'),
            content_queue_items_json=_safe_getattr(template_campaign, 'content_queue_items_json'),
            articles_url=_safe_getattr(template_campaign, 'articles_url'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user_campaign)
        db.flush()  # Flush to get the ID
        
        # Copy raw_data from template to user's copy
        template_raw_data = db.query(CampaignRawData).filter(
            CampaignRawData.campaign_id == DEMO_CAMPAIGN_ID
        ).all()
        
        copied_raw_data_count = 0
        for template_row in template_raw_data:
            user_raw_data = CampaignRawData(
                campaign_id=user_demo_campaign_id,
                source_url=template_row.source_url,
                fetched_at=template_row.fetched_at,
                raw_html=template_row.raw_html,
                extracted_text=template_row.extracted_text,
                meta_json=template_row.meta_json
            )
            db.add(user_raw_data)
            copied_raw_data_count += 1
        
        db.commit()
        logger.info(f"✅ Created user demo campaign {user_demo_campaign_id} with {copied_raw_data_count} raw_data rows")
        return user_demo_campaign_id
        
    except Exception as e:
        logger.error(f"❌ Error creating user demo campaign: {e}", exc_info=True)
        db.rollback()
        return None


