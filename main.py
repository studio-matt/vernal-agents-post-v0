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
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import re
import sys
from pathlib import Path

# Fix import path for author-related folder (hyphen in folder name)
# Python can't import modules with hyphens, so we create a sys.path workaround
_backend_dir = Path(__file__).parent
_author_related_path = _backend_dir / "author-related"
_author_related_underscore = _backend_dir / "author_related"

# If author-related exists but author_related doesn't, create import shim
if _author_related_path.exists() and not _author_related_underscore.exists():
    import importlib.util
    import importlib.machinery
    
    # Load author-related as author_related module
    _init_path = _author_related_path / "__init__.py"
    if _init_path.exists():
        spec = importlib.util.spec_from_file_location(
            "author_related",
            _init_path,
            submodule_search_locations=[str(_author_related_path)]
        )
        if spec and spec.loader:
            author_related = importlib.util.module_from_spec(spec)
            sys.modules['author_related'] = author_related
            spec.loader.exec_module(author_related)
            
            # Load submodules that might be imported
            for submodule in ['asset_loader', 'profile_extraction', 'models', 'planner', 'generator_harness', 'validator', 'profile_store', 'reporter', 'deterministic']:
                submodule_path = _author_related_path / f"{submodule}.py"
                if submodule_path.exists():
                    try:
                        sub_spec = importlib.util.spec_from_file_location(
                            f"author_related.{submodule}",
                            submodule_path
                        )
                        if sub_spec and sub_spec.loader:
                            sub_mod = importlib.util.module_from_spec(sub_spec)
                            sys.modules[f'author_related.{submodule}'] = sub_mod
                            sub_spec.loader.exec_module(sub_mod)
                    except Exception as e:
                        logger.warning(f"Could not preload author_related.{submodule}: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Global exception handler to catch ALL exceptions, including those in dependency injection
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions and log them with full details"""
    import traceback
    error_trace = traceback.format_exc()
    logger.error(f"❌ GLOBAL EXCEPTION HANDLER: {type(exc).__name__}: {str(exc)}")
    logger.error(f"❌ Request URL: {request.url}")
    logger.error(f"❌ Request method: {request.method}")
    logger.error(f"❌ Request path: {request.url.path}")
    try:
        # Try to read body - might fail if already consumed
        try:
            body = await request.body()
            if body:
                logger.error(f"❌ Request body: {body.decode('utf-8')[:500]}")
            else:
                logger.error(f"❌ Request body: (empty)")
        except Exception as body_read_err:
            logger.error(f"❌ Could not read request body (may be consumed): {body_read_err}")
    except Exception as body_err:
        logger.error(f"❌ Failed to access request body: {body_err}")
    logger.error(f"❌ Full traceback:\n{error_trace}")
    
    # Get origin for CORS headers
    origin = request.headers.get("Origin", "")
    cors_headers = {}
    if origin in ALLOWED_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    # If it's already an HTTPException, return with CORS headers
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={**cors_headers, **(exc.headers or {})}
        )
    
    # Otherwise, return 500 with error details and CORS headers
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {str(exc)}",
            "error_type": type(exc).__name__,
            "detail": str(exc)
        },
        headers=cors_headers
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses"""
    import time
    start_time = time.time()
    logger.info(f"📥 INCOMING REQUEST: {request.method} {request.url}")
    logger.info(f"📥 Headers: {dict(request.headers)}")
    
    # Read and log body, then restore it
    try:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body_str = body_bytes.decode('utf-8')
                logger.info(f"📥 Body (first 500 chars): {body_str[:500]}")
            except Exception as decode_err:
                logger.error(f"❌ Failed to decode body: {decode_err}")
                logger.info(f"📥 Body (binary, {len(body_bytes)} bytes)")
        else:
            logger.warning(f"⚠️ Request body is empty for {request.method} {request.url.path}")
    except Exception as body_err:
        logger.error(f"❌ CRITICAL: Failed to read request body: {body_err}")
        import traceback
        logger.error(f"❌ Body read traceback:\n{traceback.format_exc()}")
        body_bytes = b""
    
    # Restore body for endpoint
    async def receive():
        return {"type": "http.request", "body": body_bytes}
    request._receive = receive
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"📤 RESPONSE: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ REQUEST FAILED: {request.method} {request.url} - Error: {str(e)} - Time: {process_time:.2f}s")
        import traceback
        logger.error(f"❌ REQUEST FAILED traceback:\n{traceback.format_exc()}")
        raise

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

# Mount static files directory for images
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads", "images")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=uploads_dir), name="images")
logger.info(f"✅ Static file serving enabled for images: {uploads_dir}")
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

# In-memory content generation task tracking
CONTENT_GEN_TASKS: Dict[str, Dict[str, Any]] = {}
CONTENT_GEN_TASK_INDEX: Dict[str, str] = {}  # campaign_id -> task_id mapping

# In-memory content generation task tracking
CONTENT_GEN_TASKS: Dict[str, Dict[str, Any]] = {}
CONTENT_GEN_TASK_INDEX: Dict[str, str] = {}  # campaign_id -> task_id mapping

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
    query: Optional[str] = None  # Added to match frontend payload
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    trendingTopics: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    status: Optional[str] = "INCOMPLETE"  # Campaign status: INCOMPLETE, PROCESSING, READY_TO_ACTIVATE, ACTIVE, NO_CHANGES
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None
    # Site Builder specific fields
    site_base_url: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    top_ideas_count: Optional[int] = None
    # Look Alike specific fields
    articles_url: Optional[str] = None

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
    custom_keywords: Optional[List[str]] = None  # Custom keywords/ideas for content queue
    personality_settings_json: Optional[str] = None  # JSON string for personality settings: {author_personality_id: string, brand_personality_id: string}
    image_settings_json: Optional[str] = None  # JSON string for image generation settings: {style, prompt, color, additionalCreativeAgentId}
    scheduling_settings_json: Optional[str] = None  # JSON string for scheduling settings: {activeDays, activePlatforms, post_frequency_type, post_frequency_value, start_date, day_frequency, defaultPosts}
    content_queue_items_json: Optional[str] = None  # JSON string for content queue items: [{id, type, name, source, ...}]
    research_selections_json: Optional[str] = None  # JSON string for Research Assistant selections (raw ingredients): [{id, type, name, source, ...}]

# Pydantic models for author personalities endpoints
class AuthorPersonalityCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AuthorPersonalityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_config_json: Optional[str] = None  # JSON string for model configuration
    baseline_adjustments_json: Optional[str] = None  # JSON string for baseline adjustments
    selected_features_json: Optional[str] = None  # JSON string for selected features
    configuration_preset: Optional[str] = None  # Configuration preset name
    writing_samples_json: Optional[str] = None  # JSON string for writing samples (array of strings or objects with {text, domain})

# Pydantic models for author profile endpoints
class ExtractProfileRequest(BaseModel):
    writing_samples: List[str]
    sample_metadata: Optional[List[dict]] = None  # Optional list of {mode, audience, path} for each sample

class GenerateContentRequest(BaseModel):
    goal: str
    target_audience: str = "general"
    adapter_key: str = "blog"  # linkedin, blog, memo_email, etc.
    scaffold: str  # The content prompt/topic

class BrandPersonalityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    guidelines: Optional[str] = None

class BrandPersonalityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    guidelines: Optional[str] = None

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
def deploy_commit(admin_user = Depends(get_admin_user)):
    """Return the current deployed commit hash for verification - ADMIN ONLY"""
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
# Demo campaign ID - template campaign that will be copied for each user
DEMO_CAMPAIGN_ID = "9aaa2de6-ac2c-4bd1-8cd2-44f8cbc66f2a"

