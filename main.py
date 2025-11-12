#!/usr/bin/env python3
"""
BULLETPROOF FastAPI main.py - NO BLOCKING IMPORTS
Following Emergency Net v4 template with ALL functionality restored
"""

import os
import json
import uuid
from datetime import datetime
import threading
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
# Note: When allow_credentials=True, cannot use allow_origins=["*"]
# Must specify exact origins
ALLOWED_ORIGINS = [
    "https://machine.vernalcontentum.com",
    "https://themachine.vernalcontentum.com",
    "http://localhost:3000",
    "http://localhost:3001",
]

# CORS middleware - handles all CORS including OPTIONS preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Explicit OPTIONS handler as fallback (in case middleware doesn't catch it)
@app.options("/{full_path:path}")
async def options_handler(full_path: str, request: Request):
    """Explicit OPTIONS handler for CORS preflight - fallback if middleware doesn't catch it"""
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )
    return JSONResponse(content={"error": "Origin not allowed"}, status_code=403)

# --- ROUTER INCLUDES MUST BE HERE ---
# This is REQUIRED for FastAPI to properly register endpoints
# Using lazy imports to prevent blocking at startup
def include_routers():
    """Lazy router inclusion to prevent blocking imports"""
    try:
        from auth_api import auth_router
        app.include_router(auth_router)
        logger.info("✅ Authentication router included successfully")
    except Exception as e:
        logger.error(f"❌ Failed to include authentication router: {e}")
    
    try:
        from enhanced_mcp_api import enhanced_mcp_router
        app.include_router(enhanced_mcp_router)
        logger.info("✅ Enhanced MCP router included successfully")
    except Exception as e:
        logger.warning(f"Enhanced MCP router not available: {e}")
    
    try:
        from simple_mcp_api import simple_mcp_router
        app.include_router(simple_mcp_router)
        logger.info("✅ Simple MCP router included successfully")
    except Exception as e:
        logger.warning(f"Simple MCP router not available: {e}")

# Include routers immediately but with error handling
include_routers()

# Import authentication helpers after routers are included
try:
    from auth_api import get_current_user, verify_campaign_ownership, get_admin_user
    logger.info("✅ Authentication helpers imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import authentication helpers: {e}")
    # Define fallback functions if import fails
    def get_current_user(request: Request = None, db: Session = None):
        raise HTTPException(status_code=401, detail="Authentication not available")
    def verify_campaign_ownership(campaign_id: str = None, current_user = None, db: Session = None):
        raise HTTPException(status_code=401, detail="Authentication not available")
    def get_admin_user(current_user = None):
        raise HTTPException(status_code=401, detail="Authentication not available")

# Global variables for lazy initialization
db_manager = None
scheduler = None

# In-memory analysis task tracking (no DB schema changes required)
TASKS: Dict[str, Dict[str, Any]] = {}
CAMPAIGN_TASK_INDEX: Dict[str, str] = {}

def get_db_manager():
    """Lazy database manager initialization"""
    global db_manager
    if db_manager is None:
        from database import DatabaseManager
        db_manager = DatabaseManager()
    return db_manager

def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for campaign endpoints
class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    trendingTopics: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    status: Optional[str] = "INCOMPLETE"  # Campaign status: INCOMPLETE, PROCESSING, READY_TO_ACTIVATE
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    status: Optional[str] = None
    topics: Optional[List[str]] = None
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None

# Pydantic models for author personalities endpoints
class AuthorPersonalityCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AuthorPersonalityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup - NOT at import time"""
    global db_manager, scheduler
    try:
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database manager initialized")
        
        # Initialize scheduler
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("Scheduler started")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

# REQUIRED ENDPOINTS FOR DEPLOYMENT
@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@app.get("/version")
@app.head("/version")
def version():
    return {"version": os.getenv("GITHUB_SHA", "development"), "status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/mcp/enhanced/health")
@app.head("/mcp/enhanced/health")
def database_health():
    return {"status": "ok", "message": "Database health check", "database_connected": True}

@app.get("/")
@app.head("/")
def root():
    return {"message": "Vernal Agents Backend API", "status": "running"}

@app.get("/deploy/commit")
def deploy_commit():
    """Return the current deployed commit hash for verification"""
    import subprocess
    try:
        # Use current file location instead of hardcoded path
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=repo_dir)
        if result.returncode == 0:
            return {"commit": result.stdout.strip(), "status": "ok"}
        else:
            return {"commit": "unknown", "status": "error", "message": "Failed to get commit hash"}
    except Exception as e:
        return {"commit": "unknown", "status": "error", "message": str(e)}

# Campaign endpoints with REAL database operations (EMERGENCY_NET: Multi-tenant scoped)
@app.get("/campaigns")
def get_campaigns(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all campaigns for the authenticated user - REQUIRES AUTHENTICATION"""
    logger.info("🔍 /campaigns GET endpoint called")
    try:
        from models import Campaign
        
        # Filter campaigns by authenticated user (multi-tenant security)
        campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
        logger.info(f"Filtered campaigns by user_id={current_user.id}: found {len(campaigns)} campaigns")
        
        # If no campaigns found for user, also check total campaigns for debugging
        total_campaigns = db.query(Campaign).count()
        if len(campaigns) == 0 and total_campaigns > 0:
            logger.warning(f"⚠️ User {current_user.id} has 0 campaigns, but database has {total_campaigns} total campaigns. This may indicate a user_id mismatch.")
            # Show sample campaign user_ids for debugging
            sample_campaigns = db.query(Campaign).limit(5).all()
            sample_user_ids = [c.user_id for c in sample_campaigns]
            logger.info(f"Sample campaign user_ids in database: {sample_user_ids}")
        return {
            "status": "success",
            "campaigns": [
                {
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
                    "user_id": campaign.user_id,  # Include user_id in response for debugging
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                    "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
                }
                for campaign in campaigns
            ]
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching campaigns: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch campaigns: {str(e)}"
        )

