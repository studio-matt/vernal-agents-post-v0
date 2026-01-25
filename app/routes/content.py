"""
Content generation, scheduling, and image endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Form
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal

logger = logging.getLogger(__name__)

content_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import shared utilities from main (TODO: move to app/utils in future refactor)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.utils.openai_helpers import get_openai_api_key
from app.utils.content_tasks import CONTENT_GEN_TASKS, CONTENT_GEN_TASK_INDEX
from app.schemas.models import AnalyzeRequest

@content_router.post("/analyze/test")
def test_analyze_endpoint():
    """Simple test endpoint to verify /analyze route is working"""
    return {"status": "ok", "message": "Test endpoint is reachable"}

@content_router.post("/analyze")
def analyze_campaign(analyze_data: AnalyzeRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Analyze campaign - Stub endpoint (returns task_id for now)
    TODO: Implement full analysis workflow
    
    IMPORTANT: This endpoint should NOT delete campaigns. It only starts analysis.
    REQUIRES AUTHENTICATION
    """
    try:
        logger.info(f"🔍 /analyze endpoint called - starting request processing")
        logger.info(f"🔍 SUCCESS: Request reached endpoint - Pydantic validation passed")
        logger.info(f"🔍 analyze_data type: {type(analyze_data)}")
        logger.info(f"🔍 analyze_data received: campaign_id={getattr(analyze_data, 'campaign_id', 'N/A')}, type={getattr(analyze_data, 'type', 'N/A')}")
        logger.info(f"🔍 current_user: {current_user}, user_id: {getattr(current_user, 'id', 'N/A')}")
        logger.info(f"🔍 db session: {db}")
        
        # Log all fields for debugging
        try:
            if hasattr(analyze_data, 'model_dump'):
                all_fields = analyze_data.model_dump()
            elif hasattr(analyze_data, 'dict'):
                all_fields = analyze_data.dict()
            else:
                all_fields = {k: getattr(analyze_data, k, None) for k in dir(analyze_data) if not k.startswith('_')}
            logger.info(f"🔍 All analyze_data fields: {json.dumps({k: str(v)[:100] for k, v in all_fields.items()}, indent=2)}")
        except Exception as log_err:
            logger.warning(f"⚠️ Could not log all fields: {log_err}")
        user_id = current_user.id
        campaign_id = analyze_data.campaign_id or f"campaign-{uuid.uuid4()}"
        campaign_name = analyze_data.campaign_name or "Unknown Campaign"
        logger.info(f"🔍 User ID: {user_id}, Campaign ID: {campaign_id}, Campaign Name: {campaign_name}")
        
        # If campaign_id is provided, verify ownership (or allow admin)
        if analyze_data.campaign_id:
            from models import Campaign
            is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
            if is_admin:
                # Admin can build any campaign
                campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
                if campaign:
                    logger.info(f"Admin user {current_user.id} building campaign {campaign_id} (owner: {campaign.user_id})")
            else:
                # Regular users can only build their own campaigns
                campaign = db.query(Campaign).filter(
                    Campaign.campaign_id == campaign_id,
                    Campaign.user_id == current_user.id
                ).first()
            
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found or access denied"
                )
        
        logger.info(f"🔍 /analyze POST endpoint called for campaign: {campaign_name} (ID: {campaign_id}) by user {user_id}")
        logger.info(f"🔍 Request data: campaign_name={analyze_data.campaign_name}, type={analyze_data.type}, keywords={len(analyze_data.keywords or [])} keywords")
        logger.info(f"🔍 CRITICAL: Keywords received from frontend: {analyze_data.keywords}")
        if analyze_data.keywords:
            logger.info(f"🔍 First keyword: '{analyze_data.keywords[0]}'")
        
        # Log Site Builder specific fields
        if analyze_data.type == "site_builder":
            logger.info(f"🏗️ Site Builder: site_base_url={analyze_data.site_base_url}")
            logger.info(f"🏗️ Site Builder: target_keywords={analyze_data.target_keywords}")
            logger.info(f"🏗️ Site Builder: top_ideas_count={analyze_data.top_ideas_count}")
        
        # CRITICAL: Validate Site Builder requirements BEFORE creating task
        # This prevents campaigns from showing progress when they should fail immediately
        if analyze_data.type == "site_builder":
            from models import Campaign
            import json
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            
            # Get site_base_url - check request first, then database
            site_url = analyze_data.site_base_url
            if not site_url and campaign:
                site_url = campaign.site_base_url
            
            # Update campaign with site_base_url if provided in request but missing in DB
            if site_url and campaign and not campaign.site_base_url:
                campaign.site_base_url = site_url
                db.commit()
                logger.info(f"✅ Saved site_base_url to database during validation: {site_url}")
            
            # Update other Site Builder fields if provided
            if campaign:
                updated = False
                try:
                    if analyze_data.target_keywords:
                        # Ensure target_keywords is a list/array that can be serialized
                        if isinstance(analyze_data.target_keywords, list):
                            campaign.target_keywords_json = json.dumps(analyze_data.target_keywords)
                        else:
                            campaign.target_keywords_json = json.dumps([analyze_data.target_keywords])
                        updated = True
                    if analyze_data.top_ideas_count:
                        campaign.top_ideas_count = analyze_data.top_ideas_count
                        updated = True
                    if updated:
                        db.commit()
                        logger.info(f"✅ Campaign {campaign_id} updated with Site Builder fields")
                except Exception as update_error:
                    logger.error(f"❌ Error updating Site Builder fields: {update_error}")
                    # Don't fail the request, just log the error
                    db.rollback()
            
            # FAIL IMMEDIATELY if site_base_url is missing - don't create task
            if not site_url or not site_url.strip():
                logger.error(f"❌ Site Builder campaign requires site_base_url - FAILING BEFORE TASK CREATION")
                logger.error(f"❌ Request data.site_base_url: {analyze_data.site_base_url}")
                logger.error(f"❌ Campaign {campaign_id} has site_base_url=NULL in database")
                
                # Create error row so user can see what went wrong
                try:
                    from models import CampaignRawData
                    # datetime is already imported at top of file
                    error_row = CampaignRawData(
                        campaign_id=campaign_id,
                        source_url=f"error:missing_site_base_url",
                        fetched_at=datetime.utcnow(),
                        raw_html=None,
                        extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {analyze_data.type}\n- Request site_base_url: {analyze_data.site_base_url}\n- Request URLs: {analyze_data.urls if hasattr(analyze_data, 'urls') else 'N/A'}",
                        meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": analyze_data.type})
                    )
                    db.add(error_row)
                    if campaign:
                        campaign.status = "INCOMPLETE"
                    db.commit()
                    logger.error(f"❌ Created error row for campaign {campaign_id} - missing site_base_url")
                except Exception as error_row_error:
                    logger.error(f"❌ Failed to create error row: {error_row_error}")
                    # Don't fail the request, just log the error
                    db.rollback()
                
                # Return error response - don't create task
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL."
                )
        
        # Verify campaign exists and update Site Builder fields if provided (for non-Site Builder campaigns)
        try:
            from models import Campaign
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if campaign:
                logger.info(f"✅ Campaign {campaign_id} found in database (user_id: {campaign.user_id}, site_base_url: {campaign.site_base_url})")
            else:
                logger.warning(f"⚠️ Campaign {campaign_id} not found in database - analysis will continue anyway")
        except Exception as db_err:
            logger.warning(f"⚠️ Skipping campaign existence check: {db_err}")
        
        # Create task and seed progress (in-memory)
        # Only create task if validation passed (for Site Builder, this means site_base_url exists)
        try:
            task_id = str(uuid.uuid4())
            logger.info(f"🔍 Generated task_id: {task_id}")
            
            CONTENT_GEN_TASKS[task_id] = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "started_at": datetime.utcnow().isoformat(),
                "progress": 5,  # start at 5%
                "current_step": "initializing",
                "progress_message": "Starting analysis",
            }
            logger.info(f"🔍 Created CONTENT_GEN_TASKS entry for task_id: {task_id}")
            
            CONTENT_GEN_TASK_INDEX[campaign_id] = task_id
            logger.info(f"🔍 Created CONTENT_GEN_TASK_INDEX entry: {campaign_id} -> {task_id}")
            
            logger.info(f"✅ Analysis task created (stub): task_id={task_id}, campaign_id={campaign_id}, user_id={user_id}")
        except Exception as task_creation_error:
            logger.error(f"❌ CRITICAL: Failed to create task: {task_creation_error}")
            import traceback
            logger.error(f"❌ Task creation traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create analysis task: {str(task_creation_error)}"
            )
        
        # Kick off a lightweight background job to simulate real steps and persist raw data
        def run_analysis_background(tid: str, cid: str, data: Dict[str, Any]):
            from database import SessionLocal
            from models import CampaignRawData, Campaign
            from pydantic import ValidationError
            session = SessionLocal()
            try:
                logger.info(f"🔵 Background thread started for task {tid}, campaign {cid}")
                
                # Reconstruct AnalyzeRequest from dict
                try:
                    analyze_data = AnalyzeRequest(**data)
                    logger.info(f"✅ Reconstructed AnalyzeRequest from dict")
                except (ValidationError, TypeError) as ve:
                    logger.error(f"❌ Failed to reconstruct AnalyzeRequest from dict: {ve}")
                    # Create a minimal AnalyzeRequest with just the essential fields
                    analyze_data = AnalyzeRequest(
                        campaign_id=data.get('campaign_id'),
                        campaign_name=data.get('campaign_name'),
                        type=data.get('type', 'keyword'),
                        site_base_url=data.get('site_base_url'),
                        target_keywords=data.get('target_keywords'),
                        top_ideas_count=data.get('top_ideas_count', 10),
                        most_recent_urls=data.get('most_recent_urls'),
                        keywords=data.get('keywords', []),
                        urls=data.get('urls', []),
                        description=data.get('description'),
                        query=data.get('query'),
                    )
                    logger.info(f"✅ Created minimal AnalyzeRequest from dict")
                
                # Use analyze_data instead of data from now on
                data = analyze_data
                
                # Helper to update task atomically
                def set_task(step: str, prog: int, msg: str):
                    task = CONTENT_GEN_TASKS.get(tid)
                    if not task:
                        logger.warning(f"⚠️ Task {tid} not found in CONTENT_GEN_TASKS dict")
                        return
                    task["current_step"] = step
                    task["progress"] = prog
                    task["progress_message"] = msg
                    logger.info(f"📊 Task {tid}: {prog}% - {step} - {msg}")

                # CRITICAL: Check if raw_data already exists for this campaign
                # If it does, skip scraping to prevent re-scraping and data growth
                # Raw data should only be written during initial scrape
                existing_raw_data = session.query(CampaignRawData).filter(
                    CampaignRawData.campaign_id == cid,
                    ~CampaignRawData.source_url.startswith("error:"),
                    ~CampaignRawData.source_url.startswith("placeholder:")
                ).first()
                
                if existing_raw_data:
                    logger.info(f"📋 Raw data already exists for campaign {cid} - skipping scrape phase to prevent data growth")
                    logger.info(f"📋 Raw data was created at: {existing_raw_data.fetched_at}")
                    set_task("raw_data_exists", 50, "Raw data already exists - using existing data")
                    # Skip to completion - raw data is already available
                    # Research operations will read from existing raw_data
                    set_task("complete", 100, "Analysis complete - using existing raw data")
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        camp.status = "COMPLETE"
                        camp.updated_at = datetime.utcnow()
                        session.commit()
                    logger.info(f"✅ Skipped scraping for campaign {cid} - raw data already exists")
                    return  # Exit early - don't write any new raw_data

                # CRITICAL: Set campaign status to PROCESSING at the start of analysis
                try:
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        if camp.status != "PROCESSING":
                            camp.status = "PROCESSING"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Set campaign {cid} status to PROCESSING at analysis start")
                        else:
                            logger.info(f"ℹ️ Campaign {cid} already has PROCESSING status")
                    else:
                        logger.warning(f"⚠️ Campaign {cid} not found when trying to set PROCESSING status")
                except Exception as status_err:
                    logger.error(f"❌ Failed to set PROCESSING status for campaign {cid}: {status_err}")
                    # Don't fail the analysis, just log the error
                
                # Step 1: collecting inputs
                logger.info(f"📝 Step 1: Collecting inputs for campaign {cid}")
                set_task("collecting_inputs", 15, "Collecting inputs and settings")
                
                # Validate Site Builder requirements EARLY (fail at "Initializing" stage)
                if data.type == "site_builder":
                    from models import Campaign
                    # json is already imported globally at top of file
                    
                    # Get site URL - check request data first, then database
                    # DO NOT fall back to urls array - site_base_url must be explicitly set
                    site_url = getattr(data, 'site_base_url', None)
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    
                    if not site_url:
                        # Try to get from campaign in database
                        if camp and camp.site_base_url:
                            site_url = camp.site_base_url
                            logger.info(f"✅ Retrieved site_base_url from campaign database: {site_url}")
                        # NOTE: We intentionally do NOT fall back to data.urls - site_base_url must be explicitly saved
                        # This ensures the field is properly persisted in the database
                    elif camp and not camp.site_base_url:
                        # If site_url is in request but not in database, save it now
                        camp.site_base_url = site_url
                        session.commit()
                        logger.info(f"✅ Saved site_base_url to database during validation: {site_url}")
                    
                    # FAIL EARLY if site_base_url is missing (no fallback to urls array)
                    if not site_url or not site_url.strip():
                        logger.error(f"❌ Site Builder campaign requires site_base_url - FAILING AT INITIALIZING STAGE")
                        logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                        logger.error(f"❌ Request data.urls: {data.urls if hasattr(data, 'urls') else 'N/A'}")
                        logger.error(f"❌ Campaign {cid} has site_base_url=NULL in database")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:missing_site_base_url",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {data.type}\n- Request site_base_url: {getattr(data, 'site_base_url', None)}\n- Request URLs: {data.urls if hasattr(data, 'urls') else 'N/A'}",
                            meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": data.type})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - missing site_base_url")
                        
                        # Set campaign status to INCOMPLETE
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to missing site_base_url")
                        
                        # Set progress to error state - FAIL AT INITIALIZING STAGE
                        set_task("error", 15, "Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL.")
                        logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - site_base_url is missing")
                        return
                    
                    # VALIDATE URL FORMAT AND ACCESSIBILITY AT INITIALIZATION
                    logger.info(f"🔍 Validating site URL format and accessibility: {site_url}")
                    set_task("validating_url", 18, f"Validating site URL: {site_url}")
                    
                    try:
                        from sitemap_parser import validate_url_format, validate_url_accessibility, quick_sitemap_check
                    except ImportError as import_error:
                        logger.error(f"❌ Failed to import validation functions: {import_error}")
                        logger.error(f"❌ This is a critical error - validation cannot proceed")
                        # Don't fail the campaign, just log and continue without validation
                        logger.warning(f"⚠️ Continuing without URL validation - this should not happen")
                        # Skip validation and proceed to sitemap parsing
                        pass
                    else:
                        # Step 1: Validate URL format
                        try:
                            is_valid_format, format_error = validate_url_format(site_url)
                        except Exception as format_validation_error:
                            logger.error(f"❌ Error during URL format validation: {format_validation_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue
                            is_valid_format, format_error = True, None
                        
                        if not is_valid_format:
                            error_msg = f"Invalid URL format: {format_error}"
                            logger.error(f"❌ {error_msg}")
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:invalid_url_format",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Invalid URL format.\n\nError: {format_error}\n\nURL provided: {site_url}\n\nPlease edit the campaign and provide a valid URL starting with http:// or https://",
                                meta_json=json.dumps({"type": "error", "reason": "invalid_url_format", "site_url": site_url, "error": format_error})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 18, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - invalid URL format")
                            return
                    
                        # Step 2: Validate URL accessibility (DNS, connectivity, HTTP status)
                        logger.info(f"🔍 Checking if site is accessible: {site_url}")
                        try:
                            is_accessible, access_error, http_status = validate_url_accessibility(site_url, timeout=10)
                        except Exception as access_validation_error:
                            logger.error(f"❌ Error during URL accessibility validation: {access_validation_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue (validation is best effort)
                            is_accessible, access_error, http_status = True, None, None
                        
                        if not is_accessible:
                            error_msg = f"Site is not accessible: {access_error}"
                            logger.error(f"❌ {error_msg}")
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:site_not_accessible",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Site is not accessible.\n\nError: {access_error}\n\nURL: {site_url}\nHTTP Status: {http_status if http_status else 'N/A (connection failed)'}\n\nPossible reasons:\n- Domain does not exist (DNS error)\n- Server is down or not responding\n- Site requires authentication\n- Network connectivity issues\n\nPlease verify the URL is correct and the site is accessible.",
                                meta_json=json.dumps({"type": "error", "reason": "site_not_accessible", "site_url": site_url, "error": access_error, "http_status": http_status})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 18, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - site not accessible")
                            return
                    
                        logger.info(f"✅ Site URL is accessible: {site_url} (HTTP {http_status})")
                        
                        # Step 3: Quick sitemap check (fail early if sitemap definitely doesn't exist)
                        logger.info(f"🔍 Performing quick sitemap check: {site_url}")
                        set_task("checking_sitemap", 20, f"Checking for sitemap at {site_url}")
                        try:
                            sitemap_found, sitemap_url, sitemap_error = quick_sitemap_check(site_url, timeout=10)
                        except Exception as sitemap_check_error:
                            logger.error(f"❌ Error during quick sitemap check: {sitemap_check_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue (will try full parsing)
                            sitemap_found, sitemap_url, sitemap_error = False, None, None
                    
                        if not sitemap_found:
                            # If quick check fails, we'll still try full parsing, but log a warning
                            # Only fail if the error indicates the site itself is inaccessible
                            if sitemap_error and ("not accessible" in sitemap_error.lower() or "dns" in sitemap_error.lower() or "connection" in sitemap_error.lower()):
                                error_msg = f"Sitemap check failed: {sitemap_error}"
                                logger.error(f"❌ {error_msg}")
                                
                                error_row = CampaignRawData(
                                    campaign_id=cid,
                                    source_url=f"error:sitemap_check_failed",
                                    fetched_at=datetime.utcnow(),
                                    raw_html=None,
                                    extracted_text=f"Site Builder: Sitemap check failed during initialization.\n\nError: {sitemap_error}\n\nURL: {site_url}\n\nThis usually means:\n- The site is not accessible\n- DNS resolution failed\n- Network connectivity issues\n\nPlease verify the site is accessible and try again.",
                                    meta_json=json.dumps({"type": "error", "reason": "sitemap_check_failed", "site_url": site_url, "error": sitemap_error})
                                )
                                session.add(error_row)
                                if camp:
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                session.commit()
                                set_task("error", 20, error_msg)
                                logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - sitemap check failed")
                                return
                            else:
                                # Sitemap not found at common locations, but site is accessible
                                # We'll proceed to full parsing which will try more locations
                                logger.warning(f"⚠️ Sitemap not found at common locations, but site is accessible. Will attempt full discovery.")
                        else:
                            logger.info(f"✅ Sitemap found at: {sitemap_url}")
                
                time.sleep(1)  # Brief pause before proceeding

                # Step 2: Web scraping with DuckDuckGo + Playwright (or Site Builder sitemap parsing)
                logger.info(f"📝 Step 2: Starting content collection for campaign {cid} (type: {data.type})")
                set_task("fetching_content", 25, "Collecting content from site" if data.type == "site_builder" else "Searching web and scraping content")
                
                # Handle Site Builder campaign type
                if data.type == "site_builder":
                    from sitemap_parser import parse_sitemap_from_site
                    from gap_analysis import identify_content_gaps, rank_gaps_by_priority
                    from text_processing import extract_topics
                    import json
                    
                    # Get site URL and target keywords (we already validated it exists above)
                    # Use the site_url we validated in Step 1 - no need to check again
                    # If we got here, site_url was already validated and set
                    site_url = getattr(data, 'site_base_url', None)
                    if not site_url:
                        # Try to get from campaign in database (should already be there from validation)
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp and camp.site_base_url:
                            site_url = camp.site_base_url
                            logger.info(f"✅ Retrieved site_base_url from campaign database: {site_url}")
                        else:
                            # This should never happen if validation worked, but log error if it does
                            logger.error(f"❌ site_url is missing after validation - this should not happen")
                            logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                            logger.error(f"❌ Campaign {cid} site_base_url in database: {camp.site_base_url if camp else 'campaign not found'}")
                    
                    target_keywords = getattr(data, 'target_keywords', None) or data.keywords or []
                    top_ideas_count = getattr(data, 'top_ideas_count', 10)
                    
                    logger.info(f"🏗️ Site Builder: site_url={site_url}, target_keywords={target_keywords}, top_ideas_count={top_ideas_count}")
                    
                    # This check should never trigger now since we validate above, but keep as safety
                    if not site_url:
                        logger.error(f"❌ Site Builder campaign requires site_base_url")
                        logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                        logger.error(f"❌ Request data.urls: {data.urls if hasattr(data, 'urls') else 'N/A'}")
                        logger.error(f"❌ Campaign {cid} has site_base_url=NULL in database")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:missing_site_base_url",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {data.type}\n- Request site_base_url: {getattr(data, 'site_base_url', None)}\n- Request URLs: {data.urls if hasattr(data, 'urls') else 'N/A'}",
                            meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": data.type})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - missing site_base_url")
                        
                        # Set campaign status to INCOMPLETE
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to missing site_base_url")
                        
                        # Set progress to error state
                        set_task("error", 95, "Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL.")
                        logger.error(f"❌ Campaign {cid} analysis failed - site_base_url is missing")
                        return
                    
                    logger.info(f"🏗️ Site Builder: Parsing sitemap from {site_url}")
                    logger.info(f"🏗️ Site Builder: Site URL details - scheme: {urlparse(site_url).scheme}, netloc: {urlparse(site_url).netloc}")
                    set_task("parsing_sitemap", 30, f"Parsing sitemap from {site_url}")
                    
                    # Parse sitemap to get all URLs
                    logger.info(f"🏗️ Site Builder: Starting sitemap parsing for {site_url}")
                    # For Site Builder, ignore max_pages from extraction settings
                    # Use a high limit to get all URLs, then filter by most_recent_urls if provided
                    max_sitemap_urls = 10000  # High limit to get all URLs from sitemap
                    # Get most_recent_urls setting if provided
                    most_recent_urls = getattr(data, 'most_recent_urls', None)
                    logger.info(f"🔍 DEBUG: most_recent_urls value received: {most_recent_urls} (type: {type(most_recent_urls)})")
                    logger.info(f"🔍 DEBUG: data object has most_recent_urls attr: {hasattr(data, 'most_recent_urls')}")
                    if hasattr(data, 'most_recent_urls'):
                        logger.info(f"🔍 DEBUG: data.most_recent_urls = {getattr(data, 'most_recent_urls', 'NOT_FOUND')}")
                    if most_recent_urls:
                        logger.info(f"📅 Site Builder: Will filter to {most_recent_urls} most recent URLs by date")
                    else:
                        logger.warning(f"⚠️ Site Builder: most_recent_urls is None/0/empty - Will collect ALL URLs from sitemap (no date filter)")
                        logger.warning(f"⚠️ This means it will scrape all {len(sitemap_urls) if 'sitemap_urls' in locals() else 'unknown'} URLs instead of limiting to most recent")
                    
                    # Parse sitemap (we already validated accessibility at initialization, so this should work)
                    # But handle network failures gracefully with better error messages
                    try:
                        sitemap_urls = parse_sitemap_from_site(site_url, max_urls=max_sitemap_urls, most_recent=most_recent_urls)
                        logger.info(f"✅ Sitemap parsing complete: Found {len(sitemap_urls)} URLs from sitemap")
                        if len(sitemap_urls) > 0:
                            logger.info(f"✅ First 5 sitemap URLs: {sitemap_urls[:5]}")
                    except Exception as sitemap_error:
                        # Handle different types of errors with appropriate messages
                        error_str = str(sitemap_error).lower()
                        sitemap_urls = []
                        
                        # Check for timeout errors
                        if "timeout" in error_str or "timed out" in error_str:
                            logger.error(f"❌ Sitemap parsing timed out: {sitemap_error}")
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_timeout",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Sitemap parsing timed out.\n\nURL: {site_url}\n\nThis usually means:\n- The server is slow to respond\n- Network connectivity issues\n- The sitemap is very large\n\nPlease try again or check your network connection.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_timeout", "site_url": site_url})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, f"Sitemap parsing timed out for {site_url}")
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap parsing timed out")
                            return
                        # Check for connection errors
                        elif "connection" in error_str or "dns" in error_str or "refused" in error_str:
                            logger.error(f"❌ Sitemap parsing connection error: {sitemap_error}")
                            if "dns" in error_str or "name resolution" in error_str:
                                error_msg = "DNS resolution failed during sitemap parsing"
                            elif "refused" in error_str:
                                error_msg = "Connection refused during sitemap parsing"
                            else:
                                error_msg = f"Connection error: {str(sitemap_error)}"
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_connection_error",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Connection error during sitemap parsing.\n\nError: {error_msg}\n\nURL: {site_url}\n\nThis usually means:\n- Network connectivity issues\n- DNS resolution problems\n- Server is not accepting connections\n\nPlease check your network connection and try again.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_connection_error", "site_url": site_url, "error": error_msg})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap connection error")
                            return
                        # Handle all other exceptions
                        else:
                            logger.error(f"❌ Exception during sitemap parsing: {sitemap_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_parsing_exception",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Unexpected error during sitemap parsing.\n\nError: {str(sitemap_error)}\n\nURL: {site_url}\n\nPlease check the backend logs for more details.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_parsing_exception", "site_url": site_url, "error": str(sitemap_error)})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, f"Sitemap parsing failed: {str(sitemap_error)}")
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap parsing exception")
                            return
                    
                    if not sitemap_urls:
                        logger.error(f"❌ Site Builder: No URLs found in sitemap for {site_url}")
                        logger.error(f"❌ This could mean:")
                        logger.error(f"   1. sitemap.xml doesn't exist at common locations ({site_url}/sitemap.xml)")
                        logger.error(f"   2. sitemap is empty or malformed")
                        logger.error(f"   3. sitemap requires authentication")
                        logger.error(f"   4. sitemap is blocked by robots.txt or CDN")
                        logger.error(f"   5. Network/timeout issues accessing the sitemap")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:sitemap_parsing_failed",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Failed to parse sitemap from {site_url}. No URLs found.\n\nPossible reasons:\n- sitemap.xml doesn't exist at {site_url}/sitemap.xml\n- sitemap is empty or malformed\n- sitemap requires authentication\n- Network/timeout issues\n\nPlease verify the sitemap exists and is accessible. You can check by visiting {site_url}/sitemap.xml in your browser.",
                            meta_json=json.dumps({"type": "error", "reason": "sitemap_parsing_failed", "site_url": site_url})
                        )
                        session.add(error_row)
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - sitemap parsing failed")
                        
                        # Set progress to error state at LOW percentage (30%) - FAIL EARLY
                        set_task("error", 30, f"Sitemap parsing failed for {site_url}. No URLs found. Check if sitemap.xml exists.")
                        logger.error(f"❌ Campaign {cid} analysis FAILED at parsing stage - sitemap parsing returned no URLs")
                        return
                    
                    # Validate URLs before scraping
                    valid_urls = []
                    invalid_urls = []
                    for url in sitemap_urls:
                        try:
                            parsed = urlparse(url)
                            if parsed.scheme in ('http', 'https') and parsed.netloc:
                                valid_urls.append(url)
                            else:
                                invalid_urls.append(url)
                                logger.warning(f"⚠️ Invalid URL from sitemap: {url}")
                        except Exception as e:
                            invalid_urls.append(url)
                            logger.warning(f"⚠️ Error validating URL {url}: {e}")
                    
                    if invalid_urls:
                        logger.warning(f"⚠️ Found {len(invalid_urls)} invalid URLs out of {len(sitemap_urls)} total")
                    
                    if not valid_urls:
                        logger.error(f"❌ Site Builder: All {len(sitemap_urls)} URLs from sitemap are invalid!")
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:invalid_sitemap_urls",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Found {len(sitemap_urls)} URLs in sitemap, but all are invalid. Please check the sitemap format.",
                            meta_json=json.dumps({"type": "error", "reason": "invalid_sitemap_urls", "site_url": site_url, "url_count": len(sitemap_urls)})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - all sitemap URLs invalid")
                        set_task("error", 0, f"All {len(sitemap_urls)} URLs from sitemap are invalid")
                        return
                    
                    logger.info(f"✅ Validated {len(valid_urls)} valid URLs out of {len(sitemap_urls)} total")
                    
                    # Use validated sitemap URLs for scraping
                    urls = valid_urls
                    keywords = []  # Don't use keywords for Site Builder
                    depth = 1  # Only scrape the URLs from sitemap
                    max_pages = len(valid_urls)  # Scrape all validated URLs from sitemap
                    include_images = False
                    include_links = False
                    
                    logger.info(f"🏗️ Site Builder: Ready to scrape {len(valid_urls)} URLs")
                    logger.info(f"🏗️ Site Builder: First 5 URLs: {valid_urls[:5]}")
                else:
                    # Standard campaign types (keyword, url, trending)
                    urls = data.urls or []
                    keywords = data.keywords or []
                    depth = data.depth if hasattr(data, 'depth') and data.depth else 1
                    max_pages = data.max_pages if hasattr(data, 'max_pages') and data.max_pages else 10
                    include_images = data.include_images if hasattr(data, 'include_images') else False
                    include_links = data.include_links if hasattr(data, 'include_links') else False
                
                logger.info(f"📝 Scraping settings: URLs={len(urls)}, Keywords={len(keywords)}, depth={depth}, max_pages={max_pages}")
                logger.info(f"📝 URL list: {urls[:10] if urls else []}")  # Show first 10 URLs
                logger.info(f"📝 Keywords list: {keywords}")
                # Only warn about missing keywords if we also don't have URLs (Site Builder uses URLs only)
                if not keywords and not urls:
                    logger.error(f"❌ CRITICAL: No keywords or URLs provided! This will cause scraping to fail.")
                elif not keywords and urls:
                    logger.info(f"ℹ️ No keywords provided, but {len(urls)} URLs will be scraped (Site Builder mode)")
                elif keywords and not urls:
                    logger.info(f"ℹ️ No URLs provided, will search DuckDuckGo for keywords: {keywords}")
                
                # Import web scraping module
                scrape_campaign_data = None
                try:
                    from web_scraping import scrape_campaign_data
                except ImportError as e:
                    logger.error(f"❌ Failed to import web_scraping module: {e}")
                    scrape_campaign_data = None  # Mark as unavailable
                
                # Perform actual web scraping
                created = 0
                now = datetime.utcnow()
                
                if scrape_campaign_data is None:
                    # Module import failed - create error row
                    logger.error(f"❌ Cannot proceed with scraping - module import failed")
                    row = CampaignRawData(
                        campaign_id=cid,
                        source_url="error:module_import_failed",
                        fetched_at=now,
                        raw_html=None,
                        extracted_text=f"Web scraping module not available. Please check server logs.",
                        meta_json=json.dumps({"type": "error", "reason": "module_import_failed"})
                    )
                    session.add(row)
                    created = 1
                elif not urls and not keywords:
                    logger.warning(f"⚠️ No URLs or keywords provided for campaign {cid}")
                    # Create error row (not placeholder) so user knows something went wrong
                    error_text = f"Site Builder: No URLs or keywords provided for scraping.\n\nCampaign type: {data.type}\nSite URL: {getattr(data, 'site_base_url', 'Not provided')}\nURLs: {len(data.urls or [])}\nKeywords: {len(data.keywords or [])}\n\nThis usually means sitemap parsing failed or returned no URLs."
                    row = CampaignRawData(
                        campaign_id=cid,
                        source_url="error:no_urls_or_keywords",
                        fetched_at=now,
                        raw_html=None,
                        extracted_text=error_text,
                        meta_json=json.dumps({"type": "error", "reason": "no_urls_or_keywords", "campaign_type": data.type, "site_base_url": getattr(data, 'site_base_url', None)})
                    )
                    session.add(row)
                    created = 1
                    logger.error(f"❌ Created error row for campaign {cid} - no URLs or keywords provided")
                else:
                    # Perform real web scraping
                    logger.info(f"🚀 Starting web scraping for campaign {cid}")
                    logger.info(f"📋 Parameters: keywords={keywords}, urls={urls}, depth={depth}, max_pages={max_pages}, include_images={include_images}, include_links={include_links}")
                    
                    try:
                        logger.info(f"🚀 Calling scrape_campaign_data with: keywords={keywords}, urls={urls}, query={data.query or ''}, depth={depth}, max_pages={max_pages}")
                        # Update progress to show scraping is starting
                        set_task("scraping", 50, f"Scraping 0/{len(urls)} URLs... (this may take several minutes)")
                        
                        # Progress callback to update as each URL is scraped
                        def update_scraping_progress(scraped: int, total: int, progress_pct: int):
                            set_task("scraping", progress_pct, f"Scraping {scraped}/{total} URLs... ({progress_pct}%)")
                        
                        scraped_results = scrape_campaign_data(
                            keywords=keywords,
                            urls=urls,
                            query=data.query or "",
                            depth=depth,
                            max_pages=max_pages,
                            include_images=include_images,
                            include_links=include_links,
                            progress_callback=update_scraping_progress
                        )
                        
                        logger.info(f"✅ Web scraping completed: {len(scraped_results)} pages scraped")
                        # Update progress after scraping completes
                        set_task("scraping_complete", 70, f"Scraped {len(scraped_results)} pages, saving to database...")
                        logger.info(f"📊 Progress updated: 70% - scraping_complete")
                        
                        # Log detailed results for diagnostics
                        if len(scraped_results) == 0:
                            logger.error(f"❌ CRITICAL: Scraping returned 0 results for campaign {cid}")
                            logger.error(f"❌ Campaign type: {data.type}")
                            logger.error(f"❌ Keywords used: {keywords}")
                            logger.error(f"❌ URLs provided: {len(urls) if urls else 0} URLs")
                            if urls:
                                logger.error(f"❌ First 5 URLs: {urls[:5]}")
                            logger.error(f"❌ Query: {data.query or '(empty)'}")
                            logger.error(f"❌ Depth: {depth}, Max pages: {max_pages}")
                            logger.error(f"❌ This likely means scraping failed - check Playwright/DuckDuckGo availability")
                            
                            # Create error row for ALL campaign types when scraping returns 0 results
                            if data.type == "site_builder":
                                error_text = f"Site Builder: Sitemap parsing succeeded ({len(urls)} URLs found), but scraping returned 0 results.\n\nPossible reasons:\n- Network/timeout issues accessing URLs\n- URLs require authentication\n- URLs are blocked by robots.txt\n- Playwright/scraping service unavailable\n\nPlease check backend logs for details."
                                error_reason = "scraping_failed"
                                error_meta = {"type": "error", "reason": "scraping_failed", "urls_count": len(urls), "urls": urls[:10]}
                            else:
                                # Keyword or other campaign types
                                error_text = f"No results from web scraping.\n\nCampaign type: {data.type}\nKeywords: {keywords}\nURLs: {len(urls) if urls else 0} URLs\nQuery: {data.query or '(empty)'}\n\nPossible reasons:\n- DuckDuckGo search returned no results\n- Playwright/scraping service unavailable\n- Network/firewall blocking\n- Invalid or empty keywords\n\nPlease check backend logs for details."
                                error_reason = "no_scrape_results"
                                error_meta = {"type": "error", "reason": "no_scrape_results", "keywords": keywords, "urls_count": len(urls) if urls else 0, "query": data.query or ""}
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:{error_reason}",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=error_text,
                                meta_json=json.dumps(error_meta)
                            )
                            session.add(error_row)
                            try:
                                session.commit()
                                created = 1  # Mark that we created an error row
                                logger.error(f"❌ Created error row for campaign {cid} - scraping returned 0 results")
                            except Exception as commit_err:
                                logger.error(f"❌ Failed to commit error row for campaign {cid}: {commit_err}")
                                session.rollback()
                                # Continue anyway - we'll check for created == 0 later
                        else:
                            logger.info(f"📊 Scraping results breakdown:")
                            success_count = 0
                            error_count = 0
                            total_text_length = 0
                            for i, result in enumerate(scraped_results):
                                url = result.get("url", "unknown")
                                text = result.get("text", "")
                                text_len = len(text)
                                has_error = result.get("error") is not None
                                if has_error:
                                    error_count += 1
                                    logger.warning(f"  [{i+1}] ❌ {url}: ERROR - {result.get('error')}")
                                else:
                                    success_count += 1
                                    total_text_length += text_len
                                    if i < 5:  # Log first 5 successful results
                                        logger.info(f"  [{i+1}] ✅ {url}: {text_len} chars")
                            logger.info(f"📊 Summary: {success_count} successful, {error_count} errors, {total_text_length} total chars")
                            
                            if success_count == 0:
                                logger.error(f"❌ CRITICAL: All {len(scraped_results)} scraping attempts failed!")
                        
                        # Store scraped data in database
                        # Initialize tracking variables before try block so they're accessible later
                        skipped_count = 0
                        created = 0
                        total_urls_scraped = len(scraped_results) if 'scraped_results' in locals() else 0
                        
                        try:
                            # Ensure json is available (it's imported globally, but ensure it's in scope)
                            import json as json_module
                            json = json_module  # Use global json module
                            
                            logger.info(f"💾 Starting to save {len(scraped_results)} scraped results to database...")
                            
                            # Update total_urls_scraped now that we're in the try block
                            total_urls_scraped = len(scraped_results)
                            
                            # CRITICAL: Check for existing scraped data to avoid duplicates
                            # Query all existing URLs for this campaign to reuse instead of re-scraping
                            existing_urls = {}
                            try:
                                existing_rows = session.query(CampaignRawData).filter(
                                    CampaignRawData.campaign_id == cid,
                                    ~CampaignRawData.source_url.startswith("error:"),
                                    ~CampaignRawData.source_url.startswith("placeholder:")
                                ).all()
                                for row in existing_rows:
                                    if row.source_url and row.extracted_text and len(row.extracted_text.strip()) > 10:
                                        existing_urls[row.source_url] = row
                                logger.info(f"📋 Found {len(existing_urls)} existing scraped URLs for campaign {cid} - will reuse instead of re-scraping")
                            except Exception as query_err:
                                logger.warning(f"⚠️ Error querying existing URLs: {query_err}, will proceed with saving all results")
                                existing_urls = {}
                            
                            skipped_count = 0
                            for i, result in enumerate(scraped_results, 1):
                                # Update progress periodically during database save (every 10 items)
                                if i % 10 == 0 or i == len(scraped_results):
                                    set_task("scraping_complete", 70, f"Saving to database... ({i}/{len(scraped_results)})")
                                    logger.debug(f"💾 Saving progress: {i}/{len(scraped_results)}")
                                url = result.get("url", "unknown")
                                text = result.get("text", "")
                                html = result.get("html")
                                images = result.get("images", [])
                                links = result.get("links", [])
                                error = result.get("error")
                                depth_level = result.get("depth", 0)
                                
                                # CRITICAL: Skip if URL already exists in database (reuse existing data)
                                if url in existing_urls and not error:
                                    skipped_count += 1
                                    existing_row = existing_urls[url]
                                    logger.debug(f"♻️ Skipping {url} - already exists in database (DB ID: {existing_row.id}, {len(existing_row.extracted_text or '')} chars)")
                                    continue  # Skip creating duplicate row
                                
                                # Build metadata JSON
                                meta = {
                                    "type": "scraped",
                                    "depth": depth_level,
                                    "scraped_at": result.get("scraped_at"),
                                    "has_images": len(images) > 0,
                                    "image_count": len(images),
                                    "link_count": len(links)
                                }
                                if error:
                                    meta["error"] = error
                                if images:
                                    meta["sample_images"] = images[:5]  # Store first 5 images
                                
                                # Safety guard: Truncate text to MEDIUMTEXT limit (16MB) to prevent DB errors
                                # MEDIUMTEXT max: 16,777,215 bytes (≈16 MB)
                                # Note: Truncation at 16MB is extremely rare - most web pages are <100KB
                                # If truncation occurs, it's likely mostly noise (ads, scripts, duplicate content)
                                MAX_TEXT_SIZE = 16_777_000  # Leave small buffer (≈16 MB)
                                
                                # Language detection and filtering
                                detected_language = None
                                safe_text = None
                                if text:
                                    # Detect language before processing
                                    try:
                                        from langdetect import detect, LangDetectException
                                        # Use first 1000 chars for faster detection
                                        sample_text = text[:1000] if len(text) > 1000 else text
                                        if len(sample_text.strip()) > 10:  # Need minimum text for detection
                                            detected_language = detect(sample_text)
                                            meta["detected_language"] = detected_language
                                            
                                            # Filter out non-English content
                                            if detected_language != 'en':
                                                logger.warning(f"🌐 Non-English content detected ({detected_language}) for {url}, filtering out")
                                                logger.warning(f"🌐 Sample text: {sample_text[:200]}...")
                                                meta["language_filtered"] = True
                                                meta["filter_reason"] = f"non_english_{detected_language}"
                                                safe_text = ""  # Skip non-English content
                                            else:
                                                logger.debug(f"✅ English content confirmed for {url}")
                                        else:
                                            logger.debug(f"⚠️ Text too short for language detection for {url}")
                                            meta["detected_language"] = "unknown"
                                    except LangDetectException as lang_err:
                                        logger.warning(f"⚠️ Language detection failed for {url}: {lang_err}")
                                        meta["detected_language"] = "unknown"
                                        meta["language_detection_error"] = str(lang_err)
                                    except ImportError:
                                        logger.warning("⚠️ langdetect not available - skipping language filtering")
                                        meta["detected_language"] = "not_checked"
                                    except Exception as lang_err:
                                        logger.warning(f"⚠️ Unexpected error in language detection for {url}: {lang_err}")
                                        meta["detected_language"] = "error"
                                    
                                    # Only process text if it's English (or if language detection failed/not available)
                                    if safe_text is None:  # Only process if not already filtered
                                        try:
                                            # Remove emojis and 4-byte UTF-8 characters (they cause DataError 1366)
                                            # Keep only 1-3 byte UTF-8 characters (basic unicode)
                                            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                            # Remove any remaining problematic characters (emojis are >0xFFFF)
                                            safe_text = ''.join(char for char in safe_text if ord(char) < 0x10000)
                                        except Exception as encode_err:
                                            logger.warning(f"⚠️ Error encoding extracted_text for {url}: {encode_err}, using empty string")
                                            safe_text = ""
                                        
                                        # Smart truncation: Keep first portion if too large
                                        if len(safe_text) > MAX_TEXT_SIZE:
                                            safe_text = safe_text[:MAX_TEXT_SIZE]
                                            logger.warning(f"⚠️ Truncated extracted_text for {url}: {len(text):,} chars → {len(safe_text):,} chars (exceeded MEDIUMTEXT 16MB limit)")
                                            logger.warning(f"⚠️ This is extremely rare - text >16MB likely contains mostly noise. First {MAX_TEXT_SIZE:,} chars preserved.")
                                            meta["text_truncated"] = True
                                            meta["original_length"] = len(text)
                                            meta["truncation_reason"] = "exceeded_mediumtext_limit"
                                else:
                                    safe_text = ""
                                
                                # Sanitize HTML to remove emojis/unicode that can't be stored in utf8mb3
                                # Keep only ASCII + basic UTF-8, remove 4-byte UTF-8 (emojis)
                                safe_html = None
                                if html and include_links:
                                    try:
                                        # Remove emojis and 4-byte UTF-8 characters (they cause DataError 1366)
                                        # Keep only 1-3 byte UTF-8 characters (basic unicode)
                                        safe_html = html[:MAX_TEXT_SIZE].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        # Remove any remaining problematic characters
                                        safe_html = ''.join(char for char in safe_html if ord(char) < 0x10000)
                                    except Exception as encode_err:
                                        logger.warning(f"⚠️ Error encoding HTML for {url}: {encode_err}, storing as None")
                                        safe_html = None
                                
                                row = CampaignRawData(
                                    campaign_id=cid,
                                    source_url=url,
                                    fetched_at=now,
                                    raw_html=safe_html,  # Sanitized HTML (no emojis)
                                    extracted_text=safe_text if safe_text else (f"Error scraping {url}: {error}" if error else ""),
                                    meta_json=json.dumps(meta)
                                )
                                session.add(row)
                                # Flush to get DB ID immediately for logging
                                session.flush()
                                created += 1
                                
                                # Enhanced per-URL logging with DB ID
                                text_len = len(safe_text) if safe_text else 0
                                original_len = len(text) if text else 0
                                truncation_note = f" (truncated from {original_len})" if original_len > MAX_TEXT_SIZE else ""
                                
                                if error:
                                    logger.warning(f"⚠️ Scraped {url} (DB ID: {row.id}): ERROR - {error}")
                                else:
                                    logger.info(f"✅ Scraped {url} (DB ID: {row.id}): {text_len} chars{truncation_note}, {len(links)} links, {len(images)} images")
                            
                            logger.info(f"💾 Finished saving {len(scraped_results)} results to database (created={created} new, skipped={skipped_count} duplicates - reused existing data)")
                        except Exception as save_error:
                            logger.error(f"❌ CRITICAL: Error saving scraped data to database for campaign {cid}: {save_error}")
                            import traceback
                            logger.error(f"❌ Traceback: {traceback.format_exc()}")
                            # Continue anyway - we'll create an error row below
                        
                        # Only create error row if we haven't already created one (e.g., for Site Builder with 0 results)
                        if created == 0 and len(scraped_results) == 0:
                            logger.warning(f"⚠️ Web scraping returned no results for campaign {cid}")
                            # Create error row
                            row = CampaignRawData(
                                campaign_id=cid,
                                source_url="error:no_results",
                                fetched_at=now,
                                raw_html=None,
                                extracted_text=f"No results from web scraping. Keywords: {keywords}, URLs: {urls}",
                                meta_json=json.dumps({"type": "error", "reason": "no_scrape_results"})
                            )
                            session.add(row)
                            created = 1
                    
                    except Exception as scrape_error:
                        logger.error(f"❌ Web scraping failed for campaign {cid}: {scrape_error}")
                        import traceback
                        error_trace = traceback.format_exc()
                        logger.error(f"❌ Traceback: {error_trace}")
                        
                        # Check if this is a missing dependency error
                        error_msg = str(scrape_error)
                        if "No module named" in error_msg or "ImportError" in error_msg:
                            logger.error(f"❌ CRITICAL: Missing dependency detected: {error_msg}")
                            logger.error(f"❌ This will cause silent failures. Install missing packages immediately.")
                        
                        # Create error row with full error details
                        row = CampaignRawData(
                            campaign_id=cid,
                            source_url="error:scrape_failed",
                            fetched_at=now,
                            raw_html=None,
                            extracted_text=f"Web scraping error: {error_msg}",
                            meta_json=json.dumps({
                                "type": "error", 
                                "reason": "scrape_exception", 
                                "error": error_msg,
                                "traceback": error_trace[:500]  # Store first 500 chars of traceback
                            })
                        )
                        session.add(row)
                        created = 1
                
                if created > 0:
                    logger.info(f"💾 Committing {created} rows to database for campaign {cid}...")
                    set_task("scraping_complete", 75, f"Committing {created} rows to database...")
                    try:
                        session.commit()
                        logger.info(f"✅ Successfully committed {created} rows to database for campaign {cid}")
                        set_task("scraping_complete", 78, f"Database commit successful, verifying data...")
                    except Exception as commit_error:
                        # Check if campaign was deleted (foreign key constraint)
                        error_msg = str(commit_error).lower()
                        if "foreign key" in error_msg or "constraint" in error_msg or "campaign" in error_msg:
                            logger.error(f"❌ CRITICAL: Failed to save scraped data for campaign {cid} - campaign may have been deleted!")
                            logger.error(f"❌ Error: {commit_error}")
                            logger.error(f"❌ This usually happens when a campaign is deleted while scraping is in progress.")
                            logger.error(f"❌ {created} rows were scraped but could not be saved due to campaign deletion.")
                        else:
                            logger.error(f"❌ Failed to commit scraped data for campaign {cid}: {commit_error}")
                            import traceback
                            logger.error(f"❌ Traceback: {traceback.format_exc()}")
                        session.rollback()
                        # Don't re-raise - continue with analysis even if save failed
                    
                    # CRITICAL: Verify data was saved and check for valid (non-error) rows
                    all_saved_rows = session.query(CampaignRawData).filter(CampaignRawData.campaign_id == cid).all()
                    total_count = len(all_saved_rows)
                    valid_count = 0
                    error_count = 0
                    
                    total_text_size = 0
                    max_text_size = 0
                    
                    for row in all_saved_rows:
                        if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                            error_count += 1
                        else:
                            # Valid row - check if it has meaningful text
                            if row.extracted_text and len(row.extracted_text.strip()) > 10:
                                valid_count += 1
                                text_size = len(row.extracted_text)
                                total_text_size += text_size
                                max_text_size = max(max_text_size, text_size)
                                logger.debug(f"✅ Valid data row: {row.source_url} ({text_size} chars)")
                    
                    avg_text_size = total_text_size // valid_count if valid_count > 0 else 0
                    
                    logger.info(f"📊 Post-commit verification for campaign {cid}:")
                    logger.info(f"   Total rows: {total_count}")
                    logger.info(f"   Valid rows (with text): {valid_count}")
                    logger.info(f"   Error/placeholder rows: {error_count}")
                    logger.info(f"   Storage: {total_text_size:,} total chars, {avg_text_size:,} avg, {max_text_size:,} max")
                    
                    # Warn if approaching MEDIUMTEXT limit
                    if max_text_size > 15_000_000:
                        logger.warning(f"⚠️ Large page detected: {max_text_size:,} chars (close to MEDIUMTEXT 16MB limit)")
                    
                    # CRITICAL: If only error rows exist, log a warning
                    if valid_count == 0 and error_count > 0:
                        logger.error(f"❌ CRITICAL: Campaign {cid} has {error_count} error rows but 0 valid data rows!")
                        logger.error(f"❌ This indicates scraping failed. Check logs above for ImportError or missing dependencies.")
                        # Extract error messages for diagnostics
                        error_messages = []
                        for row in all_saved_rows:
                            if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                error_text = row.extracted_text or row.source_url
                                if error_text not in error_messages:
                                    error_messages.append(error_text[:200])
                        if error_messages:
                            logger.error(f"❌ Error details from saved rows:")
                            for i, msg in enumerate(error_messages[:5], 1):
                                logger.error(f"   [{i}] {msg}")
                    elif valid_count == 0:
                        logger.warning(f"⚠️ Campaign {cid} has no rows saved at all - scraping may not have run")
                else:
                    logger.warning(f"⚠️ No rows to commit for campaign {cid}")

                # Step 3: processing content (scraping is already done, now just mark progress)
                logger.info(f"📊 Moving to processing_content step (80%) for campaign {cid}")
                set_task("processing_content", 80, f"Processing {created} scraped pages")
                logger.info(f"📊 Progress updated: 80% - processing_content")
                # Content is already processed during scraping, minimal delay
                time.sleep(2)

                # Step 3.5: Gap Analysis for Site Builder campaigns
                if data.type == "site_builder" and valid_count > 0:
                    try:
                        from gap_analysis import identify_content_gaps, rank_gaps_by_priority
                        from text_processing import extract_topics
                        
                        logger.info(f"🏗️ Site Builder: Starting gap analysis for campaign {cid}")
                        set_task("gap_analysis", 70, "Analyzing content gaps")
                        
                        # Get scraped texts for topic extraction
                        all_rows = session.query(CampaignRawData).filter(
                            CampaignRawData.campaign_id == cid,
                            ~CampaignRawData.source_url.startswith(("error:", "placeholder:"))
                        ).all()
                        
                        texts = [row.extracted_text for row in all_rows if row.extracted_text and len(row.extracted_text.strip()) > 50]
                        
                        if texts:
                            # Extract topics from existing content
                            logger.info(f"🔍 Extracting topics from {len(texts)} pages...")
                            existing_topics = extract_topics(
                                texts=texts,
                                topic_tool="system",  # Use system model for speed
                                num_topics=20,
                                iterations=25,
                                query=data.query or "",
                                keywords=[],
                                urls=[]
                            )
                            logger.info(f"✅ Extracted {len(existing_topics)} topics from site content")
                            
                            # Build knowledge graph structure from existing topics
                            # (Simplified - full KG would come from research endpoint)
                            existing_kg = {
                                "nodes": [{"id": t.lower(), "label": t} for t in existing_topics[:50]],
                                "edges": []  # Simplified - full edges would come from research endpoint
                            }
                            
                            # Perform gap analysis
                            target_keywords = getattr(data, 'target_keywords', None) or data.keywords or []
                            if target_keywords:
                                gaps = identify_content_gaps(
                                    existing_topics=existing_topics,
                                    knowledge_graph=existing_kg,
                                    target_keywords=target_keywords,
                                    existing_urls=[row.source_url for row in all_rows[:100]]
                                )
                                
                                # Rank and filter gaps
                                top_ideas_count = getattr(data, 'top_ideas_count', 10)
                                top_gaps = rank_gaps_by_priority(gaps, top_n=top_ideas_count)
                                
                                logger.info(f"✅ Gap analysis complete: {len(gaps)} total gaps, {len(top_gaps)} top priority gaps")
                                
                                # Store gap analysis results in campaign
                                camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                                if camp:
                                    camp.gap_analysis_results_json = json.dumps({
                                        "total_gaps": len(gaps),
                                        "top_gaps": top_gaps,
                                        "existing_topics": existing_topics[:50],
                                        "target_keywords": target_keywords,
                                        "coverage_score": len([g for g in gaps if g.get("priority") == "high"]) / len(gaps) if gaps else 0
                                    })
                                    camp.site_base_url = site_url
                                    camp.target_keywords_json = json.dumps(target_keywords)
                                    camp.top_ideas_count = top_ideas_count
                                    session.commit()
                                    logger.info(f"✅ Saved gap analysis results to campaign {cid}")
                            else:
                                logger.warning(f"⚠️ No target keywords provided for gap analysis")
                        else:
                            logger.warning(f"⚠️ No valid text content found for gap analysis")
                    except Exception as gap_error:
                        logger.error(f"❌ Gap analysis failed: {gap_error}")
                        import traceback
                        logger.error(traceback.format_exc())

                # Step 4: extracting entities
                set_task("extracting_entities", 75, "Extracting entities from scraped content")
                # Entities will be extracted when research endpoint is called
                time.sleep(2)

                # Step 5: modeling topics (only if we have data)
                if created > 0:
                    set_task("modeling_topics", 90, "Preparing content for analysis")
                    # Topics will be modeled when research endpoint is called
                    time.sleep(2)
                else:
                    set_task("modeling_topics", 90, "Waiting for scraping to complete...")
                    # Wait a bit longer if no data yet (scraping might still be running)
                    time.sleep(5)

                # Mark campaign ready in DB - validate data BEFORE setting progress to 100%
                logger.info(f"📝 Step 6: Finalizing campaign {cid}")
                try:
                    # Use a fresh query to ensure we get the latest campaign state
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        logger.info(f"📝 Found campaign {cid} in database, updating status...")
                        logger.info(f"📝 Current status: {camp.status}, current topics: {camp.topics}")
                        
                        # Check if we have scraped data before marking as ready
                        # IMPORTANT: Only count valid scraped data (exclude error/placeholder rows)
                        all_rows = session.query(CampaignRawData).filter(CampaignRawData.campaign_id == cid).all()
                        valid_data_count = 0
                        valid_text_count = 0
                        error_count = 0
                        
                        for row in all_rows:
                            if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                error_count += 1
                                logger.debug(f"⚠️ Skipping error/placeholder row: {row.source_url}")
                            else:
                                # Valid scraped data - check if it has meaningful content
                                if row.source_url and row.extracted_text and len(row.extracted_text.strip()) > 10:
                                    valid_data_count += 1
                                    valid_text_count += 1
                                    logger.debug(f"✅ Valid data row: {row.source_url} ({len(row.extracted_text)} chars)")
                                elif row.source_url:
                                    # Has URL but no/minimal text - DON'T count as valid (frontend can't use it)
                                    # This prevents false-positive READY_TO_ACTIVATE status
                                    logger.debug(f"⚠️ Skipping row with URL but no/minimal text: {row.source_url} (text length: {len(row.extracted_text or '')})")
                                    # Don't increment valid_data_count - this row is not usable
                        
                        logger.info(f"📊 Data validation: {valid_data_count} valid rows, {valid_text_count} with text, {error_count} error/placeholder rows")
                        
                        # CRITICAL: Check if all URLs were already scraped (100% duplicates = no changes)
                        # This happens when a campaign is re-scraped but all URLs already exist in the database
                        all_urls_were_duplicates = (
                            total_urls_scraped > 0 and 
                            skipped_count > 0 and 
                            created == 0 and 
                            skipped_count == total_urls_scraped
                        )
                        
                        if all_urls_were_duplicates and valid_data_count > 0:
                            # All URLs were already scraped - no changes detected
                            logger.info(f"🔄 Campaign {cid} re-scraped but all {skipped_count} URLs were already in database - no changes detected")
                            
                            # Store coarse topics from keywords as a ready signal (if not already set)
                            if (data.keywords or []) and not camp.topics:
                                camp.topics = ",".join((data.keywords or [])[:10])
                                logger.info(f"📝 Set topics to: {camp.topics}")
                            
                            # Set status to NO_CHANGES to indicate re-run with no new data
                            camp.status = "NO_CHANGES"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Campaign {cid} marked as NO_CHANGES - re-scraped but all {skipped_count} URLs already existed (reused existing data)")
                            
                            # Set progress to 100% to indicate completion
                            set_task("finalizing", 100, f"Re-scraped - all {skipped_count} URLs already existed, no changes detected")
                            
                            # Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "NO_CHANGES":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected NO_CHANGES, got {camp.status}")
                                # Force update again
                                camp.status = "NO_CHANGES"
                                camp.updated_at = datetime.utcnow()
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to NO_CHANGES")
                        # For Site Builder campaigns, require at least some valid data
                        elif data.type == "site_builder" and valid_data_count == 0:
                            logger.error(f"❌ Site Builder campaign {cid} has no valid scraped data!")
                            logger.error(f"❌ Total rows: {len(all_rows)}, Error rows: {error_count}")
                            if error_count > 0:
                                logger.error(f"❌ This indicates sitemap parsing or scraping failed. Check error rows above.")
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to no valid data")
                            
                            # CRITICAL: Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "INCOMPLETE":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected INCOMPLETE, got {camp.status}")
                                # Force update again
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to INCOMPLETE")
                            else:
                                logger.info(f"✅ Verified campaign {cid} status is INCOMPLETE in database")
                            
                            # Keep progress at 95% to indicate it's not fully complete
                            set_task("error", 95, "Scraping completed but no valid data found. Check logs for details.")
                        elif valid_data_count > 0:
                            # Store coarse topics from keywords as a ready signal
                            if (data.keywords or []) and not camp.topics:
                                camp.topics = ",".join((data.keywords or [])[:10])
                                logger.info(f"📝 Set topics to: {camp.topics}")
                            
                            # CRITICAL: Set status to READY_TO_ACTIVATE and commit immediately
                            camp.status = "READY_TO_ACTIVATE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Campaign {cid} marked as READY_TO_ACTIVATE with {valid_data_count} valid data rows ({valid_text_count} with text)")
                            
                            # Only set progress to 100% AFTER we've confirmed valid data exists
                            set_task("finalizing", 100, f"Scraping complete - {valid_data_count} pages scraped successfully")
                            
                            # Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "READY_TO_ACTIVATE":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected READY_TO_ACTIVATE, got {camp.status}")
                                # Force update again
                                camp.status = "READY_TO_ACTIVATE"
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to READY_TO_ACTIVATE")
                        else:
                            # No valid scraped data - check if we have errors
                            if error_count > 0:
                                logger.error(f"❌ Campaign {cid} scraping failed: {error_count} error rows, 0 valid data rows")
                                logger.error(f"❌ This indicates scraping did not succeed. Check logs above for scraping errors.")
                                # Keep progress at 95% to indicate failure - NEVER set to 100% if no valid data
                                set_task("error", 95, f"Scraping failed: {error_count} errors, 0 valid data. Check logs for details.")
                                
                                # Extract error messages from error rows for better diagnostics
                                error_messages = []
                                missing_deps = []
                                for row in all_rows:
                                    if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                        error_msg = row.extracted_text or row.source_url
                                        if error_msg not in error_messages:
                                            error_messages.append(error_msg[:200])  # Limit length
                                        # Check for missing dependency errors
                                        if "No module named" in error_msg or "ImportError" in error_msg:
                                            missing_deps.append(error_msg)
                                
                                if missing_deps:
                                    logger.error(f"❌ CRITICAL: Missing dependencies detected:")
                                    for dep_error in missing_deps:
                                        logger.error(f"   - {dep_error[:150]}")
                                    logger.error(f"❌ Fix: Run './scripts/fix_missing_deps_now.sh' or 'pip install beautifulsoup4 gensim'")
                                
                                if error_messages:
                                    logger.error(f"❌ Error details from database:")
                                    for i, msg in enumerate(error_messages[:5], 1):  # Show first 5
                                        logger.error(f"   [{i}] {msg}")
                                
                                logger.error(f"❌ Common causes:")
                                logger.error(f"   1. Missing dependencies (bs4, gensim): Run 'pip install beautifulsoup4 gensim'")
                                logger.error(f"   2. Playwright not installed: Run 'python -m playwright install chromium'")
                                logger.error(f"   3. DuckDuckGo search failing: Check 'ddgs' package is installed")
                                logger.error(f"   4. Network/firewall blocking: Check server can access external URLs")
                                logger.error(f"   5. Invalid keywords: Empty or malformed keywords return no results")
                                
                                # Set status with diagnostic message
                                camp.status = "INCOMPLETE"
                                if missing_deps:
                                    camp.description = (camp.description or "") + f"\n[ERROR: Missing dependencies - check logs]"
                            else:
                                # No rows at all - this shouldn't happen but handle it
                                logger.error(f"❌ Campaign {cid} has no data rows at all (no errors, no valid data)")
                                logger.error(f"❌ This suggests scraping never ran or failed before creating any rows")
                                # Keep progress at 95% to indicate failure
                                set_task("error", 95, "No data was scraped. Check backend logs for details.")
                            
                            # Set status to INCOMPLETE for all failure cases
                            logger.info(f"🔧 Setting campaign {cid} status to INCOMPLETE (no valid data)")
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            try:
                                session.commit()
                                logger.info(f"✅ Campaign {cid} status committed to database as INCOMPLETE")
                            except Exception as commit_err:
                                logger.error(f"❌ CRITICAL: Failed to commit INCOMPLETE status for campaign {cid}: {commit_err}")
                                import traceback
                                logger.error(f"❌ Commit error traceback:\n{traceback.format_exc()}")
                                session.rollback()
                                # Try one more time
                                try:
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                    session.commit()
                                    logger.info(f"🔧 Retry: Campaign {cid} status committed to database as INCOMPLETE")
                                except Exception as retry_err:
                                    logger.error(f"❌ CRITICAL: Retry commit also failed for campaign {cid}: {retry_err}")
                            
                            # CRITICAL: Verify the status was saved correctly (same as READY_TO_ACTIVATE path)
                            try:
                                session.refresh(camp)
                                if camp.status != "INCOMPLETE":
                                    logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected INCOMPLETE, got {camp.status}")
                                    # Force update again
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                    session.commit()
                                    logger.info(f"🔧 Force-updated campaign {cid} status to INCOMPLETE")
                                else:
                                    logger.info(f"✅ Verified campaign {cid} status is INCOMPLETE in database")
                            except Exception as verify_err:
                                logger.error(f"❌ CRITICAL: Failed to verify INCOMPLETE status for campaign {cid}: {verify_err}")
                                import traceback
                                logger.error(f"❌ Verify error traceback:\n{traceback.format_exc()}")
                    else:
                        logger.warning(f"⚠️ Campaign {cid} not found in database when trying to finalize")
                except Exception as finalize_err:
                    logger.error(f"❌ Error finalizing campaign {cid}: {finalize_err}")
                    import traceback
                    logger.error(traceback.format_exc())
                    session.rollback()
                    # Try to set status to INCOMPLETE as fallback
                    try:
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"⚠️ Set campaign {cid} to INCOMPLETE due to finalization error")
                    except:
                        pass
                    
                logger.info(f"✅ Background analysis completed successfully for campaign {cid}")
            except Exception as e:
                import traceback
                logger.error(f"❌ Background analysis error for campaign {cid}: {e}")
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
            finally:
                session.close()
                logger.info(f"🔵 Background thread finished for task {tid}, campaign {cid}")

        # Start background thread
        # Convert Pydantic model to dict to avoid serialization issues when passing to thread
        try:
            logger.info(f"🔍 About to start background thread for task {task_id}")
            # Convert analyze_data to dict for thread safety
            try:
                # Try Pydantic v2 method first
                if hasattr(analyze_data, 'model_dump'):
                    analyze_data_dict = analyze_data.model_dump()
                    logger.info(f"🔍 Used model_dump() to convert to dict")
                # Fallback to Pydantic v1 method
                elif hasattr(analyze_data, 'dict'):
                    analyze_data_dict = analyze_data.dict()
                    logger.info(f"🔍 Used dict() to convert to dict")
                else:
                    # Last resort: manual conversion
                    analyze_data_dict = {
                        'campaign_id': getattr(analyze_data, 'campaign_id', None),
                        'campaign_name': getattr(analyze_data, 'campaign_name', None),
                        'type': getattr(analyze_data, 'type', 'keyword'),
                        'site_base_url': getattr(analyze_data, 'site_base_url', None),
                        'target_keywords': getattr(analyze_data, 'target_keywords', None),
                        'top_ideas_count': getattr(analyze_data, 'top_ideas_count', 10),
                        'most_recent_urls': getattr(analyze_data, 'most_recent_urls', None),
                        'keywords': getattr(analyze_data, 'keywords', []),
                        'urls': getattr(analyze_data, 'urls', []),
                        'description': getattr(analyze_data, 'description', None),
                        'query': getattr(analyze_data, 'query', None),
                    }
                    logger.info(f"🔍 Used manual conversion to dict")
                logger.info(f"🔍 Converted analyze_data to dict, keys: {list(analyze_data_dict.keys())}")
            except Exception as dict_error:
                logger.error(f"❌ CRITICAL: Failed to convert analyze_data to dict: {dict_error}")
                import traceback
                logger.error(f"❌ Dict conversion traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to prepare analysis data: {str(dict_error)}"
                )
            
            # Reconstruct AnalyzeRequest from dict in the background thread
            thread = threading.Thread(target=run_analysis_background, args=(task_id, campaign_id, analyze_data_dict), daemon=True)
            thread.start()
            logger.info(f"✅ Background thread started successfully for task {task_id}")
        except Exception as thread_error:
            logger.error(f"❌ CRITICAL: Failed to start background thread: {thread_error}")
            import traceback
            logger.error(f"❌ Thread start traceback: {traceback.format_exc()}")
            # Remove task from CONTENT_GEN_TASKS since thread failed to start
            if task_id in CONTENT_GEN_TASKS:
                del CONTENT_GEN_TASKS[task_id]
            if campaign_id in CONTENT_GEN_TASK_INDEX:
                del CONTENT_GEN_TASK_INDEX[campaign_id]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start analysis thread: {str(thread_error)}"
            )

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Analysis started",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 404) as-is
        raise
    except Exception as e:
        import traceback
        from pydantic import ValidationError
        error_trace = traceback.format_exc()
        logger.error(f"❌ CRITICAL: Error in /analyze endpoint: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Full traceback:\n{error_trace}")
        # Log the request data for debugging
        try:
            logger.error(f"❌ Request data: campaign_id={analyze_data.campaign_id}, type={analyze_data.type}, site_base_url={getattr(analyze_data, 'site_base_url', None)}")
        except:
            pass
        
        # Handle ValidationError specifically
        if isinstance(e, ValidationError):
            logger.error(f"❌ Pydantic ValidationError: {e.errors()}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "error",
                    "message": "Validation error in request data",
                    "errors": e.errors(),
                    "error_type": "ValidationError"
                }
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Failed to start analysis: {str(e)}",
                "error_type": type(e).__name__
            }
        )