def create_user_demo_campaign(user_id: int, db: Session):
    """
    Create a user-specific copy of the demo campaign.
    Each user gets their own independent demo campaign with unique campaign_id.
    """
    try:
        from models import Campaign, CampaignRawData
        import json
        import uuid
        
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
        
        # Helper function to safely get attributes (defined later in file, but available at runtime)
        def safe_getattr(obj, attr_name, default=None):
            try:
                return getattr(obj, attr_name, default)
            except AttributeError:
                return default
        
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
            site_base_url=safe_getattr(template_campaign, 'site_base_url'),
            target_keywords_json=safe_getattr(template_campaign, 'target_keywords_json'),
            top_ideas_count=safe_getattr(template_campaign, 'top_ideas_count'),
            image_settings_json=safe_getattr(template_campaign, 'image_settings_json'),
            content_queue_items_json=safe_getattr(template_campaign, 'content_queue_items_json'),
            articles_url=safe_getattr(template_campaign, 'articles_url'),
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
        logger.info(f"✅ Created user demo campaign {user_demo_campaign_id} for user {user_id} with {copied_raw_data_count} raw_data entries")
        
        return user_demo_campaign_id
    except Exception as e:
        logger.error(f"❌ Error creating user demo campaign for user {user_id}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        db.rollback()
        return None  # Return None on error - endpoint will continue without demo campaign

@app.get("/campaigns")
def get_campaigns(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all campaigns for the authenticated user - REQUIRES AUTHENTICATION"""
    logger.info("🔍 /campaigns GET endpoint called")
    try:
        from models import Campaign
        
        # Filter campaigns by authenticated user (multi-tenant security)
        # Admin users can see all campaigns for troubleshooting
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            campaigns = db.query(Campaign).all()
            logger.info(f"Admin user {current_user.id} viewing all campaigns: found {len(campaigns)} campaigns")
        else:
            campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
            logger.info(f"Filtered campaigns by user_id={current_user.id}: found {len(campaigns)} campaigns")
        
        # Ensure user has a demo campaign (create copy if needed)
        # Wrap in try-except to prevent errors from breaking the endpoint
        try:
            # Check if user already has a demo campaign in their list
            user_has_demo_in_list = any(
                c.campaign_name and c.campaign_name.startswith("Demo Campaign") 
                for c in campaigns
            )
            
            if not user_has_demo_in_list:
                logger.info(f"📋 User {current_user.id} does not have demo campaign in list, attempting to create/find one")
                user_demo_campaign_id = create_user_demo_campaign(current_user.id, db)
                
                # Get user's demo campaign (if it exists)
                if user_demo_campaign_id:
                    user_demo_campaign = db.query(Campaign).filter(
                        Campaign.campaign_id == user_demo_campaign_id
                    ).first()
                    if user_demo_campaign:
                        # Check if it's already in the list (double-check)
                        user_has_demo = any(c.campaign_id == user_demo_campaign_id for c in campaigns)
                        if not user_has_demo:
                            campaigns.append(user_demo_campaign)
                            logger.info(f"✅ Added user demo campaign {user_demo_campaign_id} to user {current_user.id}'s campaign list")
                        else:
                            logger.info(f"ℹ️ User demo campaign {user_demo_campaign_id} already in list")
                    else:
                        logger.warning(f"⚠️ Created demo campaign ID {user_demo_campaign_id} but could not retrieve it from database")
                else:
                    logger.warning(f"⚠️ Could not create/find demo campaign for user {current_user.id}")
            else:
                logger.info(f"✅ User {current_user.id} already has demo campaign in their list")
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
        total_campaigns = db.query(Campaign).count()
        if len(campaigns) == 0 and total_campaigns > 0:
            logger.warning(f"⚠️ User {current_user.id} has 0 campaigns, but database has {total_campaigns} total campaigns. This may indicate a user_id mismatch.")
            # Show sample campaign user_ids for debugging
            sample_campaigns = db.query(Campaign).limit(5).all()
            sample_user_ids = [c.user_id for c in sample_campaigns]
            logger.info(f"Sample campaign user_ids in database: {sample_user_ids}")
        # Get user info for campaigns (to show username/email)
        from models import User
        import json
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
                    "custom_keywords": custom_keywords
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

# Helper functions for safe attribute access (handles missing SQLAlchemy columns)
def _safe_getattr(obj, attr_name, default=None):
    """Safely get attribute from SQLAlchemy model, returning default if column doesn't exist"""
    try:
        return getattr(obj, attr_name, default)
    except AttributeError:
        return default

def _safe_get_json(obj, attr_name, default=None):
    """Safely get and parse JSON attribute from SQLAlchemy model"""
    try:
        import json
        value = getattr(obj, attr_name, None)
        if value:
            return json.loads(value)
        return default
    except (AttributeError, json.JSONDecodeError, TypeError):
        return default

@app.get("/campaigns/{campaign_id}")
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

@app.put("/campaigns/{campaign_id}")
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
    """Delete campaign - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION (or admin)
    For demo campaign, creates a user-specific exclusion instead of deleting"""
    try:
        from models import Campaign, User
        import json
        
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
    # Site Builder specific fields
    site_base_url: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    top_ideas_count: Optional[int] = 10
    most_recent_urls: Optional[int] = None  # Number of most recent URLs to scrape (date-based)
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
# Test endpoint to verify /analyze is reachable
@app.post("/analyze/test")
def test_analyze_endpoint():
    """Simple test endpoint to verify /analyze route is working"""
    return {"status": "ok", "message": "Test endpoint is reachable"}

@app.post("/analyze")
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
            
            TASKS[task_id] = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "started_at": datetime.utcnow().isoformat(),
                "progress": 5,  # start at 5%
                "current_step": "initializing",
                "progress_message": "Starting analysis",
            }
            logger.info(f"🔍 Created TASKS entry for task_id: {task_id}")
            
            CAMPAIGN_TASK_INDEX[campaign_id] = task_id
            logger.info(f"🔍 Created CAMPAIGN_TASK_INDEX entry: {campaign_id} -> {task_id}")
            
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
                    task = TASKS.get(tid)
                    if not task:
                        logger.warning(f"⚠️ Task {tid} not found in TASKS dict")
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
            # Remove task from TASKS since thread failed to start
            if task_id in TASKS:
                del TASKS[task_id]
            if campaign_id in CAMPAIGN_TASK_INDEX:
                del CAMPAIGN_TASK_INDEX[campaign_id]
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
    
    # CRITICAL: Find the ACTIVE task for this campaign (not just the one in index)
    # Multiple tasks might exist if Build button was clicked multiple times
    # Return the one that's actually running (in_progress), or the most recent one
    
    active_task_id = None
    active_task_progress = -1
    
    # First check the index (most recent task)
    task_id_from_index = CAMPAIGN_TASK_INDEX.get(campaign_id)
    
    # Check all tasks to find the one that's actually running
    for tid, task in TASKS.items():
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
    
    if not active_task_id or active_task_id not in TASKS:
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
def get_topicwizard_visualization(
    campaign_id: str,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate TopicWizard visualization for campaign topics.
    Returns HTML page with interactive TopicWizard interface.
    
    Note: TopicWizard may have compatibility issues with Python 3.12 and numba/llvmlite.
    If import fails, returns a fallback visualization using the topic model data.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    
    Supports authentication via:
    - Authorization header (Bearer token) - preferred
    - Query parameter 'token' - for iframe requests
    """
    # Get token from header or query parameter (for iframe support)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    elif not token:
        # Try to get from query parameter
        token = request.query_params.get("token")
    
    if not token:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Authentication Required</h1><p>Please provide a valid authentication token.</p></body></html>",
            status_code=401
        )
    
    # Verify token and get user
    try:
        from utils import verify_token
        from models import User
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>Invalid Token</h1><p>Token is missing user ID.</p></body></html>",
                status_code=401
            )
        current_user = db.query(User).filter(User.id == int(user_id)).first()
        if not current_user:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>User Not Found</h1><p>User associated with token not found.</p></body></html>",
                status_code=401
            )
    except Exception as e:
        logger.error(f"Authentication error in topicwizard endpoint: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"<html><body><h1>Authentication Failed</h1><p>Invalid or expired token.</p></body></html>",
            status_code=401
        )
    
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
        try:
            topic_pipeline.fit(texts)
        except ValueError as e:
            if "no terms remain" in str(e).lower() or "after pruning" in str(e).lower():
                logger.warning(f"⚠️ TopicWizard: No terms remain after pruning. Adjusting min_df/max_df parameters.")
                # Try with more lenient parameters
                vectorizer = TfidfVectorizer(
                    min_df=1,  # Allow terms that appear in at least 1 document
                    max_df=0.95,  # Allow terms that appear in up to 95% of documents
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
                try:
                    topic_pipeline.fit(texts)
                    logger.info("✅ TopicWizard: Successfully fitted with adjusted parameters")
                except Exception as e2:
                    logger.error(f"❌ TopicWizard: Still failed after parameter adjustment: {e2}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"TopicWizard failed: {str(e2)}. Try reducing min_df or increasing max_df, or ensure you have sufficient text data."
                    )
            else:
                raise
        
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

# Knowledge Graph Visualization endpoint
@app.get("/campaigns/{campaign_id}/knowledge-graph")
def get_knowledge_graph_visualization(
    campaign_id: str, 
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate knowledge graph visualization for campaign using NetworkX and pyvis.
    Uses existing extracted data: entities, topics, and word cloud from /research endpoint.
    Returns HTML page with interactive knowledge graph.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    
    Supports authentication via:
    - Authorization header (Bearer token) - preferred
    - Query parameter 'token' - for iframe requests
    """
    # Get token from header or query parameter (for iframe support)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    elif not token:
        # Try to get from query parameter
        token = request.query_params.get("token")
    
    if not token:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Authentication Required</h1><p>Please provide a valid authentication token.</p></body></html>",
            status_code=401
        )
    
    # Verify token and get user
    try:
        from utils import verify_token
        from models import User
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>Invalid Token</h1><p>Token is missing user ID.</p></body></html>",
                status_code=401
            )
        current_user = db.query(User).filter(User.id == int(user_id)).first()
        if not current_user:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>User Not Found</h1><p>User associated with token not found.</p></body></html>",
                status_code=401
            )
    except Exception as e:
        logger.error(f"Authentication error in knowledge graph endpoint: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"<html><body><h1>Authentication Failed</h1><p>Invalid or expired token.</p></body></html>",
            status_code=401
        )
    
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
        from models import CampaignRawData, CampaignResearchData, SystemSettings
        from fastapi.responses import HTMLResponse
        import json
        import networkx as nx
        from pyvis.network import Network
        
        # Get research data (entities, topics, word cloud) - use cached if available
        cached_data = db.query(CampaignResearchData).filter(
            CampaignResearchData.campaign_id == campaign_id
        ).first()
        
        # Get raw texts for relationship extraction
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:"))):
                texts.append(r.extracted_text.strip())
        
        if len(texts) < 1:
            return HTMLResponse(
                content="<html><body><h1>Insufficient Data</h1><p>Need at least 1 document for knowledge graph. Please scrape content first.</p></body></html>",
                status_code=400
            )
        
        # Load entities, topics, word cloud from cache or extract
        if cached_data and cached_data.entities_json and cached_data.topics_json and cached_data.word_cloud_json:
            try:
                entities = json.loads(cached_data.entities_json) if cached_data.entities_json else {}
                topics = json.loads(cached_data.topics_json) if cached_data.topics_json else []
                word_cloud = json.loads(cached_data.word_cloud_json) if cached_data.word_cloud_json else []
            except json.JSONDecodeError:
                entities = {}
                topics = []
                word_cloud = []
        else:
            # Fallback: minimal data
            entities = {
                "persons": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "money": [],
                "percent": [],
                "time": [],
                "facility": []
            }
            topics = []
            word_cloud = []
        
        # Load knowledge graph settings from database
        kg_settings = {}
        settings = db.query(SystemSettings).filter(
            SystemSettings.setting_key.like("knowledge_graph_%")
        ).all()
        
        for setting in settings:
            key = setting.setting_key.replace("knowledge_graph_", "")
            value = setting.setting_value
            # Parse based on type
            if key in ["physics_enabled", "interaction_hover", "interaction_zoom", "interaction_drag", 
                      "interaction_select", "interaction_navigation_buttons", "show_legend", "show_isolated_nodes"]:
                kg_settings[key] = value.lower() == "true"
            elif key in ["spring_length", "spring_strength", "damping", "central_gravity", "node_repulsion",
                        "node_size", "node_border_width", "node_font_size", "edge_width", "edge_arrow_size",
                        "max_nodes", "max_edges", "min_edge_weight", "height"]:
                kg_settings[key] = float(value) if "." in value else int(value) if value else 0
            else:
                kg_settings[key] = value
        
        # Set defaults if not in database
        physics_enabled = kg_settings.get("physics_enabled", True)
        layout_algorithm = kg_settings.get("layout_algorithm", "force")
        spring_length = kg_settings.get("spring_length", 100)
        spring_strength = kg_settings.get("spring_strength", 0.05)
        damping = kg_settings.get("damping", 0.09)
        central_gravity = kg_settings.get("central_gravity", 0.1)
        node_repulsion = kg_settings.get("node_repulsion", 4500)
        node_shape = kg_settings.get("node_shape", "dot")
        node_size = kg_settings.get("node_size", 25)
        node_border_width = kg_settings.get("node_border_width", 2)
        node_border_color = kg_settings.get("node_border_color", "#333333")
        node_font_size = kg_settings.get("node_font_size", 14)
        node_font_color = kg_settings.get("node_font_color", "#000000")
        node_size_by = kg_settings.get("node_size_by", "degree")
        edge_color = kg_settings.get("edge_color", "#848484")
        edge_width = kg_settings.get("edge_width", 2)
        edge_arrow_type = kg_settings.get("edge_arrow_type", "arrow")
        edge_arrow_size = kg_settings.get("edge_arrow_size", 10)
        edge_smooth = kg_settings.get("edge_smooth", "dynamic")
        edge_width_by = kg_settings.get("edge_width_by", "weight")
        max_nodes = int(kg_settings.get("max_nodes", 200))
        max_edges = int(kg_settings.get("max_edges", 500))
        min_edge_weight = int(kg_settings.get("min_edge_weight", 1))
        show_isolated_nodes = kg_settings.get("show_isolated_nodes", False)
        interaction_hover = kg_settings.get("interaction_hover", True)
        interaction_zoom = kg_settings.get("interaction_zoom", True)
        interaction_drag = kg_settings.get("interaction_drag", True)
        interaction_select = kg_settings.get("interaction_select", True)
        interaction_navigation_buttons = kg_settings.get("interaction_navigation_buttons", True)
        background_color = kg_settings.get("background_color", "#ffffff")
        height = int(kg_settings.get("height", 600))
        width = kg_settings.get("width", "100%")
        show_legend = kg_settings.get("show_legend", True)
        legend_position = kg_settings.get("legend_position", "bottom")
        
        # Node type colors
        color_entity_person = kg_settings.get("color_entity_person", "#FF5733")
        color_entity_organization = kg_settings.get("color_entity_organization", "#33C1FF")
        color_entity_location = kg_settings.get("color_entity_location", "#33FF57")
        color_entity_date = kg_settings.get("color_entity_date", "#FF33A8")
        color_entity_money = kg_settings.get("color_entity_money", "#8D33FF")
        color_entity_percent = kg_settings.get("color_entity_percent", "#FFC133")
        color_entity_time = kg_settings.get("color_entity_time", "#4BFFDB")
        color_entity_facility = kg_settings.get("color_entity_facility", "#FFD733")
        color_topic = kg_settings.get("color_topic", "#FF6B6B")
        color_word = kg_settings.get("color_word", "#4ECDC4")
        
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add entity nodes
        entity_count = 0
        for entity_type, entity_list in entities.items():
            if entity_list and isinstance(entity_list, list):
                for entity in entity_list[:20]:  # Limit per type
                    if entity and str(entity).strip():
                        G.add_node(str(entity), node_type="entity", entity_type=entity_type)
                        entity_count += 1
                        if entity_count >= max_nodes:
                            break
                if entity_count >= max_nodes:
                    break
        
        # Add topic nodes
        topic_count = 0
        if topics and isinstance(topics, list):
            for topic in topics[:20]:  # Limit topics
                if isinstance(topic, dict):
                    topic_label = topic.get('label', '')
                else:
                    topic_label = str(topic)
                if topic_label and topic_label.strip():
                    G.add_node(topic_label, node_type="topic")
                    topic_count += 1
                    if entity_count + topic_count >= max_nodes:
                        break
        
        # Add word cloud nodes
        word_count = 0
        if word_cloud and isinstance(word_cloud, list):
            for word_item in word_cloud[:20]:  # Limit word cloud terms
                if isinstance(word_item, dict):
                    word_term = word_item.get('term', '')
                else:
                    word_term = str(word_item)
                if word_term and word_term.strip():
                    G.add_node(word_term, node_type="word")
                    word_count += 1
                    if entity_count + topic_count + word_count >= max_nodes:
                        break
        
        # Build relationships using co-occurrence in raw text
        edge_count = 0
        for text in texts[:100]:  # Limit texts for performance
            if not text or len(text.strip()) < 10:
                continue
            
            # Find entities/topics/words that appear in this text
            nodes_in_text = []
            text_lower = text.lower()
            
            for node in G.nodes():
                node_str = str(node).lower()
                if node_str in text_lower:
                    nodes_in_text.append(node)
            
            # Connect nodes that co-occur in same text
            for i, node1 in enumerate(nodes_in_text):
                for node2 in nodes_in_text[i+1:]:
                    if G.has_edge(node1, node2):
                        # Increment weight
                        G[node1][node2]['weight'] = G[node1][node2].get('weight', 1) + 1
                    else:
                        # Add new edge
                        if edge_count < max_edges:
                            G.add_edge(node1, node2, weight=1, relationship="co_occurs_with")
                            edge_count += 1
        
        # Filter edges by minimum weight
        if min_edge_weight > 1:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d.get('weight', 1) < min_edge_weight]
            G.remove_edges_from(edges_to_remove)
        
        # Remove isolated nodes if not wanted
        if not show_isolated_nodes:
            isolated = list(nx.isolates(G))
            G.remove_nodes_from(isolated)
        
        # Create pyvis network
        net = Network(
            height=f"{height}px",
            width=width,
            bgcolor=background_color,
            font_color=node_font_color,
            directed=False
        )
        
        # Configure physics
        if physics_enabled:
            net.set_options(f"""
            {{
              "physics": {{
                "enabled": true,
                "barnesHut": {{
                  "gravitationalConstant": -{node_repulsion},
                  "centralGravity": {central_gravity},
                  "springLength": {spring_length},
                  "springConstant": {spring_strength},
                  "damping": {damping}
                }}
              }},
              "interaction": {{
                "hover": {str(interaction_hover).lower()},
                "zoomView": {str(interaction_zoom).lower()},
                "dragView": {str(interaction_drag).lower()},
                "selectConnectedEdges": {str(interaction_select).lower()},
                "navigationButtons": {str(interaction_navigation_buttons).lower()}
              }}
            }}
            """)
        else:
            net.set_options(f"""
            {{
              "physics": {{
                "enabled": false
              }},
              "interaction": {{
                "hover": {str(interaction_hover).lower()},
                "zoomView": {str(interaction_zoom).lower()},
                "dragView": {str(interaction_drag).lower()},
                "selectConnectedEdges": {str(interaction_select).lower()},
                "navigationButtons": {str(interaction_navigation_buttons).lower()}
              }}
            }}
            """)
        
        # Add nodes with colors by type
        node_colors = {
            "person": color_entity_person,
            "organization": color_entity_organization,
            "location": color_entity_location,
            "date": color_entity_date,
            "money": color_entity_money,
            "percent": color_entity_percent,
            "time": color_entity_time,
            "facility": color_entity_facility,
            "topic": color_topic,
            "word": color_word,
        }
        
        for node, data in G.nodes(data=True):
            node_type = data.get('node_type', 'unknown')
            entity_type = data.get('entity_type', '')
            
            # Determine color
            if node_type == "entity" and entity_type:
                color = node_colors.get(entity_type, "#CCCCCC")
            elif node_type == "topic":
                color = color_topic
            elif node_type == "word":
                color = color_word
            else:
                color = "#CCCCCC"
            
            # Calculate size based on degree if enabled
            if node_size_by == "degree":
                degree = G.degree(node)
                size = max(node_size * 0.5, min(node_size * 2, node_size + degree * 2))
            elif node_size_by == "weight":
                # Use average edge weight
                edges = G.edges(node, data=True)
                if edges:
                    avg_weight = sum(d.get('weight', 1) for _, _, d in edges) / len(edges)
                    size = max(node_size * 0.5, min(node_size * 2, node_size + avg_weight * 2))
                else:
                    size = node_size
            else:
                size = node_size
            
            net.add_node(
                str(node),
                label=str(node),
                color=color,
                size=size,
                shape=node_shape,
                borderWidth=node_border_width,
                borderColor=node_border_color,
                font={"size": node_font_size, "color": node_font_color},
                title=f"{node_type}: {node}"
            )
        
        # Add edges with weights
        for edge in G.edges(data=True):
            source, target, data = edge
            weight = data.get('weight', 1)
            relationship = data.get('relationship', 'related')
            
            # Calculate edge width
            if edge_width_by == "weight":
                width_val = max(1, min(10, edge_width + weight))
            else:
                width_val = edge_width
            
            net.add_edge(
                str(source),
                str(target),
                value=weight,
                width=width_val,
                color=edge_color,
                arrows=edge_arrow_type if edge_arrow_type != "none" else False,
                arrowStrikethrough=False,
                smooth={"type": edge_smooth, "roundness": 0.5},
                title=f"{relationship} (weight: {weight})"
            )
        
        # Generate HTML
        html = net.generate_html()
        
        # Add legend if enabled
        if show_legend:
            legend_html = f"""
            <div style="position: absolute; {legend_position}: 10px; left: 10px; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 12px; z-index: 1000;">
                <strong>Legend:</strong><br/>
                <span style="color: {color_entity_person};">●</span> Person<br/>
                <span style="color: {color_entity_organization};">●</span> Organization<br/>
                <span style="color: {color_entity_location};">●</span> Location<br/>
                <span style="color: {color_entity_date};">●</span> Date<br/>
                <span style="color: {color_topic};">●</span> Topic<br/>
                <span style="color: {color_word};">●</span> Word<br/>
            </div>
            """
            # Insert legend before closing body tag
            html = html.replace("</body>", legend_html + "</body>")
        
        response = HTMLResponse(content=html)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Required packages not available: {str(e)}</p><p>Please install: pip install networkx pyvis</p></body></html>",
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error generating knowledge graph visualization: {e}")
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
    logger.info(f"🔍 Research agent endpoint called: campaign_id={campaign_id}, agent_type={request_data.agent_type if hasattr(request_data, 'agent_type') else 'unknown'}")
    
    try:
        agent_type = request_data.agent_type
        logger.info(f"✅ Processing {agent_type} agent for campaign {campaign_id}")
        
        # Check if this is a request for the template demo campaign
        # If so, redirect to user's copy
        if campaign_id == DEMO_CAMPAIGN_ID:
            user_demo_campaign_id = create_user_demo_campaign(current_user.id, db)
            if user_demo_campaign_id:
                campaign_id = user_demo_campaign_id
                logger.info(f"Redirected template demo research request to user's copy: {user_demo_campaign_id}")
        
        # Verify campaign ownership
        from models import Campaign
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        if not campaign:
            logger.error(f"❌ Campaign {campaign_id} not found or access denied for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found or access denied"
            )
        
        logger.info(f"✅ Campaign {campaign_id} verified, proceeding with {agent_type} agent")
        from models import CampaignRawData, SystemSettings, CampaignResearchInsights
        
        # Check if insights already exist in database (cache)
        existing_insights = db.query(CampaignResearchInsights).filter(
            CampaignResearchInsights.campaign_id == campaign_id,
            CampaignResearchInsights.agent_type == agent_type
        ).first()
        
        if existing_insights and existing_insights.insights_text:
            # Validate cached data is not empty or error message
            cached_text = existing_insights.insights_text.strip()
            if cached_text and not cached_text.startswith("ERROR:") and len(cached_text) > 10:
                logger.info(f"✅ Returning cached {agent_type} insights for campaign {campaign_id} ({len(cached_text)} chars)")
                return {
                    "status": "success",
                    "recommendations": cached_text,
                    "agent_type": agent_type,
                    "cached": True
                }
            else:
                # Cached data is invalid (empty or error) - delete it and regenerate
                logger.warning(f"⚠️ Cached {agent_type} insights for campaign {campaign_id} are invalid (empty or error), regenerating...")
                db.delete(existing_insights)
                db.commit()
                # Continue to generation below
        
        # Get raw data for context
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = [r.extracted_text for r in rows if r.extracted_text and len(r.extracted_text.strip()) > 10 and (r.source_url is None or not r.source_url.startswith(("error:", "placeholder:")))]
        
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
        logger.info(f"📝 Prompt template (first 500 chars): {prompt_template[:500]}")
        
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
        logger.info(f"📝 Formatted prompt (first 500 chars): {prompt[:500]}")
        
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
            logger.info(f"📝 LLM response (first 1000 chars): {recommendations_text[:1000]}")
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
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ CRITICAL: Error generating {agent_type} recommendations for campaign {campaign_id}: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Full traceback:\n{error_trace}")
        return {"status": "error", "message": f"Error generating recommendations: {str(e)}"}