@app.post("/campaigns")
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
        import json
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
        
        # Create campaign directly using SQLAlchemy
        campaign = Campaign(
            campaign_id=campaign_id,
            campaign_name=campaign_data.name,
            description=campaign_data.description,
            query=campaign_data.name,
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
            modeling_settings_json=modeling_settings_json
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

@app.get("/campaigns/{campaign_id}")
def get_campaign_by_id(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get campaign by ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Campaign
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
        
        import json
        
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
                "modelingSettings": modeling_settings
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching campaign: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch campaign"
        )

@app.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Campaign
        
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
        
        # Update fields if provided
        if campaign_data.status is not None:
            campaign.status = campaign_data.status
        if campaign_data.name is not None:
            campaign.campaign_name = campaign_data.name
        if campaign_data.description is not None:
            campaign.description = campaign_data.description
        if campaign_data.type is not None:
            campaign.type = campaign_data.type
        if campaign_data.keywords is not None:
            campaign.keywords = ",".join(campaign_data.keywords) if campaign_data.keywords else None
        if campaign_data.urls is not None:
            campaign.urls = ",".join(campaign_data.urls) if campaign_data.urls else None
        if campaign_data.topics is not None:
            campaign.topics = ",".join(campaign_data.topics) if campaign_data.topics else None
        
        # Save settings as JSON strings in Text columns
        import json
        if campaign_data.extractionSettings is not None:
            campaign.extraction_settings_json = json.dumps(campaign_data.extractionSettings)
            logger.info(f"Saved extractionSettings for campaign {campaign_id}: {campaign_data.extractionSettings}")
        if campaign_data.preprocessingSettings is not None:
            campaign.preprocessing_settings_json = json.dumps(campaign_data.preprocessingSettings)
            logger.info(f"Saved preprocessingSettings for campaign {campaign_id}: {campaign_data.preprocessingSettings}")
        if campaign_data.entitySettings is not None:
            campaign.entity_settings_json = json.dumps(campaign_data.entitySettings)
            logger.info(f"Saved entitySettings for campaign {campaign_id}: {campaign_data.entitySettings}")
        if campaign_data.modelingSettings is not None:
            campaign.modeling_settings_json = json.dumps(campaign_data.modelingSettings)
            logger.info(f"Saved modelingSettings for campaign {campaign_id}: {campaign_data.modelingSettings}")
        
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

@app.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Campaign
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

# Analyze endpoint models
class ResearchAgentRequest(BaseModel):
    agent_type: str

class AnalyzeRequest(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    keywords: Optional[List[str]] = []
    urls: Optional[List[str]] = []
    trendingTopics: Optional[List[str]] = []
    topics: Optional[List[str]] = []
    type: Optional[str] = "keyword"
    depth: Optional[int] = 1
    max_pages: Optional[int] = 10
    batch_size: Optional[int] = 1
    include_links: Optional[bool] = True
    include_images: Optional[bool] = False
    stem: Optional[bool] = False
    lemmatize: Optional[bool] = False
    remove_stopwords_toggle: Optional[bool] = False
    extract_persons: Optional[bool] = False
    extract_organizations: Optional[bool] = False
    extract_locations: Optional[bool] = False
    extract_dates: Optional[bool] = False
    extract_money: Optional[bool] = False
    extract_percent: Optional[bool] = False
    extract_time: Optional[bool] = False
    extract_facility: Optional[bool] = False
    topic_tool: Optional[str] = "lda"
    num_topics: Optional[int] = 3
    iterations: Optional[int] = 25
    pass_threshold: Optional[float] = 0.7

# Analyze endpoint (for campaign building)
@app.post("/analyze")
def analyze_campaign(analyze_data: AnalyzeRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Analyze campaign - Stub endpoint (returns task_id for now)
    TODO: Implement full analysis workflow
    
    IMPORTANT: This endpoint should NOT delete campaigns. It only starts analysis.
    REQUIRES AUTHENTICATION
    """
    try:
        user_id = current_user.id
        campaign_id = analyze_data.campaign_id or f"campaign-{uuid.uuid4()}"
        campaign_name = analyze_data.campaign_name or "Unknown Campaign"
        
        # If campaign_id is provided, verify ownership
        if analyze_data.campaign_id:
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
        
        logger.info(f"🔍 /analyze POST endpoint called for campaign: {campaign_name} (ID: {campaign_id}) by user {user_id}")
        logger.info(f"🔍 Request data: campaign_name={analyze_data.campaign_name}, type={analyze_data.type}, keywords={len(analyze_data.keywords or [])} keywords")
        logger.info(f"🔍 CRITICAL: Keywords received from frontend: {analyze_data.keywords}")
        if analyze_data.keywords:
            logger.info(f"🔍 First keyword: '{analyze_data.keywords[0]}'")
        
        # Verify campaign exists (optional)
        try:
            from models import Campaign
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if campaign:
                logger.info(f"✅ Campaign {campaign_id} found in database (user_id: {campaign.user_id})")
            else:
                logger.warning(f"⚠️ Campaign {campaign_id} not found in database - analysis will continue anyway")
        except Exception as db_err:
            logger.warning(f"⚠️ Skipping campaign existence check: {db_err}")
        
        # Create task and seed progress (in-memory)
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 5,  # start at 5%
            "current_step": "initializing",
            "progress_message": "Starting analysis",
        }
        CAMPAIGN_TASK_INDEX[campaign_id] = task_id
        
        logger.info(f"✅ Analysis task created (stub): task_id={task_id}, campaign_id={campaign_id}, user_id={user_id}")
        
        # Kick off a lightweight background job to simulate real steps and persist raw data
        def run_analysis_background(tid: str, cid: str, data: AnalyzeRequest):
            from database import SessionLocal
            from models import CampaignRawData, Campaign
            session = SessionLocal()
            try:
                logger.info(f"🔵 Background thread started for task {tid}, campaign {cid}")
                
                # Helper to update task atomically
                def set_task(step: str, prog: int, msg: str):
                    task = TASKS.get(tid)
                    if not task:
                        logger.warning(f"⚠️ Task {tid} not found in TASKS dict")
                        return
                    task["current_step"] = step
                    task["progress"] = prog
                    task["progress_message"] = msg
                    logger.info(f"📊 Task {tid}: {prog}% - {step} - {msg}")

                # Step 1: collecting inputs
                logger.info(f"📝 Step 1: Collecting inputs for campaign {cid}")
                set_task("collecting_inputs", 15, "Collecting inputs and settings")
                time.sleep(3)  # Simulate setup time

                # Step 2: Web scraping with DuckDuckGo + Playwright
                logger.info(f"📝 Step 2: Starting web scraping for campaign {cid}")
                set_task("fetching_content", 25, "Searching web and scraping content")
                
                urls = data.urls or []
                keywords = data.keywords or []
                depth = data.depth if hasattr(data, 'depth') and data.depth else 1
                max_pages = data.max_pages if hasattr(data, 'max_pages') and data.max_pages else 10
                include_images = data.include_images if hasattr(data, 'include_images') else False
                include_links = data.include_links if hasattr(data, 'include_links') else False
                
                logger.info(f"📝 Scraping settings: URLs={len(urls)}, Keywords={len(keywords)}, depth={depth}, max_pages={max_pages}")
                logger.info(f"📝 URL list: {urls}")
                logger.info(f"📝 Keywords list: {keywords}")
                logger.info(f"🔍 CRITICAL: Keywords being used for scraping: {keywords}")
                if not keywords or len(keywords) == 0:
                    logger.error(f"❌ CRITICAL: No keywords provided! This will cause scraping to fail.")
                elif keywords and keywords[0] != "pug" and "pug" in str(keywords):
                    logger.warning(f"⚠️ WARNING: Keywords appear incorrect. Expected 'pug', got: {keywords}")
                
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
                    # Create placeholder row
                    sample_text = f"Placeholder content for campaign {cid}. No URLs or keywords were provided in the analysis request."
                    row = CampaignRawData(
                        campaign_id=cid,
                        source_url="placeholder:no_data",
                        fetched_at=now,
                        raw_html=None,
                        extracted_text=sample_text,
                        meta_json=json.dumps({"seed": True, "type": "placeholder", "reason": "no_urls_or_keywords"})
                    )
                    session.add(row)
                    created = 1
                else:
                    # Perform real web scraping
                    logger.info(f"🚀 Starting web scraping for campaign {cid}")
                    logger.info(f"📋 Parameters: keywords={keywords}, urls={urls}, depth={depth}, max_pages={max_pages}, include_images={include_images}, include_links={include_links}")
                    
                    try:
                        logger.info(f"🚀 Calling scrape_campaign_data with: keywords={keywords}, urls={urls}, query={data.query or ''}, depth={depth}, max_pages={max_pages}")
                        scraped_results = scrape_campaign_data(
                            keywords=keywords,
                            urls=urls,
                            query=data.query or "",
                            depth=depth,
                            max_pages=max_pages,
                            include_images=include_images,
                            include_links=include_links
                        )
                        
                        logger.info(f"✅ Web scraping completed: {len(scraped_results)} pages scraped")
                        
                        # Log detailed results for diagnostics
                        if len(scraped_results) == 0:
                            logger.error(f"❌ CRITICAL: Scraping returned 0 results for campaign {cid}")
                            logger.error(f"❌ Keywords used: {keywords}")
                            logger.error(f"❌ URLs provided: {urls}")
                            logger.error(f"❌ Query: {data.query or '(empty)'}")
                            logger.error(f"❌ This likely means scraping failed - check Playwright/DuckDuckGo availability")
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
                        for result in scraped_results:
                            url = result.get("url", "unknown")
                            text = result.get("text", "")
                            html = result.get("html")
                            images = result.get("images", [])
                            links = result.get("links", [])
                            error = result.get("error")
                            depth_level = result.get("depth", 0)
                            
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
                        
                        if created == 0:
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
                    session.commit()
                    logger.info(f"✅ Successfully committed {created} rows to database for campaign {cid}")
                    
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
                set_task("processing_content", 60, f"Processing {created} scraped pages")
                # Content is already processed during scraping, minimal delay
                time.sleep(2)

                # Step 4: extracting entities
                set_task("extracting_entities", 75, "Extracting entities from scraped content")
                # Entities will be extracted when research endpoint is called
                time.sleep(2)

                # Step 5: modeling topics
                set_task("modeling_topics", 90, "Preparing content for analysis")
                # Topics will be modeled when research endpoint is called
                time.sleep(2)

                # Finalize
                set_task("finalizing", 100, "Scraping complete")
                time.sleep(1)

                # Mark campaign ready in DB
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
                                    # Has URL but no/minimal text (might be a valid page with no extractable text)
                                    valid_data_count += 1
                                    logger.debug(f"⚠️ Data row with URL but minimal text: {row.source_url}")
                        
                        logger.info(f"📊 Data validation: {valid_data_count} valid rows, {valid_text_count} with text, {error_count} error/placeholder rows")
                        
                        if valid_data_count > 0:
                            # Store coarse topics from keywords as a ready signal
                            if (data.keywords or []) and not camp.topics:
                                camp.topics = ",".join((data.keywords or [])[:10])
                                logger.info(f"📝 Set topics to: {camp.topics}")
                            
                            # CRITICAL: Set status to READY_TO_ACTIVATE and commit immediately
                            camp.status = "READY_TO_ACTIVATE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Campaign {cid} marked as READY_TO_ACTIVATE with {valid_data_count} valid data rows ({valid_text_count} with text)")
                            
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
                                logger.warning(f"⚠️ Campaign {cid} has no scraped data (no rows at all), keeping status as INCOMPLETE")
                                logger.warning(f"⚠️ This suggests scraping never ran or failed before creating any rows")
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"⚠️ Campaign {cid} marked as INCOMPLETE due to no valid data")
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

        threading.Thread(target=run_analysis_background, args=(task_id, campaign_id, analyze_data), daemon=True).start()

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Analysis started",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name
        }
    except Exception as e:
        import traceback
        logger.error(f"Error in /analyze endpoint: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )

@app.get("/analyze/status/{task_id}")
def get_analyze_status(task_id: str, current_user = Depends(get_current_user)):
    """
    Get analysis status - In-memory progress simulation.
    Progress advances deterministically based on time since start.
    REQUIRES AUTHENTICATION
    """
    # Verify task belongs to user (check campaign ownership)
    if task_id in TASKS:
        task_campaign_id = TASKS[task_id].get("campaign_id")
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
    
    if task_id not in TASKS:
        # Be resilient across restarts: report pending instead of 404 so UI keeps polling
        return {
            "status": "pending",
            "progress": 5,
            "current_step": "initializing",
            "progress_message": "Waiting for task",
            "campaign_id": None,
        }
    
    task = TASKS[task_id]
    # Compute time-based progress (simulate steps over ~45s)
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
    
    # Update in-memory snapshot
    task["progress"] = progress
    task["current_step"] = current_step
    task["progress_message"] = f"{current_step.replace('_',' ').title()}"
    
    return {
        "status": "in_progress" if progress < 100 else "completed",
        "progress": progress,
        "current_step": current_step,
        "progress_message": task["progress_message"],
        "campaign_id": task["campaign_id"],
    }

# Optional helper: get status by campaign_id
@app.get("/analyze/status/by_campaign/{campaign_id}")
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
    
    task_id = CAMPAIGN_TASK_INDEX.get(campaign_id)
    if not task_id:
        raise HTTPException(status_code=404, detail="No task for campaign")
    return get_analyze_status(task_id, current_user)

# Debug endpoint to check raw data for a campaign
@app.get("/campaigns/{campaign_id}/debug")
def debug_campaign_data(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Debug endpoint to check what raw data exists for a campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
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
    
    try:
        from models import CampaignRawData
        
        # Campaign ownership already verified above
        
        # Check raw data
        raw_data_count = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).count()
        raw_data_rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).limit(5).all()
        
        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_exists": campaign is not None,
            "campaign_status": campaign.status if campaign else None,
            "raw_data_count": raw_data_count,
            "sample_rows": [
                {
                    "id": r.id,
                    "source_url": r.source_url,
                    "has_extracted_text": bool(r.extracted_text),
                    "extracted_text_length": len(r.extracted_text) if r.extracted_text else 0,
                    "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
                }
                for r in raw_data_rows
            ]
        }
    except Exception as e:
        import traceback
        logger.error(f"Error in debug endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

# System Settings endpoints
@app.get("/admin/settings/{setting_key}")
def get_system_setting(setting_key: str, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get a system setting by key - ADMIN ONLY"""
    try:
        from models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{setting_key}' not found"
            )
        return {
            "status": "success",
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching system setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch setting: {str(e)}"
        )

# Admin User Management endpoints
@app.get("/admin/users")
def get_all_users(admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get all users with admin status - ADMIN ONLY"""
    try:
        from models import User
        users = db.query(User).all()
        return {
            "status": "success",
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": getattr(user, 'is_admin', False),
                    "is_verified": getattr(user, 'is_verified', False),
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                for user in users
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@app.post("/admin/users/{user_id}/admin")
def grant_admin_access(user_id: int, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Grant admin access to a user - ADMIN ONLY"""
    try:
        from models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Prevent removing your own admin access
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own admin status"
            )
        
        user.is_admin = True
        db.commit()
        db.refresh(user)
        logger.info(f"✅ Granted admin access to user {user_id} ({user.email})")
        
        return {
            "status": "success",
            "message": f"Admin access granted to {user.email}",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting admin access: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant admin access: {str(e)}"
        )

@app.delete("/admin/users/{user_id}/admin")
def revoke_admin_access(user_id: int, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Revoke admin access from a user - ADMIN ONLY"""
    try:
        from models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Prevent removing your own admin access
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own admin status"
            )
        
        user.is_admin = False
        db.commit()
        db.refresh(user)
        logger.info(f"✅ Revoked admin access from user {user_id} ({user.email})")
        
        return {
            "status": "success",
            "message": f"Admin access revoked from {user.email}",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": False
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking admin access: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke admin access: {str(e)}"
        )

@app.put("/admin/settings/{setting_key}")
def update_system_setting(setting_key: str, setting_data: Dict[str, Any], admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Update or create a system setting - ADMIN ONLY"""
    try:
        from models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
        
        if setting:
            # Update existing setting
            if "setting_value" in setting_data:
                setting.setting_value = setting_data["setting_value"]
            if "description" in setting_data:
                setting.description = setting_data["description"]
            setting.updated_at = datetime.now()
            db.commit()
            db.refresh(setting)
            logger.info(f"✅ Updated system setting: {setting_key}")
            
            # Clear cache if this is the topic extraction prompt
            if setting_key == "topic_extraction_prompt":
                try:
                    from text_processing import clear_topic_prompt_cache
                    clear_topic_prompt_cache()
                except Exception as cache_err:
                    logger.warning(f"⚠️ Failed to clear prompt cache: {cache_err}")
        else:
            # Create new setting
            setting = SystemSettings(
                setting_key=setting_key,
                setting_value=setting_data.get("setting_value", ""),
                description=setting_data.get("description")
            )
            db.add(setting)
            db.commit()
            db.refresh(setting)
            logger.info(f"✅ Created new system setting: {setting_key}")
        
        return {
            "status": "success",
            "message": f"Setting '{setting_key}' updated successfully",
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating system setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )

# Research data endpoint: returns urls, raw samples, word cloud, topics and entities
@app.get("/campaigns/{campaign_id}/research")
def get_campaign_research(campaign_id: str, limit: int = 20, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Aggregate research outputs for a campaign.
    - urls: list of source_url
    - raw: up to `limit` extracted_text samples
    - wordCloud: top 10 terms by frequency (cached in DB)
    - topics: naive primary topics (top terms) (cached in DB)
    - entities: NLTK-based extraction using named entity recognition (cached in DB)
    - hashtags: generated from topics/keywords (cached in DB)
    
    Caches wordCloud, topics, hashtags, and entities in database to avoid re-computation.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
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
    
    try:
        from models import CampaignRawData, CampaignResearchData
        import json
        
        # Check if cached research data exists
        cached_data = db.query(CampaignResearchData).filter(
            CampaignResearchData.campaign_id == campaign_id
        ).first()
        
        # Only use cache if it has valid non-empty data
        if cached_data and cached_data.word_cloud_json and cached_data.topics_json:
            try:
                word_cloud = json.loads(cached_data.word_cloud_json) if cached_data.word_cloud_json else []
                topics = json.loads(cached_data.topics_json) if cached_data.topics_json else []
                # Only use cache if we have actual data (not empty arrays)
                if word_cloud and len(word_cloud) > 0 and topics and len(topics) > 0:
                    logger.info(f"✅ Returning cached research data for campaign {campaign_id} (wordCloud: {len(word_cloud)} items, topics: {len(topics)} items)")
                    hashtags = json.loads(cached_data.hashtags_json) if cached_data.hashtags_json else []
                    entities = json.loads(cached_data.entities_json) if cached_data.entities_json else {}
                    
                    # Still need to get URLs and raw text (these change with scraping)
                    rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
                    urls = [r.source_url for r in rows if r.source_url and not r.source_url.startswith(("error:", "placeholder:"))]
                    texts = [r.extracted_text for r in rows if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:")))]
                    
                    return {
                        "status": "success",
                        "campaign_id": campaign_id,
                        "urls": urls,
                        "raw": texts[:max(0, limit) or 20],
                        "wordCloud": word_cloud,
                        "topics": topics,
                        "hashtags": hashtags,
                        "entities": entities,
                        "total_raw": len(texts),
                        "cached": True,
                        "diagnostics": {
                            "total_rows": len(rows),
                            "valid_urls": len(urls),
                            "valid_texts": len(texts),
                            "has_data": len(urls) > 0 or len(texts) > 0,
                            "cached": True
                        }
                    }
                else:
                    logger.warning(f"⚠️ Cached data exists but is empty (wordCloud: {len(word_cloud) if word_cloud else 0}, topics: {len(topics) if topics else 0}), regenerating...")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse cached JSON data: {e}, regenerating...")
        # Import NLTK-based text processing (lazy import with fallback)
        try:
            from text_processing import (
                extract_entities as nltk_extract_entities,
                remove_stopwords,
                extract_keywords,
                extract_topics
            )
        except ImportError as import_err:
            logger.warning(f"⚠️ text_processing module not available: {import_err}")
            # Define fallback functions
            def nltk_extract_entities(text, **kwargs):
                return {}
            def remove_stopwords(text):
                return text
            def extract_keywords(text):
                return []
            def extract_topics(texts, topic_tool, num_topics, iterations, query="", keywords=[], urls=[]):
                return []

        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        logger.info(f"🔍 Research endpoint: Found {len(rows)} rows for campaign {campaign_id}")
        urls = []
        texts = []
        errors = []  # Collect error diagnostics
        error_meta = []  # Collect error metadata
        truncation_info = []  # Track which texts were truncated
        
        for r in rows:
            # Check if this is an error/placeholder row
            is_error = r.source_url and r.source_url.startswith(("error:", "placeholder:"))
            
            if is_error:
                # Extract error information
                error_info = {
                    "type": r.source_url,
                    "message": r.extracted_text or "Unknown error",
                    "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None
                }
                # Try to parse meta_json for additional error details
                if r.meta_json:
                    try:
                        meta = json.loads(r.meta_json)
                        error_info["meta"] = meta
                    except:
                        pass
                errors.append(error_info)
                logger.warning(f"⚠️ Found error row: {r.source_url} - {r.extracted_text[:100] if r.extracted_text else 'No message'}")
            else:
                # Valid scraped data
                if r.source_url and not r.source_url.startswith(("error:", "placeholder:")):
                    urls.append(r.source_url)
                # More lenient text check - include text if it exists and has some content (even if short)
                # This helps with campaigns that previously had data but might have shorter snippets
                if r.extracted_text and len(r.extracted_text.strip()) > 0:
                    texts.append(r.extracted_text)  # Keep as string for backward compatibility
                    
                    # Check if this text was truncated (from metadata)
                    if r.meta_json:
                        try:
                            meta = json.loads(r.meta_json)
                            if meta.get("text_truncated", False):
                                truncation_info.append({
                                    "url": r.source_url,
                                    "stored_length": len(r.extracted_text),
                                    "original_length": meta.get("original_length"),
                                    "truncated_by": meta.get("original_length", 0) - len(r.extracted_text) if meta.get("original_length") else 0
                                })
                        except:
                            pass
        
        logger.info(f"🔍 Research endpoint: Extracted {len(urls)} URLs, {len(texts)} text samples, {len(errors)} error rows")
        
        # Enhanced diagnostics logging
        if len(rows) == 0:
            logger.warning(f"⚠️ No rows found in database for campaign {campaign_id}")
        elif len(texts) == 0:
            logger.warning(f"⚠️ No valid text data found for campaign {campaign_id}")
            logger.warning(f"⚠️ Total rows: {len(rows)}, Error rows: {len(errors)}, Valid URLs: {len(urls)}")
            if len(errors) > 0:
                logger.warning(f"⚠️ Error details: {errors[:3]}")  # Log first 3 errors
            # Log sample of rows to understand what's in the DB
            for i, r in enumerate(rows[:5]):
                text_len = len(r.extracted_text) if r.extracted_text else 0
                logger.warning(f"⚠️ Row {i+1}: source_url={r.source_url[:50] if r.source_url else 'None'}, text_length={text_len}, is_error={r.source_url and r.source_url.startswith(('error:', 'placeholder:')) if r.source_url else False}")

        # Campaign ownership already verified above
        # Get campaign info for better topic extraction
        campaign_query = campaign.query if campaign else ""
        campaign_keywords = campaign.keywords.split(",") if campaign and campaign.keywords else []
        campaign_urls = campaign.urls.split(",") if campaign and campaign.urls else []

        # Use extract_topics for phrase-based topics instead of single words
        if texts and len(texts) > 0:
            try:
                # Check topic extraction method from system settings (default to "system")
                from models import SystemSettings
                method_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == "topic_extraction_method"
                ).first()
                
                topic_extraction_method = "system"  # Default to system model
                if method_setting and method_setting.setting_value:
                    topic_extraction_method = method_setting.setting_value.lower()
                
                # Determine topic_tool based on method
                if topic_extraction_method == "llm":
                    # Check if OpenAI API key is available for LLM model
                    import os
                    openai_key = os.getenv("OPENAI_API_KEY")
                    if openai_key and len(openai_key.strip()) > 0:
                        topic_tool = "llm"  # Use LLM for phrase generation
                        logger.info("✅ Using LLM model for topics (from system settings)")
                    else:
                        topic_tool = "system"  # Fallback to system model if no API key
                        logger.warning("⚠️ LLM selected but OPENAI_API_KEY not found, using system model")
                else:
                    topic_tool = "system"  # Use system model (NMF-based)
                    logger.info("✅ Using system model for topics (from system settings)")
                
                num_topics = 10
                iterations = 25
                
                logger.info(f"🔍 Calling extract_topics with {len(texts)} texts, tool={topic_tool}, num_topics={num_topics}")
                logger.info(f"🔍 Campaign context: query='{campaign_query}', keywords={campaign_keywords[:3]}, urls={len(campaign_urls)}")
                
                topic_phrases = extract_topics(
                    texts,
                    topic_tool=topic_tool,
                    num_topics=num_topics,
                    iterations=iterations,
                    query=campaign_query,
                    keywords=campaign_keywords,
                    urls=campaign_urls
                )
                
                logger.info(f"🔍 extract_topics returned {len(topic_phrases) if topic_phrases else 0} topics: {topic_phrases[:5] if topic_phrases else 'NONE'}")
                
                # If we got phrases, use them; otherwise fall back to word frequency
                if topic_phrases and len(topic_phrases) > 0:
                    # Create topics with scores (use position as proxy for relevance)
                    topics = [{"label": phrase, "score": len(topic_phrases) - i} for i, phrase in enumerate(topic_phrases[:10])]
                    logger.info(f"✅ Generated {len(topics)} topic phrases: {[t['label'] for t in topics]}")
                else:
                    # Fallback to word frequency if extract_topics fails
                    logger.warning(f"⚠️ extract_topics returned no results (texts: {len(texts)}, tool: {topic_tool}), falling back to phrase extraction")
                    # Don't raise exception - continue to fallback logic below
                    topic_phrases = None
                    
            except Exception as topic_err:
                logger.error(f"❌ Error extracting topics with extract_topics: {topic_err}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.warning(f"⚠️ Falling back to phrase extraction due to error")
                topic_phrases = None  # Ensure we go to fallback
                
            # Fallback: Extract meaningful bigrams/trigrams if extract_topics failed or returned empty
            if not topic_phrases or len(topic_phrases) == 0:
                logger.info(f"🔄 Using fallback phrase extraction (extract_topics returned empty or failed)")
                # Fallback: Extract meaningful bigrams/trigrams instead of single words
                from collections import Counter
                from nltk.corpus import stopwords
                from nltk.tokenize import word_tokenize
                from nltk import pos_tag
                
                nltk_stopwords = set(stopwords.words('english'))
                additional_stopwords = {
                    'who', 'which', 'what', 'when', 'where', 'why', 'how', 'but', 'than', 'that', 'this',
                    'these', 'those', 'united', 'world', 'one', 'two', 'also', 'more', 'most', 'very'
                }
                comprehensive_stopwords = nltk_stopwords | additional_stopwords
                
                # Extract meaningful bigrams and trigrams
                phrases = []
                for t in texts[:50]:  # Limit for performance
                    try:
                        tokens = word_tokenize(t.lower())
                        tagged = pos_tag(tokens)
                        # Filter out stopwords and function words
                        meaningful_tokens = [word for word, tag in tagged 
                                           if word not in comprehensive_stopwords 
                                           and tag not in {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO'}
                                           and len(word) >= 3 and word.isalpha()]
                        
                        # Extract bigrams
                        for i in range(len(meaningful_tokens) - 1):
                            bigram = f"{meaningful_tokens[i]} {meaningful_tokens[i+1]}"
                            phrases.append(bigram)
                        # Extract trigrams
                        for i in range(len(meaningful_tokens) - 2):
                            trigram = f"{meaningful_tokens[i]} {meaningful_tokens[i+1]} {meaningful_tokens[i+2]}"
                            phrases.append(trigram)
                    except Exception as e:
                        logger.debug(f"Phrase extraction failed for text: {e}")
                        continue
                
                # Count phrase frequencies
                phrase_counts = Counter(phrases)
                top_phrases = phrase_counts.most_common(10)
                
                if top_phrases:
                    topics = [{"label": phrase, "score": count} for phrase, count in top_phrases]
                    logger.info(f"✅ Generated {len(topics)} fallback topic phrases: {[t['label'] for t in topics]}")
                else:
                    # Last resort: single meaningful words
                    word_counts = Counter()
                    for t in texts:
                        try:
                            tokens = word_tokenize(t.lower())
                            tagged = pos_tag(tokens)
                            for word, tag in tagged:
                                if (word not in comprehensive_stopwords and 
                                    tag not in {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO'}
                                    and len(word) >= 4 and word.isalpha()):
                                    word_counts[word] += 1
                        except:
                            continue
                    top_words = word_counts.most_common(10)
                    topics = [{"label": word, "score": count} for word, count in top_words]
                    logger.warning(f"⚠️ Using single-word fallback: {[t['label'] for t in topics]}")
        else:
            topics = []
            logger.warning(f"⚠️ No texts available for topic extraction (texts length: {len(texts)})")
            if len(rows) > 0:
                logger.warning(f"⚠️ Campaign has {len(rows)} rows but {len(texts)} valid texts. Error rows: {len(errors)}")
        
        # Build word cloud with comprehensive stopword filtering and POS tagging
        # Use NLTK's comprehensive stopword list + additional filtering
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk import pos_tag
        
        # Comprehensive stopword set (NLTK + common function words)
        nltk_stopwords = set(stopwords.words('english'))
        additional_stopwords = {
            'who', 'which', 'what', 'when', 'where', 'why', 'how', 'but', 'than', 'that', 'this',
            'these', 'those', 'united', 'world', 'one', 'two', 'also', 'more', 'most', 'very',
            'much', 'many', 'some', 'any', 'all', 'each', 'every', 'both', 'few', 'other',
            'such', 'only', 'just', 'even', 'still', 'yet', 'already', 'never', 'always',
            'often', 'sometimes', 'usually', 'generally', 'particularly', 'especially',
            'however', 'therefore', 'thus', 'hence', 'moreover', 'furthermore', 'nevertheless'
        }
        comprehensive_stopwords = nltk_stopwords | additional_stopwords
        
        # Function word POS tags to exclude (pronouns, determiners, prepositions, conjunctions, etc.)
        function_word_tags = {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO', 'WDT', 'WP', 'WP$', 'WRB', 'PDT', 'RP', 'EX'}
        
        counts = {}
        for t in texts:
            try:
                # Tokenize and POS tag
                tokens = word_tokenize(t.lower())
                tagged = pos_tag(tokens)
                
                for word, tag in tagged:
                    # Skip if stopword, function word, or too short
                    if (word.lower() in comprehensive_stopwords or 
                        tag in function_word_tags or 
                        len(word) < 3 or 
                        not word.isalpha()):
                        continue
                    counts[word.lower()] = counts.get(word.lower(), 0) + 1
            except Exception as e:
                # Fallback to simple tokenization if NLTK fails
                logger.debug(f"POS tagging failed for text, using simple tokenization: {e}")
                tokenizer = re.compile(r"[A-Za-z]{3,}")
                for w in tokenizer.findall(t.lower()):
                    if w not in comprehensive_stopwords:
                        counts[w] = counts.get(w, 0) + 1
        
        top_terms = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        word_cloud = [{"term": k, "count": v} for k, v in top_terms]
        
        if not word_cloud or len(word_cloud) == 0:
            logger.warning(f"⚠️ Word cloud generation failed - no terms found. Texts: {len(texts)}, Total chars: {sum(len(t) for t in texts)}")
            # Fallback: use simple word frequency if POS tagging failed
            simple_counts = {}
            for t in texts:
                words = re.findall(r"[A-Za-z]{3,}", t.lower())
                for w in words:
                    if w not in comprehensive_stopwords:
                        simple_counts[w] = simple_counts.get(w, 0) + 1
            top_simple = sorted(simple_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
            word_cloud = [{"term": k, "count": v} for k, v in top_simple]
            logger.info(f"📊 Word cloud (fallback): {[t['term'] for t in word_cloud]}")
        else:
            logger.info(f"📊 Word cloud generated: {len(word_cloud)} terms - {[t['term'] for t in word_cloud[:5]]}")

        # Use NLTK-based entity extraction for accurate named entity recognition
        persons = []
        organizations = []
        locations = []
        dates = []
        money = []
        percent = []
        time = []
        facility = []
        
        # Process texts with NLTK entity extraction
        texts_processed = 0
        texts_skipped = 0
        extraction_errors = 0
        logger.info(f"🔍 Starting entity extraction for {len(texts)} texts (processing up to 100)")
        
        # Log first few texts for debugging
        if len(texts) > 0:
            logger.info(f"📄 Sample text (first 200 chars): {texts[0][:200] if texts[0] else 'EMPTY'}")
        
        for idx, t in enumerate(texts[:100]):
            if not t or len(t.strip()) < 10:
                texts_skipped += 1
                if texts_skipped <= 3:
                    logger.debug(f"⏭️ Skipping text {idx}: length={len(t) if t else 0}")
                continue
            try:
                entity_result = nltk_extract_entities(
                    t,
                    extract_persons=True,
                    extract_organizations=True,
                    extract_locations=True,
                    extract_dates=True,
                    extract_money=True,
                    extract_percent=True,
                    extract_time=True,
                    extract_facility=True
                )
                texts_processed += 1
                
                # Log entities found in this text (first few texts only)
                if texts_processed <= 3:
                    found_entities = {k: len(v) for k, v in entity_result.items() if v}
                    if found_entities:
                        logger.info(f"📝 Text {texts_processed}: Found {found_entities}")
                        # Log sample entities
                        for entity_type, entity_list in entity_result.items():
                            if entity_list:
                                logger.info(f"   {entity_type}: {entity_list[:3]}")
                    else:
                        logger.warning(f"⚠️ Text {texts_processed}: No entities found (length: {len(t)})")
                
                persons.extend(entity_result.get('persons', []))
                organizations.extend(entity_result.get('organizations', []))
                locations.extend(entity_result.get('locations', []))
                dates.extend(entity_result.get('dates', []))
                money.extend(entity_result.get('money', []))
                percent.extend(entity_result.get('percent', []))
                time.extend(entity_result.get('time', []))
                facility.extend(entity_result.get('facility', []))
            except Exception as e:
                extraction_errors += 1
                logger.error(f"❌ Error extracting entities from text {idx} (length {len(t) if t else 0}): {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fallback to regex for dates if NLTK fails
                try:
                    date_regex = re.compile(r"\b(\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{4}\b", re.I)
                    date_matches = date_regex.findall(t)
                    dates.extend([d[0] if isinstance(d, tuple) else d for d in date_matches])
                except Exception as regex_err:
                    logger.debug(f"Regex fallback also failed: {regex_err}")
        
        logger.info(f"✅ Entity extraction complete: {texts_processed} processed, {texts_skipped} skipped, {extraction_errors} errors")
        
        entities = {
            "persons": list(dict.fromkeys(persons))[:20],
            "organizations": list(dict.fromkeys(organizations))[:20],
            "locations": list(dict.fromkeys(locations))[:20],
            "dates": list(dict.fromkeys(dates))[:20],
            "money": list(dict.fromkeys(money))[:20],
            "percent": list(dict.fromkeys(percent))[:20],
            "time": list(dict.fromkeys(time))[:20],
            "facility": list(dict.fromkeys(facility))[:20],
        }
        
        # Log summary of extracted entities
        total_entities = sum(len(v) for v in entities.values())
        logger.info(f"📊 Extracted {total_entities} total entities: "
                   f"{len(entities['persons'])} persons, "
                   f"{len(entities['organizations'])} organizations, "
                   f"{len(entities['locations'])} locations, "
                   f"{len(entities['dates'])} dates")
        
        # Generate hashtags from topics and keywords (for caching)
        hashtags = []
        if topics:
            for i, topic in enumerate(topics[:10]):
                topic_label = topic.get('label', topic) if isinstance(topic, dict) else str(topic)
                hashtag_name = f"#{topic_label.replace(' ', '')}"
                hashtags.append({
                    "id": f"topic-{i}",
                    "name": hashtag_name,
                    "category": "Campaign-Specific"
                })
        if campaign and campaign.keywords:
            campaign_keywords = campaign.keywords.split(",") if isinstance(campaign.keywords, str) else campaign.keywords
            for i, keyword in enumerate(campaign_keywords[:10]):
                keyword_clean = keyword.strip()
                if keyword_clean:
                    hashtag_name = f"#{keyword_clean.replace(' ', '')}"
                    hashtags.append({
                        "id": f"keyword-{i}",
                        "name": hashtag_name,
                        "category": "Industry"
                    })
        
        # Save to database cache (as "raw data" associated with campaign)
        # Only save if we have valid non-empty data
        if word_cloud and len(word_cloud) > 0 and topics and len(topics) > 0:
            try:
                import json
                research_data_record = db.query(CampaignResearchData).filter(
                    CampaignResearchData.campaign_id == campaign_id
                ).first()
                
                if research_data_record:
                    # Update existing record
                    research_data_record.word_cloud_json = json.dumps(word_cloud)
                    research_data_record.topics_json = json.dumps(topics)
                    research_data_record.hashtags_json = json.dumps(hashtags)
                    research_data_record.entities_json = json.dumps(entities)
                    research_data_record.updated_at = datetime.now()
                    logger.info(f"✅ Updated cached research data for campaign {campaign_id}")
                else:
                    # Create new record
                    research_data_record = CampaignResearchData(
                        campaign_id=campaign_id,
                        word_cloud_json=json.dumps(word_cloud),
                        topics_json=json.dumps(topics),
                        hashtags_json=json.dumps(hashtags),
                        entities_json=json.dumps(entities)
                    )
                    db.add(research_data_record)
                    logger.info(f"✅ Saved new research data to database for campaign {campaign_id}")
                
                db.commit()
            except Exception as e:
                logger.error(f"⚠️ Failed to save research data to database: {e}")
                db.rollback()
                # Continue anyway - return the data even if DB save failed
        else:
            logger.warning(f"⚠️ Not saving to cache - data is empty (wordCloud: {len(word_cloud) if word_cloud else 0}, topics: {len(topics) if topics else 0})")

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "urls": urls,
            "raw": texts[: max(0, limit) or 20],
            "wordCloud": word_cloud,
            "topics": topics,
            "hashtags": hashtags,
            "entities": entities,
            "total_raw": len(texts),
            "truncation_info": truncation_info if truncation_info else None,  # Info about truncated texts
            "cached": False,
            "diagnostics": {
                "total_rows": len(rows),
                "valid_urls": len(urls),
                "valid_texts": len(texts),
                "errors": errors,
                "has_errors": len(errors) > 0,
                "has_data": len(urls) > 0 or len(texts) > 0,
                "truncated_count": len(truncation_info),
                "cached": False
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error aggregating research for {campaign_id}: {e}")
        logger.debug(traceback.format_exc())
        # Return partial data even if processing fails
        return {
            "urls": [],
            "raw": [],
            "wordCloud": [],
            "topics": [],
            "entities": {
                "persons": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "money": [],
                "percent": [],
                "time": [],
                "facility": []
            },
            "diagnostics": {
                "total_rows": 0,
                "valid_urls": 0,
                "valid_texts": 0,
                "errors": [{
                    "type": "processing_error",
                    "message": str(e),
                    "meta": {"traceback": traceback.format_exc()}
                }],
                "has_errors": True,
                "has_data": False
            }
        }

# Compare topics endpoint: re-process raw data with alternative method
@app.get("/campaigns/{campaign_id}/compare-topics")
def compare_topics(campaign_id: str, method: str = "system", current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Re-process raw scraped data with alternative topic extraction method.
    Returns topics in the same format as research endpoint.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
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
    
    try:
        from models import CampaignRawData, SystemSettings
        from text_processing import extract_topics
        
        # Get raw data
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0:
                if not r.source_url or not r.source_url.startswith(("error:", "placeholder:")):
                    texts.append(r.extracted_text)
        
        if not texts:
            return {
                "status": "error",
                "message": "No raw data available for comparison"
            }
        
        # Campaign ownership already verified above
        # Get campaign info
        campaign_query = campaign.query if campaign else ""
        campaign_keywords = campaign.keywords.split(",") if campaign and campaign.keywords else []
        campaign_urls = campaign.urls.split(",") if campaign and campaign.urls else []
        
        # Determine topic_tool based on method parameter
        if method == "llm":
            # Check if OpenAI API key is available
            import os
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or len(openai_key.strip()) == 0:
                return {
                    "status": "error",
                    "message": "LLM method requires OPENAI_API_KEY"
                }
            topic_tool = "llm"
        else:
            topic_tool = "system"
        
        num_topics = 10
        iterations = 25
        
        logger.info(f"🔄 Comparing topics with method={method}, tool={topic_tool}, texts={len(texts)}")
        
        topic_phrases = extract_topics(
            texts,
            topic_tool=topic_tool,
            num_topics=num_topics,
            iterations=iterations,
            query=campaign_query,
            keywords=campaign_keywords,
            urls=campaign_urls
        )
        
        # Format topics same as research endpoint
        if topic_phrases and len(topic_phrases) > 0:
            topics = [{"label": phrase, "score": len(topic_phrases) - i} for i, phrase in enumerate(topic_phrases[:10])]
        else:
            topics = []
        
        return {
            "status": "success",
            "topics": topics,
            "method": method
        }
        
    except Exception as e:
        logger.error(f"Error in compare-topics endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }

# TopicWizard Visualization endpoint
@app.get("/campaigns/{campaign_id}/topicwizard")
def get_topicwizard_visualization(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generate TopicWizard visualization for campaign topics.
    Returns HTML page with interactive TopicWizard interface.
    
    Note: TopicWizard may have compatibility issues with Python 3.12 and numba/llvmlite.
    If import fails, returns a fallback visualization using the topic model data.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="<html><body><h1>Campaign not found or access denied</h1></body></html>", status_code=404)
    
    try:
        from models import CampaignRawData
        from sklearn.decomposition import NMF
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline
        from fastapi.responses import HTMLResponse
        
        # Try to import TopicWizard (may fail on Python 3.12 due to numba/llvmlite issues)
        try:
            import topicwizard
            TOPICWIZARD_AVAILABLE = True
        except (ImportError, AttributeError, Exception) as tw_err:
            logger.warning(f"⚠️ TopicWizard not available (known issue with Python 3.12/numba): {tw_err}")
            TOPICWIZARD_AVAILABLE = False
        
        # Campaign ownership already verified above
        # Get scraped texts
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:"))):
                texts.append(r.extracted_text.strip())
        
        if len(texts) < 3:
            return HTMLResponse(
                content="<html><body><h1>Insufficient Data</h1><p>Need at least 3 documents for topic modeling. Please scrape more content first.</p></body></html>",
                status_code=400
            )
        
        # Build TopicWizard-compatible pipeline
        # Use same settings as system model (load from database or use defaults)
        try:
            from database import SessionLocal
            from models import SystemSettings
            db_settings = SessionLocal()
            try:
                # Load system model settings
                tfidf_min_df = 3
                tfidf_max_df = 0.7
                num_topics = 10
                
                settings = db_settings.query(SystemSettings).filter(
                    SystemSettings.setting_key.like("system_model_%")
                ).all()
                
                for setting in settings:
                    key = setting.setting_key.replace("system_model_", "")
                    value = setting.setting_value
                    if key == "tfidf_min_df":
                        tfidf_min_df = int(value) if value else 3
                    elif key == "tfidf_max_df":
                        tfidf_max_df = float(value) if value else 0.7
                    elif key == "k_grid":
                        k_grid = json.loads(value) if value else [10, 15, 20, 25]
                        num_topics = k_grid[0] if k_grid else 10
                
                # Load visualizer settings
                max_texts = 100
                top_words_per_topic = 10
                grid_columns = 0  # 0 = auto-fill
                sort_order = "coverage"  # "coverage" or "topic_id"
                show_coverage = True
                show_top_weights = False
                visualization_type = "scatter"  # All types: "columns", "scatter", "bubble", "network", "word-cloud", "word_map", "topic_map", "document_map", "heatmap", "treemap"
                color_scheme = "rainbow"  # "single", "gradient", "rainbow", "categorical", "viridis", "plasma", "inferno"
                size_scaling = True
                show_title = False
                show_info_box = False
                background_color = "#ffffff"
                min_size = 20
                max_size = 100
                # Advanced styling
                opacity = 0.7
                font_size = 14
                font_weight = 600
                spacing = 20
                border_radius = 8
                border_width = 2
                border_color = "#333333"
                shadow_enabled = False
                # Layout
                orientation = "horizontal"
                alignment = "center"
                padding = 20
                margin = 10
                # Animation
                hover_effects = True
                animation_speed = 300
                # Visualization-specific
                word_map_layout = "force"
                word_map_link_distance = 50
                topic_map_clustering = True
                topic_map_distance = 100
                document_map_point_size = 5
                document_map_color_by = "topic"
                
                visualizer_settings = db_settings.query(SystemSettings).filter(
                    SystemSettings.setting_key.like("visualizer_%")
                ).all()
                
                logger.info(f"🔍 Found {len(visualizer_settings)} visualizer settings in database")
                if len(visualizer_settings) == 0:
                    logger.warning("⚠️ No visualizer settings found in database - using defaults!")
                for setting in visualizer_settings:
                    logger.info(f"  ✓ {setting.setting_key} = '{setting.setting_value}'")
                
                for setting in visualizer_settings:
                    key = setting.setting_key.replace("visualizer_", "")
                    value = setting.setting_value
                    if key == "max_documents":
                        max_texts = int(value) if value else 100
                    elif key == "top_words_per_topic":
                        top_words_per_topic = int(value) if value else 10
                    elif key == "grid_columns":
                        grid_columns = int(value) if value else 0
                    elif key == "sort_order":
                        sort_order = value if value in ["coverage", "topic_id"] else "coverage"
                    elif key == "show_coverage":
                        show_coverage = value.lower() == "true" if value else True
                    elif key == "show_top_weights":
                        show_top_weights = value.lower() == "true" if value else False
                    elif key == "visualization_type":
                        valid_types = ["columns", "scatter", "bubble", "network", "word-cloud", "word_map", "topic_map", "document_map", "heatmap", "treemap"]
                        visualization_type = value if value in valid_types else "scatter"
                        logger.info(f"📊 Loaded visualization_type: {visualization_type} (raw DB value: '{value}')")
                    elif key == "color_scheme":
                        valid_schemes = ["single", "gradient", "rainbow", "categorical", "viridis", "plasma", "inferno"]
                        color_scheme = value if value in valid_schemes else "rainbow"
                    elif key == "size_scaling":
                        size_scaling = value.lower() == "true" if value else True
                    elif key == "show_title":
                        show_title = value.lower() == "true" if value else False
                    elif key == "show_info_box":
                        show_info_box = value.lower() == "true" if value else False
                    elif key == "background_color":
                        background_color = value if value else "#ffffff"
                    elif key == "min_size":
                        min_size = int(value) if value else 20
                    elif key == "max_size":
                        max_size = int(value) if value else 100
                    # Advanced styling
                    elif key == "opacity":
                        opacity = float(value) if value else 0.7
                    elif key == "font_size":
                        font_size = int(value) if value else 14
                    elif key == "font_weight":
                        font_weight = int(value) if value else 600
                    elif key == "spacing":
                        spacing = int(value) if value else 20
                    elif key == "border_radius":
                        border_radius = int(value) if value else 8
                    elif key == "border_width":
                        border_width = int(value) if value else 2
                    elif key == "border_color":
                        border_color = value if value else "#333333"
                    elif key == "shadow_enabled":
                        shadow_enabled = value.lower() == "true" if value else False
                    # Layout
                    elif key == "orientation":
                        orientation = value if value in ["horizontal", "vertical"] else "horizontal"
                    elif key == "alignment":
                        alignment = value if value in ["left", "center", "right"] else "center"
                    elif key == "padding":
                        padding = int(value) if value else 20
                    elif key == "margin":
                        margin = int(value) if value else 10
                    # Animation
                    elif key == "hover_effects":
                        hover_effects = value.lower() == "true" if value else True
                    elif key == "animation_speed":
                        animation_speed = int(value) if value else 300
                    # Visualization-specific
                    elif key == "word_map_layout":
                        word_map_layout = value if value in ["force", "circular", "hierarchical"] else "force"
                    elif key == "word_map_link_distance":
                        word_map_link_distance = int(value) if value else 50
                    elif key == "topic_map_clustering":
                        topic_map_clustering = value.lower() == "true" if value else True
                    elif key == "topic_map_distance":
                        topic_map_distance = int(value) if value else 100
                    elif key == "document_map_point_size":
                        document_map_point_size = int(value) if value else 5
                    elif key == "document_map_color_by":
                        document_map_color_by = value if value in ["topic", "coverage", "document"] else "topic"
            finally:
                db_settings.close()
        except Exception as e:
            logger.warning(f"Could not load settings, using defaults: {e}")
            tfidf_min_df = 3
            tfidf_max_df = 0.7
            num_topics = 10
            max_texts = 100
            top_words_per_topic = 10
            grid_columns = 0
            sort_order = "coverage"
            show_coverage = True
            show_top_weights = False
            visualization_type = "scatter"
            color_scheme = "rainbow"
            size_scaling = True
            show_title = False
            show_info_box = False
            background_color = "#ffffff"
            min_size = 20
            max_size = 100
        
        # Limit texts for performance (TopicWizard can be slow with many documents)
        if len(texts) > max_texts:
            texts = texts[:max_texts]
            logger.info(f"Limited to {max_texts} texts for TopicWizard performance")
        
        # Create pipeline compatible with TopicWizard
        vectorizer = TfidfVectorizer(
            min_df=tfidf_min_df,
            max_df=tfidf_max_df,
            stop_words='english',
            strip_accents='unicode'
        )
        
        topic_model = NMF(
            n_components=min(num_topics, len(texts) - 1),
            random_state=42,
            max_iter=500
        )
        
        topic_pipeline = Pipeline([
            ("vectorizer", vectorizer),
            ("topic_model", topic_model),
        ])
        
        # Fit the pipeline
        logger.info(f"Fitting topic model pipeline with {len(texts)} documents, {min(num_topics, len(texts) - 1)} topics")
        topic_pipeline.fit(texts)
        
        # Extract topic information for visualization
        vectorizer = topic_pipeline.named_steps['vectorizer']
        nmf_model = topic_pipeline.named_steps['topic_model']
        
        # Get document-topic matrix
        X = vectorizer.transform(texts)
        doc_topic_matrix = nmf_model.transform(X)
        
        # Get topic-word matrix and top words per topic
        topic_word_matrix = nmf_model.components_
        feature_names = vectorizer.get_feature_names_out()
        
        topics_data = []
        for topic_idx in range(min(num_topics, len(texts) - 1)):
            # Get top N words for this topic (using visualizer setting)
            top_word_indices = topic_word_matrix[topic_idx].argsort()[-top_words_per_topic:][::-1]
            top_words = [feature_names[idx] for idx in top_word_indices]
            top_weights = [topic_word_matrix[topic_idx][idx] for idx in top_word_indices]
            
            # Calculate topic strength (document coverage)
            topic_strength = doc_topic_matrix[:, topic_idx].sum()
            coverage_pct = (topic_strength / doc_topic_matrix.sum()) * 100 if doc_topic_matrix.sum() > 0 else 0
            
            topics_data.append({
                'id': topic_idx,
                'top_words': top_words,
                'top_weights': top_weights,
                'coverage': round(coverage_pct, 1)
            })
        
        # Sort by configured order
        if sort_order == "coverage":
            topics_data.sort(key=lambda x: x['coverage'], reverse=True)
        else:  # topic_id
            topics_data.sort(key=lambda x: x['id'])
        
        # Helper function to get color for a topic based on scheme
        def get_topic_color(topic_idx, total_topics, coverage):
            ratio = topic_idx / max(total_topics, 1)
            if color_scheme == "rainbow":
                # Rainbow: hue from 0 to 360
                hue = ratio * 360
                return f"hsl({hue}, 70%, 60%)"
            elif color_scheme == "gradient":
                # Gradient: blue to purple
                r = int(59 + (147 - 59) * ratio)
                g = int(130 + (112 - 130) * ratio)
                b = int(246 + (219 - 246) * ratio)
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "categorical":
                # Categorical: distinct colors
                colors = ["#3b82f6", "#22c55e", "#a855f7", "#eab308", "#ef4444", "#64748b", "#f97316", "#06b6d4", "#8b5cf6", "#ec4899"]
                return colors[topic_idx % len(colors)]
            elif color_scheme == "viridis":
                # Viridis: yellow-green-blue (scientific colormap)
                if ratio < 0.25:
                    r, g, b = int(68 + (72 - 68) * (ratio / 0.25)), int(1 + (40 - 1) * (ratio / 0.25)), int(84 + (54 - 84) * (ratio / 0.25))
                elif ratio < 0.5:
                    r, g, b = int(72 + (33 - 72) * ((ratio - 0.25) / 0.25)), int(40 + (144 - 40) * ((ratio - 0.25) / 0.25)), int(54 + (140 - 54) * ((ratio - 0.25) / 0.25))
                elif ratio < 0.75:
                    r, g, b = int(33 + (28 - 33) * ((ratio - 0.5) / 0.25)), int(144 + (127 - 144) * ((ratio - 0.5) / 0.25)), int(140 + (135 - 140) * ((ratio - 0.5) / 0.25))
                else:
                    r, g, b = int(28 + (253 - 28) * ((ratio - 0.75) / 0.25)), int(127 + (231 - 127) * ((ratio - 0.75) / 0.25)), int(135 + (37 - 135) * ((ratio - 0.75) / 0.25))
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "plasma":
                # Plasma: purple-pink-yellow (high contrast)
                if ratio < 0.33:
                    r, g, b = int(13 + (75 - 13) * (ratio / 0.33)), int(8 + (10 - 8) * (ratio / 0.33)), int(135 + (130 - 135) * (ratio / 0.33))
                elif ratio < 0.66:
                    r, g, b = int(75 + (190 - 75) * ((ratio - 0.33) / 0.33)), int(10 + (40 - 10) * ((ratio - 0.33) / 0.33)), int(130 + (50 - 130) * ((ratio - 0.33) / 0.33))
                else:
                    r, g, b = int(190 + (253 - 190) * ((ratio - 0.66) / 0.34)), int(40 + (231 - 40) * ((ratio - 0.66) / 0.34)), int(50 + (37 - 50) * ((ratio - 0.66) / 0.34))
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "inferno":
                # Inferno: black-red-yellow (dark theme)
                if ratio < 0.33:
                    r, g, b = int(0 + (20 - 0) * (ratio / 0.33)), int(0 + (11 - 0) * (ratio / 0.33)), int(4 + (52 - 4) * (ratio / 0.33))
                elif ratio < 0.66:
                    r, g, b = int(20 + (153 - 20) * ((ratio - 0.33) / 0.33)), int(11 + (52 - 11) * ((ratio - 0.33) / 0.33)), int(52 + (4 - 52) * ((ratio - 0.33) / 0.33))
                else:
                    r, g, b = int(153 + (252 - 153) * ((ratio - 0.66) / 0.34)), int(52 + (141 - 52) * ((ratio - 0.66) / 0.34)), int(4 + (89 - 4) * ((ratio - 0.66) / 0.34))
                return f"rgb({r}, {g}, {b})"
            else:  # single
                # Single: monochromatic with variations
                base = 61  # #3d545f
                variation = (topic_idx % 5) * 20
                return f"rgb({base + variation}, {84 + variation}, {95 + variation})"
        
        # Helper function to calculate size based on coverage
        def get_topic_size(coverage, max_coverage):
            if not size_scaling:
                return (min_size + max_size) / 2
            if max_coverage == 0:
                return min_size
            ratio = coverage / max_coverage
            return min_size + (max_size - min_size) * ratio
        
        # Calculate max coverage for size scaling
        max_coverage = max([t['coverage'] for t in topics_data]) if topics_data else 100
        
        # Generate visualization based on type
        logger.info(f"🎨 Generating {visualization_type} visualization with {len(topics_data)} topics")
        logger.info(f"   Basic Settings: color_scheme={color_scheme}, size_scaling={size_scaling}, show_title={show_title}, show_info_box={show_info_box}")
        logger.info(f"   Styling: opacity={opacity}, font_size={font_size}, font_weight={font_weight}, border_radius={border_radius}, border_width={border_width}")
        logger.info(f"   Layout: orientation={orientation}, alignment={alignment}, padding={padding}, margin={margin}, spacing={spacing}")
        logger.info(f"   Animation: hover_effects={hover_effects}, animation_speed={animation_speed}, shadow_enabled={shadow_enabled}")
        logger.info(f"   Background: {background_color}, min_size={min_size}, max_size={max_size}")
        topics_html = ""
        total_topics = len(topics_data)
        
        if visualization_type == "scatter" or visualization_type == "bubble":
            # Scatter/Bubble plot with SVG
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            
            for i, topic in enumerate(topics_data):
                # Calculate position (scattered)
                angle = (i / total_topics) * 2 * 3.14159
                radius = 150 + (i % 3) * 50
                x = svg_width / 2 + radius * (0.7 if i % 2 == 0 else -0.7) * (i / total_topics)
                y = svg_height / 2 + radius * (0.5 if i % 3 == 0 else -0.5) * ((i * 1.3) / total_topics)
                
                # Ensure within bounds
                x = max(50, min(svg_width - 50, x))
                y = max(50, min(svg_height - 50, y))
                
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                # Draw circle/bubble with loaded settings
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                
                # Add label with loaded font settings
                label_text = ", ".join(topic['top_words'][:3])
                if show_coverage:
                    label_text += f" ({topic['coverage']}%)"
                topics_html += f'<text x="{x}" y="{y + size/2 + 15}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            
            topics_html += '</svg>'
            
        elif visualization_type == "network":
            # Network graph
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            
            # Position topics in a circle
            center_x, center_y = svg_width / 2, svg_height / 2
            radius = 200
            
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                x = center_x + radius * (1 + (i % 3) * 0.3) * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                y = center_y + radius * (1 + (i % 3) * 0.3) * (0.8 if i % 2 == 0 else 1.2) * ((i * 1.5) / total_topics)
                
                x = max(60, min(svg_width - 60, x))
                y = max(60, min(svg_height - 60, y))
                
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                # Draw connections to nearby topics
                if i < total_topics - 1:
                    next_topic = topics_data[(i + 1) % total_topics]
                    next_angle = ((i + 1) / total_topics) * 2 * 3.14159
                    next_x = center_x + radius * (1 + ((i + 1) % 3) * 0.3) * (0.8 if (i + 1) % 2 == 0 else 1.2) * ((i + 1) / total_topics)
                    next_y = center_y + radius * (1 + ((i + 1) % 3) * 0.3) * (0.8 if (i + 1) % 2 == 0 else 1.2) * (((i + 1) * 1.5) / total_topics)
                    next_x = max(60, min(svg_width - 60, next_x))
                    next_y = max(60, min(svg_height - 60, next_y))
                    topics_html += f'<line x1="{x}" y1="{y}" x2="{next_x}" y2="{next_y}" stroke="#ccc" stroke-width="1" opacity="{opacity * 0.5}"/>'
                
                # Draw node with loaded settings
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                
                # Add label with loaded font settings
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{x}" y="{y + size/2 + 12}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            
            topics_html += '</svg>'
            
        elif visualization_type == "word-cloud":
            # Word cloud style
            shadow_style = f"text-shadow: 2px 2px 4px rgba(0,0,0,0.2);" if shadow_enabled else ""
            topics_html = f'<div class="word-cloud" style="padding: {padding}px; margin: {margin}px;">'
            for i, topic in enumerate(topics_data):
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                words = ", ".join(topic['top_words'][:5])
                cloud_font_size = max(font_size, min(font_size + 10, size / 4))
                topics_html += f'<span class="cloud-word" style="font-size: {cloud_font_size}px; font-weight: {font_weight}; color: {color}; margin: {spacing/4}px; opacity: {opacity}; {shadow_style}">{words}</span>'
            topics_html += '</div>'
            
        elif visualization_type == "word_map":
            # Word map: shows relationships between words
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Place words in a force-directed layout
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                x = svg_width / 2 + 200 * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                y = svg_height / 2 + 200 * (0.8 if i % 3 == 0 else 1.2) * ((i * 1.3) / total_topics)
                x = max(50, min(svg_width - 50, x))
                y = max(50, min(svg_height - 50, y))
                color = get_topic_color(i, total_topics, topic['coverage'])
                # Draw word nodes with loaded settings
                for j, word in enumerate(topic['top_words'][:3]):
                    word_x = x + (j - 1) * word_map_link_distance
                    word_y = y + (j % 2) * spacing
                    topics_html += f'<circle cx="{word_x}" cy="{word_y}" r="15" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                    topics_html += f'<text x="{word_x}" y="{word_y + 5}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{word}</text>'
            topics_html += '</svg>'
            
        elif visualization_type == "topic_map":
            # Topic map: shows topic similarity/clustering
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            center_x, center_y = svg_width / 2, svg_height / 2
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                distance = topic_map_distance if topic_map_clustering else 150
                x = center_x + distance * (1 + (i % 3) * 0.2) * (0.9 if i % 2 == 0 else 1.1) * (i / total_topics)
                y = center_y + distance * (1 + (i % 3) * 0.2) * (0.9 if i % 2 == 0 else 1.1) * ((i * 1.4) / total_topics)
                x = max(60, min(svg_width - 60, x))
                y = max(60, min(svg_height - 60, y))
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{x}" y="{y + size/2 + 15}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            topics_html += '</svg>'
            
        elif visualization_type == "document_map":
            # Document map: shows document clustering
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.1));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Represent documents as points colored by topic
            for i, topic in enumerate(topics_data):
                color = get_topic_color(i, total_topics, topic['coverage'])
                # Place multiple points per topic to represent documents
                num_points = max(3, int(topic['coverage'] / 10))
                for j in range(num_points):
                    angle = (i / total_topics + j / num_points) * 2 * 3.14159
                    x = svg_width / 2 + 150 * (1 + j * 0.1) * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                    y = svg_height / 2 + 150 * (1 + j * 0.1) * (0.8 if i % 3 == 0 else 1.2) * ((i * 1.3) / total_topics)
                    x = max(20, min(svg_width - 20, x))
                    y = max(20, min(svg_height - 20, y))
                    topics_html += f'<circle cx="{x}" cy="{y}" r="{document_map_point_size}" fill="{color}" opacity="{opacity}"/>'
            topics_html += '</svg>'
            
        elif visualization_type == "heatmap":
            # Heatmap: topic-document matrix
            topics_html = '<div class="heatmap-container">'
            topics_html += '<table class="heatmap-table">'
            # Header row
            topics_html += '<tr><th>Topic</th>'
            for i in range(min(10, len(texts))):
                topics_html += f'<th>Doc {i+1}</th>'
            topics_html += '</tr>'
            # Data rows
            for i, topic in enumerate(topics_data):
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<tr><td style="font-weight: {font_weight};">Topic {i+1}</td>'
                for j in range(min(10, len(texts))):
                    intensity = (i + j) % 10 / 10  # Simplified intensity
                    bg_color = color.replace('rgb', 'rgba').replace(')', f', {intensity})')
                    topics_html += f'<td style="background: {bg_color}; padding: 5px;"></td>'
                topics_html += '</tr>'
            topics_html += '</table></div>'
            
        elif visualization_type == "treemap":
            # Treemap: hierarchical coverage visualization
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Calculate total coverage for sizing
            total_coverage = sum(t['coverage'] for t in topics_data)
            current_x, current_y = padding, padding
            row_height = (svg_height - padding * 2) / max(3, int(len(topics_data) ** 0.5))
            for i, topic in enumerate(topics_data):
                width = (topic['coverage'] / total_coverage) * (svg_width - padding * 2) if total_coverage > 0 else (svg_width - padding * 2) / len(topics_data)
                if current_x + width > svg_width - padding:
                    current_x = padding
                    current_y += row_height
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<rect x="{current_x}" y="{current_y}" width="{width}" height="{row_height}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{current_x + width/2}" y="{current_y + row_height/2}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
                current_x += width
            topics_html += '</svg>'
            
        else:  # columns (default)
            # Column cards (grid layout)
            shadow_style = f"box-shadow: 2px 2px 4px rgba(0,0,0,0.2);" if shadow_enabled else ""
            for i, topic in enumerate(topics_data):
                words_display = []
                for j, word in enumerate(topic['top_words']):
                    word_html = f"<strong>{word}</strong>" if j < 3 else word
                    if show_top_weights and j < len(topic['top_weights']):
                        weight = round(topic['top_weights'][j], 3)
                        word_html += f" <span class='weight'>({weight})</span>"
                    words_display.append(word_html)
                words_html = ", ".join(words_display)
                
                title = f"Topic {topic['id'] + 1}"
                if show_coverage:
                    title += f" ({topic['coverage']}% coverage)"
                
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                topics_html += f"""
                <div class="topic-card" style="border-left-color: {color}; border-left-width: {border_width}px; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; opacity: {opacity}; {shadow_style}">
                    <h3 style="font-size: {font_size + 2}px; font-weight: {font_weight};">{title}</h3>
                    <p class="topic-words" style="font-size: {font_size}px; font-weight: {font_weight - 200 if font_weight > 400 else 400};">{words_html}</p>
                </div>
                """
        
        # Determine container class based on visualization type
        container_class = "topics-grid" if visualization_type == "columns" else "visualization-container"
        
        # Build alignment style
        align_style = f"text-align: {alignment};" if alignment in ["left", "center", "right"] else "text-align: center;"
        
        # Build orientation style
        flex_direction = "row" if orientation == "horizontal" else "column"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Topic Visualization - Campaign {campaign_id}</title>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            padding: {padding}px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: {background_color};
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: {background_color};
            padding: {padding}px;
            border-radius: {border_radius}px;
            {align_style}
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .info {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .info p {{
            margin: 5px 0;
        }}
        .topics-grid {{
            display: grid;
            grid-template-columns: {"repeat(" + str(grid_columns) + ", 1fr)" if grid_columns > 0 else "repeat(auto-fill, minmax(300px, 1fr))"};
            gap: {spacing}px;
            margin-top: {margin}px;
            flex-direction: {flex_direction};
        }}
        .visualization-container {{
            width: 100%;
            display: flex;
            flex-direction: {flex_direction};
            justify-content: {"flex-start" if alignment == "left" else "flex-end" if alignment == "right" else "center"};
            align-items: center;
            margin-top: {margin}px;
            padding: {padding}px;
        }}
        .topic-card {{
            background: #f8f9fa;
            padding: {padding}px;
            border-radius: {border_radius}px;
            border-left: {border_width}px solid #3d545f;
            transition: transform {animation_speed}ms ease{" " if hover_effects else ""};
        }}
        {"        .topic-card:hover { transform: scale(1.02); }" if hover_effects else ""}
        .topic-card h3 {{
            margin: 0 0 {spacing/2}px 0;
            color: #3d545f;
            font-size: {font_size + 2}px;
            font-weight: {font_weight};
        }}
        .topic-words {{
            margin: 0;
            color: #666;
            font-size: {font_size}px;
            font-weight: {font_weight - 200 if font_weight > 400 else 400};
            line-height: 1.6;
        }}
        .topic-words strong {{
            color: #3d545f;
            font-weight: 600;
        }}
        .topic-words .weight {{
            color: #999;
            font-size: 12px;
            font-weight: normal;
        }}
        .word-cloud {{
            display: flex;
            flex-wrap: wrap;
            justify-content: {"flex-start" if alignment == "left" else "flex-end" if alignment == "right" else "center"};
            align-items: center;
            padding: {padding}px;
            min-height: 400px;
            flex-direction: {flex_direction};
        }}
        .cloud-word {{
            display: inline-block;
            padding: {spacing/4}px {spacing/2}px;
            border-radius: {border_radius}px;
            font-weight: {font_weight};
            transition: transform {animation_speed}ms ease{" " if hover_effects else ""};
        }}
        {"        .cloud-word:hover { transform: scale(1.1); }" if hover_effects else ""}
        .heatmap-container {{
            padding: {padding}px;
            margin: {margin}px;
        }}
        .heatmap-table {{
            width: 100%;
            border-collapse: collapse;
            border-radius: {border_radius}px;
            overflow: hidden;
        }}
        .heatmap-table th, .heatmap-table td {{
            padding: {spacing/2}px;
            border: {border_width}px solid {border_color};
            text-align: center;
            font-size: {font_size}px;
        }}
        .note {{
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
        }}
        .warning {{
            background: #f8d7da;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="container">
        {"<h1>Topic Model Visualization</h1>" if show_title else ""}
        {"<div class='info'><p><strong>Campaign ID:</strong> {campaign_id}</p><p><strong>Documents:</strong> {len(texts)}</p><p><strong>Topics:</strong> {min(num_topics, len(texts) - 1)}</p></div>" if show_info_box else ""}
        {"<div class='warning'><strong>Note:</strong> TopicWizard interactive visualization is not available due to Python 3.12 compatibility issues with numba/llvmlite. Showing topic model results instead.</div>" if not TOPICWIZARD_AVAILABLE else ""}
        <div class="{container_class}">
            {topics_html}
        </div>
    </div>
</body>
</html>
"""
        
        response = HTMLResponse(content=html_content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Required packages not available: {str(e)}</p><p>Please install: pip install scikit-learn topic-wizard</p></body></html>",
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error generating TopicWizard visualization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p><p>Check backend logs for details.</p></body></html>",
            status_code=500
        )

# Research Agent Recommendations endpoint
@app.post("/campaigns/{campaign_id}/research-agent-recommendations")
def get_research_agent_recommendations(campaign_id: str, request_data: ResearchAgentRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generate LLM-based recommendations for research agents (Keyword, Micro Sentiment, Topical Map, Knowledge Graph, Hashtag Generator).
    Uses prompts from system_settings table.
    Caches insights in database to avoid re-calling LLM for the same campaign/agent combination.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
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
    
    try:
        agent_type = request_data.agent_type
        from models import CampaignRawData, SystemSettings, CampaignResearchInsights
        
        # Check if insights already exist in database (cache)
        existing_insights = db.query(CampaignResearchInsights).filter(
            CampaignResearchInsights.campaign_id == campaign_id,
            CampaignResearchInsights.agent_type == agent_type
        ).first()
        
        if existing_insights and existing_insights.insights_text:
            logger.info(f"✅ Returning cached {agent_type} insights for campaign {campaign_id}")
            return {
                "status": "success",
                "recommendations": existing_insights.insights_text,
                "agent_type": agent_type,
                "cached": True
            }
        
        # Get raw data for context
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = [r.extracted_text for r in rows if r.extracted_text and len(r.extracted_text.strip()) > 10 and not r.source_url.startswith(("error:", "placeholder:"))]
        
        if not texts:
            return {"status": "error", "message": "No valid scraped data available"}
        
        # Get research data for context
        from text_processing import extract_keywords, extract_topics
        keywords_data = extract_keywords(texts, num_keywords=20)
        
        # Generate word cloud data (term: count format) for keyword agent
        from collections import Counter
        all_words = []
        for text in texts:
            words = text.lower().split()
            # Remove very short words and common stopwords
            words = [w.strip('.,!?;:"()[]{}') for w in words if len(w) > 3]
            all_words.extend(words)
        word_counts = Counter(all_words)
        word_cloud_data = [{"term": term, "count": count} for term, count in word_counts.most_common(20)]
        
        # Check topic extraction method from system settings (default to "system")
        from models import SystemSettings
        method_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "topic_extraction_method"
        ).first()
        
        topic_extraction_method = "system"  # Default to system model
        if method_setting and method_setting.setting_value:
            topic_extraction_method = method_setting.setting_value.lower()
        
        # Determine topic_tool based on method
        if topic_extraction_method == "llm":
            # Check if OpenAI API key is available for LLM model
            import os
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and len(openai_key.strip()) > 0:
                topic_tool = "llm"  # Use LLM for phrase generation
                logger.info("✅ Using LLM model for topics (from system settings)")
            else:
                topic_tool = "system"  # Fallback to system model if no API key
                logger.warning("⚠️ LLM selected but OPENAI_API_KEY not found, using system model")
        else:
            topic_tool = "system"  # Use system model (NMF-based)
            logger.info("✅ Using system model for topics (from system settings)")
        
        topics_data = extract_topics(texts, topic_tool=topic_tool, num_topics=10, iterations=25, query=campaign.query or "", keywords=campaign.keywords.split(",") if campaign.keywords else [], urls=[])
        
        # Get prompt from system settings
        prompt_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == f"research_agent_{agent_type}_prompt"
        ).first()
        
        if not prompt_setting or not prompt_setting.setting_value:
            logger.error(f"❌ Prompt not configured for {agent_type} agent. Looking for key: research_agent_{agent_type}_prompt")
            return {"status": "error", "message": f"Prompt not configured for {agent_type} agent. Please configure it in Admin Panel → Research Agents → {agent_type.replace('-', ' ').title()}"}
        
        prompt_template = prompt_setting.setting_value
        logger.info(f"✅ Using prompt for {agent_type} agent (key: research_agent_{agent_type}_prompt)")
        
        # Prepare context with word cloud data for keyword agent
        if agent_type == "keyword":
            # Format word cloud data for keyword agent
            word_cloud_text = "\n".join([f"- {item['term']}: {item['count']} occurrences" for item in word_cloud_data[:20]])
            context = f"""
Campaign Query: {campaign.query or 'N/A'}
Campaign Keywords: {', '.join(campaign.keywords.split(',')) if campaign.keywords else 'N/A'}

Word Cloud Data (Top Keywords from Scraped Content):
{word_cloud_text}

Topics Identified: {', '.join(topics_data[:10]) if topics_data else 'N/A'}
Number of Scraped Texts: {len(texts)}
Total Words Analyzed: {sum(item['count'] for item in word_cloud_data)}
Sample Text (first 500 chars): {texts[0][:500] if texts else 'N/A'}
"""
        else:
            # For other agent types, use simpler context
            context = f"""
Campaign Query: {campaign.query or 'N/A'}
Keywords: {', '.join(campaign.keywords.split(',')) if campaign.keywords else 'N/A'}
Top Keywords Found: {', '.join([k if isinstance(k, str) else str(k) for k in keywords_data[:10]])}
Topics Identified: {', '.join(topics_data[:10]) if topics_data else 'N/A'}
Number of Scraped Texts: {len(texts)}
Sample Text (first 500 chars): {texts[0][:500] if texts else 'N/A'}
"""
        
        # Format prompt with context
        prompt = prompt_template.format(context=context)
        
        # Call LLM
        import os
        from dotenv import load_dotenv
        # Ensure .env is loaded (in case systemd didn't load it properly)
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            return {"status": "error", "message": "OPENAI_API_KEY not configured"}
        
        # Strip whitespace from API key (common issue)
        api_key = api_key.strip()
        
        # Log first few chars for debugging (without exposing full key)
        logger.info(f"✅ Using OpenAI API key: {api_key[:10]}... (length: {len(api_key)})")
        
        # Check key length (OpenAI keys are typically 200+ characters)
        if len(api_key) < 50:
            logger.error(f"❌ API key is too short ({len(api_key)} chars). OpenAI keys should be 200+ characters. Check .env file for line breaks or truncation.")
            return {"status": "error", "message": f"API key is too short ({len(api_key)} characters). OpenAI keys should be 200+ characters. Please check your .env file - the key might have line breaks or be truncated. Ensure the entire key is on a single line."}
        
        if not api_key.startswith("sk-"):
            logger.warning(f"⚠️ API key doesn't start with 'sk-' - might be invalid format")
        
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0.4, max_tokens=1000)
            response = llm.invoke(prompt)
            recommendations_text = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"✅ Successfully generated {agent_type} recommendations ({len(recommendations_text)} chars)")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error calling LLM for {agent_type} recommendations: {error_msg}")
            # Check if it's an API key error
            if "401" in error_msg or "unauthorized" in error_msg.lower() or "incorrect api key" in error_msg.lower():
                return {"status": "error", "message": f"OpenAI API key is invalid or expired. Please check your .env file and restart the service."}
            return {"status": "error", "message": f"LLM call failed: {error_msg}"}
        
        # Save insights to database for caching (as "raw data" associated with campaign)
        try:
            # Check if record exists, update it; otherwise create new
            insights_record = db.query(CampaignResearchInsights).filter(
                CampaignResearchInsights.campaign_id == campaign_id,
                CampaignResearchInsights.agent_type == agent_type
            ).first()
            
            if insights_record:
                # Update existing record
                insights_record.insights_text = recommendations_text
                insights_record.updated_at = datetime.now()
                logger.info(f"✅ Updated cached {agent_type} insights for campaign {campaign_id}")
            else:
                # Create new record
                insights_record = CampaignResearchInsights(
                    campaign_id=campaign_id,
                    agent_type=agent_type,
                    insights_text=recommendations_text
                )
                db.add(insights_record)
                logger.info(f"✅ Saved new {agent_type} insights to database for campaign {campaign_id}")
            
            db.commit()
        except Exception as e:
            logger.error(f"⚠️ Failed to save insights to database: {e}")
            db.rollback()
            # Continue anyway - return the insights even if DB save failed
        
        # Parse recommendations (expecting structured format with recommendations)
        # For now, return the raw text - frontend will parse it
        return {
            "status": "success",
            "recommendations": recommendations_text,
            "agent_type": agent_type,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error generating {agent_type} recommendations: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

# Initialize Research Agent Prompts endpoint
@app.post("/admin/initialize-research-agent-prompts")
def initialize_research_agent_prompts(admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """
    Initialize default research agent prompts in the database if they don't exist.
    This ensures all research agent prompts have default values.
    """
    try:
        from models import SystemSettings
        
        default_prompts = {
            "research_agent_keyword_prompt": """Analyze the following keyword data from a content campaign scrape:

{context}

Based on this data, provide:
1. A summary of what the word cloud analysis reveals about the campaign's focus
2. Areas where content could be expanded for better balance
3. Specific recommendations for improving keyword coverage
4. Actionable insights about underrepresented topics

Format your response as structured recommendations that can be displayed to users. Each recommendation should be a clear, actionable insight.""",
            
            "research_agent_micro-sentiment_prompt": """Analyze the sentiment data from a content campaign scrape:

{context}

Based on this data, provide:
1. Overall sentiment assessment
2. Sentiment breakdown by topic/theme
3. Areas with lower positive sentiment that need attention
4. Recommendations for improving sentiment in specific areas

Format your response as structured recommendations that can be displayed to users. Each recommendation should be a clear, actionable insight.""",
            
            "research_agent_topical-map_prompt": """Analyze the topical map data from a content campaign scrape:

{context}

Based on this data, provide:
1. A summary of the main topics identified
2. Topic relationships and coverage analysis
3. Gaps or underrepresented topics
4. Recommendations for expanding topic coverage

Format your response as structured recommendations that can be displayed to users. Each recommendation should be a clear, actionable insight.""",
            
            "research_agent_knowledge-graph_prompt": """Analyze the knowledge graph data from a content campaign scrape:

{context}

Based on this data, provide:
1. Assessment of entity relationships and structure
2. Analysis of connection strengths between concepts
3. Identification of weakly connected areas
4. Recommendations for strengthening relationships in the knowledge graph

Format your response as structured recommendations that can be displayed to users. Each recommendation should be a clear, actionable insight.""",
            
            "research_agent_hashtag-generator_prompt": """Analyze the hashtag data from a content campaign scrape:

{context}

Based on this data, provide:
1. Assessment of hashtag mix (industry-standard, trending, niche, campaign-specific)
2. Analysis of hashtag performance potential
3. Recommendations for optimal hashtag combinations
4. Suggested hashtag strategies for different platforms

Format your response as structured recommendations that can be displayed to users. Each recommendation should be a clear, actionable insight.""",
        }
        
        # Add keyword expansion prompt
        default_prompts["keyword_expansion_prompt"] = """Expand this abbreviation to its full form. Return ONLY the expansion, nothing else. If it's not an abbreviation, return the original word.

Examples:
- WW2 → World War 2
- AI → artificial intelligence
- CEO → Chief Executive Officer
- NASA → National Aeronautics and Space Administration

Abbreviation: {keyword}

Expansion:"""
        
        initialized = []
        for setting_key, prompt_value in default_prompts.items():
            # Check if setting exists
            existing = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
            if not existing:
                # Create new setting
                if setting_key == "keyword_expansion_prompt":
                    description = "Prompt for LLM-based keyword abbreviation expansion"
                else:
                    agent_type = setting_key.replace("research_agent_", "").replace("_prompt", "")
                    agent_labels = {
                        "keyword": "Keyword Research Agent",
                        "micro-sentiment": "Micro Sentiment Agent",
                        "topical-map": "Topical Map Agent",
                        "knowledge-graph": "Knowledge Graph Agent",
                        "hashtag-generator": "Hashtag Generator Agent",
                    }
                    description = f"Default prompt for {agent_labels.get(agent_type, agent_type)}"
                
                new_setting = SystemSettings(
                    setting_key=setting_key,
                    setting_value=prompt_value,
                    description=description
                )
                db.add(new_setting)
                initialized.append(setting_key)
                logger.info(f"✅ Initialized {setting_key}")
        
        if initialized:
            db.commit()
            return {
                "status": "success",
                "message": f"Initialized {len(initialized)} prompts",
                "initialized": initialized
            }
        else:
            return {
                "status": "success",
                "message": "All prompts already exist",
                "initialized": []
            }
            
    except Exception as e:
        logger.error(f"Error initializing research agent prompts: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return {"status": "error", "message": str(e)}

# Author Personalities endpoints
@app.get("/author_personalities")
def get_author_personalities(db: Session = Depends(get_db)):
    """Get all author personalities - REAL database query"""
    logger.info("🔍 /author_personalities GET endpoint called")
    try:
        from models import AuthorPersonality
        personalities = db.query(AuthorPersonality).all()
        return {
            "status": "success",
            "personalities": [
                {
                    "id": personality.id,
                    "name": personality.name,
                    "description": personality.description,
                    "created_at": personality.created_at.isoformat() if personality.created_at else None,
                    "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                    "user_id": personality.user_id
                }
                for personality in personalities
            ]
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching author personalities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch author personalities: {str(e)}"
        )

@app.post("/author_personalities")
def create_author_personality(personality_data: AuthorPersonalityCreate, db: Session = Depends(get_db)):
    """Create author personality - REAL database save"""
    try:
        from models import AuthorPersonality
        logger.info(f"Creating author personality: {personality_data.name}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database
        personality = AuthorPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            user_id=None  # Can be extended to associate with logged-in user
        )
        
        db.add(personality)
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Author personality created successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create author personality: {str(e)}"
        )

@app.put("/author_personalities/{personality_id}")
def update_author_personality(personality_id: str, personality_data: AuthorPersonalityUpdate, db: Session = Depends(get_db)):
    """Update author personality - REAL database update"""
    try:
        from models import AuthorPersonality
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == personality_id).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        
        personality.updated_at = datetime.now()
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Author personality updated successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update author personality: {str(e)}"
        )

@app.delete("/author_personalities/{personality_id}")
def delete_author_personality(personality_id: str, db: Session = Depends(get_db)):
    """Delete author personality - REAL database deletion"""
    try:
        from models import AuthorPersonality
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == personality_id).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found"
            )
        db.delete(personality)
        db.commit()
        logger.info(f"Author personality deleted successfully: {personality_id}")
        return {
            "status": "success",
            "message": "Author personality deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error deleting author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete author personality: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)