@content_router.get("/analyze/status/{task_id}")
def get_analyze_status(task_id: str, current_user = Depends(get_current_user)):
    """
    Get analysis status - In-memory progress simulation.
    Progress advances deterministically based on time since start.
    REQUIRES AUTHENTICATION
    """
    # Verify task belongs to user (check campaign ownership)
    if task_id in CONTENT_GEN_TASKS:
        task_campaign_id = CONTENT_GEN_TASKS[task_id].get("campaign_id")
        if task_campaign_id:
            from models import Campaign
            from database import SessionLocal
            session = SessionLocal()
            try:
                campaign = session.query(Campaign).filter(
                    Campaign.campaign_id == task_campaign_id,
                    Campaign.user_id == current_user.id
                ).first()
                if not campaign:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Task not found or access denied"
                    )
            finally:
                session.close()
    
    if task_id not in CONTENT_GEN_TASKS:
        # Be resilient across restarts: report pending instead of 404 so UI keeps polling
        return {
            "status": "pending",
            "progress": 5,
            "current_step": "initializing",
            "progress_message": "Waiting for task",
            "campaign_id": None,
        }
    
    task = CONTENT_GEN_TASKS[task_id]
    
    # CRITICAL: Return REAL progress if it's been set (from scraping, etc.)
    # Only use time-based simulation if real progress hasn't been set yet
    real_progress = task.get("progress")
    real_step = task.get("current_step")
    real_message = task.get("progress_message")
    
    # CRITICAL: If real_progress has been set (even if 0), use it
    # This ensures we return progress even when it's 0 initially
    if real_progress is not None and real_step:
        # Real progress has been set (e.g., during scraping)
        progress = real_progress
        current_step = real_step
        progress_message = real_message or f"{current_step.replace('_',' ').title()}"
        
        # Determine status based on progress
        if progress >= 100:
            status = "completed"
        elif progress > 0:
            status = "in_progress"
        else:
            status = "pending"
        
        logger.debug(f"📊 Returning REAL progress for task {task_id}: {progress}% - {current_step} - {progress_message}")
        return {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "progress_message": progress_message,
            "campaign_id": task["campaign_id"],
        }
    
    # Fallback: Compute time-based progress (only if real progress not set yet)
    try:
        from datetime import datetime as dt
        started = dt.fromisoformat(task["started_at"])  # UTC naive ISO ok
        elapsed = (dt.utcnow() - started).total_seconds()
    except Exception:
        elapsed = 0
    
    # Step thresholds (seconds -> progress, step label)
    steps = [
        (0,   5,  "initializing"),
        (5,  15,  "collecting_inputs"),
        (10, 25,  "fetching_content"),
        (20, 50,  "processing_content"),
        (30, 70,  "extracting_entities"),
        (40, 85,  "modeling_topics"),
        (45, 100, "finalizing"),
    ]
    progress = 5
    current_step = "initializing"
    for threshold, prog, step in steps:
        if elapsed >= threshold:
            progress = prog
            current_step = step
        else:
            break
    
    # Only update if real progress wasn't set
    if real_progress is None:
        task["progress"] = progress
        task["current_step"] = current_step
        task["progress_message"] = f"{current_step.replace('_',' ').title()}"
    
    # Use real progress if available, otherwise use time-based
    final_progress = real_progress if real_progress is not None else progress
    final_step = real_step if real_step else current_step
    final_message = real_message if real_message else f"{current_step.replace('_',' ').title()}"
    
    return {
        "status": "in_progress" if final_progress < 100 else "completed",
        "progress": final_progress,
        "current_step": final_step,
        "progress_message": final_message,
        "campaign_id": task["campaign_id"],
    }