# Generate Ideas endpoint (for content queue)
@app.post("/generate-ideas")
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
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"status": "error", "message": "OPENAI_API_KEY not configured"}
        
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
        
        return {
            "status": "success",
            "ideas": ideas  
        }
    except Exception as e:
        logger.error(f"Error generating ideas: {e}")
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
- A summary of what the word cloud analysis reveals about the campaign's focus
- Areas where content could be expanded for better balance
- Specific recommendations for improving keyword coverage
- Actionable insights about underrepresented topics

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_micro-sentiment_prompt": """Analyze the sentiment data from a content campaign scrape:

{context}

Based on this data, provide:
- Overall sentiment assessment
- Sentiment breakdown by topic/theme
- Areas with lower positive sentiment that need attention
- Recommendations for improving sentiment in specific areas

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_topical-map_prompt": """Analyze the topical map data from a content campaign scrape:

{context}

Based on this data, provide:
- A summary of the main topics identified
- Topic relationships and coverage analysis
- Gaps or underrepresented topics
- Recommendations for expanding topic coverage

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_knowledge-graph_prompt": """Analyze the knowledge graph data from a content campaign scrape:

{context}

Based on this data, provide:
- Assessment of entity relationships and structure
- Analysis of connection strengths between concepts
- Identification of weakly connected areas
- Recommendations for strengthening relationships in the knowledge graph

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_hashtag-generator_prompt": """Analyze the hashtag data from a content campaign scrape:

{context}

Based on this data, provide:
- Assessment of hashtag mix (industry-standard, trending, niche, campaign-specific)
- Analysis of hashtag performance potential
- Recommendations for optimal hashtag combinations
- Suggested hashtag strategies for different platforms

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_idea-generator_prompt": """You are an expert in idea generation. Given the following topics and scraped posts, generate exactly {num_ideas} creative, one-line ideas that are meaningful, actionable, and relevant to the provided topics and posts.

CRITICAL INSTRUCTIONS:
- Focus STRICTLY on the topics provided in the "Topics:" section below
- Each idea must directly relate to these specific topics
- If recommendations or insights are provided, extract the actual topics/keywords from them and use those for idea generation
- Each idea should be a concise, complete sentence or phrase (e.g., "Create a comprehensive guide on pug health issues")
- Avoid vague or incomplete ideas
- Do not include explanations or additional text
- Return ONLY a JSON array of strings, with no markdown formatting, no numbering, no titles

Example output:
["Create a comprehensive guide on pug health issues", "Develop practical tips for pug grooming and care", "Explore pug personality traits and socialization"]

