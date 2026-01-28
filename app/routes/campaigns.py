"""
Campaign CRUD endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import text
from auth_api import get_current_user
from database import SessionLocal
from app.schemas.models import CampaignCreate, CampaignUpdate
from app.services.campaigns import DEMO_CAMPAIGN_ID, create_user_demo_campaign
from app.utils.helpers import _safe_getattr, _safe_get_json

logger = logging.getLogger(__name__)

campaigns_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@campaigns_router.get("/campaigns")
def get_campaigns(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all campaigns for the authenticated user - REQUIRES AUTHENTICATION"""
    logger.info("🔍 /campaigns GET endpoint called")
    try:
        from models import Campaign
        from sqlalchemy.orm import defer
        
        # Filter campaigns by authenticated user (multi-tenant security)
        # Admin users can see all campaigns for troubleshooting
        # Use defer() to exclude potentially missing columns from SELECT to prevent SQL errors
        campaigns = None
        try:
            # Try to defer cornerstone_platform if it might not exist in database
            query = db.query(Campaign)
            try:
                # Check if column exists by trying to defer it
                query = query.options(defer(Campaign.cornerstone_platform))
            except (AttributeError, Exception) as defer_error:
                # Column doesn't exist in model or can't be deferred - continue without defer
                logger.debug(f"Could not defer cornerstone_platform: {defer_error}")
            
            if hasattr(current_user, 'is_admin') and current_user.is_admin:
                campaigns = query.all()
                logger.info(f"Admin user {current_user.id} viewing all campaigns: found {len(campaigns)} campaigns")
            else:
                campaigns = query.filter(Campaign.user_id == current_user.id).all()
                logger.info(f"Filtered campaigns by user_id={current_user.id}: found {len(campaigns)} campaigns")
        except Exception as query_error:
            # If query fails due to missing column, try without defer
            logger.warning(f"Campaign query failed, trying without defer: {query_error}")
            import traceback
            logger.error(f"Query error traceback: {traceback.format_exc()}")
            try:
                # Retry query without defer
                if hasattr(current_user, 'is_admin') and current_user.is_admin:
                    campaigns = db.query(Campaign).all()
                    logger.info(f"Admin user {current_user.id} viewing all campaigns (retry): found {len(campaigns)} campaigns")
                else:
                    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
                    logger.info(f"Filtered campaigns by user_id={current_user.id} (retry): found {len(campaigns)} campaigns")
        # If campaigns is still None, use raw SQL fallback
        if campaigns is None:
            logger.warning("Campaigns query failed, attempting raw SQL fallback")
            try:
                # Hardcoded list of all Campaign columns except cornerstone_platform
                columns = [
                    'id', 'campaign_id', 'campaign_name', 'description', 'query', 'type',
                    'keywords', 'urls', 'trending_topics', 'topics', 'status', 'user_id',
                    'created_at', 'updated_at', 'extraction_settings_json', 'preprocessing_settings_json',
                    'entity_settings_json', 'modeling_settings_json', 'scheduling_settings_json',
                    'campaign_plan_json', 'content_queue_items_json', 'research_selections_json',
                    'custom_keywords_json', 'personality_settings_json', 'image_settings_json',
                    'site_base_url', 'target_keywords_json', 'top_ideas_count', 'articles_url',
                    'gap_analysis_results_json'
                ]
                
                columns_str = ', '.join(columns)
                if hasattr(current_user, 'is_admin') and current_user.is_admin:
                    sql = text(f"SELECT {columns_str} FROM campaigns")
                    result = db.execute(sql)
                else:
                    sql = text(f"SELECT {columns_str} FROM campaigns WHERE user_id = :user_id")
                    result = db.execute(sql, {"user_id": current_user.id})
                
                campaigns = []
                for row in result:
                    row_dict = dict(row._mapping)
                    campaign = Campaign()
                    for key, value in row_dict.items():
                        if hasattr(campaign, key):
                            setattr(campaign, key, value)
                    campaigns.append(campaign)
                
                logger.info(f"Raw SQL fallback successful: found {len(campaigns)} campaigns")
            except Exception as raw_sql_error:
                logger.error(f"Raw SQL fallback failed: {raw_sql_error}")
                import traceback
                logger.error(f"Raw SQL fallback traceback: {traceback.format_exc()}")
                # Try with essential columns only
                try:
                    essential_columns = ['id', 'campaign_id', 'campaign_name', 'description', 'query', 'type', 'keywords', 'urls', 'status', 'user_id', 'created_at', 'updated_at']
                    columns_str = ', '.join(essential_columns)
                    if hasattr(current_user, 'is_admin') and current_user.is_admin:
                        sql = text(f"SELECT {columns_str} FROM campaigns")
                        result = db.execute(sql)
                    else:
                        sql = text(f"SELECT {columns_str} FROM campaigns WHERE user_id = :user_id")
                        result = db.execute(sql, {"user_id": current_user.id})
                    
                    campaigns = []
                    for row in result:
                        row_dict = dict(row._mapping)
                        campaign = Campaign()
                        for key, value in row_dict.items():
                            if hasattr(campaign, key):
                                setattr(campaign, key, value)
                        campaigns.append(campaign)
                    
                    logger.info(f"Essential columns fallback successful: found {len(campaigns)} campaigns")
                except Exception as essential_error:
                    logger.error(f"Essential columns fallback also failed: {essential_error}")
                    raise
        
        # Continue with existing logic - ensure user has demo campaign, etc.
        # Ensure user has a demo campaign (create copy if needed)
        # Ensure every user has their own demo campaign copy
        # Wrap in try-except to prevent errors from breaking the endpoint
        try:
            # Check if user already has a demo campaign (by name pattern)
            # Use safe query with defer to avoid column errors
            try:
                demo_check_query = db.query(Campaign)
                try:
                    demo_check_query = demo_check_query.options(defer(Campaign.cornerstone_platform))
                except (AttributeError, Exception):
                    pass
                user_has_demo = demo_check_query.filter(
                    Campaign.user_id == current_user.id,
                    Campaign.campaign_name.like("Demo Campaign%")
                ).first()
            except Exception as demo_check_error:
                logger.warning(f"⚠️ Failed to check for demo campaign, assuming none exists: {demo_check_error}")
                user_has_demo = None
            
            if not user_has_demo:
                logger.info(f"📋 User {current_user.id} does not have demo campaign, creating one now")
                user_demo_campaign_id = create_user_demo_campaign(current_user.id, db)
                
                if user_demo_campaign_id:
                    # For non-admin users, refresh the entire campaigns list to include the newly created demo campaign
                    # This ensures the demo campaign is included even if it was created after the initial query
                    if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
                        # Use safe query with defer to avoid column errors
                        try:
                            refresh_query = db.query(Campaign)
                            try:
                                refresh_query = refresh_query.options(defer(Campaign.cornerstone_platform))
                            except (AttributeError, Exception):
                                pass
                            campaigns = refresh_query.filter(Campaign.user_id == current_user.id).all()
                            logger.info(f"✅ Refreshed campaigns list for user {current_user.id} after creating demo campaign")
                        except Exception as refresh_error:
                            logger.warning(f"⚠️ Failed to refresh campaigns after demo creation, using existing list: {refresh_error}")
                            # Continue with existing campaigns list
                    else:
                        # For admin users, just add it to the list if not already present
                        try:
                            refresh_query = db.query(Campaign)
                            try:
                                refresh_query = refresh_query.options(defer(Campaign.cornerstone_platform))
                            except (AttributeError, Exception):
                                pass
                            user_demo_campaign = refresh_query.filter(
                                Campaign.campaign_id == user_demo_campaign_id,
                                Campaign.user_id == current_user.id
                            ).first()
                            if user_demo_campaign and not any(c.campaign_id == user_demo_campaign_id for c in campaigns):
                                campaigns.append(user_demo_campaign)
                                logger.info(f"✅ Added user demo campaign {user_demo_campaign_id} to admin user {current_user.id}'s campaign list")
                        except Exception as refresh_error:
                            logger.warning(f"⚠️ Failed to fetch demo campaign for admin, skipping: {refresh_error}")
                else:
                    logger.warning(f"⚠️ Could not create demo campaign for user {current_user.id}")
                    # Check if template exists (use safe query)
                    try:
                        template_check_query = db.query(Campaign)
                        try:
                            template_check_query = template_check_query.options(defer(Campaign.cornerstone_platform))
                        except (AttributeError, Exception):
                            pass
                        template_exists = template_check_query.filter(Campaign.campaign_id == DEMO_CAMPAIGN_ID).first()
                    except Exception as template_check_error:
                        logger.warning(f"⚠️ Failed to check for template campaign: {template_check_error}")
                        template_exists = None
                    if not template_exists:
                        logger.error(f"❌ Template demo campaign {DEMO_CAMPAIGN_ID} does not exist in database!")
                        logger.error(f"❌ This is a critical error - template campaign must exist for demo campaign creation to work")
            else:
                logger.info(f"✅ User {current_user.id} already has demo campaign: {user_has_demo.campaign_id}")
                # Ensure it's in the campaigns list (refresh for non-admin if needed)
                if not any(c.campaign_id == user_has_demo.campaign_id for c in campaigns):
                    if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
                        # For non-admin, refresh the list to ensure we have the latest data
                        # Use safe query with defer to avoid column errors
                        try:
                            refresh_query = db.query(Campaign)
                            try:
                                refresh_query = refresh_query.options(defer(Campaign.cornerstone_platform))
                            except (AttributeError, Exception):
                                pass
                            campaigns = refresh_query.filter(Campaign.user_id == current_user.id).all()
                            logger.info(f"✅ Refreshed campaigns list for user {current_user.id} to include existing demo campaign")
                        except Exception as refresh_error:
                            logger.warning(f"⚠️ Failed to refresh campaigns, using existing list: {refresh_error}")
                            # Add the demo campaign to existing list if not present
                            campaigns.append(user_has_demo)
                    else:
                        campaigns.append(user_has_demo)
                        logger.info(f"✅ Added existing demo campaign {user_has_demo.campaign_id} to admin user {current_user.id}'s campaign list")
        except Exception as demo_error:
            logger.error(f"❌ Error handling demo campaign for user {current_user.id}: {demo_error}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Continue without demo campaign - don't break the endpoint
        
        # Sort campaigns: demo campaign first, then by created_at
        from datetime import datetime as dt
        campaigns.sort(key=lambda c: (
            0 if c.campaign_name and c.campaign_name.startswith("Demo Campaign") else 1,
            c.created_at or dt.min
        ))
        
        # If no campaigns found for user, also check total campaigns for debugging
        # Use safe query to avoid column errors
        try:
            total_campaigns_query = db.query(Campaign)
            try:
                total_campaigns_query = total_campaigns_query.options(defer(Campaign.cornerstone_platform))
            except (AttributeError, Exception):
                pass
            total_campaigns = total_campaigns_query.count()
            if len(campaigns) == 0 and total_campaigns > 0:
                logger.warning(f"⚠️ User {current_user.id} has 0 campaigns, but database has {total_campaigns} total campaigns. This may indicate a user_id mismatch.")
                # Show sample campaign user_ids for debugging
                try:
                    sample_query = db.query(Campaign)
                    try:
                        sample_query = sample_query.options(defer(Campaign.cornerstone_platform))
                    except (AttributeError, Exception):
                        pass
                    sample_campaigns = sample_query.limit(5).all()
                    sample_user_ids = [c.user_id for c in sample_campaigns]
                    logger.info(f"Sample campaign user_ids in database: {sample_user_ids}")
                except Exception as sample_error:
                    logger.warning(f"⚠️ Failed to fetch sample campaigns for debugging: {sample_error}")
        except Exception as total_error:
            logger.warning(f"⚠️ Failed to check total campaigns count: {total_error}")
        # Get user info for campaigns (to show username/email)
        from models import User
        user_cache = {}
        for campaign in campaigns:
            if campaign.user_id and campaign.user_id not in user_cache:
                user = db.query(User).filter(User.id == campaign.user_id).first()
                if user:
                    user_cache[campaign.user_id] = {
                        "username": user.username,
                        "email": user.email
                    }
        
        # Build campaigns response with error handling for each field
        campaigns_list = []
        for campaign in campaigns:
            try:
                # Safely parse custom_keywords_json
                custom_keywords = []
                if campaign.custom_keywords_json:
                    try:
                        custom_keywords = json.loads(campaign.custom_keywords_json)
                        if not isinstance(custom_keywords, list):
                            custom_keywords = []
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse custom_keywords_json for campaign {campaign.id}: {e}")
                        custom_keywords = []
                
                # Safely format dates
                created_at = None
                if campaign.created_at:
                    try:
                        created_at = campaign.created_at.isoformat()
                    except (AttributeError, ValueError) as e:
                        logger.warning(f"Failed to format created_at for campaign {campaign.id}: {e}")
                
                updated_at = None
                if campaign.updated_at:
                    try:
                        updated_at = campaign.updated_at.isoformat()
                    except (AttributeError, ValueError) as e:
                        logger.warning(f"Failed to format updated_at for campaign {campaign.id}: {e}")
                
                campaigns_list.append({
                    "id": campaign.id,
                    "campaign_id": campaign.campaign_id,
                    "name": campaign.campaign_name or "",
                    "description": campaign.description or "",
                    "type": campaign.type or "",
                    "query": campaign.query or "",
                    "keywords": campaign.keywords.split(",") if campaign.keywords else [],
                    "urls": campaign.urls.split(",") if campaign.urls else [],
                    "trending_topics": campaign.trending_topics.split(",") if campaign.trending_topics else [],
                    "topics": campaign.topics.split(",") if campaign.topics else [],
                    "status": campaign.status or "INCOMPLETE",
                    "user_id": campaign.user_id,
                    "user_username": user_cache.get(campaign.user_id, {}).get("username") if campaign.user_id else None,
                    "user_email": user_cache.get(campaign.user_id, {}).get("email") if campaign.user_id else None,
                    "createdAt": created_at,  # Use camelCase for frontend
                    "updated_at": updated_at,
                    "custom_keywords": custom_keywords,
                    "cornerstone_platform": _safe_getattr(campaign, 'cornerstone_platform')
                })
            except Exception as e:
                logger.error(f"Error processing campaign {campaign.id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Skip this campaign but continue with others
                continue
        
        logger.info(f"✅ Successfully processed {len(campaigns_list)} campaigns")
        return {
            "status": "success",
            "campaigns": campaigns_list
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching campaigns: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch campaigns: {str(e)}"
        )

@campaigns_router.post("/campaigns")
def create_campaign(campaign_data: CampaignCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create campaign for the authenticated user - REQUIRES AUTHENTICATION"""
    try:
        from models import Campaign
        
        logger.info(f"Creating campaign: {campaign_data.name} for user {current_user.id}")
        
        # Generate unique campaign ID
        campaign_id = str(uuid.uuid4())
        
        # Convert lists to comma-separated strings for database storage (matching model)
        keywords_str = ",".join(campaign_data.keywords) if campaign_data.keywords else None
        urls_str = ",".join(campaign_data.urls) if campaign_data.urls else None
        trending_topics_str = ",".join(campaign_data.trendingTopics) if campaign_data.trendingTopics else None
        topics_str = ",".join(campaign_data.topics) if campaign_data.topics else None
        
        # Save settings as JSON strings
        extraction_settings_json = None
        if campaign_data.extractionSettings:
            extraction_settings_json = json.dumps(campaign_data.extractionSettings)
        
        preprocessing_settings_json = None
        if campaign_data.preprocessingSettings:
            preprocessing_settings_json = json.dumps(campaign_data.preprocessingSettings)
        
        entity_settings_json = None
        if campaign_data.entitySettings:
            entity_settings_json = json.dumps(campaign_data.entitySettings)
        
        modeling_settings_json = None
        if campaign_data.modelingSettings:
            modeling_settings_json = json.dumps(campaign_data.modelingSettings)
        
        # Handle Site Builder specific fields
        site_base_url = getattr(campaign_data, 'site_base_url', None)
        target_keywords_json = None
        if hasattr(campaign_data, 'target_keywords') and campaign_data.target_keywords:
            target_keywords_json = json.dumps(campaign_data.target_keywords)
        top_ideas_count = getattr(campaign_data, 'top_ideas_count', None)
        
        # Create campaign directly using SQLAlchemy
        campaign = Campaign(
            campaign_id=campaign_id,
            campaign_name=campaign_data.name,
            description=campaign_data.description,
            query=campaign_data.query or campaign_data.name,  # Use query if provided, otherwise use name
            type=campaign_data.type,
            keywords=keywords_str,
            urls=urls_str,
            trending_topics=trending_topics_str,
            topics=topics_str,
            status=campaign_data.status or "INCOMPLETE",  # Use provided status or default to INCOMPLETE
            user_id=current_user.id,  # Use authenticated user
            extraction_settings_json=extraction_settings_json,
            preprocessing_settings_json=preprocessing_settings_json,
            entity_settings_json=entity_settings_json,
            modeling_settings_json=modeling_settings_json,
            site_base_url=site_base_url,
            target_keywords_json=target_keywords_json,
            top_ideas_count=top_ideas_count
        )
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"Campaign created successfully: {campaign_id}")
        
        return {
            "status": "success",
            "message": {
                "campaign_id": campaign_id,
                "id": campaign_id,
                "name": campaign_data.name,
                "description": campaign_data.description,
                "type": campaign_data.type,
                "status": campaign.status  # Return actual campaign status from database
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating campaign: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}"
        )

@campaigns_router.get("/campaigns/{campaign_id}")
def get_campaign_by_id(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get campaign by ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Campaign
        from sqlalchemy.orm import defer
        
        # Check if this is a request for the template demo campaign
        # If so, create/return user's copy instead
        if campaign_id == DEMO_CAMPAIGN_ID:
            user_demo_campaign_id = create_user_demo_campaign(current_user.id, db)
            if user_demo_campaign_id:
                campaign_id = user_demo_campaign_id
                logger.info(f"Redirected template demo request to user's copy: {user_demo_campaign_id}")
        
        # Verify ownership
        # Exclude potentially missing columns from query to avoid SQL errors
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found or access denied"
            )
        
        # Parse settings from JSON strings
        extraction_settings = None
        if campaign.extraction_settings_json:
            try:
                extraction_settings = json.loads(campaign.extraction_settings_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse extraction_settings_json for campaign {campaign_id}")
        
        preprocessing_settings = None
        if campaign.preprocessing_settings_json:
            try:
                preprocessing_settings = json.loads(campaign.preprocessing_settings_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse preprocessing_settings_json for campaign {campaign_id}")
        
        entity_settings = None
        if campaign.entity_settings_json:
            try:
                entity_settings = json.loads(campaign.entity_settings_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse entity_settings_json for campaign {campaign_id}")
        
        modeling_settings = None
        if campaign.modeling_settings_json:
            try:
                modeling_settings = json.loads(campaign.modeling_settings_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse modeling_settings_json for campaign {campaign_id}")
        
        # Custom keywords/ideas
        custom_keywords = []
        if campaign.custom_keywords_json:
            try:
                custom_keywords = json.loads(campaign.custom_keywords_json)
            except (json.JSONDecodeError, TypeError):
                custom_keywords = []
        
        # Image settings (handle missing column gracefully with try-except)
        image_settings = None
        try:
            # Try to access the column - will raise AttributeError if column doesn't exist
            img_settings_json = campaign.image_settings_json
            if img_settings_json:
                image_settings = json.loads(img_settings_json)
        except (AttributeError, json.JSONDecodeError, TypeError):
            # Column doesn't exist or invalid JSON - return None
            image_settings = None
        
        return {
            "status": "success",
            "campaign": {
                "id": campaign.id,
                "campaign_id": campaign.campaign_id,
                "name": campaign.campaign_name,
                "description": campaign.description,
                "type": campaign.type,
                "query": campaign.query,
                "keywords": campaign.keywords.split(",") if campaign.keywords else [],
                "urls": campaign.urls.split(",") if campaign.urls else [],
                "trending_topics": campaign.trending_topics.split(",") if campaign.trending_topics else [],
                "topics": campaign.topics.split(",") if campaign.topics else [],
                "status": campaign.status or "INCOMPLETE",  # Include status field
                "user_id": campaign.user_id,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
                "extractionSettings": extraction_settings,
                "preprocessingSettings": preprocessing_settings,
                "entitySettings": entity_settings,
                "modelingSettings": modeling_settings,
                # Site Builder specific fields (safely access potentially missing columns)
                "site_base_url": _safe_getattr(campaign, 'site_base_url'),
                "target_keywords": _safe_get_json(campaign, 'target_keywords_json'),
                "top_ideas_count": _safe_getattr(campaign, 'top_ideas_count'),
                # Custom keywords/ideas
                "custom_keywords": custom_keywords,
                # Image settings
                "image_settings": image_settings,
                # Content queue items
                "content_queue_items_json": _safe_getattr(campaign, 'content_queue_items_json'),
                # Research selections
                "research_selections_json": _safe_getattr(campaign, 'research_selections_json'),
                # Cornerstone platform
                "cornerstone_platform": _safe_getattr(campaign, 'cornerstone_platform'),
                # Look Alike specific fields
                "articles_url": _safe_getattr(campaign, 'articles_url')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching campaign: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch campaign: {str(e)}"
        )

@campaigns_router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Campaign
        
        # Check if this is a request for the template demo campaign
        # If so, redirect to user's copy
        if campaign_id == DEMO_CAMPAIGN_ID:
            user_demo_campaign_id = create_user_demo_campaign(current_user.id, db)
            if user_demo_campaign_id:
                campaign_id = user_demo_campaign_id
                logger.info(f"Redirected template demo update request to user's copy: {user_demo_campaign_id}")
        
        # Verify ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found or access denied"
            )
        
        # Track if processing-related fields are being modified
        # If so, set status to INCOMPLETE so "Build Campaign Base" appears
        processing_fields_changed = False
        
        # Update fields if provided
        if campaign_data.status is not None:
            campaign.status = campaign_data.status
        if campaign_data.name is not None:
            campaign.campaign_name = campaign_data.name
        if campaign_data.description is not None:
            campaign.description = campaign_data.description
        if campaign_data.type is not None:
            if campaign.type != campaign_data.type:
                processing_fields_changed = True
            campaign.type = campaign_data.type
        if campaign_data.keywords is not None:
            new_keywords = ",".join(campaign_data.keywords) if campaign_data.keywords else None
            if campaign.keywords != new_keywords:
                processing_fields_changed = True
            campaign.keywords = new_keywords
        if campaign_data.urls is not None:
            new_urls = ",".join(campaign_data.urls) if campaign_data.urls else None
            if campaign.urls != new_urls:
                processing_fields_changed = True
            campaign.urls = new_urls
        if campaign_data.query is not None:
            if campaign.query != campaign_data.query:
                processing_fields_changed = True
            campaign.query = campaign_data.query
        if campaign_data.trendingTopics is not None:
            new_trending = ",".join(campaign_data.trendingTopics) if campaign_data.trendingTopics else None
            if campaign.trending_topics != new_trending:
                processing_fields_changed = True
            campaign.trending_topics = new_trending
        if campaign_data.topics is not None:
            campaign.topics = ",".join(campaign_data.topics) if campaign_data.topics else None
        
        # Save settings as JSON strings in Text columns
        # These are processing-related fields - changes require re-processing
        if campaign_data.extractionSettings is not None:
            old_extraction = campaign.extraction_settings_json
            campaign.extraction_settings_json = json.dumps(campaign_data.extractionSettings)
            if old_extraction != campaign.extraction_settings_json:
                processing_fields_changed = True
            logger.info(f"Saved extractionSettings for campaign {campaign_id}: {campaign_data.extractionSettings}")
        if campaign_data.preprocessingSettings is not None:
            old_preprocessing = campaign.preprocessing_settings_json
            campaign.preprocessing_settings_json = json.dumps(campaign_data.preprocessingSettings)
            if old_preprocessing != campaign.preprocessing_settings_json:
                processing_fields_changed = True
            logger.info(f"Saved preprocessingSettings for campaign {campaign_id}: {campaign_data.preprocessingSettings}")
        if campaign_data.entitySettings is not None:
            old_entity = campaign.entity_settings_json
            campaign.entity_settings_json = json.dumps(campaign_data.entitySettings)
            if old_entity != campaign.entity_settings_json:
                processing_fields_changed = True
            logger.info(f"Saved entitySettings for campaign {campaign_id}: {campaign_data.entitySettings}")
        if campaign_data.modelingSettings is not None:
            old_modeling = campaign.modeling_settings_json
            campaign.modeling_settings_json = json.dumps(campaign_data.modelingSettings)
            if old_modeling != campaign.modeling_settings_json:
                processing_fields_changed = True
            logger.info(f"Saved modelingSettings for campaign {campaign_id}: {campaign_data.modelingSettings}")
        if campaign_data.custom_keywords is not None:
            campaign.custom_keywords_json = json.dumps(campaign_data.custom_keywords)
            logger.info(f"Saved custom_keywords for campaign {campaign_id}: {campaign_data.custom_keywords}")
        if campaign_data.personality_settings_json is not None:
            campaign.personality_settings_json = campaign_data.personality_settings_json
            logger.info(f"Saved personality_settings_json for campaign {campaign_id}: {campaign_data.personality_settings_json}")
        if campaign_data.image_settings_json is not None:
            try:
                campaign.image_settings_json = campaign_data.image_settings_json
                logger.info(f"Saved image_settings_json for campaign {campaign_id}: {campaign_data.image_settings_json}")
            except AttributeError:
                logger.warning(f"image_settings_json column does not exist in database for campaign {campaign_id}")
        if campaign_data.scheduling_settings_json is not None:
            campaign.scheduling_settings_json = campaign_data.scheduling_settings_json
            logger.info(f"Saved scheduling_settings_json for campaign {campaign_id}")
        if campaign_data.content_queue_items_json is not None:
            campaign.content_queue_items_json = campaign_data.content_queue_items_json
            logger.info(f"Saved content_queue_items_json for campaign {campaign_id}")
        
        if campaign_data.research_selections_json is not None:
            campaign.research_selections_json = campaign_data.research_selections_json
            logger.info(f"Saved research_selections_json for campaign {campaign_id}")
        
        if campaign_data.cornerstone_platform is not None:
            campaign.cornerstone_platform = campaign_data.cornerstone_platform
            logger.info(f"Saved cornerstone_platform for campaign {campaign_id}: {campaign_data.cornerstone_platform}")
        
        # Site Builder specific fields - changes require re-processing
        if hasattr(campaign_data, 'site_base_url') and campaign_data.site_base_url is not None:
            old_site_base_url = _safe_getattr(campaign, 'site_base_url')
            if old_site_base_url != campaign_data.site_base_url:
                processing_fields_changed = True
            campaign.site_base_url = campaign_data.site_base_url
        
        if hasattr(campaign_data, 'target_keywords') and campaign_data.target_keywords is not None:
            old_target_keywords = _safe_get_json(campaign, 'target_keywords_json')
            new_target_keywords_json = json.dumps(campaign_data.target_keywords)
            if old_target_keywords != new_target_keywords_json:
                processing_fields_changed = True
            campaign.target_keywords_json = new_target_keywords_json
        
        # If processing-related fields changed, set status to INCOMPLETE
        # This ensures "Build Campaign Base" button appears so user can re-process
        if processing_fields_changed and campaign.status in ["READY_TO_ACTIVATE", "ACTIVE", "NO_CHANGES"]:
            campaign.status = "INCOMPLETE"
            logger.info(f"Campaign {campaign_id} processing fields changed - set status to INCOMPLETE for re-processing")
        
        campaign.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"Campaign updated successfully: {campaign_id}")
        return {
            "status": "success",
            "message": {
                "campaign_id": campaign.campaign_id,
                "id": campaign.campaign_id,
                "name": campaign.campaign_name,
                "status": campaign.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update campaign: {str(e)}"
        )

@campaigns_router.post("/campaigns/{campaign_id}/duplicate")
def duplicate_campaign(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Duplicate a campaign with all processed data - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    
    This endpoint:
    1. Creates a new campaign with all settings from the original
    2. Copies all CampaignRawData entries (processed posts, entities, etc.)
    3. Copies all research insights and research data
    4. Does NOT trigger new processing - duplicate has all original data
    
    The duplicate campaign will have the same processed data as the original,
    so "Build Campaign Base" is not needed unless you want to re-process.
    """
    try:
        from models import Campaign, CampaignRawData, CampaignResearchInsights, CampaignResearchData
        
        # Get original campaign
        original_campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not original_campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found or access denied"
            )
        
        # Generate new campaign ID
        new_campaign_id = str(uuid.uuid4())
        new_campaign_name = f"{original_campaign.campaign_name} Duplicate"
        
        logger.info(f"Duplicating campaign {campaign_id} -> {new_campaign_id} for user {current_user.id}")
        
        # Create new campaign with all settings from original
        new_campaign = Campaign(
            campaign_id=new_campaign_id,
            campaign_name=new_campaign_name,
            description=original_campaign.description,
            query=original_campaign.query,
            type=original_campaign.type,
            keywords=original_campaign.keywords,
            urls=original_campaign.urls,
            trending_topics=original_campaign.trending_topics,
            topics=original_campaign.topics,  # Copy processed topics
            status=original_campaign.status,  # Copy status (if READY_TO_ACTIVATE, duplicate is also ready)
            user_id=current_user.id,
            extraction_settings_json=original_campaign.extraction_settings_json,
            preprocessing_settings_json=original_campaign.preprocessing_settings_json,
            entity_settings_json=original_campaign.entity_settings_json,
            modeling_settings_json=original_campaign.modeling_settings_json,
            scheduling_settings_json=original_campaign.scheduling_settings_json,
            campaign_plan_json=original_campaign.campaign_plan_json,
            content_queue_items_json=original_campaign.content_queue_items_json,
            research_selections_json=original_campaign.research_selections_json,
            custom_keywords_json=original_campaign.custom_keywords_json,
            personality_settings_json=original_campaign.personality_settings_json,
            cornerstone_platform=_safe_getattr(original_campaign, 'cornerstone_platform'),
            site_base_url=_safe_getattr(original_campaign, 'site_base_url'),
            target_keywords_json=_safe_get_json(original_campaign, 'target_keywords_json'),
            gap_analysis_results_json=_safe_get_json(original_campaign, 'gap_analysis_results_json'),
            top_ideas_count=_safe_getattr(original_campaign, 'top_ideas_count') or 10,
        )
        
        db.add(new_campaign)
        db.flush()  # Flush to get the new campaign ID without committing
        
        # Copy all CampaignRawData entries (processed posts, entities, etc.)
        original_raw_data = db.query(CampaignRawData).filter(
            CampaignRawData.campaign_id == campaign_id
        ).all()
        
        raw_data_count = 0
        for raw_data in original_raw_data:
            new_raw_data = CampaignRawData(
                campaign_id=new_campaign_id,
                source_url=raw_data.source_url,
                fetched_at=raw_data.fetched_at,
                raw_html=raw_data.raw_html,
                extracted_text=raw_data.extracted_text,
                meta_json=raw_data.meta_json,
                content_hash=raw_data.content_hash,
            )
            db.add(new_raw_data)
            raw_data_count += 1
        
        # Copy all CampaignResearchInsights
        original_insights = db.query(CampaignResearchInsights).filter(
            CampaignResearchInsights.campaign_id == campaign_id
        ).all()
        
        insights_count = 0
        for insight in original_insights:
            new_insight = CampaignResearchInsights(
                campaign_id=new_campaign_id,
                agent_type=insight.agent_type,
                insights_text=insight.insights_text,
                created_at=insight.created_at,
            )
            db.add(new_insight)
            insights_count += 1
        
        # Copy CampaignResearchData (only one record per campaign due to unique constraint)
        original_research_data = db.query(CampaignResearchData).filter(
            CampaignResearchData.campaign_id == campaign_id
        ).first()
        
        research_data_count = 0
        if original_research_data:
            new_research_data = CampaignResearchData(
                campaign_id=new_campaign_id,
                word_cloud_json=original_research_data.word_cloud_json,
                topics_json=original_research_data.topics_json,
                hashtags_json=original_research_data.hashtags_json,
                entities_json=original_research_data.entities_json,
                created_at=original_research_data.created_at,
            )
            db.add(new_research_data)
            research_data_count = 1
        
        db.commit()
        
        logger.info(f"✅ Campaign duplicated successfully: {new_campaign_id} (copied {raw_data_count} raw data entries, {insights_count} insights, {research_data_count} research data)")
        
        return {
            "status": "success",
            "message": {
                "campaign_id": new_campaign_id,
                "id": new_campaign_id,
                "name": new_campaign_name,
                "status": new_campaign.status,
                "copied_data": {
                    "raw_data_entries": raw_data_count,
                    "research_insights": insights_count,
                    "research_data": research_data_count,
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error duplicating campaign: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate campaign: {str(e)}"
        )

@campaigns_router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION (or admin)
    For demo campaign, creates a user-specific exclusion instead of deleting"""
    try:
        from models import Campaign, User
        
        # Prevent deletion of template demo campaign
        if campaign_id == DEMO_CAMPAIGN_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete template demo campaign"
            )
        
        # Verify ownership (or allow admin to delete any campaign)
        is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
        if is_admin:
            # Admin can delete any campaign (except template demo)
            if campaign_id == DEMO_CAMPAIGN_ID:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete template demo campaign"
                )
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            logger.info(f"Admin user {current_user.id} deleting campaign {campaign_id} (owner: {campaign.user_id if campaign else 'not found'})")
        else:
            # Regular users can only delete their own campaigns (including their demo copy)
            campaign = db.query(Campaign).filter(
                Campaign.campaign_id == campaign_id,
                Campaign.user_id == current_user.id
            ).first()
        
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found or access denied"
            )
        
        # Delete associated raw data (cascade delete)
        from models import CampaignRawData
        raw_data_count = db.query(CampaignRawData).filter(
            CampaignRawData.campaign_id == campaign_id
        ).count()
        if raw_data_count > 0:
            db.query(CampaignRawData).filter(
                CampaignRawData.campaign_id == campaign_id
            ).delete()
            logger.info(f"Deleted {raw_data_count} raw data records for campaign {campaign_id}")
        
        db.delete(campaign)
        db.commit()
        logger.info(f"Campaign deleted successfully: {campaign_id}")
        return {
            "status": "success",
            "message": "Campaign deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete campaign"
        )