# Optional helper: get status by campaign_id
@content_router.get("/analyze/status/by_campaign/{campaign_id}")
def get_status_by_campaign(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get analysis status by campaign ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or access denied"
        )
    
    # CRITICAL: Find the ACTIVE task for this campaign (not just the one in index)
    # Multiple tasks might exist if Build button was clicked multiple times
    # Return the one that's actually running (in_progress), or the most recent one
    
    active_task_id = None
    active_task_progress = -1
    
    # First check the index (most recent task)
    task_id_from_index = CONTENT_GEN_TASK_INDEX.get(campaign_id)
    
    # Check all tasks to find the one that's actually running
    for tid, task in CONTENT_GEN_TASKS.items():
        if task.get("campaign_id") == campaign_id:
            task_progress = task.get("progress", 0)
            # Prefer tasks that are actively running (progress > 0 and < 100)
            if 0 < task_progress < 100:
                if task_progress > active_task_progress:
                    active_task_id = tid
                    active_task_progress = task_progress
            # If no active task found yet, use the one from index
            elif active_task_id is None and tid == task_id_from_index:
                active_task_id = tid
    
    # Fallback to index if no active task found
    if not active_task_id:
        active_task_id = task_id_from_index
    
    if not active_task_id or active_task_id not in CONTENT_GEN_TASKS:
        # Task doesn't exist - return a clear status instead of 404
        # This happens if server restarted or analysis never started
        return {
            "status": "not_found",
            "progress": 0,
            "current_step": "not_started",
            "progress_message": "Analysis task not found. The campaign may not have started analysis yet, or the server was restarted. Try clicking 'Build Campaign' again.",
            "campaign_id": campaign_id
        }
    
    logger.debug(f"📊 get_status_by_campaign: Using task {active_task_id} for campaign {campaign_id} (index had {task_id_from_index})")
    return get_analyze_status(active_task_id, current_user)