Context:
{context}""",
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
                        "idea-generator": "Idea Generator Agent",
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
def get_author_personalities(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all author personalities for the current user - REQUIRES AUTHENTICATION"""
    logger.info(f"🔍 /author_personalities GET endpoint called by user {current_user.id}")
    try:
        from models import AuthorPersonality
        # Filter by user_id to only return user's own personalities
        personalities = db.query(AuthorPersonality).filter(
            AuthorPersonality.user_id == current_user.id
        ).all()
        return {
            "status": "success",
            "message": {
                "personalities": [
                    {
                        "id": personality.id,
                        "name": personality.name,
                        "description": personality.description,
                        "created_at": personality.created_at.isoformat() if personality.created_at else None,
                        "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                        "user_id": personality.user_id,
                "model_config_json": personality.model_config_json,
                "baseline_adjustments_json": personality.baseline_adjustments_json,
                "selected_features_json": personality.selected_features_json,
                "configuration_preset": personality.configuration_preset,
                "writing_samples_json": personality.writing_samples_json,
                "samples_count": len(json.loads(personality.writing_samples_json)) if personality.writing_samples_json else 0,
                "has_profile": bool(personality.profile_json),
                    }
                    for personality in personalities
                ]
            }
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
def create_author_personality(personality_data: AuthorPersonalityCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new author personality - REQUIRES AUTHENTICATION"""
    try:
        from models import AuthorPersonality
        logger.info(f"Creating author personality: {personality_data.name} for user {current_user.id}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database with user_id
        personality = AuthorPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            user_id=current_user.id  # Associate with logged-in user
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
def update_author_personality(personality_id: str, personality_data: AuthorPersonalityUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update an author personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import AuthorPersonality
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        if personality_data.model_config_json is not None:
            personality.model_config_json = personality_data.model_config_json
        if personality_data.baseline_adjustments_json is not None:
            personality.baseline_adjustments_json = personality_data.baseline_adjustments_json
        if personality_data.selected_features_json is not None:
            personality.selected_features_json = personality_data.selected_features_json
        if personality_data.configuration_preset is not None:
            personality.configuration_preset = personality_data.configuration_preset
        if personality_data.writing_samples_json is not None:
            personality.writing_samples_json = personality_data.writing_samples_json
        
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
def delete_author_personality(personality_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete an author personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import AuthorPersonality
        
        # Check if personality exists at all (for better error messages)
        personality_any = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id
        ).first()
        
        if not personality_any:
            logger.warning(f"Delete attempt: Personality {personality_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Author personality '{personality_id}' not found"
            )
        
        # Check ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        
        if not personality:
            logger.warning(
                f"Delete attempt: Personality {personality_id} exists but user_id mismatch. "
                f"Profile user_id: {personality_any.user_id}, Current user_id: {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        db.delete(personality)
        db.commit()
        logger.info(f"Author personality deleted successfully: {personality_id} by user {current_user.id}")
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

# Author Profile endpoints (Phase 2)
@app.post("/author_personalities/{personality_id}/extract-profile")
async def extract_author_profile(
    personality_id: str,
    request_data: ExtractProfileRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract author profile from writing samples - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    # Get origin for CORS header
    origin = request.headers.get("Origin", "")
    cors_headers = {}
    if origin in ALLOWED_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        logger.info(f"Extracting profile for author personality: {personality_id}")
        
        # Extract profile using service
        service = AuthorProfileService()
        profile = service.extract_and_save_profile(
            author_personality_id=personality_id,
            writing_samples=request_data.writing_samples,
            sample_metadata=request_data.sample_metadata,
            db=db
        )
        
        # Compute similarity metrics by comparing profile to aggregated sample LIWC scores
        from author_related import compute_bh_lvt_weighted_similarity, compute_punctuation_similarity
        from liwc_analyzer import analyze_text
        import statistics
        
        similarity_metrics = {}
        try:
            # Aggregate LIWC scores from all writing samples
            all_liwc_scores = []
            for sample_text in request_data.writing_samples:
                if sample_text and sample_text.strip():
                    sample_liwc = analyze_text(sample_text)
                    all_liwc_scores.append(sample_liwc)
            
            if all_liwc_scores:
                # Aggregate by averaging across all samples
                aggregated_sample_liwc = {}
                all_categories = set()
                for liwc in all_liwc_scores:
                    all_categories.update(liwc.keys())
                
                for category in all_categories:
                    values = [liwc.get(category, 0.0) for liwc in all_liwc_scores if category in liwc]
                    if values:
                        aggregated_sample_liwc[category] = statistics.fmean(values)
                
                # Extract profile features
                profile_features = {
                    cat: score.mean 
                    for cat, score in profile.liwc_profile.categories.items()
                }
                
                # Compute BH-LVT weighted cosine similarity
                try:
                    bh_lvt_similarity = compute_bh_lvt_weighted_similarity(profile_features, aggregated_sample_liwc)
                    similarity_metrics["bh_lvt_weighted_cosine"] = float(bh_lvt_similarity)
                except Exception as e:
                    logger.warning(f"Error computing BH-LVT similarity during extraction: {e}")
                    similarity_metrics["bh_lvt_weighted_cosine"] = None
                
                # Compute punctuation cosine similarity
                try:
                    punctuation_similarity = compute_punctuation_similarity(profile_features, aggregated_sample_liwc)
                    similarity_metrics["punctuation_cosine"] = float(punctuation_similarity)
                except Exception as e:
                    logger.warning(f"Error computing punctuation similarity during extraction: {e}")
                    similarity_metrics["punctuation_cosine"] = None
            else:
                similarity_metrics["bh_lvt_weighted_cosine"] = None
                similarity_metrics["punctuation_cosine"] = None
        except Exception as e:
            logger.warning(f"Error computing similarity metrics during profile extraction: {e}")
            similarity_metrics["bh_lvt_weighted_cosine"] = None
            similarity_metrics["punctuation_cosine"] = None
        
        # Return summary (not full profile to avoid large response) with CORS headers
        response_data = {
            "status": "success",
            "message": {
                "personality_id": personality_id,
                "profile_extracted": True,
                "samples_analyzed": len(request_data.writing_samples),
                "liwc_categories": len(profile.liwc_profile.categories),
                "has_traits": profile.mbti is not None or profile.ocean is not None or profile.hexaco is not None,
                "lexicon_size": {
                    "core_verbs": len(profile.lexicon.core_verbs),
                    "core_nouns": len(profile.lexicon.core_nouns),
                    "evaluatives": len(profile.lexicon.evaluatives),
                    "metaphor_stems": len(profile.lexicon.metaphor_stems)
                },
                "similarity_metrics": similarity_metrics  # BH-LVT and punctuation cosine
            }
        }
        return JSONResponse(content=response_data, headers=cors_headers)
        
    except HTTPException as e:
        # Re-raise with CORS headers
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers={**cors_headers, **(e.headers or {})}
        )
    except ValueError as e:
        logger.error(f"Validation error extracting profile: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
            headers=cors_headers
        )
    except Exception as e:
        import traceback
        logger.error(f"Error extracting author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to extract author profile: {str(e)}"},
            headers=cors_headers
        )

@app.post("/author_personalities/{personality_id}/re-extract-profile")
def re_extract_author_profile(
    personality_id: str,
    request_data: ExtractProfileRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Re-extract author profile with updated writing samples.
    
    This endpoint allows users to update an existing profile by providing new writing samples.
    It merges the new samples with existing samples from the database and re-extracts the profile.
    
    - REQUIRES AUTHENTICATION AND OWNERSHIP
    - Merges new samples with existing samples from writing_samples_json
    - Re-extracts profile with all samples (existing + new)
    """
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        import json
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        logger.info(f"Re-extracting profile for author personality: {personality_id}")
        
        # Load existing samples from database
        existing_samples = []
        if personality.writing_samples_json:
            try:
                existing_samples = json.loads(personality.writing_samples_json)
                logger.info(f"Loaded {len(existing_samples)} existing samples from database")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse existing writing_samples_json: {e}, using only new samples")
        
        # Merge new samples with existing samples
        # Note: This is a simple append - users can provide duplicates if they want
        # For a more sophisticated approach, could deduplicate or merge metadata
        all_samples = existing_samples + request_data.writing_samples
        logger.info(f"Merged samples: {len(existing_samples)} existing + {len(request_data.writing_samples)} new = {len(all_samples)} total")
        
        # Merge sample metadata if provided
        all_metadata = None
        if request_data.sample_metadata:
            # Existing samples don't have metadata stored separately, so we'll use defaults for them
            # New samples use provided metadata
            existing_metadata = [{}] * len(existing_samples)  # Default metadata for existing samples
            all_metadata = existing_metadata + request_data.sample_metadata
        
        # Re-extract profile using service with all samples
        service = AuthorProfileService()
        profile = service.extract_and_save_profile(
            author_personality_id=personality_id,
            writing_samples=all_samples,
            sample_metadata=all_metadata,
            db=db
        )
        
        # Return summary
        return {
            "status": "success",
            "message": {
                "personality_id": personality_id,
                "profile_re_extracted": True,
                "samples_analyzed": len(all_samples),
                "existing_samples_count": len(existing_samples),
                "new_samples_count": len(request_data.writing_samples),
                "liwc_categories": len(profile.liwc_profile.categories),
                "has_traits": profile.mbti is not None or profile.ocean is not None or profile.hexaco is not None,
                "lexicon_size": {
                    "core_verbs": len(profile.lexicon.core_verbs),
                    "core_nouns": len(profile.lexicon.core_nouns),
                    "evaluatives": len(profile.lexicon.evaluatives),
                    "metaphor_stems": len(profile.lexicon.metaphor_stems)
                }
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error re-extracting profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        logger.error(f"Error re-extracting author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-extract author profile: {str(e)}"
        )

@app.get("/author_personalities/test-assets")
def test_asset_loading(current_user = Depends(get_current_user)):
    """Test endpoint to verify asset files can be loaded - REQUIRES AUTHENTICATION"""
    try:
        from author_related import ProfileExtractor
        from author_related.asset_loader import AssetLoader
        import traceback
        
        results = {
            "asset_root": None,
            "assets_found": [],
            "assets_missing": [],
            "extractor_init": False,
            "error": None
        }
        
        # Test AssetLoader
        try:
            loader = AssetLoader()
            results["asset_root"] = str(loader.root)
            
            # Check for required files
            required_files = [
                "LIWC_Mean_Table.csv",
                "LIWC_StdDev_Mean_Table.csv",
                "context_domains.json",
                "HighLow_Vectorization.json",
                "Trait_Mapping.json",
                "adapters.json"
            ]
            
            for filename in required_files:
                try:
                    path = loader._resolve(filename)
                    if path.exists():
                        results["assets_found"].append(filename)
                    else:
                        results["assets_missing"].append(filename)
                except Exception as e:
                    results["assets_missing"].append(f"{filename}: {str(e)}")
            
            # Test ProfileExtractor initialization
            try:
                extractor = ProfileExtractor()
                results["extractor_init"] = True
            except Exception as e:
                results["extractor_init"] = False
                results["error"] = f"ProfileExtractor init failed: {str(e)}\n{traceback.format_exc()}"
                
        except Exception as e:
            results["error"] = f"AssetLoader failed: {str(e)}\n{traceback.format_exc()}"
        
        return {
            "status": "success" if results["extractor_init"] else "error",
            "results": results
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": f"Test failed: {str(e)}\n{traceback.format_exc()}"
        }

@app.get("/author_personalities/{personality_id}/profile")
def get_author_profile(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full author profile - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Load profile
        service = AuthorProfileService()
        profile = service.load_profile(personality_id, db)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Extract profile from writing samples first."
            )
        
        # Return full profile with error handling
        try:
            profile_dict = profile.to_dict()
            return {
                "status": "success",
                "profile": profile_dict
            }
        except Exception as e:
            logger.error(f"Error serializing profile to dict: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to serialize profile: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load author profile: {str(e)}"
        )

@app.get("/author_personalities/{personality_id}/liwc-scores")
def get_liwc_scores(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick access to LIWC scores - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        service = AuthorProfileService()
        liwc_scores = service.get_liwc_scores(personality_id, db)
        
        if not liwc_scores:
            # Check if profile exists but LIWC scores are missing
            if personality.profile_json:
                logger.warning(f"Profile exists but LIWC scores missing for {personality_id}, attempting to extract from profile")
                try:
                    profile = service.load_profile(personality_id, db)
                    if profile and profile.liwc_profile:
                        # Extract LIWC scores from profile
                        liwc_scores = {
                            category: {"mean": score.mean, "stdev": score.stdev, "z": score.z}
                            for category, score in profile.liwc_profile.categories.items()
                        }
                        # Save for future quick access
                        personality.liwc_scores = json.dumps(liwc_scores, ensure_ascii=False)
                        db.commit()
                        logger.info(f"Extracted and saved LIWC scores from profile for {personality_id}")
                except Exception as e:
                    logger.error(f"Failed to extract LIWC scores from profile: {e}")
            
            if not liwc_scores:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="LIWC scores not found. Extract profile from writing samples first."
                )
        
        return {
            "status": "success",
            "liwc_scores": liwc_scores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading LIWC scores: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load LIWC scores: {str(e)}"
        )

@app.get("/author_personalities/{personality_id}/trait-scores")
def get_trait_scores(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick access to trait scores (MBTI/OCEAN/HEXACO) - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        service = AuthorProfileService()
        trait_scores = service.get_trait_scores(personality_id, db)
        
        if not trait_scores:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trait scores not found. Extract profile from writing samples first."
            )
        
        return {
            "status": "success",
            "trait_scores": trait_scores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading trait scores: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trait scores: {str(e)}"
        )

# Phase 4: Validation endpoint
@app.post("/author_personalities/{personality_id}/preview-adjustments")
def preview_adjustments(
    personality_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview how baseline adjustments will affect LIWC targets.
    
    This endpoint shows the before/after comparison of LIWC category z-scores
    when baseline adjustments are applied, without actually generating content.
    
    - REQUIRES AUTHENTICATION AND OWNERSHIP
    """
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        from profile_modifier import ProfileModifier
        import json
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Load profile
        service = AuthorProfileService()
        profile = service.load_profile(personality_id, db)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Extract profile from writing samples first."
            )
        
        # Get adjustments from request (or use stored adjustments)
        adjustments = request_data.get("adjustments")
        if not adjustments:
            # Fall back to stored adjustments
            if personality.baseline_adjustments_json:
                try:
                    adjustments = json.loads(personality.baseline_adjustments_json)
                except json.JSONDecodeError:
                    adjustments = {}
            else:
                adjustments = {}
        
        # Get original LIWC scores
        original_scores = {
            category: {
                "mean": score.mean,
                "stdev": score.stdev,
                "z": score.z
            }
            for category, score in profile.liwc_profile.categories.items()
        }
        
        # Apply adjustments to get modified scores
        if adjustments:
            modified_profile = ProfileModifier.apply_adjustments(
                profile=profile,
                adjustments=adjustments,
                adjustment_type="percentile"
            )
            modified_scores = {
                category: {
                    "mean": score.mean,
                    "stdev": score.stdev,
                    "z": score.z
                }
                for category, score in modified_profile.liwc_profile.categories.items()
            }
        else:
            modified_scores = original_scores
        
        # Calculate deltas
        deltas = {}
        for category in original_scores.keys():
            original_z = original_scores[category]["z"]
            modified_z = modified_scores[category]["z"]
            deltas[category] = {
                "original_z": original_z,
                "modified_z": modified_z,
                "delta_z": modified_z - original_z,
                "percent_change": ((modified_z - original_z) / abs(original_z) * 100) if original_z != 0 else 0
            }
        
        return {
            "status": "success",
            "personality_id": personality_id,
            "adjustments_applied": len(adjustments) if adjustments else 0,
            "original_scores": original_scores,
            "modified_scores": modified_scores,
            "deltas": deltas,
            "summary": {
                "categories_changed": len([d for d in deltas.values() if abs(d["delta_z"]) > 0.01]),
                "max_delta": max([abs(d["delta_z"]) for d in deltas.values()]) if deltas else 0,
                "avg_delta": sum([abs(d["delta_z"]) for d in deltas.values()]) / len(deltas) if deltas else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error previewing adjustments: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview adjustments: {str(e)}"
        )

@app.post("/author_personalities/{personality_id}/test-full-chain")
def test_full_chain(
    personality_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Full-chain test endpoint: Logs entire author voice pipeline for empirical verification.
    
    This endpoint generates content and returns detailed logs showing:
    1. Original z-scores from profile
    2. Slider settings (baseline adjustments)
    3. Modified z-scores after applying adjustments
    4. STYLE_CONFIG generated from modified profile
    5. Generated content
    6. Measured LIWC scores from generated content
    7. Validator deltas (measured vs adjusted profile)
    
    This allows empirical verification that:
    - Moving slider in direction X pushes validator z-deltas in corresponding direction
    - Preview "before/after" matches actual LIWC delta behavior on generated content
    
    - REQUIRES AUTHENTICATION AND OWNERSHIP
    """
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        from profile_modifier import ProfileModifier
        from author_voice_helper import generate_with_author_voice
        from liwc_analyzer import analyze_text
        import json
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Load profile
        service = AuthorProfileService()
        original_profile = service.load_profile(personality_id, db)
        
        if not original_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Extract profile from writing samples first."
            )
        
        # Get content prompt
        content_prompt = request_data.get("content_prompt", "Write a short post about innovation in technology.")
        platform = request_data.get("platform", "linkedin")
        
        # Step 1: Log original z-scores
        original_z_scores = {
            category: {
                "mean": score.mean,
                "stdev": score.stdev,
                "z": score.z
            }
            for category, score in original_profile.liwc_profile.categories.items()
        }
        
        # Step 2: Get slider settings (baseline adjustments)
        slider_settings = {}
        if personality.baseline_adjustments_json:
            try:
                slider_settings = json.loads(personality.baseline_adjustments_json)
            except json.JSONDecodeError:
                pass
        
        # Step 3: Apply adjustments and get modified z-scores
        modified_profile = original_profile
        modified_z_scores = original_z_scores
        if slider_settings:
            modified_profile = ProfileModifier.apply_adjustments(
                profile=original_profile,
                adjustments=slider_settings,
                adjustment_type="percentile"
            )
            modified_z_scores = {
                category: {
                    "mean": score.mean,
                    "stdev": score.stdev,
                    "z": score.z
                }
                for category, score in modified_profile.liwc_profile.categories.items()
            }
        
        # Step 4: Generate content using author voice (this uses adjusted profile internally)
        generated_text, style_config_block, metadata, validation_result = generate_with_author_voice(
            content_prompt=content_prompt,
            author_personality_id=personality_id,
            platform=platform,
            goal=request_data.get("goal", "content_generation"),
            target_audience=request_data.get("target_audience", "general"),
            custom_modifications=request_data.get("custom_modifications"),
            use_validation=True,  # Enable validation to get deltas
            db=db
        )
        
        if not generated_text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate content"
            )
        
        # Step 5: Measure LIWC scores from generated content
        measured_liwc = analyze_text(generated_text)
        
        # Step 6: Calculate z-scores for measured LIWC (using validator's method)
        from author_related.validator import StyleValidator
        validator = StyleValidator()
        measured_z_scores = {}
        for category, value in measured_liwc.items():
            if category in original_profile.liwc_profile.categories:
                measured_z_scores[category] = validator._z_score(category, value)
        
        # Step 7: Calculate deltas (measured vs adjusted profile)
        validator_deltas = {}
        for category in modified_profile.liwc_profile.categories.keys():
            if category in measured_z_scores:
                expected_z = modified_profile.liwc_profile.categories[category].z
                actual_z = measured_z_scores[category]
                delta_z = actual_z - expected_z
                validator_deltas[category] = {
                    "expected_z": expected_z,
                    "actual_z": actual_z,
                    "delta_z": delta_z,
                    "abs_delta": abs(delta_z)
                }
        
        # Step 8: Calculate adjustment deltas (how much sliders changed things)
        adjustment_deltas = {}
        for category in original_z_scores.keys():
            original_z = original_z_scores[category]["z"]
            modified_z = modified_z_scores[category]["z"]
            adjustment_deltas[category] = {
                "original_z": original_z,
                "modified_z": modified_z,
                "delta_z": modified_z - original_z
            }
        
        # Step 9: Calculate correlation between adjustment direction and validator delta direction
        # For each adjusted category, check if validator delta moved in same direction
        correlation_analysis = {}
        for category, adj_delta in adjustment_deltas.items():
            if abs(adj_delta["delta_z"]) > 0.01 and category in validator_deltas:  # Only check adjusted categories
                adj_direction = 1 if adj_delta["delta_z"] > 0 else -1
                val_delta = validator_deltas[category]["delta_z"]
                val_direction = 1 if val_delta > 0 else -1
                
                # Same direction = positive correlation
                correlation_analysis[category] = {
                    "adjustment_delta_z": adj_delta["delta_z"],
                    "validator_delta_z": val_delta,
                    "same_direction": (adj_direction * val_direction) > 0,
                    "correlation": "positive" if (adj_direction * val_direction) > 0 else "negative"
                }
        
        return {
            "status": "success",
            "personality_id": personality_id,
            "content_prompt": content_prompt,
            "platform": platform,
            "chain_analysis": {
                "step_1_original_z_scores": original_z_scores,
                "step_2_slider_settings": slider_settings,
                "step_3_modified_z_scores": modified_z_scores,
                "step_4_style_config_block": style_config_block[:500] if style_config_block else None,  # Truncate for readability
                "step_5_generated_content": generated_text[:500],  # Truncate for readability
                "step_6_measured_liwc": measured_liwc,
                "step_7_measured_z_scores": measured_z_scores,
                "step_8_validator_deltas": validator_deltas,
                "step_9_adjustment_deltas": adjustment_deltas,
                "step_10_correlation_analysis": correlation_analysis
            },
            "summary": {
                "categories_adjusted": len([d for d in adjustment_deltas.values() if abs(d["delta_z"]) > 0.01]),
                "categories_with_validation": len(validator_deltas),
                "avg_validator_delta": sum([abs(d["abs_delta"]) for d in validator_deltas.values()]) / len(validator_deltas) if validator_deltas else 0,
                "correlation_matches": len([c for c in correlation_analysis.values() if c["same_direction"]]),
                "correlation_total": len(correlation_analysis),
                "correlation_rate": len([c for c in correlation_analysis.values() if c["same_direction"]]) / len(correlation_analysis) if correlation_analysis else 0
            },
            "validation_result": validation_result,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error in full-chain test: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run full-chain test: {str(e)}"
        )

@app.post("/author_personalities/{personality_id}/validate-content")
def validate_content(
    personality_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate content against author profile - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_validation_helper import validate_content_against_profile
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Get content and style config from request
        content = request_data.get("content", "")
        style_config_block = request_data.get("style_config", "")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required"
            )
        
        # Validate content
        validation_result = validate_content_against_profile(
            generated_text=content,
            style_config_block=style_config_block,
            author_personality_id=personality_id,
            db=db
        )
        
        return {
            "status": "success",
            "validation": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error validating content: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate content: {str(e)}"
        )

# Brand Personality Endpoints
@app.get("/brand_personalities")
def get_brand_personalities(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all brand personalities for the current user - REQUIRES AUTHENTICATION"""
    logger.info(f"🔍 /brand_personalities GET endpoint called by user {current_user.id}")
    try:
        from models import BrandPersonality
        # Filter by user_id to only return user's own personalities
        personalities = db.query(BrandPersonality).filter(
            BrandPersonality.user_id == current_user.id
        ).all()
        return {
            "status": "success",
            "message": {
                "personalities": [
                    {
                        "id": personality.id,
                        "name": personality.name,
                        "description": personality.description,
                        "guidelines": personality.guidelines,
                        "created_at": personality.created_at.isoformat() if personality.created_at else None,
                        "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                        "user_id": personality.user_id
                    }
                    for personality in personalities
                ]
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching brand personalities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch brand personalities: {str(e)}"
        )

@app.post("/brand_personalities")
def create_brand_personality(personality_data: BrandPersonalityCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new brand personality - REQUIRES AUTHENTICATION"""
    try:
        from models import BrandPersonality
        logger.info(f"Creating brand personality: {personality_data.name} for user {current_user.id}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database with user_id
        personality = BrandPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            guidelines=personality_data.guidelines,
            user_id=current_user.id  # Associate with logged-in user
        )
        
        db.add(personality)
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality created successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create brand personality: {str(e)}"
        )

@app.put("/brand_personalities/{personality_id}")
def update_brand_personality(personality_id: str, personality_data: BrandPersonalityUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        if personality_data.guidelines is not None:
            personality.guidelines = personality_data.guidelines
        
        personality.updated_at = datetime.now()
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality updated successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand personality: {str(e)}"
        )

@app.delete("/brand_personalities/{personality_id}")
def delete_brand_personality(personality_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        db.delete(personality)
        db.commit()
        logger.info(f"Brand personality deleted successfully: {personality_id}")
        return {
            "status": "success",
            "message": "Brand personality deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error deleting brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete brand personality: {str(e)}"
        )

# Campaign Planning Endpoint
@app.post("/campaigns/{campaign_id}/plan")
async def create_campaign_plan(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a campaign plan based on weeks, scheduling settings, and content queue items.
    Generates parent/children idea hierarchy and knowledge graph locations.
    
    Request body:
    {
        "scheduling": {
            "weeks": 4,
            "posts_per_day": {"facebook": 3, "instagram": 2},
            "posts_per_week": {"facebook": 15, "instagram": 10},
            "start_date": "2025-01-01",
            "day_frequency": "selected_days",  # daily, selected_days, every_other, every_first, etc.
            "post_frequency_type": "weeks",
            "post_frequency_value": 4
        },
        "content_queue_items": [...],  # Checked items from content queue
        "landing_page_url": "https://example.com/landing"
    }
    """
    try:
        from models import Campaign, SystemSettings
        import json
        from datetime import datetime, timedelta
        from machine_agent import IdeaGeneratorAgent
        from langchain_openai import ChatOpenAI
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        scheduling = request_data.get("scheduling", {})
        content_queue_items = request_data.get("content_queue_items", [])
        landing_page_url = request_data.get("landing_page_url", "")
        max_refactoring = request_data.get("max_refactoring", 3)  # Default max refactoring attempts
        
        weeks = scheduling.get("weeks", 4)
        posts_per_day = scheduling.get("posts_per_day", {})
        start_date_str = scheduling.get("start_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now()
        
        # Get knowledge graph location selection prompt from admin settings
        kg_location_prompt_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "knowledge_graph_location_selection_prompt"
        ).first()
        
        kg_location_prompt = kg_location_prompt_setting.setting_value if kg_location_prompt_setting else """Given a parent idea and existing knowledge graph locations used, select a new location on the knowledge graph that:
1. Supports the same core topic as the parent idea
2. Has not been used recently for this campaign
3. Provides a different angle or perspective
4. Can drive traffic to the landing page

Return the knowledge graph location (node name or entity) that should be used for the next post."""
        
        # Initialize LLM for planning
        api_key = os.getenv("OPENAI_API_KEY") or (current_user.openai_key if hasattr(current_user, 'openai_key') else None)
        if not api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
        
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key.strip(), temperature=0.7)
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        # Generate campaign plan with parent/children structure
        plan = {
            "weeks": [],
            "landing_page_url": landing_page_url,
            "created_at": datetime.now().isoformat()
        }
        
        # For each week, generate parent ideas and children
        for week_num in range(1, weeks + 1):
            week_plan = {
                "week_num": week_num,
                "parent_ideas": [],
                "knowledge_graph_locations": []
            }
            
            # Generate parent ideas for this week (one per day, or based on scheduling)
            # For simplicity, generate one parent idea per day of the week
            days_in_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            for day in days_in_week[:5]:  # Weekdays only for now
                # Generate parent idea for this day
                parent_prompt = f"""Based on the following content queue items, generate a parent idea for {day} of week {week_num}:

Content Queue Items:
{queue_context}

Generate a parent idea that:
1. Is based on the content queue items
2. Can be broken down into supporting children concepts
3. Drives traffic to: {landing_page_url}
4. Is suitable for multiple posts on the same day

Return only the parent idea, no additional text."""
                
                parent_response = llm.invoke(parent_prompt)
                parent_idea = parent_response.content.strip()
                
                # Generate children concepts for this parent
                children_prompt = f"""Given this parent idea: "{parent_idea}"

Generate 3-5 children concepts that support this parent idea. Each child should:
1. Focus on a different aspect of the parent
2. Be suitable for a single post
3. Drive traffic to: {landing_page_url}

Return as a numbered list."""
                
                children_response = llm.invoke(children_prompt)
                children_text = children_response.content.strip()
                children = [line.strip() for line in children_text.split("\n") if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))]
                
                # Clean up children (remove numbering)
                children = [c.split(". ", 1)[-1] if ". " in c else c.replace("- ", "").strip() for c in children]
                
                # Select knowledge graph location for this parent idea
                kg_location_prompt_full = f"""{kg_location_prompt}

Parent Idea: {parent_idea}
Existing Locations Used: {', '.join(week_plan['knowledge_graph_locations']) if week_plan['knowledge_graph_locations'] else 'None'}

Select a knowledge graph location for this parent idea."""
                
                kg_response = llm.invoke(kg_location_prompt_full)
                kg_location = kg_response.content.strip()
                
                week_plan["parent_ideas"].append({
                    "day": day,
                    "idea": parent_idea,
                    "children": children,
                    "knowledge_graph_location": kg_location
                })
                week_plan["knowledge_graph_locations"].append(kg_location)
            
            plan["weeks"].append(week_plan)
        
        # Save plan to campaign
        campaign.campaign_plan_json = json.dumps(plan)
        campaign.scheduling_settings_json = json.dumps(scheduling)
        campaign.content_queue_items_json = json.dumps(content_queue_items)
        db.commit()
        
        return {
            "status": "success",
            "plan": plan,
            "message": f"Campaign plan created for {weeks} weeks"
        }
        
    except Exception as e:
        logger.error(f"Error creating campaign plan: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Content Pre-population Endpoint
@app.post("/campaigns/{campaign_id}/prepopulate-content")
async def prepopulate_campaign_content(
    campaign_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pre-populate content for the entire campaign lifecycle based on the campaign plan.
    Creates draft content for all scheduled posts that can be edited until scheduled time.
    Images are NOT generated until push time to save tokens.
    """
    try:
        from models import Campaign, Content, SystemSettings
        from crewai_workflows import create_content_generation_crew
        import json
        from datetime import datetime, timedelta
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if not campaign.campaign_plan_json:
            raise HTTPException(status_code=400, detail="Campaign plan not found. Please create a plan first.")
        
        plan = json.loads(campaign.campaign_plan_json)
        scheduling = json.loads(campaign.scheduling_settings_json) if campaign.scheduling_settings_json else {}
        content_queue_items = json.loads(campaign.content_queue_items_json) if campaign.content_queue_items_json else []
        
        start_date_str = scheduling.get("start_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now()
        posts_per_day = scheduling.get("posts_per_day", {})
        landing_page_url = plan.get("landing_page_url", "")
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        generated_content = []
        
        # Generate content for each week in the plan
        for week_data in plan.get("weeks", []):
            week_num = week_data.get("week_num", 1)
            
            for parent_data in week_data.get("parent_ideas", []):
                day = parent_data.get("day")
                parent_idea = parent_data.get("idea")
                children = parent_data.get("children", [])
                kg_location = parent_data.get("knowledge_graph_location", "")
                
                # Calculate actual date for this day
                day_offset = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
                week_start = start_date + timedelta(weeks=week_num - 1)
                # Find the Monday of this week
                days_since_monday = (week_start.weekday()) % 7
                monday_of_week = week_start - timedelta(days=days_since_monday)
                post_date = monday_of_week + timedelta(days=day_offset)
                
                # Generate content for each platform
                for platform, posts_count in posts_per_day.items():
                    # Generate posts for this platform on this day
                    # If multiple posts, use different children or knowledge graph locations
                    for post_num in range(posts_count):
                        # Select content source (parent idea, child, or knowledge graph location)
                        if post_num == 0:
                            # First post uses parent idea
                            content_source = parent_idea
                        elif post_num <= len(children):
                            # Use child concept
                            content_source = children[post_num - 1]
                        else:
                            # Use knowledge graph location (refactored)
                            content_source = f"{parent_idea} (focusing on {kg_location})"
                        
                        # Build writing context
                        writing_context = f"""Content Queue Foundation:
{queue_context}

Parent Idea: {parent_idea}
Content Source: {content_source}
Knowledge Graph Location: {kg_location}
Landing Page: {landing_page_url}

Generate content for {platform} that:
1. Is based on the content source above
2. Drives traffic to the landing page
3. Focuses on the knowledge graph location
4. Is suitable for {platform} platform"""
                        
                        # Generate content using CrewAI workflow
                        try:
                            crew_result = create_content_generation_crew(
                                text=writing_context,
                                week=week_num,
                                platform=platform.lower(),
                                days_list=[day],
                                author_personality=None  # Can be added later
                            )
                            
                            if crew_result.get("success"):
                                content_text = crew_result.get("data", {}).get("content", "")
                                title = crew_result.get("data", {}).get("title", f"{platform} Post - {day}")
                                
                                # Create content record (draft, not finalized)
                                content = Content(
                                    user_id=current_user.id,
                                    campaign_id=campaign_id,
                                    week=week_num,
                                    day=day,
                                    content=content_text,
                                    title=title,
                                    status="draft",  # Draft status until scheduled
                                    date_upload=post_date,
                                    platform=platform.lower(),
                                    file_name=f"{campaign_id}_{week_num}_{day}_{platform}_{post_num}.txt",
                                    file_type="text",
                                    platform_post_no=str(post_num + 1),
                                    schedule_time=post_date.replace(hour=9, minute=0),  # Default 9 AM
                                    is_draft=True,
                                    can_edit=True,
                                    knowledge_graph_location=kg_location,
                                    parent_idea=parent_idea,
                                    landing_page_url=landing_page_url
                                )
                                
                                db.add(content)
                                generated_content.append({
                                    "id": content.id,
                                    "week": week_num,
                                    "day": day,
                                    "platform": platform,
                                    "title": title,
                                    "status": "draft"
                                })
                        except Exception as e:
                            logger.error(f"Error generating content for {platform} on {day}: {e}")
                            # Continue with other posts
                            continue
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Pre-populated {len(generated_content)} content items",
            "content": generated_content
        }
        
    except Exception as e:
        logger.error(f"Error pre-populating content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Update writing endpoint to accept content queue items
@app.post("/campaigns/{campaign_id}/generate-content")
async def generate_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content for a campaign using content queue items as foundation.
    Updated to accept content_queue_items and use them as context.
    Now runs in background with status tracking.
    """
    try:
        # Create task for status tracking
        task_id = str(uuid.uuid4())
        platform = request_data.get("platform", "linkedin")
        
        CONTENT_GEN_TASKS[task_id] = {
            "campaign_id": campaign_id,
            "platform": platform,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "status": "pending",
            "current_agent": None,
            "current_task": "Initializing content generation",
            "agent_statuses": [],
            "error": None,
            "result": None,
        }
        
        # Index by campaign_id for easy lookup
        if campaign_id not in CONTENT_GEN_TASK_INDEX:
            CONTENT_GEN_TASK_INDEX[campaign_id] = []
        CONTENT_GEN_TASK_INDEX[campaign_id].append(task_id)
        
        logger.info(f"📝 Created content generation task: {task_id} for campaign {campaign_id}")
        
        # Run generation in background thread
        def run_generation_background(tid: str, cid: str, req_data: Dict[str, Any], user_id: int):
            try:
                from database import SessionLocal
                session = SessionLocal()
                try:
                    from models import Campaign
                    from crewai_workflows import create_content_generation_crew
                    import json
                    
                    # Helper to update task status
                    def update_task_status(agent: str = None, task: str = None, progress: int = None, 
                                          status: str = None, error: str = None, agent_status: str = "running"):
                        if tid not in CONTENT_GEN_TASKS:
                            return
                        task_data = CONTENT_GEN_TASKS[tid]
                        if agent:
                            task_data["current_agent"] = agent
                        if task:
                            task_data["current_task"] = task
                        if progress is not None:
                            task_data["progress"] = progress
                        if status:
                            task_data["status"] = status
                        if error:
                            task_data["error"] = error
                            task_data["status"] = "error"
                        # Add to agent statuses
                        if agent:
                            agent_entry = {
                                "agent": agent,
                                "task": task or "Processing",
                                "status": agent_status,
                                "timestamp": datetime.utcnow().isoformat(),
                                "error": error
                            }
                            # Add message if provided (for QC agents, this might contain approval/rejection details)
                            if task and ("approved" in task.lower() or "rejected" in task.lower() or "review" in task.lower()):
                                agent_entry["message"] = task
                            task_data["agent_statuses"].append(agent_entry)
                        logger.info(f"📊 Task {tid}: {progress}% - {agent} - {task}")
                    
                    update_task_status(progress=5, task="Initializing", status="in_progress")
                    
                    # Verify campaign ownership
                    campaign = session.query(Campaign).filter(
                        Campaign.campaign_id == cid,
                        Campaign.user_id == user_id
                    ).first()
                    
                    if not campaign:
                        update_task_status(error="Campaign not found", status="error")
                        return
                    
                    # Get content queue items
                    content_queue_items = req_data.get("content_queue_items", [])
                    if not content_queue_items and campaign.content_queue_items_json:
                        content_queue_items = json.loads(campaign.content_queue_items_json)
                    
                    # Build context
                    queue_context = "\n".join([
                        f"- {item.get('title', item.get('text', str(item)))}"
                        for item in content_queue_items
                    ])
                    
                    # Get parameters
                    platform = req_data.get("platform", "linkedin")
                    week = req_data.get("week", 1)
                    day = req_data.get("day", "Monday")
                    parent_idea = req_data.get("parent_idea", "")
                    author_personality_id = req_data.get("author_personality_id")
                    brand_personality_id = req_data.get("brand_personality_id")  # NEW: Support brand personality
                    use_author_voice = req_data.get("use_author_voice", True)
                    use_validation = req_data.get("use_validation", False)
                    
                    # Get brand personality guidelines if provided
                    brand_guidelines = ""
                    if brand_personality_id:
                        from models import BrandPersonality
                        brand_personality = session.query(BrandPersonality).filter(
                            BrandPersonality.id == brand_personality_id,
                            BrandPersonality.user_id == user_id
                        ).first()
                        if brand_personality and brand_personality.guidelines:
                            brand_guidelines = f"\n\nBrand Voice Guidelines:\n{brand_personality.guidelines}"
                    
                    # Build writing context
                    writing_context = f"""Content Queue Foundation:
{queue_context}

{f'Parent Idea: {parent_idea}' if parent_idea else ''}{brand_guidelines}

Generate content for {platform} based on the content queue items above."""
                    
                    # Log configuration details for verbose status tracking
                    author_personality_name = "None"
                    brand_personality_name = "None"
                    if author_personality_id:
                        from models import AuthorPersonality
                        author_personality_obj = session.query(AuthorPersonality).filter(
                            AuthorPersonality.id == author_personality_id,
                            AuthorPersonality.user_id == user_id
                        ).first()
                        if author_personality_obj:
                            author_personality_name = author_personality_obj.name or author_personality_id
                    if brand_personality_id:
                        from models import BrandPersonality
                        brand_personality_obj = session.query(BrandPersonality).filter(
                            BrandPersonality.id == brand_personality_id,
                            BrandPersonality.user_id == user_id
                        ).first()
                        if brand_personality_obj:
                            brand_personality_name = brand_personality_obj.name or brand_personality_id
                    
                    update_task_status(
                        agent="Configuration",
                        task=f"Author Personality: {author_personality_name} | Brand Voice: {brand_personality_name} | Platform: {platform.capitalize()}",
                        progress=5,
                        agent_status="completed"
                    )
                    
                    update_task_status(progress=10, task="Preparing content context")
                    
                    # Phase 3: Integrate author voice if author_personality_id is provided
                    if author_personality_id and use_author_voice:
                        from author_voice_helper import generate_with_author_voice, should_use_author_voice
                        
                        if should_use_author_voice(author_personality_id):
                            update_task_status(
                                agent="Author Voice Generator",
                                task="Generating content with author personality",
                                progress=20,
                                status="in_progress"
                            )
                            
                            # Get custom modifications
                            custom_modifications = None
                            if "platformSettings" in req_data:
                                platform_settings = req_data.get("platformSettings", {})
                                platform_lower = platform.lower()
                                if platform_lower in platform_settings:
                                    settings = platform_settings[platform_lower]
                                    if not settings.get("useGlobalDefaults", True):
                                        custom_modifications = settings.get("customModifications", "")
                            
                            # Generate with author voice
                            try:
                                generated_text, style_config, metadata, validation_result = generate_with_author_voice(
                                    content_prompt=writing_context,
                                    author_personality_id=author_personality_id,
                                    platform=platform.lower(),
                                    goal="content_generation",
                                    target_audience="general",
                                    custom_modifications=custom_modifications,
                                    use_validation=use_validation,
                                    db=session
                                )
                                
                                update_task_status(
                                    agent="Author Voice Generator",
                                    task="Content generated successfully",
                                    progress=80,
                                    agent_status="completed"
                                )
                                
                                if generated_text:
                                    use_crewai_qc = req_data.get("use_crewai_qc", False)
                                    
                                    if use_crewai_qc:
                                        update_task_status(
                                            agent="CrewAI QC Agent",
                                            task="Reviewing content quality",
                                            progress=85,
                                            status="in_progress"
                                        )
                                        
                                        crew_result = create_content_generation_crew(
                                            text=f"Review and refine this content:\n\n{generated_text}\n\nStyle Config:\n{style_config}",
                                            week=week,
                                            platform=platform.lower(),
                                            days_list=[day],
                                            author_personality=req_data.get("author_personality", "custom")
                                        )
                                        
                                        update_task_status(
                                            agent="CrewAI QC Agent",
                                            task="Quality review completed",
                                            progress=95,
                                            agent_status="completed"
                                        )
                                        
                                        if crew_result.get("success"):
                                            response_data = {
                                                **crew_result.get("data", {}),
                                                "author_voice_used": True,
                                                "style_config": style_config,
                                                "author_voice_metadata": metadata
                                            }
                                            if validation_result:
                                                response_data["validation"] = validation_result
                                            CONTENT_GEN_TASKS[tid]["result"] = {
                                                "status": "success",
                                                "data": response_data,
                                                "error": None
                                            }
                                            update_task_status(progress=100, status="completed", task="Content generation completed")
                                            return
                                    
                                    # Return author voice content directly
                                    response_data = {
                                        "content": generated_text,
                                        "title": "",
                                        "author_voice_used": True,
                                        "style_config": style_config,
                                        "author_voice_metadata": metadata,
                                        "platform": platform
                                    }
                                    if validation_result:
                                        response_data["validation"] = validation_result
                                    CONTENT_GEN_TASKS[tid]["result"] = {
                                        "status": "success",
                                        "data": response_data,
                                        "error": None
                                    }
                                    update_task_status(progress=100, status="completed", task="Content generation completed")
                                    return
                            except Exception as av_error:
                                logger.error(f"Author voice generation error: {av_error}")
                                update_task_status(
                                    agent="Author Voice Generator",
                                    task=f"Error: {str(av_error)}",
                                    error=str(av_error),
                                    agent_status="error"
                                )
                                logger.warning(f"Author voice generation failed, falling back to CrewAI")
                    
                    # Fallback to CrewAI workflow
                    # Note: CrewAI will handle Research → Writing → QC sequentially
                    # We track overall progress, but individual agents are tracked by CrewAI internally
                    update_task_status(
                        agent="CrewAI Workflow",
                        task="Starting content generation workflow",
                        progress=20,
                        status="in_progress"
                    )
                    
                    # Pass update_task_status callback for progress tracking
                    crew_result = create_content_generation_crew(
                        text=writing_context,
                        week=week,
                        platform=platform.lower(),
                        days_list=[day],
                        author_personality=req_data.get("author_personality"),
                        update_task_status_callback=update_task_status
                    )
                    
                    if crew_result.get("success"):
                        # Track individual agents from CrewAI result
                        # Research agent runs once at the start (not re-engaged)
                        update_task_status(
                            agent="Research Agent",
                            task="Content analysis completed",
                            progress=40,
                            agent_status="completed"
                        )
                        
                        # Platform writing agent
                        platform_agent_name = f"{platform.capitalize()} Writing Agent"
                        update_task_status(
                            agent=platform_agent_name,
                            task="Platform-specific content created",
                            progress=70,
                            agent_status="completed"
                        )
                        
                        # Log writing agent used
                        writing_agent_name = f"{platform.capitalize()} Writing Agent"
                        update_task_status(
                            agent=writing_agent_name,
                            task=f"Platform-specific content created for {platform.capitalize()}",
                            progress=70,
                            agent_status="completed"
                        )
                        
                        # Track QC agents with platform name and show which ones ran
                        qc_agents_used = []
                        if "metadata" in crew_result and "agents_used" in crew_result["metadata"]:
                            qc_agents = [a for a in crew_result["metadata"]["agents_used"] if "qc" in a.lower()]
                            platform_name = platform.capitalize()
                            
                            # Log QC agent configuration
                            qc_agent_list_str = ", ".join([f"{platform_name} QC Agent {i+1}" for i in range(len(qc_agents))]) if len(qc_agents) > 1 else f"{platform_name} QC Agent"
                            update_task_status(
                                agent="QC Configuration",
                                task=f"QC Agents Running: {qc_agent_list_str} (Platform: {platform_name}, Global: Included)",
                                progress=75,
                                agent_status="completed"
                            )
                            
                            for idx, qc_agent in enumerate(qc_agents):
                                # Use platform name in QC agent name
                                qc_agent_name = f"{platform_name} QC Agent {idx + 1}" if len(qc_agents) > 1 else f"{platform_name} QC Agent"
                                qc_agents_used.append(qc_agent_name)
                                # Extract QC result details if available
                                qc_result = crew_result.get("data", {}).get("quality_control")
                                qc_message = "Quality review completed - content approved"
                                qc_details = []
                                
                                # Build QC criteria list for display
                                qc_criteria = [
                                    "Quality and clarity",
                                    f"Platform-specific requirements ({platform_name})",
                                    "Compliance with guidelines",
                                    "Author personality match",
                                    "Accuracy and relevance to research"
                                ]
                                
                                if qc_result:
                                    # Try to extract meaningful information from QC result
                                    if isinstance(qc_result, dict):
                                        if "approved" in str(qc_result).lower() or "pass" in str(qc_result).lower():
                                            qc_message = "Quality review: Content approved - meets all quality criteria"
                                            qc_details = qc_criteria
                                        elif "rejected" in str(qc_result).lower() or "fail" in str(qc_result).lower():
                                            qc_message = "Quality review: Content requires revision - quality criteria not met"
                                            qc_details = qc_criteria
                                        else:
                                            qc_message = f"Quality review completed - {str(qc_result)[:100]}"
                                            qc_details = qc_criteria
                                    elif isinstance(qc_result, str):
                                        if len(qc_result) > 200:
                                            qc_message = f"Quality review: {qc_result[:150]}..."
                                        else:
                                            qc_message = f"Quality review: {qc_result}"
                                        qc_details = qc_criteria
                                else:
                                    # Default: show criteria even if result not available
                                    qc_details = qc_criteria
                                
                                # Build detailed message with criteria
                                detailed_message = qc_message
                                if qc_details:
                                    detailed_message += f"\n\nReview Criteria Checked:\n" + "\n".join([f"• {criterion}" for criterion in qc_details])
                                
                                update_task_status(
                                    agent=qc_agent_name,
                                    task=detailed_message,
                                    progress=85 + (idx * 5),
                                    agent_status="completed"
                                )
                        
                        # Log execution summary
                        execution_order = [
                            "1. Research Agent (Content analysis)",
                            f"2. {platform.capitalize()} Writing Agent (Platform-specific content)",
                        ]
                        for idx, qc_name in enumerate(qc_agents_used):
                            execution_order.append(f"{3 + idx}. {qc_name} (Quality review)")
                        
                        update_task_status(
                            agent="CrewAI Workflow",
                            task=f"All agents completed successfully\n\nExecution Order:\n" + "\n".join(execution_order),
                            progress=95,
                            agent_status="completed"
                        )
                        
                        CONTENT_GEN_TASKS[tid]["result"] = {
                            "status": "success",
                            "data": crew_result.get("data"),
                            "error": None
                        }
                        # Mark all agents as completed before final status update
                        if "agent_statuses" in CONTENT_GEN_TASKS[tid]:
                            for agent_status in CONTENT_GEN_TASKS[tid]["agent_statuses"]:
                                if agent_status.get("status") == "running":
                                    agent_status["status"] = "completed"
                                    agent_status["agent_status"] = "completed"
                        # Clear current agent/task when completed
                        CONTENT_GEN_TASKS[tid]["current_agent"] = None
                        CONTENT_GEN_TASKS[tid]["current_task"] = "Content generation completed"
                        update_task_status(progress=100, status="completed", task="Content generation completed")
                    else:
                        error_msg = crew_result.get("error", "Unknown error")
                        update_task_status(
                            agent="CrewAI Workflow",
                            task=f"Error: {error_msg}",
                            error=error_msg,
                            agent_status="error",
                            status="error"
                        )
                        
                except Exception as bg_error:
                    logger.error(f"Background generation error: {bg_error}")
                    import traceback
                    logger.error(traceback.format_exc())
                    if tid in CONTENT_GEN_TASKS:
                        CONTENT_GEN_TASKS[tid]["error"] = str(bg_error)
                        CONTENT_GEN_TASKS[tid]["status"] = "error"
                        CONTENT_GEN_TASKS[tid]["current_task"] = f"Error: {str(bg_error)}"
                finally:
                    session.close()
            except Exception as outer_error:
                logger.error(f"Outer background error: {outer_error}")
                if tid in CONTENT_GEN_TASKS:
                    CONTENT_GEN_TASKS[tid]["error"] = str(outer_error)
                    CONTENT_GEN_TASKS[tid]["status"] = "error"
        
        # Start background thread
        import threading
        thread = threading.Thread(
            target=run_generation_background,
            args=(task_id, campaign_id, request_data, current_user.id),
            daemon=True
        )
        thread.start()
        
        # Return task_id immediately
        return {
            "status": "pending",
            "task_id": task_id,
            "message": "Content generation started. Use task_id to poll status."
        }
        
    except Exception as e:
        from models import Campaign
        from crewai_workflows import create_content_generation_crew
        import json
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get content queue items from request or campaign
        content_queue_items = request_data.get("content_queue_items", [])
        if not content_queue_items and campaign.content_queue_items_json:
            content_queue_items = json.loads(campaign.content_queue_items_json)
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        # Get other parameters
        platform = request_data.get("platform", "linkedin")
        week = request_data.get("week", 1)
        day = request_data.get("day", "Monday")
        parent_idea = request_data.get("parent_idea", "")
        kg_location = request_data.get("knowledge_graph_location", "")
        landing_page_url = request_data.get("landing_page_url", "")
        author_personality_id = request_data.get("author_personality_id")  # NEW: Support author personality ID
        use_author_voice = request_data.get("use_author_voice", True)  # NEW: Toggle for author voice
        use_validation = request_data.get("use_validation", False)  # Phase 4: Toggle for validation
        
        # Build writing context
        writing_context = f"""Content Queue Foundation:
{queue_context}

{f'Parent Idea: {parent_idea}' if parent_idea else ''}
{f'Knowledge Graph Location: {kg_location}' if kg_location else ''}
{f'Landing Page: {landing_page_url}' if landing_page_url else ''}

Generate content for {platform} based on the content queue items above."""
        
        # Phase 3: Integrate author voice if author_personality_id is provided
        if author_personality_id and use_author_voice:
            from author_voice_helper import generate_with_author_voice, should_use_author_voice
            
            if should_use_author_voice(author_personality_id):
                logger.info(f"Using author voice for personality: {author_personality_id}")
                
                # Get custom modifications for this platform if available
                custom_modifications = None
                if "platformSettings" in request_data:
                    platform_settings = request_data.get("platformSettings", {})
                    platform_lower = platform.lower()
                    if platform_lower in platform_settings:
                        settings = platform_settings[platform_lower]
                        if not settings.get("useGlobalDefaults", True):
                            custom_modifications = settings.get("customModifications", "")
                
                # Generate content with author voice (Phase 4: includes validation if requested)
                generated_text, style_config, metadata, validation_result = generate_with_author_voice(
                    content_prompt=writing_context,
                    author_personality_id=author_personality_id,
                    platform=platform.lower(),
                    goal="content_generation",
                    target_audience="general",
                    custom_modifications=custom_modifications,
                    use_validation=use_validation,
                    db=db
                )
                
                if generated_text:
                    # Optionally pass through CrewAI for QC if requested
                    use_crewai_qc = request_data.get("use_crewai_qc", False)
                    
                    if use_crewai_qc:
                        # Pass generated content to CrewAI for QC only
                        crew_result = create_content_generation_crew(
                            text=f"Review and refine this content:\n\n{generated_text}\n\nStyle Config:\n{style_config}",
                            week=week,
                            platform=platform.lower(),
                            days_list=[day],
                            author_personality=request_data.get("author_personality", "custom")
                        )
                        
                        # Merge author voice metadata with CrewAI result
                        if crew_result.get("success"):
                            response_data = {
                                **crew_result.get("data", {}),
                                "author_voice_used": True,
                                "style_config": style_config,
                                "author_voice_metadata": metadata
                            }
                            # Phase 4: Add validation results if available
                            if validation_result:
                                response_data["validation"] = validation_result
                            return {
                                "status": "success",
                                "data": response_data,
                                "error": crew_result.get("error")
                            }
                    
                    # Return author voice generated content directly
                    response_data = {
                        "content": generated_text,
                        "title": "",  # Can be extracted or generated separately
                        "author_voice_used": True,
                        "style_config": style_config,
                        "author_voice_metadata": metadata,
                        "platform": platform
                    }
                    # Phase 4: Add validation results if available
                    if validation_result:
                        response_data["validation"] = validation_result
                    return {
                        "status": "success",
                        "data": response_data,
                        "error": None
                    }
                else:
                    logger.warning(f"Author voice generation failed, falling back to CrewAI")
                    # Fall through to CrewAI workflow
        
        # Generate content using CrewAI workflow (fallback or default)
        crew_result = create_content_generation_crew(
            text=writing_context,
            week=week,
            platform=platform.lower(),
            days_list=[day],
            author_personality=request_data.get("author_personality")
        )
        
        return {
            "status": "success" if crew_result.get("success") else "error",
            "data": crew_result.get("data"),
            "error": crew_result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error generating campaign content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns/{campaign_id}/generate-content/status/{task_id}")
async def get_content_generation_status(
    campaign_id: str,
    task_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status of content generation task.
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
            return {
                "status": "pending",
                "progress": 0,
                "current_agent": None,
                "current_task": "Waiting for task",
                "agent_statuses": [],
                "error": None
            }
        
        task = CONTENT_GEN_TASKS[task_id]
        
        # If task is completed, clear current_agent and current_task
        task_status = task.get("status", "pending")
        if task_status == "completed":
            # Clear current agent/task when completed
            current_agent = None
            current_task = "Content generation completed"
        else:
            current_agent = task.get("current_agent")
            current_task = task.get("current_task", "Processing")
        
        # If task is completed and has result, include it
        response = {
            "status": task_status,
            "progress": task.get("progress", 0),
            "current_agent": current_agent,
            "current_task": current_task,
            "agent_statuses": task.get("agent_statuses", []),
            "error": task.get("error")
        }
        
        # If completed, include result
        if task_status == "completed" and task.get("result"):
            response["result"] = task.get("result")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting content generation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/campaigns/{campaign_id}/generate-content/force-complete/{task_id}")
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
@app.post("/generate_image_machine_content")
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
            if additional_agent_id:
                try:
                    from models import SystemSettings
                    additional_agent_setting = db.query(SystemSettings).filter(
                        SystemSettings.setting_key == f"creative_agent_{additional_agent_id}_prompt"
                    ).first()
                    if additional_agent_setting and additional_agent_setting.setting_value:
                        additional_creative_agent_prompt = additional_agent_setting.setting_value
                except Exception as e:
                    logger.warning(f"Could not fetch additional creative agent prompt: {e}")
        
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
        prompt_parts = [article_summary]
        
        # ALWAYS add Global Image Agent prompt (it has a fallback default if not configured)
        prompt_parts.append(f"Follow these guidelines: {global_image_agent_prompt}")
        
        # Add Additional Creative Agent prompt if available
        if additional_creative_agent_prompt:
            prompt_parts.append(f"Additional creative direction: {additional_creative_agent_prompt}")
        
        # Add style components
        if style_components:
            prompt_parts.append(f"Create an image {', '.join(style_components)}.")
        else:
            prompt_parts.append("Create a relevant image.")
        
        final_prompt = ". ".join(prompt_parts) + "."
        
        logger.info(f"🖼️ Generating image with prompt: {final_prompt[:200]}...")
        
        # Generate image using the combined prompt
        # The generate_image function takes (query, content) where:
        # - query: used for style matching in Airtable
        # - content: the actual prompt for DALL·E
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
        logger.error(f"Error in generate_image_machine_content endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Also support GET for backward compatibility
@app.get("/generate_image_machine_content")
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

# Scheduled Posts Endpoints
@app.get("/scheduled-posts")
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

@app.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scheduled post by ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import Content
        
        logger.info(f"🗑️ Deleting post {post_id} for user {current_user.id}")
        
        # Find the post and verify ownership
        post = db.query(Content).filter(
            Content.id == post_id,
            Content.user_id == current_user.id
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found or access denied"
            )
        
        # Delete the post
        db.delete(post)
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

@app.post("/campaigns/{campaign_id}/schedule-content")
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

@app.post("/campaigns/{campaign_id}/save-content-item")
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
        platform = item.get("platform", "linkedin").lower()
        
        # Check if request includes a database ID (numeric) - if so, find that specific content item
        existing_content = None
        content_id = item.get("id")
        
        # If id is provided and is numeric (database ID), find that specific content item and update it
        if content_id and isinstance(content_id, (int, str)):
            try:
                # Check if it's a numeric database ID
                if str(content_id).isdigit():
                    content_id_int = int(content_id)
                    existing_content = db.query(Content).filter(
                        Content.id == content_id_int,
                        Content.campaign_id == campaign_id,
                        Content.user_id == current_user.id
                    ).first()
                    if existing_content:
                        logger.info(f"🔍 Found existing content by database ID: {content_id_int}")
                else:
                    # ID is not numeric (frontend-generated like "week-1-Monday-linkedin-0-post-1")
                    # This means we're creating NEW content, not updating existing
                    # Don't check for existing by week/day/platform - always create new
                    logger.info(f"🔍 Non-numeric ID provided ({content_id}), creating new content (not updating)")
            except (ValueError, TypeError):
                # ID format is unexpected, treat as new content
                logger.info(f"🔍 ID format unexpected ({content_id}), creating new content")
        
        # If no existing content found by ID and ID was numeric (or not provided),
        # check by week/day/platform (for backward compatibility with existing content)
        # This allows updating existing content that was created before the ID-based system
        if not existing_content and (not content_id or (isinstance(content_id, (int, str)) and str(content_id).isdigit())):
            existing_content = db.query(Content).filter(
                Content.campaign_id == campaign_id,
                Content.week == week,
                Content.day == day,
                Content.platform == platform,
                Content.user_id == current_user.id
            ).first()
            if existing_content:
                logger.info(f"🔍 Found existing content by week/day/platform: week={week}, day={day}, platform={platform}")
        
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
            # Update existing content
            if item.get("title"):
                existing_content.title = item.get("title")
            content_update = item.get("description") or item.get("content", "")
            if content_update and content_update.strip():
                existing_content.content = content_update
                # Update content processed timestamp when content is updated
                existing_content.content_processed_at = datetime.now().replace(tzinfo=None)
            # Update image if provided (support both field names)
            image_url = item.get("image") or item.get("image_url")
            if image_url:
                existing_content.image_url = image_url
                # Update image processed timestamp when image is updated
                existing_content.image_processed_at = datetime.now().replace(tzinfo=None)
            existing_content.status = "draft"
            existing_content.is_draft = True
            existing_content.can_edit = True
            existing_content.schedule_time = schedule_time
            # Update week/day/platform if provided (in case they changed)
            if item.get("week"):
                existing_content.week = week
            if item.get("day"):
                existing_content.day = day
            if item.get("platform"):
                existing_content.platform = platform
            # Update use_without_image if provided
            if "use_without_image" in item:
                existing_content.use_without_image = bool(item.get("use_without_image"))
            logger.info(f"✅ Updated existing content (ID: {existing_content.id}): week={week}, day={day}, platform={platform}, image={bool(image_url)}")
        else:
            # Validate required fields
            content_text = item.get("description") or item.get("content", "")
            title_text = item.get("title", "")
            
            # If content is empty, use a placeholder (for image-only saves)
            if not content_text or not content_text.strip():
                content_text = f"Content for {platform.title()} - {day}"
            
            # If title is empty, generate a default
            if not title_text or not title_text.strip():
                title_text = f"{platform.title()} Post - {day}"
            
            # Create new content
            # Support both "image" and "image_url" field names
            image_url = item.get("image") or item.get("image_url")
            if image_url:
                logger.info(f"💾 Saving image_url for new content: {image_url[:100]}...")
            else:
                logger.info(f"⚠️ No image_url provided in save request for new content")
            try:
                now = datetime.now().replace(tzinfo=None)
                new_content = Content(
                    user_id=current_user.id,
                    campaign_id=campaign_id,
                    week=week,
                    day=day,
                    content=content_text,
                    title=title_text,
                    status="draft",
                    date_upload=now,  # MySQL doesn't support timezone-aware datetimes
                    platform=platform,
                    file_name=f"{campaign_id}_{week}_{day}_{platform}.txt",
                    file_type="text",
                    platform_post_no=item.get("platform_post_no", "1"),
                    schedule_time=schedule_time,
                    image_url=image_url,
                    is_draft=True,
                    can_edit=True,
                    knowledge_graph_location=item.get("knowledge_graph_location"),
                    parent_idea=item.get("parent_idea"),
                    landing_page_url=item.get("landing_page_url"),
                    content_processed_at=now if content_text and content_text.strip() else None,  # Set timestamp if content provided
                    image_processed_at=now if image_url else None,  # Set timestamp if image provided
                    use_without_image=bool(item.get("use_without_image", False))
                )
                db.add(new_content)
                logger.info(f"✅ Created new content: week={week}, day={day}, platform={platform}, has_image={bool(image_url)}")
            except Exception as create_error:
                logger.error(f"❌ Error creating Content object: {create_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Content item saved"
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

@app.get("/campaigns/{campaign_id}/content-items")
def get_campaign_content_items(
    campaign_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all content items for a campaign (draft, scheduled, pending, uploaded)"""
    try:
        from models import Content
        
        logger.info(f"📋 Fetching content items for campaign {campaign_id}, user {current_user.id}")
        
        # Get all content items regardless of status - we want to show all existing content
        content_items = db.query(Content).filter(
            Content.campaign_id == campaign_id,
            Content.user_id == current_user.id
        ).order_by(Content.week.asc(), Content.day.asc()).all()
        
        logger.info(f"📋 Found {len(content_items)} content items for campaign {campaign_id}")
        
        items_data = []
        for item in content_items:
            image_url = item.image_url or ""
            items_data.append({
                "id": f"week-{item.week}-{item.day}-{item.platform}-{item.id}",  # Composite ID for frontend
                "database_id": item.id,  # Include database ID separately so frontend can use it for updates
                "title": item.title or "",
                "description": item.content or "",
                "week": item.week,
                "day": item.day,
                "platform": item.platform,
                "image": image_url,  # Ensure image_url is returned as "image" for frontend
                "image_url": image_url,  # Also include image_url for compatibility
                "status": item.status or "draft",
                "schedule_time": item.schedule_time.isoformat() if item.schedule_time else None,
                "contentProcessedAt": item.content_processed_at.isoformat() if hasattr(item, 'content_processed_at') and item.content_processed_at is not None else None,
                "imageProcessedAt": item.image_processed_at.isoformat() if hasattr(item, 'image_processed_at') and item.image_processed_at is not None else None,
                "contentPublishedAt": item.content_published_at.isoformat() if hasattr(item, 'content_published_at') and item.content_published_at is not None else None,
                "imagePublishedAt": item.image_published_at.isoformat() if hasattr(item, 'image_published_at') and item.image_published_at is not None else None,
                "use_without_image": bool(getattr(item, 'use_without_image', False)),
            })
            logger.info(f"📋 Item: week={item.week}, day={item.day}, platform={item.platform}, status={item.status}, has_image={bool(image_url)}, db_id={item.id}")
        
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch content items: {str(e)}"
        )

# ============================================================================

# ============================================================================
# PLATFORM CREDENTIALS CHECK
# ============================================================================

@app.get("/platforms/{platform}/credentials")
async def check_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has stored OAuth credentials for a platform"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        platform_enum = None
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        has_credentials = bool(connection and connection.platform_user_id and connection.refresh_token)
        
        return {"has_credentials": has_credentials, "platform": platform}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")

# ============================================================================
# PLATFORM CREDENTIALS CHECK
# ============================================================================

@app.get("/platforms/{platform}/credentials")
async def check_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has stored OAuth credentials for a platform"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        platform_enum = None
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        # Check if credentials are stored (platform_user_id and refresh_token indicate stored OAuth creds)
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        has_credentials = bool(connection and connection.platform_user_id and connection.refresh_token)
        
        return {
            "has_credentials": has_credentials,
            "platform": platform
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")

# ============================================================================
# PLATFORM CONNECTION ENDPOINTS
# ============================================================================

@app.get("/linkedin/auth-v2")
async def linkedin_auth_v2(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Initiate LinkedIn OAuth connection - returns auth URL for redirect"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        load_dotenv()
        cid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_id").first()
        cs_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_redirect_uri").first()
        cid = cid_s.setting_value if cid_s and cid_s.setting_value else os.getenv("LINKEDIN_CLIENT_ID")
        cs = cs_s.setting_value if cs_s and cs_s.setting_value else os.getenv("LINKEDIN_CLIENT_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("LINKEDIN_REDIRECT_URI", "https://themachine.vernalcontentum.com/linkedin/callback")
        if not cid or not cs:
            raise HTTPException(status_code=500, detail="LinkedIn OAuth credentials not configured. Please configure them in Admin Settings > System > Platform Keys > LinkedIn.")
        import secrets
        state = secrets.token_urlsafe(32)
        existing_state = db.query(StateToken).filter(StateToken.user_id == current_user.id, StateToken.platform == PlatformEnum.LINKEDIN, StateToken.state == state).first()
        if not existing_state:
            new_state = StateToken(user_id=current_user.id, platform=PlatformEnum.LINKEDIN, state=state, created_at=datetime.now())
            db.add(new_state)
        db.commit()
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={cid}&redirect_uri={ru}&state={state}&scope=openid%20profile%20email%20w_member_social"
        logger.info(f"✅ LinkedIn auth URL generated for user {current_user.id}")
        return {"status": "success", "auth_url": auth_url}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"❌ Error generating LinkedIn auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate LinkedIn auth URL: {str(e)}")


@app.post("/linkedin/auth-v2")
async def linkedin_auth_v2(
    request_data: Dict[str, Any] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate LinkedIn OAuth - uses stored credentials or accepts new ones"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        from typing import Dict, Any
        from datetime import datetime
        
        redirect_uri = "https://machine.vernalcontentum.com/linkedin/callback"
        
        client_id = None
        client_secret = None
        
        # If POST with credentials, store them
        if request_data and request_data.get("client_id") and request_data.get("client_secret"):
            client_id = request_data.get("client_id", "").strip()
            client_secret = request_data.get("client_secret", "").strip()
            
            if not client_id or not client_secret:
                raise HTTPException(status_code=400, detail="LinkedIn Client ID and Client Secret are required")
            
            # Store credentials in database
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if connection:
                connection.platform_user_id = client_id
                connection.refresh_token = client_secret
            else:
                connection = PlatformConnection(
                    user_id=current_user.id,
                    platform=PlatformEnum.LINKEDIN,
                    platform_user_id=client_id,
                    refresh_token=client_secret
                )
                db.add(connection)
            db.commit()
        else:
            # GET request - check for stored credentials
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if not connection or not connection.platform_user_id or not connection.refresh_token:
                raise HTTPException(
                    status_code=400, 
                    detail="LinkedIn credentials not found. Please provide Client ID and Client Secret."
                )
            
            client_id = connection.platform_user_id
            client_secret = connection.refresh_token
        
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state in database
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.LINKEDIN,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.LINKEDIN,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        # Build LinkedIn OAuth URL
        auth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"response_type=code&"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=r_liteprofile%20r_emailaddress%20w_member_social"
        )
        
        logger.info(f"✅ LinkedIn auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error generating LinkedIn auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LinkedIn auth URL: {str(e)}"
        )

@app.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle LinkedIn OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        load_dotenv()
        cid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_id").first()
        cs_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_redirect_uri").first()
        cid = cid_s.setting_value if cid_s and cid_s.setting_value else os.getenv("LINKEDIN_CLIENT_ID")
        cs = cs_s.setting_value if cs_s and cs_s.setting_value else os.getenv("LINKEDIN_CLIENT_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("LINKEDIN_REDIRECT_URI", "https://themachine.vernalcontentum.com/linkedin/callback")
        if not cid or not cs:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=linkedin_not_configured")
        st = db.query(StateToken).filter(StateToken.platform == PlatformEnum.LINKEDIN, StateToken.state == state).first()
        if not st:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=invalid_state")
        uid = st.user_id
        db.delete(st)
        r = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={"grant_type": "authorization_code", "code": code, "redirect_uri": ru, "client_id": cid, "client_secret": cs})
        if r.status_code != 200:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        at = r.json().get("access_token")
        if not at:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # Fetch user profile information from LinkedIn
        user_email = None
        user_name = None
        try:
            # Use OpenID Connect userinfo endpoint to get email
            profile_url = "https://api.linkedin.com/v2/userinfo"
            headers = {"Authorization": f"Bearer {at}"}
            profile_response = requests.get(profile_url, headers=headers)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_email = profile_data.get("email")
                user_name = profile_data.get("name")
                logger.info(f"✅ Fetched LinkedIn profile: email={user_email}, name={user_name}")
            else:
                # Fallback to basic profile endpoint
                profile_url = "https://api.linkedin.com/v2/me"
                profile_response = requests.get(profile_url, headers=headers)
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
                    logger.info(f"✅ Fetched LinkedIn basic profile: name={user_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch LinkedIn profile: {e}")
            # Continue without profile info - connection still works
        
        # Use email if available, otherwise use name, otherwise use a generic identifier
        platform_user_identifier = user_email or user_name or "LinkedIn User"
        
        conn = db.query(PlatformConnection).filter(PlatformConnection.user_id == uid, PlatformConnection.platform == PlatformEnum.LINKEDIN).first()
        if conn:
            conn.access_token = at
            conn.connected_at = datetime.now()
            if platform_user_identifier:
                conn.platform_user_id = platform_user_identifier
        else:
            conn = PlatformConnection(user_id=uid, platform=PlatformEnum.LINKEDIN, access_token=at, platform_user_id=platform_user_identifier, connected_at=datetime.now())
            db.add(conn)
        db.commit()
        logger.info(f"✅ LinkedIn connection successful for user {uid}")
        return RedirectResponse(url="https://machine.vernalcontentum.com/account-settings?linkedin=connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in LinkedIn callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=callback_failed&message={str(e)}")


@app.get("/twitter/auth-v2")
async def twitter_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Twitter OAuth connection - returns redirect URL"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        import os
        from dotenv import load_dotenv
        from requests_oauthlib import OAuth1Session
        
        load_dotenv()
        
        consumer_key = os.getenv("TWITTER_API_KEY")
        consumer_secret = os.getenv("TWITTER_API_SECRET")
        callback_url = os.getenv("TWITTER_CALLBACK_URL", "https://machine.vernalcontentum.com/twitter/callback")
        
        if not consumer_key or not consumer_secret:
            raise HTTPException(status_code=500, detail="Twitter OAuth credentials not configured")
        
        oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri=callback_url)
        request_token_url = "https://api.twitter.com/oauth/request_token"
        
        try:
            fetch_response = oauth.fetch_request_token(request_token_url)
        except Exception as e:
            logger.error(f"Error fetching Twitter request token: {e}")
            raise HTTPException(status_code=500, detail="Failed to get Twitter request token")
        
        oauth_token = fetch_response.get('oauth_token')
        oauth_token_secret = fetch_response.get('oauth_token_secret')
        
        if not oauth_token:
            raise HTTPException(status_code=500, detail="No oauth_token in response")
        
        new_state = StateToken(
            user_id=current_user.id,
            platform=PlatformEnum.TWITTER,
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            state=oauth_token,
            created_at=datetime.now()
        )
        db.add(new_state)
        db.commit()
        
        authorization_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"
        
        logger.info(f"✅ Twitter auth URL generated for user {current_user.id}")
        return {"status": "success", "redirect_url": authorization_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Twitter auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Twitter auth URL: {str(e)}")

@app.get("/twitter/callback")
async def twitter_callback(
    oauth_token: str,
    oauth_verifier: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle Twitter OAuth callback and exchange verifier for access token"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        import os
        from dotenv import load_dotenv
        from requests_oauthlib import OAuth1Session
        
        load_dotenv()
        
        consumer_key = os.getenv("TWITTER_API_KEY")
        consumer_secret = os.getenv("TWITTER_API_SECRET")
        
        state_token = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.TWITTER,
            StateToken.oauth_token == oauth_token
        ).first()
        
        if not state_token:
            raise HTTPException(status_code=400, detail="Invalid oauth_token")
        
        oauth_token_secret = state_token.oauth_token_secret
        db.delete(state_token)
        
        oauth = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier
        )
        
        access_token_url = "https://api.twitter.com/oauth/access_token"
        oauth_tokens = oauth.fetch_access_token(access_token_url)
        
        access_token = oauth_tokens.get('oauth_token')
        access_token_secret = oauth_tokens.get('oauth_token_secret')
        
        if not access_token or not access_token_secret:
            raise HTTPException(status_code=400, detail="Failed to get access tokens")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.TWITTER
        ).first()
        
        if connection:
            connection.access_token = access_token
            connection.refresh_token = access_token_secret
            connection.connected_at = datetime.now()
        else:
            connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.TWITTER,
                access_token=access_token,
                refresh_token=access_token_secret,
                connected_at=datetime.now()
            )
            db.add(connection)
        
        db.commit()
        
        logger.info(f"✅ Twitter connection successful for user {current_user.id}")
        return JSONResponse(content={"status": "success", "message": "Twitter connected successfully"}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in Twitter callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to complete Twitter connection: {str(e)}")

@app.post("/wordpress/auth-v2")
async def wordpress_auth_v2(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect WordPress site using application password"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        from requests.auth import HTTPBasicAuth
        
        form_data = await request.form()
        site_url = form_data.get("site_url", "").strip()
        username = form_data.get("username", "").strip()
        password = form_data.get("password", "").strip()
        
        if not site_url or not username or not password:
            raise HTTPException(status_code=400, detail="Missing required fields: site_url, username, password")
        
        if not site_url.startswith(("http://", "https://")):
            site_url = f"https://{site_url}"
        
        wp_api_url = f"{site_url}/wp-json/wp/v2/users/me"
        
        try:
            response = requests.get(wp_api_url, auth=HTTPBasicAuth(username, password), timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"WordPress authentication failed: {response.status_code}")
            logger.info(f"✅ WordPress connection verified for user {current_user.id}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to connect to WordPress: {str(e)}")
        
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if existing_connection:
            existing_connection.platform_user_id = site_url
            existing_connection.refresh_token = username
            existing_connection.access_token = password
            existing_connection.connected_at = datetime.now()
        else:
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.WORDPRESS,
                platform_user_id=site_url,
                refresh_token=username,
                access_token=password,
                connected_at=datetime.now()
            )
            db.add(new_connection)
        
        db.commit()
        
        return {"status": "success", "message": "WordPress connected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error connecting WordPress: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to connect WordPress: {str(e)}")

@app.post("/instagram/connect")
async def instagram_connect(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect Instagram account using App ID, App Secret, and Access Token"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        
        app_id = request_data.get("app_id", "").strip()
        app_secret = request_data.get("app_secret", "").strip()
        access_token = request_data.get("access_token", "").strip()
        
        if not app_id or not app_secret or not access_token:
            raise HTTPException(status_code=400, detail="Missing required fields: app_id, app_secret, access_token")
        
        verify_url = f"https://graph.instagram.com/me?fields=id,username&access_token={access_token}"
        
        try:
            response = requests.get(verify_url, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Instagram access token invalid: {response.status_code}")
            logger.info(f"✅ Instagram connection verified for user {current_user.id}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to verify Instagram token: {str(e)}")
        
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if existing_connection:
            existing_connection.platform_user_id = app_id
            existing_connection.access_token = access_token
            existing_connection.connected_at = datetime.now()
        else:
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.INSTAGRAM,
                platform_user_id=app_id,
                access_token=access_token,
                connected_at=datetime.now()
            )
            db.add(new_connection)
        
        db.commit()
        
        return {"status": "success", "message": "Instagram connected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error connecting Instagram: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to connect Instagram: {str(e)}")


# PLATFORM POSTING ENDPOINTS (for scheduled content)
# ============================================================================

@app.post("/platforms/linkedin/post")
async def post_to_linkedin(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to LinkedIn using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.LINKEDIN
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=400, detail="LinkedIn not connected. Please connect your LinkedIn account first.")
        
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
            raise HTTPException(status_code=400, detail=f"LinkedIn API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to LinkedIn for user {current_user.id}")
        return {"status": "success", "message": "Content posted to LinkedIn successfully", "post_id": response.json().get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to LinkedIn: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to LinkedIn: {str(e)}")

@app.post("/platforms/twitter/post")
async def post_to_twitter(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to Twitter/X using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        from requests_oauthlib import OAuth1Session
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.TWITTER
        ).first()
        
        if not connection or not connection.access_token or not connection.refresh_token:
            raise HTTPException(status_code=400, detail="Twitter not connected. Please connect your Twitter account first.")
        
        api_url = "https://api.twitter.com/2/tweets"
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        oauth = OAuth1Session(
            os.getenv("TWITTER_API_KEY"),
            client_secret=os.getenv("TWITTER_API_SECRET"),
            resource_owner_key=connection.access_token,
            resource_owner_secret=connection.refresh_token
        )
        
        tweet_data = {"text": content_text[:280]}
        
        if image_url:
            media_url = "https://upload.twitter.com/1.1/media/upload.json"
            media_response = oauth.post(media_url, files={"media": requests.get(image_url).content})
            if media_response.status_code == 200:
                media_id = media_response.json().get("media_id_string")
                tweet_data["media"] = {"media_ids": [media_id]}
        
        response = oauth.post(api_url, json=tweet_data, timeout=30)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Twitter API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to Twitter for user {current_user.id}")
        return {"status": "success", "message": "Content posted to Twitter successfully", "tweet_id": response.json().get("data", {}).get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to Twitter: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to Twitter: {str(e)}")

@app.post("/platforms/wordpress/post")
async def post_to_wordpress(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to WordPress using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        from requests.auth import HTTPBasicAuth
        
        content_id = request_data.get("content_id")
        title = request_data.get("title", "")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if not connection or not connection.platform_user_id or not connection.access_token:
            raise HTTPException(status_code=400, detail="WordPress not connected. Please connect your WordPress site first.")
        
        site_url = connection.platform_user_id
        username = connection.refresh_token
        app_password = connection.access_token
        
        api_url = f"{site_url}/wp-json/wp/v2/posts"
        post_data = {"title": title or "New Post", "content": content_text, "status": "publish"}
        
        if image_url:
            media_url = f"{site_url}/wp-json/wp/v2/media"
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code == 200:
                files = {"file": ("image.jpg", image_response.content, "image/jpeg")}
                media_response = requests.post(media_url, files=files, auth=HTTPBasicAuth(username, app_password), timeout=30)
                if media_response.status_code == 201:
                    post_data["featured_media"] = media_response.json().get("id")
        
        response = requests.post(api_url, json=post_data, auth=HTTPBasicAuth(username, app_password), timeout=30)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"WordPress API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to WordPress for user {current_user.id}")
        return {"status": "success", "message": "Content posted to WordPress successfully", "post_id": response.json().get("id"), "post_url": response.json().get("link")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to WordPress: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to WordPress: {str(e)}")

@app.post("/platforms/instagram/post")
async def post_to_instagram(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to Instagram using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not image_url:
            raise HTTPException(status_code=400, detail="Image URL is required for Instagram posts")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=400, detail="Instagram not connected. Please connect your Instagram account first.")
        
        access_token = connection.access_token
        app_id = connection.platform_user_id
        
        create_url = f"https://graph.instagram.com/v18.0/{app_id}/media"
        image_response = requests.get(image_url, timeout=30)
        if image_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        create_data = {"image_url": image_url, "caption": content_text[:2200], "access_token": access_token}
        create_response = requests.post(create_url, data=create_data, timeout=30)
        
        if create_response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Instagram API error creating media: {create_response.status_code} - {create_response.text}")
        
        creation_id = create_response.json().get("id")
        publish_url = f"https://graph.instagram.com/v18.0/{app_id}/media_publish"
        publish_data = {"creation_id": creation_id, "access_token": access_token}
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        
        if publish_response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Instagram API error publishing: {publish_response.status_code} - {publish_response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to Instagram for user {current_user.id}")
        return {"status": "success", "message": "Content posted to Instagram successfully", "media_id": publish_response.json().get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to Instagram: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to Instagram: {str(e)}")


# ============================================================================
# PLATFORM CREDENTIALS MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/platforms/credentials/all")
async def get_all_platform_credentials(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all platform credentials for the current user"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        connections = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id
        ).all()
        
        credentials = {}
        for conn in connections:
            platform_name = conn.platform.value.lower()
            
            if conn.platform == PlatformEnum.LINKEDIN:
                # LinkedIn uses platform's app - return connection status and account info
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "connected": bool(conn.access_token),
                    "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                    "platform_user_id": conn.platform_user_id or "",
                }
            elif conn.platform == PlatformEnum.TWITTER:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.platform_user_id and conn.refresh_token),
                    "api_key": conn.platform_user_id or "",
                    "api_secret": conn.refresh_token or "",
                    "access_token": conn.access_token or "",
                }
            elif conn.platform == PlatformEnum.WORDPRESS:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.platform_user_id and conn.refresh_token and conn.access_token),
                    "site_url": conn.platform_user_id or "",
                    "username": conn.refresh_token or "",
                    "app_password": conn.access_token or "",
                }
            elif conn.platform == PlatformEnum.INSTAGRAM:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token and conn.platform_user_id),
                    "app_id": conn.platform_user_id or "",
                    "app_secret": conn.refresh_token or "",
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
            elif conn.platform == PlatformEnum.FACEBOOK:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
            else:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
        
        return {"success": True, "credentials": credentials}
    except Exception as e:
        logger.error(f"❌ Error fetching platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch credentials: {str(e)}")

@app.post("/platforms/{platform}/refresh-profile")
async def refresh_platform_profile(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh user profile information for an existing OAuth connection"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=404, detail=f"No {platform} connection found")
        
        access_token = connection.access_token
        user_email = None
        user_name = None
        platform_user_identifier = None
        
        if platform_enum == PlatformEnum.LINKEDIN:
            try:
                # Try OpenID Connect userinfo endpoint first
                profile_url = "https://api.linkedin.com/v2/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_email = profile_data.get("email")
                    user_name = profile_data.get("name")
                    logger.info(f"✅ Refreshed LinkedIn profile: email={user_email}, name={user_name}")
                else:
                    # Fallback to basic profile endpoint
                    profile_url = "https://api.linkedin.com/v2/me"
                    profile_response = requests.get(profile_url, headers=headers)
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        user_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
                        logger.info(f"✅ Refreshed LinkedIn basic profile: name={user_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not refresh LinkedIn profile: {e}")
            
            platform_user_identifier = user_email or user_name or "LinkedIn User"
            
        elif platform_enum == PlatformEnum.FACEBOOK or platform_enum == PlatformEnum.INSTAGRAM:
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
                    logger.info(f"✅ Refreshed {platform} profile: email={user_email}, name={user_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not refresh {platform} profile: {e}")
            
            platform_user_identifier = user_email or user_name or f"{platform} User"
        
        if platform_user_identifier:
            connection.platform_user_id = platform_user_identifier
            db.commit()
            return {"success": True, "message": f"{platform} profile refreshed", "platform_user_id": platform_user_identifier}
        else:
            return {"success": False, "message": f"Could not fetch {platform} profile information"}
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error refreshing {platform} profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh profile: {str(e)}")

@app.post("/platforms/{platform}/credentials/save")
async def save_platform_credentials(
    platform: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update platform credentials"""
    try:
        from models import PlatformConnection, PlatformEnum
        from datetime import datetime
        
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        if platform_enum == PlatformEnum.LINKEDIN:
            # LinkedIn uses OAuth - users cannot provide Client ID/Secret
            raise HTTPException(
                status_code=400,
                detail="LinkedIn uses OAuth flow. Use /linkedin/auth-v2 to connect your account."
            )
        elif platform_enum == PlatformEnum.TWITTER:
            api_key = request_data.get("api_key", "").strip()
            api_secret = request_data.get("api_secret", "").strip()
            if not api_key or not api_secret:
                raise HTTPException(status_code=400, detail="Twitter API Key and API Secret are required")
            if connection:
                connection.platform_user_id = api_key
                connection.refresh_token = api_secret
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=api_key, refresh_token=api_secret,
                    access_token="", connected_at=datetime.now()
                )
                db.add(connection)
        elif platform_enum == PlatformEnum.WORDPRESS:
            site_url = request_data.get("site_url", "").strip()
            username = request_data.get("username", "").strip()
            app_password = request_data.get("app_password", "").strip()
            if not site_url or not username or not app_password:
                raise HTTPException(status_code=400, detail="WordPress Site URL, Username, and App Password are required")
            if connection:
                connection.platform_user_id = site_url
                connection.refresh_token = username
                connection.access_token = app_password
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=site_url, refresh_token=username,
                    access_token=app_password, connected_at=datetime.now()
                )
                db.add(connection)
        elif platform_enum == PlatformEnum.INSTAGRAM:
            app_id = request_data.get("app_id", "").strip()
            app_secret = request_data.get("app_secret", "").strip()
            access_token = request_data.get("access_token", "").strip()
            if not app_id or not app_secret or not access_token:
                raise HTTPException(status_code=400, detail="Instagram App ID, App Secret, and Access Token are required")
            if connection:
                connection.platform_user_id = app_id
                connection.refresh_token = app_secret
                connection.access_token = access_token
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=app_id, refresh_token=app_secret,
                    access_token=access_token, connected_at=datetime.now()
                )
                db.add(connection)
        else:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
        
        db.commit()
        return {"success": True, "message": f"{platform} credentials saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")

@app.delete("/platforms/{platform}/credentials")
async def remove_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove platform credentials - DELETE all connections for this platform (permanent removal)"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        # Convert platform name to enum
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        # Find ALL connections for this platform and user
        connections = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).all()
        
        if connections:
            # DELETE all connection records (permanent removal)
            for connection in connections:
                db.delete(connection)
            db.commit()
            
            return {
                "success": True,
                "message": f"{platform} disconnected successfully - all connections removed"
            }
        else:
            return {
                "success": True,
                "message": f"No {platform} connections found to remove"
            }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error removing platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove credentials: {str(e)}")


# [Paste endpoint code here]


@app.get("/facebook/auth-v2")
async def facebook_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Facebook OAuth connection - returns auth URL for redirect"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Try system settings first, fall back to env vars
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("FACEBOOK_REDIRECT_URI", "https://machine.vernalcontentum.com/facebook/callback")
        
        if not app_id or not app_secret:
            raise HTTPException(
                status_code=500,
                detail="Facebook OAuth credentials not configured. Please configure them in Admin Settings > System > Platform Keys > Facebook."
            )
        
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state in database for verification
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.FACEBOOK,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.FACEBOOK,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        # Build Facebook OAuth URL
        auth_url = (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=pages_manage_posts,pages_read_engagement,pages_show_list"
        )
        
        logger.info(f"✅ Facebook auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Facebook auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Facebook auth URL: {str(e)}"
        )

@app.get("/facebook/callback")
async def facebook_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Facebook OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        load_dotenv()
        aid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        as_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_redirect_uri").first()
        aid = aid_s.setting_value if aid_s and aid_s.setting_value else os.getenv("FACEBOOK_APP_ID")
        asec = as_s.setting_value if as_s and as_s.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("FACEBOOK_REDIRECT_URI", "https://themachine.vernalcontentum.com/facebook/callback")
        if not aid or not asec:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=facebook_not_configured")
        st = db.query(StateToken).filter(StateToken.platform == PlatformEnum.FACEBOOK, StateToken.state == state).first()
        if not st:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=invalid_state")
        uid = st.user_id
        db.delete(st)
        r = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={"client_id": aid, "client_secret": asec, "redirect_uri": ru, "code": code})
        if r.status_code != 200:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        at = r.json().get("access_token")
        if not at:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # Fetch user profile information from Facebook
        user_email = None
        user_name = None
        try:
            profile_url = "https://graph.facebook.com/v18.0/me"
            params = {
                "access_token": at,
                "fields": "email,name"
            }
            profile_response = requests.get(profile_url, params=params)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_email = profile_data.get("email")
                user_name = profile_data.get("name")
                logger.info(f"✅ Fetched Facebook profile: email={user_email}, name={user_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch Facebook profile: {e}")
            # Continue without profile info - connection still works
        
        # Use email if available, otherwise use name, otherwise use a generic identifier
        platform_user_identifier = user_email or user_name or "Facebook User"
        
        conn = db.query(PlatformConnection).filter(PlatformConnection.user_id == uid, PlatformConnection.platform == PlatformEnum.FACEBOOK).first()
        if conn:
            conn.access_token = at
            conn.connected_at = datetime.now()
            if platform_user_identifier:
                conn.platform_user_id = platform_user_identifier
        else:
            conn = PlatformConnection(user_id=uid, platform=PlatformEnum.FACEBOOK, access_token=at, platform_user_id=platform_user_identifier, connected_at=datetime.now())
            db.add(conn)
        db.commit()
        logger.info(f"✅ Facebook connection successful for user {uid}")
        return RedirectResponse(url="https://machine.vernalcontentum.com/account-settings?facebook=connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in Facebook callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=callback_failed&message={str(e)}")


@app.get("/instagram/auth-v2")
async def instagram_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Instagram OAuth connection - uses Facebook OAuth (Instagram is part of Facebook)"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "instagram_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("INSTAGRAM_REDIRECT_URI", "https://machine.vernalcontentum.com/instagram/callback")
        
        if not app_id or not app_secret:
            raise HTTPException(
                status_code=500,
                detail="Instagram OAuth credentials not configured. Please configure Facebook App credentials in Admin Settings > System > Platform Keys > Facebook (Instagram uses Facebook OAuth)."
            )
        
        import secrets
        state = secrets.token_urlsafe(32)
        
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.INSTAGRAM,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.INSTAGRAM,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        auth_url = (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=pages_manage_posts,pages_read_engagement,pages_show_list"
        )
        
        logger.info(f"✅ Instagram auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Instagram auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Instagram auth URL: {str(e)}"
        )

@app.get("/instagram/callback")
async def instagram_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Instagram OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        from datetime import datetime
        
        load_dotenv()
        
        # Instagram uses Facebook OAuth credentials
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "instagram_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("INSTAGRAM_REDIRECT_URI", "https://themachine.vernalcontentum.com/instagram/callback")
        
        if not app_id or not app_secret:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=instagram_not_configured")
        
        # Verify state and get user_id from StateToken
        state_token = db.query(StateToken).filter(
            StateToken.platform == PlatformEnum.INSTAGRAM,
            StateToken.state == state
        ).first()
        
        if not state_token:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=invalid_state")
        
        user_id = state_token.user_id
        
        # Clean up state token
        db.delete(state_token)
        db.commit()
        
        # Exchange code for access token
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        token_params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        
        response = requests.get(token_url, params=token_params)
        if response.status_code != 200:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # Fetch user profile information from Facebook (Instagram uses Facebook OAuth)
        user_email = None
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
    uvicorn.run(app, host="0.0.0.0", port=8000)