# Debug endpoint to check raw data for a campaign
@content_router.post("/generate-ideas")
async def generate_ideas_endpoint(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content ideas based on topics, posts, and days.
    Used by content queue flow after selecting platforms and number of posts.
    Accepts form-urlencoded data: topics, posts, days
    REQUIRES AUTHENTICATION
    """
    try:
        from machine_agent import IdeaGeneratorAgent
        from langchain_openai import ChatOpenAI
        from fastapi import Form
        
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            return {"status": "error", "message": "OpenAI API key not configured. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings."}
        
        # Parse form data from request
        form_data = await request.form()
        topics = form_data.get("topics", "")
        posts = form_data.get("posts", "")
        days = form_data.get("days", "")
        num_ideas_str = form_data.get("num_ideas", "")
        recommendations = form_data.get("recommendations", "")  # New: recommendations context
        
        # Parse topics, posts, and days from form data
        topics_list = []
        if topics:
            # Topics come as: "Topic A" , "Topic B"
            # Remove quotes and split by comma
            topics_list = [t.strip().strip('"').strip("'") for t in topics.split(",") if t.strip()]
        
        posts_list = []
        if posts:
            # Posts come as: "Your post here"
            posts_list = [posts.strip().strip('"').strip("'")]
        
        days_list = []
        if days:
            # Days come as: Monday, Tuesday
            days_list = [d.strip() for d in days.split(",") if d.strip()]
        
        # Parse num_ideas - use provided value or fall back to days count
        try:
            num_ideas = int(num_ideas_str) if num_ideas_str else len(days_list) if days_list else 1
        except ValueError:
            num_ideas = len(days_list) if days_list else 1
        
        # If we have recommendations but no topics, extract topics from recommendations
        if not topics_list and recommendations:
            # Extract keywords from recommendations (look for bold text, quoted text, etc.)
            import re
            # Extract **bold** text
            bold_keywords = re.findall(r'\*\*([^*]+)\*\*', recommendations)
            # Extract "quoted" text
            quoted_keywords = re.findall(r'"([^"]+)"', recommendations)
            # Extract capitalized phrases (potential topics)
            capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', recommendations)
            topics_list = list(set(bold_keywords + quoted_keywords + capitalized[:5]))  # Limit capitalized to avoid noise
        
        # If still no topics, try to extract from posts
        if not topics_list and posts_list:
            # Use the post content as a topic if available
            topics_list = [post[:100] for post in posts_list if post.strip()]  # Use first 100 chars of post as topic
        
        # If still no topics, allow proceeding with a generic topic
        # This allows users to proceed with content creation even if topics weren't explicitly provided
        # The selected items from ContentQueue/ResearchAssistant should be sufficient
        if not topics_list:
            # Use a generic topic to allow the process to continue
            # The user has already selected items, so we should proceed
            topics_list = ["Content creation"]  # Generic fallback to allow proceeding
            logger.info("⚠️ No explicit topics provided, using generic fallback to allow content creation to proceed")
        
        if num_ideas < 1:
            return {"status": "error", "message": "Number of ideas must be at least 1"}
        
        # Initialize LLM and agent
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key.strip(), temperature=0.7)
        agent = IdeaGeneratorAgent(llm, db_session=db)
        
        # Generate ideas - pass num_ideas and recommendations context
        ideas = await agent.generate_ideas(topics_list, posts_list, days_list, num_ideas=num_ideas, recommendations=recommendations)
        
        if not ideas or len(ideas) == 0:
            return {"status": "error", "message": "Failed to generate ideas"}
        
        logger.info(f"✅ Generated {len(ideas)} content ideas")
        
        # Return same format as original implementation
        return {
            "status": "success",
            "ideas": ideas
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating content ideas: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")

@content_router.post("/campaigns/{campaign_id}/generate-content/force-complete/{task_id}")
async def force_complete_content_generation(
    campaign_id: str,
    task_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force complete a hung content generation task.
    Marks all running agents as error and sets task status to error.
    """
    try:
        from models import Campaign
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if task_id not in CONTENT_GEN_TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = CONTENT_GEN_TASKS[task_id]
        
        # Mark all running agents as error
        if "agent_statuses" in task:
            for agent_status in task["agent_statuses"]:
                if agent_status.get("status") == "running":
                    agent_status["status"] = "error"
                    agent_status["agent_status"] = "error"
                    agent_status["error"] = "Force completed by user - agent was hung"
                    agent_status["task"] = f"{agent_status.get('task', 'Processing')} - FORCE COMPLETED"
        
        # Set task status to error
        task["status"] = "error"
        task["error"] = "Task force completed due to hung agents"
        task["current_agent"] = None
        task["current_task"] = "Task force completed - agents were hung"
        task["progress"] = task.get("progress", 0)
        
        logger.warning(f"⚠️ Task {task_id} force completed by user {current_user.id}")
        
        return {
            "status": "error",
            "message": "Task force completed",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Error force completing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Image Generation Endpoint
@content_router.post("/generate_image_machine_content")
async def generate_image_machine_content_endpoint(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an image for machine content using DALL·E.
    Accepts POST with body: { id, query (article content), image_settings (optional) }
    Also accepts GET with query params: ?id=...&query=...
    
    The prompt is built by:
    1. Using the article content (query) to determine what the image should depict
    2. Incorporating image settings (style, color, additional prompt) to style the image
    """
    try:
        # Try to get data from POST body first
        try:
            body = await request.json()
            content_id = body.get("id")
            article_content = body.get("query")  # This is the article content/summary
            image_settings = body.get("image_settings") or body.get("imageSettings")
        except:
            # Fallback to query params (for GET requests)
            content_id = request.query_params.get("id")
            article_content = request.query_params.get("query")
            image_settings = None
        
        if not content_id or not article_content:
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters: 'id' and 'query' (article content) are required"
            )
        
        # Import image generation function
        try:
            from tools import generate_image
        except ImportError:
            logger.error("Could not import generate_image from tools")
            raise HTTPException(
                status_code=500,
                detail="Image generation service not available"
            )
        
        # Build the image prompt:
        # 1. Extract key visual elements from article content (what the image should show)
        # 2. Apply image settings (style, color, additional prompt) to style it
        
        # Start with article content - this determines WHAT the image depicts
        # Extract a summary or key visual concept from the article
        article_summary = article_content[:500] if len(article_content) > 500 else article_content
        
        # Get Global Image Agent prompt - ALWAYS use it for image generation
        global_image_agent_prompt = ""
        try:
            from models import SystemSettings
            # Try to get the Global Image Agent prompt
            global_agent_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "creative_agent_global_image_agent_prompt"
            ).first()
            if global_agent_setting and global_agent_setting.setting_value:
                global_image_agent_prompt = global_agent_setting.setting_value
            else:
                # Fallback: use default prompt if Global Image Agent not configured yet
                global_image_agent_prompt = "Create visually compelling images that align with the content's message and tone. Ensure images are professional, on-brand, and enhance the overall content experience."
                logger.info("Using default Global Image Agent prompt (agent not yet configured)")
        except Exception as e:
            logger.warning(f"Could not fetch Global Image Agent prompt: {e}")
            # Fallback to default prompt
            global_image_agent_prompt = "Create visually compelling images that align with the content's message and tone. Ensure images are professional, on-brand, and enhance the overall content experience."
        
        # Get additional creative agent prompt if selected
        additional_creative_agent_prompt = ""
        if image_settings:
            additional_agent_id = image_settings.get("additionalCreativeAgentId")
            logger.info(f"🎨 Image settings received: {image_settings}")
            logger.info(f"🎨 Additional Creative Agent ID: {additional_agent_id}")
            if additional_agent_id:
                try:
                    from models import SystemSettings
                    setting_key = f"creative_agent_{additional_agent_id}_prompt"
                    logger.info(f"🔍 Looking for creative agent prompt with key: {setting_key}")
                    additional_agent_setting = db.query(SystemSettings).filter(
                        SystemSettings.setting_key == setting_key
                    ).first()
                    if additional_agent_setting:
                        logger.info(f"✅ Found creative agent setting: {setting_key}")
                        if additional_agent_setting.setting_value:
                            additional_creative_agent_prompt = additional_agent_setting.setting_value
                            logger.info(f"✅ Creative agent prompt loaded ({len(additional_creative_agent_prompt)} chars): {additional_creative_agent_prompt[:200]}...")
                        else:
                            logger.warning(f"⚠️ Creative agent setting found but setting_value is empty for {setting_key}")
                    else:
                        logger.warning(f"⚠️ Creative agent setting NOT FOUND for key: {setting_key}")
                        # Log all available creative agent settings for debugging
                        all_creative_agents = db.query(SystemSettings).filter(
                            SystemSettings.setting_key.like("creative_agent_%_prompt")
                        ).all()
                        logger.info(f"📋 Available creative agent prompts: {[s.setting_key for s in all_creative_agents]}")
                except Exception as e:
                    logger.error(f"❌ Could not fetch additional creative agent prompt: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.info("ℹ️ No additionalCreativeAgentId provided in image_settings")
        
        # Build style components from image settings
        style_components = []
        if image_settings:
            style = image_settings.get("style", "")
            color = image_settings.get("color", "")
            additional_prompt = image_settings.get("prompt", "") or image_settings.get("additionalPrompt", "")
            
            if style:
                style_components.append(f"in {style} style")
            if color:
                style_components.append(f"with {color} color palette")
            if additional_prompt:
                style_components.append(additional_prompt)
        
        # Combine: Article content (what) + Global Image Agent prompt + Additional Creative Agent prompt + Image settings (how)
        # IMPORTANT: Custom creative agent prompt should be prominent and early in the prompt
        prompt_parts = []
        
        # Start with article summary (what the image should show)
        prompt_parts.append(article_summary)
        
        # Add Additional Creative Agent prompt EARLY and PROMINENTLY if available
        # This ensures DALL-E pays attention to the custom agent's instructions
        if additional_creative_agent_prompt:
            prompt_parts.append(f"IMPORTANT: Apply this creative direction: {additional_creative_agent_prompt}")
            logger.info(f"✅ Custom creative agent prompt INCLUDED prominently in final prompt")
        else:
            logger.info(f"ℹ️ No custom creative agent prompt to include")
        
        # ALWAYS add Global Image Agent prompt (it has a fallback default if not configured)
        prompt_parts.append(f"Follow these guidelines: {global_image_agent_prompt}")
        
        # Add style components
        if style_components:
            prompt_parts.append(f"Create an image {', '.join(style_components)}.")
        else:
            prompt_parts.append("Create a relevant image.")
        
        final_prompt = ". ".join(prompt_parts) + "."
        
        logger.info(f"🖼️ Generating image with FULL prompt ({len(final_prompt)} chars): {final_prompt}")
        logger.info(f"🖼️ Prompt breakdown:")
        logger.info(f"   - Article summary: {article_summary[:100]}...")
        logger.info(f"   - Global agent prompt: {global_image_agent_prompt[:100]}...")
        if additional_creative_agent_prompt:
            logger.info(f"   - Custom agent prompt: {additional_creative_agent_prompt[:100]}...")
        if style_components:
            logger.info(f"   - Style components: {', '.join(style_components)}")
        
        # Get API key for image generation
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or configure in Admin Settings > System > Platform Keys."
            )
        
        # Generate image using the combined prompt
        # The generate_image function takes (query, content, api_key) where:
        # - query: used for style matching in Airtable
        # - content: the actual prompt for DALL·E
        # - api_key: OpenAI API key for authentication
        try:
            image_url = generate_image(query=article_content, content=final_prompt, api_key=api_key)
            
            return {
                "status": "success",
                "image_url": image_url,
                "message": image_url
            }
        except Exception as img_error:
            logger.error(f"Error generating image: {img_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate image: {str(img_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_image_machine_content endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Also support GET for backward compatibility
@content_router.get("/generate_image_machine_content")
async def generate_image_machine_content_get(
    id: str,
    query: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """GET endpoint for image generation (backward compatibility)"""
    try:
        # Import image generation function
        try:
            from tools import generate_image
        except ImportError:
            logger.error("Could not import generate_image from tools")
            raise HTTPException(
                status_code=500,
                detail="Image generation service not available"
            )
        
        # Build prompt from article content (query parameter)
        article_content = query
        article_summary = article_content[:300].strip() if len(article_content) > 300 else article_content.strip()
        final_prompt = f"{article_summary}. Create a relevant, visually appealing image."
        
        logger.info(f"🖼️ Generating image (GET) with prompt: {final_prompt[:200]}...")
        
        # Generate image
        try:
            image_url = generate_image(query=article_content, content=final_prompt)
            
            return {
                "status": "success",
                "image_url": image_url,
                "message": image_url
            }
        except Exception as img_error:
            logger.error(f"Error generating image: {img_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate image: {str(img_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_image_machine_content GET endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Image Serving Endpoint
@content_router.get("/images/{filename}")
async def serve_image(filename: str):
    """
    Serve images from the uploads/images directory.
    Images are saved here by generate_image function in tools.py
    """
    try:
        import os
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        # Get the directory where content.py is located
        current_dir = Path(__file__).parent.parent.parent
        upload_dir = current_dir / "uploads" / "images"
        file_path = upload_dir / filename
        
        # Security: Validate filename (prevent path traversal)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Image not found: {file_path}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Return the image file
        return FileResponse(
            path=str(file_path),
            media_type="image/png",  # Default to PNG, but could detect from extension
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")

# Scheduled Posts Endpoints
@content_router.get("/scheduled-posts")
def get_scheduled_posts(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all scheduled posts for the authenticated user"""
    try:
        from models import Content
        from datetime import datetime
        
        logger.info(f"📋 Fetching scheduled posts for user {current_user.id}")
        
        # Get all content for the user that has been scheduled (status = 'scheduled' or has schedule_time in future)
        scheduled_posts = db.query(Content).filter(
            Content.user_id == current_user.id,
            Content.status.in_(["draft", "scheduled", "published"])
        ).order_by(Content.schedule_time.asc()).all()
        
        logger.info(f"📋 Found {len(scheduled_posts)} scheduled posts for user {current_user.id}")
        
        posts_data = []
        for post in scheduled_posts:
            posts_data.append({
                "id": post.id,
                "title": post.title or "",
                "content": post.content or "",
                "platform": post.platform,
                "schedule_time": post.schedule_time.isoformat() if post.schedule_time else None,
                "day": post.day,
                "week": post.week,
                "status": post.status or "draft",
                "image_url": post.image_url or "",
                "campaign_id": post.campaign_id,
                "can_edit": post.can_edit if hasattr(post, 'can_edit') else True,
                "is_draft": post.is_draft if hasattr(post, 'is_draft') else True,
            })
            logger.info(f"📋 Scheduled post: id={post.id}, campaign_id={post.campaign_id}, status={post.status}, has_image={bool(post.image_url)}")
        
        logger.info(f"✅ Returning {len(posts_data)} scheduled posts")
        
        return {
            "status": "success",
            "message": {
                "posts": posts_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching scheduled posts: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scheduled posts: {str(e)}"
        )

@content_router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scheduled post by ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from sqlalchemy import text
        
        logger.info(f"🗑️ Deleting post {post_id} for user {current_user.id}")
        
        # Use raw SQL to verify ownership and delete (avoid ORM column issues)
        check_query = text("""
            SELECT id FROM content 
            WHERE id = :post_id AND user_id = :user_id
            LIMIT 1
        """)
        check_result = db.execute(check_query, {
            "post_id": post_id,
            "user_id": current_user.id
        }).first()
        
        if not check_result:
            raise HTTPException(
                status_code=404,
                detail="Post not found or access denied"
            )
        
        # Delete the post using raw SQL
        delete_query = text("DELETE FROM content WHERE id = :post_id AND user_id = :user_id")
        db.execute(delete_query, {
            "post_id": post_id,
            "user_id": current_user.id
        })
        db.commit()
        
        logger.info(f"✅ Post {post_id} deleted successfully")
        
        return {
            "status": "success",
            "message": "Post deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete post: {str(e)}"
        )(f"Error fetching scheduled posts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scheduled posts: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/schedule-content")
async def schedule_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule content items for a campaign - saves them to database with 'scheduled' status"""
    try:
        from models import Content, Campaign
        from datetime import datetime
        import json
        
        # Verify campaign exists and belongs to user
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found"
            )
        
        # Get content items from request
        content_items = request_data.get("content_items", [])
        
        if not content_items:
            raise HTTPException(
                status_code=400,
                detail="No content items provided"
            )
        
        scheduled_count = 0
        errors = []
        for item in content_items:
            try:
                # Parse schedule time
                schedule_time_str = item.get("schedule_time")
                schedule_time = None
                if schedule_time_str:
                    try:
                        # Try ISO format first
                        if 'T' in schedule_time_str:
                            schedule_time = datetime.fromisoformat(schedule_time_str.replace('Z', '+00:00'))
                        else:
                            # Try other formats
                            try:
                                schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%dT%H:%M:%S")
                            except:
                                schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%d %H:%M:%S")
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse schedule_time '{schedule_time_str}': {parse_error}")
                        # Default to today at 9 AM if parsing fails
                        schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    # Default to today at 9 AM
                    schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                
                # MySQL doesn't support timezone-aware datetimes, so convert to naive UTC
                from datetime import timezone
                if schedule_time.tzinfo is not None:
                    schedule_time = schedule_time.astimezone(timezone.utc).replace(tzinfo=None)
                # If already naive, assume it's UTC and use as-is
                
                # Check if content already exists (by campaign_id, week, day, platform)
                existing_content = db.query(Content).filter(
                    Content.campaign_id == campaign_id,
                    Content.week == item.get("week", 1),
                    Content.day == item.get("day", "Monday"),
                    Content.platform == item.get("platform", "linkedin").lower(),
                    Content.user_id == current_user.id
                ).first()
                
                if existing_content:
                    # Update existing content
                    content_text = item.get("description") or item.get("content", "")
                    title_text = item.get("title", "")
                    
                    # Validate and update content - ensure we don't overwrite with empty strings
                    if content_text and content_text.strip():
                        existing_content.content = content_text
                    elif not existing_content.content or not existing_content.content.strip():
                        # Only set default if content is truly empty
                        existing_content.content = f"Content for {item.get('platform', 'linkedin').title()} - {item.get('day', 'Monday')}"
                    
                    if title_text and title_text.strip():
                        existing_content.title = title_text
                    elif not existing_content.title or not existing_content.title.strip():
                        # Only set default if title is truly empty
                        existing_content.title = f"{item.get('platform', 'linkedin').title()} Post - {item.get('day', 'Monday')}"
                    
                    existing_content.schedule_time = schedule_time
                    existing_content.status = "scheduled"  # Move from draft to scheduled
                    existing_content.is_draft = False
                    existing_content.can_edit = True  # Can still edit scheduled content
                    # Update image if provided (support both field names) - ALWAYS update even if empty to preserve existing
                    image_url = item.get("image") or item.get("image_url")
                    if image_url:
                        existing_content.image_url = image_url
                        logger.info(f"💾 Updated image_url when scheduling: {image_url[:100]}...")
                    else:
                        logger.info(f"⚠️ No image_url provided when scheduling existing content (keeping existing: {existing_content.image_url[:100] if existing_content.image_url else 'none'}...)")
                    logger.info(f"✅ Updated existing content to scheduled: week={item.get('week', 1)}, day={item.get('day', 'Monday')}, platform={item.get('platform', 'linkedin')}, has_image={bool(image_url or existing_content.image_url)}")
                    scheduled_count += 1
                else:
                    # Validate required fields
                    content_text = item.get("description") or item.get("content", "")
                    title_text = item.get("title", "")
                    
                    if not content_text or not content_text.strip():
                        logger.warning(f"Skipping item with empty content: {item.get('id', 'unknown')}")
                        continue
                    
                    if not title_text or not title_text.strip():
                        title_text = f"{item.get('platform', 'linkedin').title()} Post - {item.get('day', 'Monday')}"
                    
                    # Create new content
                    image_url = item.get("image") or item.get("image_url")
                    if image_url:
                        logger.info(f"💾 Saving image_url when scheduling new content: {image_url[:100]}...")
                    else:
                        logger.info(f"⚠️ No image_url provided when scheduling new content")
                    try:
                        new_content = Content(
                            user_id=current_user.id,
                            campaign_id=campaign_id,
                            week=item.get("week", 1),
                            day=item.get("day", "Monday"),
                            content=content_text,
                            title=title_text,
                            status="scheduled",  # Status: scheduled (was draft, now committed)
                            date_upload=datetime.now().replace(tzinfo=None),  # MySQL doesn't support timezone-aware datetimes
                            platform=item.get("platform", "linkedin").lower(),
                            file_name=f"{campaign_id}_{item.get('week', 1)}_{item.get('day', 'Monday')}_{item.get('platform', 'linkedin')}.txt",
                            file_type="text",
                            platform_post_no=item.get("platform_post_no", "1"),
                            schedule_time=schedule_time,
                            image_url=image_url,  # Support both field names
                            is_draft=False,  # No longer a draft
                            can_edit=True,  # Can still edit scheduled content
                            knowledge_graph_location=item.get("knowledge_graph_location"),
                            parent_idea=item.get("parent_idea"),
                            landing_page_url=item.get("landing_page_url")
                        )
                        db.add(new_content)
                        logger.info(f"✅ Created new scheduled content: week={item.get('week', 1)}, day={item.get('day', 'Monday')}, platform={item.get('platform', 'linkedin')}, has_image={bool(image_url)}")
                        scheduled_count += 1
                    except Exception as create_error:
                        logger.error(f"❌ Error creating Content object for item {item.get('id', 'unknown')}: {create_error}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        errors.append(f"Item {item.get('id', 'unknown')}: Failed to create content - {str(create_error)}")
                        continue
            except Exception as item_error:
                logger.error(f"Error processing content item {item.get('id', 'unknown')}: {item_error}")
                import traceback
                traceback.print_exc()
                errors.append(f"Item {item.get('id', 'unknown')}: {str(item_error)}")
                continue  # Continue with next item
        
        db.commit()
        
        if errors:
            logger.warning(f"Scheduled {scheduled_count} items with {len(errors)} errors")
            return {
                "status": "partial_success",
                "message": f"Successfully scheduled {scheduled_count} content item(s), {len(errors)} failed",
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"Successfully scheduled {scheduled_count} content item(s)"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error scheduling content: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule content: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/post-now")
async def post_content_now(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Post content immediately (skip scheduling) - uses same posting workflow as scheduled posts.
    This endpoint is for testing purposes to post content immediately without waiting for schedule_time.
    """
    try:
        from models import Content, Campaign, PlatformConnection, PlatformEnum
        from datetime import datetime
        import requests
        
        # Verify campaign exists and belongs to user
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found"
            )
        
        # Get content item from request
        content_id = request_data.get("content_id")
        content_item = request_data.get("content_item")
        
        logger.info(f"📤 Post Now request received: content_id={content_id}, has_content_item={bool(content_item)}")
        
        # If content_id provided, fetch from database
        if content_id:
            content = db.query(Content).filter(
                Content.id == content_id,
                Content.campaign_id == campaign_id,
                Content.user_id == current_user.id
            ).first()
            
            if not content:
                raise HTTPException(
                    status_code=404,
                    detail="Content not found"
                )
            
            content_text = content.content or ""
            title = content.title or ""
            platform = content.platform or "linkedin"
            image_url = content.image_url
        elif content_item:
            # Use provided content item (for articles not yet saved to DB)
            content_text = content_item.get("description") or content_item.get("content", "")
            title = content_item.get("title", "")
            platform = content_item.get("platform", "linkedin").lower()
            image_url = content_item.get("image") or content_item.get("image_url")
            content_id = None
        else:
            logger.error(f"❌ Post Now: Neither content_id nor content_item provided. Request data: {request_data}")
            raise HTTPException(
                status_code=400,
                detail="Either content_id or content_item is required"
            )
        
        logger.info(f"📤 Post Now: content_text length={len(content_text) if content_text else 0}, platform={platform}, has_image={bool(image_url)}")
        
        if not content_text or not content_text.strip():
            logger.error(f"❌ Post Now: Content text is empty or missing")
            raise HTTPException(
                status_code=400,
                detail="Content text is required"
            )
        
        # Route to appropriate platform posting function
        platform_lower = platform.lower()
        
        if platform_lower == "linkedin":
            # Call LinkedIn posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if not connection or not connection.access_token:
                raise HTTPException(
                    status_code=400,
                    detail="LinkedIn not connected. Please connect your LinkedIn account first."
                )
            
            api_url = "https://api.linkedin.com/v2/ugcPosts"
            headers = {
                "Authorization": f"Bearer {connection.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            post_data = {
                "author": f"urn:li:person:{current_user.id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content_text},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            
            if image_url:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "media": image_url
                }]
            
            response = requests.post(api_url, json=post_data, headers=headers, timeout=30)
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"LinkedIn API error: {response.status_code} - {response.text}"
                )
            
            post_id = response.json().get("id")
            platform_name = "LinkedIn"
            
        elif platform_lower == "twitter" or platform_lower == "x":
            # Call Twitter posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.TWITTER
            ).first()
            
            if not connection or not connection.access_token or not connection.refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="Twitter not connected. Please connect your Twitter account first."
                )
            
            from requests_oauthlib import OAuth1Session
            from dotenv import load_dotenv
            import os
            load_dotenv()
            
            oauth = OAuth1Session(
                os.getenv("TWITTER_API_KEY"),
                client_secret=os.getenv("TWITTER_API_SECRET"),
                resource_owner_key=connection.access_token,
                resource_owner_secret=connection.refresh_token
            )
            
            api_url = "https://api.twitter.com/2/tweets"
            tweet_data = {"text": content_text[:280]}
            
            if image_url:
                media_url = "https://upload.twitter.com/1.1/media/upload.json"
                media_response = oauth.post(media_url, files={"media": requests.get(image_url).content})
                if media_response.status_code == 200:
                    media_id = media_response.json().get("media_id_string")
                    tweet_data["media"] = {"media_ids": [media_id]}
            
            response = oauth.post(api_url, json=tweet_data, timeout=30)
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Twitter API error: {response.status_code} - {response.text}"
                )
            
            post_id = response.json().get("data", {}).get("id")
            platform_name = "Twitter"
            
        elif platform_lower == "instagram":
            # Call Instagram posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.INSTAGRAM
            ).first()
            
            if not connection or not connection.access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram not connected. Please connect your Instagram account first."
                )
            
            # Validate platform_user_id - must be numeric Instagram Business Account ID
            if not connection.platform_user_id:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram Business Account ID is missing. Please reconnect your Instagram account."
                )
            
            # Check if platform_user_id is numeric (Instagram Business Account IDs are numeric)
            if not connection.platform_user_id.isdigit():
                logger.warning(f"⚠️ Invalid Instagram Business Account ID detected: '{connection.platform_user_id}' (expected numeric ID, got display name). Attempting to auto-fix...")
                
                # Try to auto-fix by fetching the Instagram Business Account ID from existing access token
                try:
                    # Get user's Facebook Pages (Instagram Business Accounts are linked to Pages)
                    pages_url = "https://graph.facebook.com/v18.0/me/accounts"
                    pages_params = {"access_token": connection.access_token}
                    pages_response = requests.get(pages_url, params=pages_params, timeout=30)
                    
                    instagram_business_account_id = None
                    page_access_token = None
                    
                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        pages = pages_data.get("data", [])
                        
                        logger.info(f"🔍 Found {len(pages)} Facebook Pages, searching for Instagram Business Account...")
                        
                        # Find the first page with an Instagram Business Account
                        for page in pages:
                            page_id = page.get("id")
                            page_access_token = page.get("access_token")
                            
                            if not page_id or not page_access_token:
                                continue
                            
                            # Get Instagram Business Account for this page
                            instagram_url = f"https://graph.facebook.com/v18.0/{page_id}"
                            instagram_params = {
                                "fields": "instagram_business_account",
                                "access_token": page_access_token
                            }
                            instagram_response = requests.get(instagram_url, params=instagram_params, timeout=30)
                            
                            if instagram_response.status_code == 200:
                                instagram_data = instagram_response.json()
                                if instagram_data.get("instagram_business_account"):
                                    instagram_business_account_id = instagram_data["instagram_business_account"]["id"]
                                    logger.info(f"✅ Auto-fixed: Found Instagram Business Account ID: {instagram_business_account_id}")
                                    # Update the connection with the correct ID and page access token
                                    connection.platform_user_id = instagram_business_account_id
                                    connection.access_token = page_access_token  # Use page access token for Instagram API
                                    db.commit()
                                    logger.info(f"✅ Updated Instagram connection with correct Business Account ID")
                                    break
                    
                    if not instagram_business_account_id:
                        logger.error(f"❌ Could not auto-fix Instagram Business Account ID. No Instagram Business Account found linked to Facebook Pages.")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections. Make sure your Instagram account is linked to a Facebook Page."
                        )
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Error auto-fixing Instagram Business Account ID: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    )
                except Exception as e:
                    logger.error(f"❌ Unexpected error auto-fixing Instagram Business Account ID: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    )
            
            # Instagram requires image, so check if we have one
            if not image_url:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram posts require an image. Please generate an image first."
                )
            
            logger.info(f"📸 Posting to Instagram Business Account ID: {connection.platform_user_id}")
            
            # Create media container
            container_url = f"https://graph.facebook.com/v18.0/{connection.platform_user_id}/media"
            container_params = {
                "image_url": image_url,
                "caption": content_text,
                "access_token": connection.access_token
            }
            
            container_response = requests.post(container_url, params=container_params, timeout=30)
            
            if container_response.status_code not in [200, 201]:
                error_text = container_response.text
                # Parse error for better user message
                try:
                    error_json = container_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    error_code = error_json.get("error", {}).get("code", "")
                    if "does not exist" in error_message or "missing permissions" in error_message:
                        user_friendly_error = f"Instagram Business Account ID '{connection.platform_user_id}' is invalid or you don't have permissions. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    else:
                        user_friendly_error = f"Instagram API error: {error_message}"
                except:
                    user_friendly_error = f"Instagram API error: {error_text[:200]}"
                
                logger.error(f"❌ Instagram container creation failed: {error_text}")
                raise HTTPException(
                    status_code=400,
                    detail=user_friendly_error
                )
            
            creation_id = container_response.json().get("id")
            
            # Publish the media
            publish_url = f"https://graph.facebook.com/v18.0/{connection.platform_user_id}/media_publish"
            publish_params = {
                "creation_id": creation_id,
                "access_token": connection.access_token
            }
            
            publish_response = requests.post(publish_url, params=publish_params, timeout=30)
            
            if publish_response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Instagram publish error: {publish_response.status_code} - {publish_response.text}"
                )
            
            post_id = publish_response.json().get("id")
            platform_name = "Instagram"
            
        elif platform_lower == "facebook":
            # Call Facebook posting logic (posts to Facebook Page)
            logger.info(f"📘 Facebook posting requested for user {current_user.id}")
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.FACEBOOK
            ).first()
            
            logger.info(f"📘 Facebook connection found: {connection is not None}, has_token: {connection.access_token is not None if connection else False}")
            
            if not connection or not connection.access_token:
                logger.error(f"❌ Facebook not connected for user {current_user.id}")
                raise HTTPException(
                    status_code=400,
                    detail="Facebook not connected. Please connect your Facebook account first."
                )
            
            # Facebook requires a Page ID to post to
            # First, get user's pages to find the page to post to
            pages_url = "https://graph.facebook.com/v18.0/me/accounts"
            pages_params = {"access_token": connection.access_token}
            logger.info(f"📘 Fetching Facebook Pages for user {current_user.id}...")
            pages_response = requests.get(pages_url, params=pages_params, timeout=30)
            
            if pages_response.status_code != 200:
                error_text = pages_response.text
                logger.error(f"❌ Facebook Pages API failed (status {pages_response.status_code}): {error_text[:500]}")
                
                # Try to parse error for better message
                try:
                    error_json = pages_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    error_code = error_json.get("error", {}).get("code", "")
                    
                    # Check if it's a permissions issue
                    if "permission" in error_message.lower() or error_code in ["200", "10"]:
                        detail = f"Missing Facebook permissions. The error was: {error_message}. Please disconnect and reconnect your Facebook account, ensuring you grant ALL requested permissions (pages_show_list, pages_read_engagement, pages_manage_posts)."
                    else:
                        detail = f"Failed to get Facebook Pages: {error_message}"
                except:
                    detail = f"Failed to get Facebook Pages: {error_text[:200]}"
                
                raise HTTPException(status_code=400, detail=detail)
            
            pages_data = pages_response.json()
            pages = pages_data.get("data", [])
            logger.info(f"📘 Facebook Pages API returned {len(pages)} pages")
            
            if not pages:
                # Check what permissions the token actually has
                try:
                    permissions_url = "https://graph.facebook.com/v18.0/me/permissions"
                    permissions_params = {"access_token": connection.access_token}
                    permissions_response = requests.get(permissions_url, params=permissions_params, timeout=10)
                    
                    if permissions_response.status_code == 200:
                        permissions_data = permissions_response.json()
                        granted_perms = [p.get("permission") for p in permissions_data.get("data", []) if p.get("status") == "granted"]
                        logger.info(f"📘 Granted Facebook permissions: {granted_perms}")
                        
                        required_perms = ["pages_show_list", "pages_read_engagement", "pages_manage_posts"]
                        missing_perms = [p for p in required_perms if p not in granted_perms]
                        
                        if missing_perms:
                            detail = f"No Facebook Pages found. Missing required permissions: {', '.join(missing_perms)}. Please disconnect and reconnect your Facebook account, ensuring you grant ALL requested permissions when Facebook shows the permission screen."
                        else:
                            detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                    else:
                        detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                except Exception as perm_error:
                    logger.warning(f"⚠️ Could not check permissions: {perm_error}")
                    detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                
                raise HTTPException(status_code=400, detail=detail)
            
            # Use the first page (or could let user select)
            page = pages[0]
            page_id = page.get("id")
            page_access_token = page.get("access_token")
            
            if not page_id or not page_access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get Facebook Page access token"
                )
            
            logger.info(f"📘 Posting to Facebook Page ID: {page_id}")
            
            # Post to Facebook Page
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
            post_params = {
                "message": content_text,
                "access_token": page_access_token
            }
            
            # Add image if available
            if image_url:
                post_params["link"] = image_url
            
            post_response = requests.post(post_url, params=post_params, timeout=30)
            
            if post_response.status_code not in [200, 201]:
                error_text = post_response.text
                try:
                    error_json = post_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    user_friendly_error = f"Facebook API error: {error_message}"
                except:
                    user_friendly_error = f"Facebook API error: {error_text[:200]}"
                
                logger.error(f"❌ Facebook post failed: {error_text}")
                raise HTTPException(
                    status_code=400,
                    detail=user_friendly_error
                )
            
            post_id = post_response.json().get("id")
            platform_name = "Facebook"
            
        elif platform_lower == "wordpress":
            # Call WordPress posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.WORDPRESS
            ).first()
            
            if not connection or not connection.platform_user_id or not connection.access_token or not connection.refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="WordPress not connected. Please connect your WordPress site first."
                )
            
            from requests.auth import HTTPBasicAuth
            
            # For WordPress: platform_user_id = site_url, refresh_token = username, access_token = plugin_api_key
            site_url = connection.platform_user_id
            username = connection.refresh_token  # WordPress username (not used for plugin endpoint)
            plugin_api_key = connection.access_token  # WordPress plugin API key (activation_key) stored in access_token
            
            # Ensure site_url doesn't have trailing slash for API endpoint
            site_url = site_url.rstrip('/')
            # Use plugin's custom endpoint which only requires API key (no user permission checks)
            api_url = f"{site_url}/wp-json/vernal-contentum/v1/posts"
            
            logger.info(f"📤 WordPress Post Now: site_url={site_url}, api_url={api_url}, has_api_key={bool(plugin_api_key)}")
            
            # Get WordPress-specific fields from content if available
            wordpress_title = title or "Untitled Post"
            wordpress_excerpt = None
            permalink_slug = None
            
            if content_id:
                # Try to get WordPress fields from database
                content_obj = db.query(Content).filter(Content.id == content_id).first()
                if content_obj:
                    if hasattr(content_obj, 'post_title') and content_obj.post_title:
                        wordpress_title = content_obj.post_title
                    if hasattr(content_obj, 'post_excerpt') and content_obj.post_excerpt:
                        wordpress_excerpt = content_obj.post_excerpt
                    if hasattr(content_obj, 'permalink') and content_obj.permalink:
                        permalink_slug = content_obj.permalink
            elif content_item:
                # Get WordPress fields from content_item
                if content_item.get("post_title"):
                    wordpress_title = content_item.get("post_title")
                if content_item.get("post_excerpt"):
                    wordpress_excerpt = content_item.get("post_excerpt")
                if content_item.get("permalink"):
                    permalink_slug = content_item.get("permalink")
            
            post_data = {
                "title": wordpress_title,
                "content": content_text,
                "status": "publish"
            }
            
            # Add WordPress-specific fields if available
            if wordpress_excerpt:
                post_data["excerpt"] = wordpress_excerpt
            
            # Plugin endpoint uses 'slug' for permalink
            if permalink_slug:
                # Note: Plugin endpoint may not support slug directly, but we'll include it
                # The plugin's create_post method doesn't explicitly handle slug, but WordPress will auto-generate from title
                pass  # Plugin endpoint doesn't support slug parameter in current implementation
            
            # Plugin endpoint supports featured_image_url (URL, not media ID)
            if image_url:
                # Plugin endpoint accepts URL and will download/attach it
                post_data["featured_image_url"] = image_url
                logger.info(f"📤 WordPress Post Now: Setting featured_image_url={image_url}")
            
            # Use plugin API key authentication (X-API-Key header)
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": plugin_api_key
            }
            
            logger.info(f"📤 WordPress Post Now: Attempting to post with plugin API key (length={len(plugin_api_key) if plugin_api_key else 0})")
            logger.info(f"📤 WordPress Post Now: Post data keys: {list(post_data.keys())}")
            
            response = requests.post(
                api_url,
                json=post_data,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"📤 WordPress API response: status={response.status_code}")
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(f"❌ WordPress API error: {response.status_code} - {error_text}")
                
                # Parse error for better user message
                try:
                    error_json = response.json()
                    error_code = error_json.get("code", "")
                    error_message = error_json.get("message", error_text)
                    
                    # Check for common WordPress permission errors
                    if response.status_code == 401:
                        if "rest_cannot_create" in error_code or "not allowed to create posts" in error_message.lower():
                            detail = f"WordPress permission error: The user '{username}' does not have permission to create posts. Please ensure:\n1. The WordPress user has the 'Editor' or 'Administrator' role\n2. The Application Password was created correctly\n3. The Application Password has not been revoked\n\nError: {error_message}"
                        else:
                            detail = f"WordPress authentication failed. Please verify:\n1. The username is correct: '{username}'\n2. The Application Password is correct and not revoked\n3. The Application Password was copied correctly (no extra spaces)\n\nError: {error_message}"
                    else:
                        detail = f"WordPress API error ({response.status_code}): {error_message}"
                except:
                    detail = f"WordPress API error ({response.status_code}): {error_text[:500]}"
                
                raise HTTPException(
                    status_code=400,
                    detail=detail
                )
            
            post_id = response.json().get("id")
            platform_name = "WordPress"
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform: {platform}. Supported platforms: linkedin, twitter, instagram, facebook, wordpress"
            )
        
        # Update content status if content_id exists
        if content_id:
            content = db.query(Content).filter(Content.id == content_id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
                logger.info(f"✅ Updated content {content_id} status to 'posted'")
        
        logger.info(f"✅ Posted to {platform_name} immediately for user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"Content posted to {platform_name} successfully",
            "post_id": post_id,
            "platform": platform_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting content immediately: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to post content: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/save-content-item")
async def save_content_item(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a single content item (draft) to database - called when content/image is generated"""
    try:
        from models import Content, Campaign
        from datetime import datetime
        
        logger.info(f"💾 save-content-item called for campaign {campaign_id} by user {current_user.id}")
        logger.info(f"📦 Request data: {request_data}")
        
        # Verify campaign exists
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        item = request_data
        week = item.get("week", 1)
        day = item.get("day", "Monday")
        platform_str = item.get("platform", "linkedin").lower()
        
        logger.info(f"🔍 Platform from request: '{platform_str}' (type: {type(platform_str)})")
        
        # Map platform string to PlatformEnum for validation, but store as string in database
        from models import PlatformEnum
        platform_map = {
            "linkedin": PlatformEnum.LINKEDIN,
            "instagram": PlatformEnum.INSTAGRAM,
            "facebook": PlatformEnum.FACEBOOK,
            "twitter": PlatformEnum.TWITTER,
            "youtube": PlatformEnum.YOUTUBE,
            "wordpress": PlatformEnum.WORDPRESS,
            "tiktok": PlatformEnum.TIKTOK,
        }
        platform_enum = platform_map.get(platform_str, PlatformEnum.LINKEDIN)
        # Convert to string for database storage (database column is String, not Enum)
        # CRITICAL: Always use lowercase for database storage to ensure consistency
        platform_db_value = (platform_enum.value if hasattr(platform_enum, 'value') else str(platform_enum)).lower()
        
        logger.info(f"🔍 Platform enum: {platform_enum}, DB value: '{platform_db_value}' (type: {type(platform_db_value)})")
        
        # Check if request includes a database ID (numeric) - if so, find that specific content item
        existing_content = None
        content_id = item.get("id")
        database_id = None  # Track if we have a numeric database ID
        
        # If id is provided and is numeric (database ID), find that specific content item and update it
        if content_id and isinstance(content_id, (int, str)):
            try:
                # Check if it's a numeric database ID
                if str(content_id).isdigit():
                    content_id_int = int(content_id)
                    database_id = content_id_int
                    # Use raw SQL to avoid ORM trying to SELECT non-existent columns
                    from sqlalchemy import text
                    id_check_query = text("""
                        SELECT id FROM content 
                        WHERE id = :id 
                        AND campaign_id = :campaign_id 
                        AND user_id = :user_id
                        LIMIT 1
                    """)
                    id_check_result = db.execute(id_check_query, {
                        "id": content_id_int,
                        "campaign_id": campaign_id,
                        "user_id": current_user.id
                    }).first()
                    
                    if id_check_result:
                        # Use raw SQL to get content data (avoid ORM column issues)
                        existing_data_query = text("SELECT * FROM content WHERE id = :id LIMIT 1")
                        existing_data = db.execute(existing_data_query, {"id": content_id_int}).first()
                        if existing_data:
                            existing_content = dict(existing_data._mapping)
                            logger.info(f"🔍 Found existing content by database ID: {content_id_int}")
                else:
                    # ID is not numeric (frontend-generated like "week-1-Monday-linkedin-0-post-1")
                    # Still check for existing content by week/day/platform to avoid duplicates
                    logger.info(f"🔍 Non-numeric ID provided ({content_id}), checking for existing content by week/day/platform")
            except (ValueError, TypeError):
                # ID format is unexpected, still check for existing content
                logger.info(f"🔍 ID format unexpected ({content_id}), checking for existing content by week/day/platform")
        
        # ALWAYS check by week/day/platform if no existing content found by database ID
        # This prevents duplicate content creation when frontend uses composite IDs
        # CRITICAL: Use raw SQL to avoid ORM trying to SELECT non-existent columns
        if not existing_content:
            from sqlalchemy import text
            # Use raw SQL to check for existing content - avoids ORM column issues
            check_query = text("""
                SELECT id FROM content 
                WHERE campaign_id = :campaign_id 
                AND week = :week 
                AND day = :day 
                AND platform = :platform 
                AND user_id = :user_id
                LIMIT 1
            """)
            check_result = db.execute(check_query, {
                "campaign_id": campaign_id,
                "week": week,
                "day": day,
                "platform": platform_db_value.lower(),  # Ensure lowercase for comparison
                "user_id": current_user.id
            }).first()
            
            if check_result:
                existing_id = dict(check_result._mapping)['id']
                # Use raw SQL to get content data (avoid ORM column issues)
                existing_data_query = text("SELECT * FROM content WHERE id = :id LIMIT 1")
                existing_data = db.execute(existing_data_query, {"id": existing_id}).first()
                if existing_data:
                    existing_content = dict(existing_data._mapping)
                    logger.info(f"🔍 Found existing content by week/day/platform: week={week}, day={day}, platform={platform_db_value}, db_id={existing_id}")
            else:
                logger.info(f"🔍 No existing content found for week={week}, day={day}, platform={platform_db_value.lower()}, will create new")
        
        # If still no existing content, we'll create a new one
        
        # Parse schedule time if provided
        schedule_time = None
        if item.get("schedule_time"):
            try:
                schedule_time_str = item.get("schedule_time")
                if 'T' in schedule_time_str:
                    schedule_time = datetime.fromisoformat(schedule_time_str.replace('Z', '+00:00'))
                else:
                    schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%dT%H:%M:%S")
            except:
                schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # MySQL doesn't support timezone-aware datetimes, so convert to naive UTC
        if schedule_time.tzinfo is not None:
            from datetime import timezone
            schedule_time = schedule_time.astimezone(timezone.utc).replace(tzinfo=None)
        
        if existing_content:
            # Update existing content using raw SQL (avoid ORM column issues)
            existing_id = existing_content['id']
            # Get content from either "description" or "content" field
            # Check if key exists (not just truthy) so we can save empty strings to clear content
            content_update = None
            if "description" in item:
                content_update = item.get("description", "")
            elif "content" in item:
                content_update = item.get("content", "")
            
            image_url = item.get("image") or item.get("image_url")
            
            # Get actual columns from database
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            content_columns = [col['name'] for col in inspector.get_columns('content')]
            
            # Build UPDATE statement with only existing columns
            update_fields = []
            update_values = {"id": existing_id}
            
            if item.get("title"):
                update_fields.append("title = :title")
                update_values["title"] = item.get("title")
            
            # Always update content if provided (even if empty string) - allows clearing content
            if content_update is not None:
                update_fields.append("content = :content")
                update_values["content"] = content_update
                logger.info(f"💾 Updating content: length={len(content_update)}, empty={not content_update.strip()}")
            
            if image_url:
                update_fields.append("image_url = :image_url")
                update_values["image_url"] = image_url
            
            update_fields.append("status = :status")
            update_values["status"] = "draft"
            
            update_fields.append("is_draft = :is_draft")
            update_values["is_draft"] = 1
            
            update_fields.append("can_edit = :can_edit")
            update_values["can_edit"] = 1
            
            update_fields.append("schedule_time = :schedule_time")
            update_values["schedule_time"] = schedule_time
            
            if item.get("week"):
                update_fields.append("week = :week")
                update_values["week"] = week
            
            if item.get("day"):
                update_fields.append("day = :day")
                update_values["day"] = day
            
            if item.get("platform"):
                update_fields.append("platform = :platform")
                update_values["platform"] = platform_db_value
            
            # WordPress-specific fields (only update if columns exist and key is present in item)
            # Check if key exists (not just truthy) so we can save empty strings to clear fields
            if "post_title" in content_columns and "post_title" in item:
                update_fields.append("post_title = :post_title")
                update_values["post_title"] = item.get("post_title") or None
                logger.info(f"💾 Updating post_title: '{item.get('post_title')}'")
            
            if "post_excerpt" in content_columns and "post_excerpt" in item:
                update_fields.append("post_excerpt = :post_excerpt")
                update_values["post_excerpt"] = item.get("post_excerpt") or None
                logger.info(f"💾 Updating post_excerpt: '{item.get('post_excerpt')}'")
            
            if "permalink" in content_columns and "permalink" in item:
                update_fields.append("permalink = :permalink")
                update_values["permalink"] = item.get("permalink") or None
                logger.info(f"💾 Updating permalink: '{item.get('permalink')}'")
            
            if update_fields:
                update_stmt = text(f"UPDATE content SET {', '.join(update_fields)} WHERE id = :id")
                logger.info(f"🔧 Executing UPDATE: {update_stmt}")
                logger.info(f"🔧 UPDATE values: {update_values}")
                db.execute(update_stmt, update_values)
                db.commit()  # Explicitly commit the transaction
                logger.info(f"✅ Updated existing content (ID: {existing_id}): week={week}, day={day}, platform={platform_db_value}, image={bool(image_url)}")
                
                # Verify the update by querying back
                verify_query = text("SELECT post_title, post_excerpt, permalink FROM content WHERE id = :id")
                verify_result = db.execute(verify_query, {"id": existing_id}).first()
                if verify_result:
                    verified = dict(verify_result._mapping)
                    logger.info(f"✅ Verified WordPress fields after update: post_title='{verified.get('post_title')}', post_excerpt='{verified.get('post_excerpt')}', permalink='{verified.get('permalink')}'")
            
            # Set final_content_id for return
            final_content_id = existing_id
        else:
            # Validate required fields
            content_text = item.get("description") or item.get("content", "")
            title_text = item.get("title", "")
            
            # If content is empty, use a placeholder (for image-only saves)
            if not content_text or not content_text.strip():
                platform_name = platform_db_value.title()
                content_text = f"Content for {platform_name} - {day}"
            
            # If title is empty, generate a default
            if not title_text or not title_text.strip():
                platform_name = platform_db_value.title()
                title_text = f"{platform_name} Post - {day}"
            
            # Create new content using ORM (more robust than raw SQL)
            # Support both "image" and "image_url" field names
            image_url = item.get("image") or item.get("image_url")
            if image_url:
                logger.info(f"💾 Saving image_url for new content: {image_url[:100]}...")
            else:
                logger.info(f"⚠️ No image_url provided in save request for new content")
            
            try:
                now = datetime.now().replace(tzinfo=None)
                # Ensure all required fields have defaults
                week = week or 1
                day = day or "Monday"
                
                # Use hybrid approach: ORM table definition but controlled INSERT
                # This prevents SQLAlchemy from trying to insert columns that don't exist
                from sqlalchemy import inspect
                
                # Get actual columns from database
                inspector = inspect(db.bind)
                content_columns = [col['name'] for col in inspector.get_columns('content')]
                logger.info(f"📋 Database content table has {len(content_columns)} columns")
                
                # Use platform_db_value (already converted to string)
                file_name = f"{campaign_id}_{week}_{day}_{platform_db_value}.txt"
                
                # Build values dict with only columns that exist in database
                values = {
                    "user_id": current_user.id,
                    "campaign_id": campaign_id,
                    "week": week,
                    "day": day,
                    "content": content_text,
                    "title": title_text,
                    "status": "draft",
                    "date_upload": now,
                    "platform": platform_db_value,  # Use string value, not PlatformEnum
                    "file_name": file_name,
                    "file_type": "text",
                    "platform_post_no": item.get("platform_post_no", "1"),
                    "schedule_time": schedule_time,
                    "image_url": image_url if image_url else None,
                    "is_draft": 1,
                    "can_edit": 1,
                }
                
                # Add optional columns only if they exist in database
                if "knowledge_graph_location" in content_columns and item.get("knowledge_graph_location"):
                    values["knowledge_graph_location"] = item.get("knowledge_graph_location")
                
                if "parent_idea" in content_columns and item.get("parent_idea"):
                    values["parent_idea"] = item.get("parent_idea")
                
                if "landing_page_url" in content_columns and item.get("landing_page_url"):
                    values["landing_page_url"] = item.get("landing_page_url")
                
                # WordPress-specific fields (only add if columns exist and values provided)
                if "post_title" in content_columns and item.get("post_title"):
                    values["post_title"] = item.get("post_title")
                
                if "post_excerpt" in content_columns and item.get("post_excerpt"):
                    values["post_excerpt"] = item.get("post_excerpt")
                
                if "permalink" in content_columns and item.get("permalink"):
                    values["permalink"] = item.get("permalink")
                
                if "use_without_image" in content_columns:
                    values["use_without_image"] = 1 if item.get("use_without_image", False) else 0
                
                # Use Content.__table__ to get the table definition, but control which columns are inserted
                # This gives us ORM benefits (type safety, table definition) but full control over INSERT
                from sqlalchemy import text
                columns_str = ", ".join([col for col in values.keys() if col in content_columns])
                placeholders_str = ", ".join([f":{col}" for col in values.keys() if col in content_columns])
                
                insert_stmt = text(f"""
                    INSERT INTO content ({columns_str})
                    VALUES ({placeholders_str})
                """)
                
                # Filter values to only include columns that exist
                filtered_values = {k: v for k, v in values.items() if k in content_columns}
                
                result = db.execute(insert_stmt, filtered_values)
                content_id = result.lastrowid
                
                # CRITICAL: For raw SQL, we need to explicitly commit the statement
                # SQLAlchemy doesn't auto-track raw SQL in the session like ORM does
                db.flush()  # Flush to ensure data is sent to database
                logger.info(f"✅ Created new content (ID: {content_id}): week={week}, day={day}, platform={platform_db_value}, has_image={bool(image_url)}")
                
                # Verify the insert worked by immediately querying
                verify_content = db.execute(text("SELECT id FROM content WHERE id = :id"), {"id": content_id}).first()
                if verify_content:
                    logger.info(f"🔍 Verification: Content {content_id} is visible in database immediately after insert")
                else:
                    logger.warning(f"⚠️ Warning: Content {content_id} not visible immediately after insert (may be transaction isolation)")
            except Exception as create_error:
                logger.error(f"❌ Error creating Content object: {create_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create content item: {str(create_error)}"
                )
        
        # Commit the transaction
        db.commit()
        
        # Get the final content_id for return value
        if not existing_content:
            final_content_id = content_id if 'content_id' in locals() else None
        
        logger.info(f"✅ Committed content save for campaign {campaign_id}, user {current_user.id}, content_id={final_content_id}")
        
        # CRITICAL: Verify the commit worked by querying the database immediately after commit
        # This helps catch transaction isolation issues where data isn't visible to subsequent queries
        try:
            verify_count = db.execute(
                text("SELECT COUNT(*) as count FROM content WHERE campaign_id = :campaign_id AND user_id = :user_id"),
                {"campaign_id": campaign_id, "user_id": current_user.id}
            ).first()
            if verify_count:
                logger.info(f"🔍 Post-commit verification: Database now has {verify_count.count} content items for campaign {campaign_id}")
            else:
                logger.warning(f"⚠️ Post-commit verification: Could not verify content count")
        except Exception as verify_error:
            logger.warning(f"⚠️ Post-commit verification failed: {verify_error}")
        
        return {
            "status": "success",
            "message": "Content item saved",
            "content_id": final_content_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving content item: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save content item: {str(e)}"
        )

@content_router.get("/campaigns/{campaign_id}/content-items")
def get_campaign_content_items(
    campaign_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all content items for a campaign (draft, scheduled, pending, uploaded)"""
    try:
        from models import Content
        from sqlalchemy import or_
        
        logger.info(f"📋 Fetching content items for campaign {campaign_id}, user {current_user.id}")
        
        # CRITICAL: Use raw SQL query to ensure we see data inserted via raw SQL
        # ORM queries might not see raw SQL inserts due to session caching
        from sqlalchemy import text
        try:
            # First try with raw SQL to ensure we see all data
            raw_query = text("""
                SELECT * FROM content 
                WHERE campaign_id = :campaign_id AND user_id = :user_id
                ORDER BY week ASC, day ASC
            """)
            raw_results = db.execute(raw_query, {"campaign_id": campaign_id, "user_id": current_user.id}).fetchall()
            logger.info(f"📋 Raw SQL query found {len(raw_results)} content items for campaign {campaign_id}")
            
            # Log sample of what we found for debugging
            if raw_results:
                sample = dict(raw_results[0]._mapping)
                logger.info(f"📋 Sample content item: id={sample.get('id')}, campaign_id={sample.get('campaign_id')}, user_id={sample.get('user_id')}, platform='{sample.get('platform')}', week={sample.get('week')}, day='{sample.get('day')}'")
            else:
                logger.warning(f"⚠️ Raw SQL returned 0 results for campaign_id='{campaign_id}', user_id={current_user.id}")
                # Double-check: query all content for this user to see if campaign_id is wrong
                all_user_content = db.execute(
                    text("SELECT COUNT(*) as count, GROUP_CONCAT(DISTINCT campaign_id) as campaigns FROM content WHERE user_id = :user_id"),
                    {"user_id": current_user.id}
                ).first()
                if all_user_content:
                    logger.info(f"🔍 User {current_user.id} has {all_user_content.count} total content items across campaigns: {all_user_content.campaigns}")
            
            # Use raw SQL results directly (avoid ORM column issues)
            content_items = []
            if raw_results and len(raw_results) > 0:
                # Convert raw SQL results to dictionaries
                content_items = [dict(row._mapping) for row in raw_results]
                logger.info(f"📋 Converted {len(content_items)} raw SQL results to dictionaries")
            else:
                content_items = []
            
            # No fallback needed - raw SQL is the source of truth
        except Exception as query_error:
            logger.error(f"❌ Error with raw SQL query: {query_error}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            content_items = []  # Return empty on error
        
        logger.info(f"📋 Found {len(content_items)} content items for campaign {campaign_id}")
        
        items_data = []
        for item in content_items:
            try:
                # item is now a dict from raw SQL, not an ORM object
                item_id = item.get('id')
                image_url = item.get('image_url') or ""
                week = item.get('week') or 1
                day = item.get('day') or "Monday"
                platform = item.get('platform') or "linkedin"
                status = item.get('status') or "draft"
                title = item.get('title') or ""
                content_text = item.get('content') or ""
                schedule_time = item.get('schedule_time')
                date_upload = item.get('date_upload')
                
                # Handle datetime objects from raw SQL
                schedule_time_str = None
                if schedule_time:
                    if hasattr(schedule_time, 'isoformat'):
                        schedule_time_str = schedule_time.isoformat()
                    elif hasattr(schedule_time, 'strftime'):
                        schedule_time_str = schedule_time.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        schedule_time_str = str(schedule_time)
                
                created_at_str = None
                if date_upload:
                    if hasattr(date_upload, 'isoformat'):
                        created_at_str = date_upload.isoformat()
                    elif hasattr(date_upload, 'strftime'):
                        created_at_str = date_upload.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        created_at_str = str(date_upload)
                
                # WordPress-specific fields
                post_title = item.get('post_title') or None
                post_excerpt = item.get('post_excerpt') or None
                permalink = item.get('permalink') or None
                
                items_data.append({
                    "id": f"week-{week}-{day}-{platform}-{item_id}",  # Composite ID for frontend
                    "database_id": item_id,  # Include database ID separately so frontend can use it for updates
                    "title": title,
                    "description": content_text,
                    "week": week,
                    "day": day,
                    "platform": platform.lower() if platform else "linkedin",  # Ensure lowercase
                    "image": image_url,  # Ensure image_url is returned as "image" for frontend
                    "image_url": image_url,  # Also include image_url for compatibility
                    "status": status,
                    "schedule_time": schedule_time_str,
                    "created_at": created_at_str,  # Creation timestamp - IMPORTANT data point
                    "contentProcessedAt": None,  # Column doesn't exist in DB
                    "imageProcessedAt": None,  # Column doesn't exist in DB
                    "contentPublishedAt": None,  # Column doesn't exist in DB
                    "imagePublishedAt": None,  # Column doesn't exist in DB
                    "use_without_image": False,  # Column doesn't exist in DB
                    # WordPress-specific fields
                    "post_title": post_title,
                    "post_excerpt": post_excerpt,
                    "permalink": permalink,
                })
                logger.info(f"📋 Item: week={week}, day={day}, platform={platform}, status={status}, has_image={bool(image_url)}, db_id={item_id}")
            except Exception as item_error:
                logger.error(f"Error processing content item {item.get('id', 'unknown')}: {item_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue  # Skip this item but continue with others
        
        logger.info(f"✅ Returning {len(items_data)} items for campaign {campaign_id}")
        return {
            "status": "success",
            "message": {
                "items": items_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching content items: {e}")
        import traceback
        traceback.print_exc()
        # Return empty array instead of 500 error for better UX
        logger.warning(f"⚠️ Returning empty items array due to error: {e}")
        return {
            "status": "success",
            "message": {
                "items": []
            }
        }

# ============================================================================

        user_name = None
        try:
            profile_url = "https://graph.facebook.com/v18.0/me"
            params = {
                "access_token": access_token,
                "fields": "email,name"
            }
            profile_response = requests.get(profile_url, params=params)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_email = profile_data.get("email")
                user_name = profile_data.get("name")
                logger.info(f"✅ Fetched Instagram/Facebook profile: email={user_email}, name={user_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch Instagram/Facebook profile: {e}")
            # Continue without profile info - connection still works
        
        # Use email if available, otherwise use name, otherwise use a generic identifier
        platform_user_identifier = user_email or user_name or "Instagram User"
        
        # Get user's Facebook Pages (Instagram Business Accounts are linked to Pages)
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        
        instagram_business_account_id = None
        if pages_response.status_code == 200:
            pages_data = pages_response.json()
            pages = pages_data.get("data", [])
            
            # Find the first page with an Instagram Business Account
            for page in pages:
                page_id = page.get("id")
                page_access_token = page.get("access_token")
                
                # Get Instagram Business Account for this page
                instagram_url = f"https://graph.facebook.com/v18.0/{page_id}"
                instagram_params = {
                    "fields": "instagram_business_account",
                    "access_token": page_access_token
                }
                instagram_response = requests.get(instagram_url, params=instagram_params)
                
                if instagram_response.status_code == 200:
                    instagram_data = instagram_response.json()
                    if instagram_data.get("instagram_business_account"):
                        instagram_business_account_id = instagram_data["instagram_business_account"]["id"]
                        # Use the page access token for Instagram API calls
                        access_token = page_access_token
                        break
        
        # Store or update connection
        # Use user email/name for display, fallback to business account ID if no profile info
        display_identifier = platform_user_identifier if platform_user_identifier != "Instagram User" else (instagram_business_account_id or "Instagram User")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if connection:
            connection.access_token = access_token
            connection.platform_user_id = display_identifier
            connection.connected_at = datetime.now()
        else:
            connection = PlatformConnection(
                user_id=user_id,
                platform=PlatformEnum.INSTAGRAM,
                platform_user_id=display_identifier,
                access_token=access_token,
                connected_at=datetime.now()
            )
            db.add(connection)
        
        db.commit()
        
        logger.info(f"✅ Instagram connection successful for user {user_id}, Instagram Business Account ID: {instagram_business_account_id}")
        return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?instagram=connected")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in Instagram callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=instagram_connection_failed")
if __name__ == "__main__":
    import uvicorn
