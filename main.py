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
from guardrails.redaction import redact_headers, redact_text, try_parse_json, redact_jsonish
from guardrails.sanitize import guard_or_raise, GuardrailsBlocked
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

# Helper function to get OpenAI API key with priority: user > global > env
def get_openai_api_key(current_user=None, db: Session = None) -> Optional[str]:
    """
    Get OpenAI API key with priority:
    1. User's personal API key (if provided and available)
    2. Global API key from system_settings table (openai_api_key)
    3. Environment variable (OPENAI_API_KEY)
    
    Args:
        current_user: Current user object (optional, for user-specific key)
        db: Database session (optional, for global key lookup)
    
    Returns:
        API key string or None if not found
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Priority 1: User's personal API key
    if current_user and hasattr(current_user, 'openai_key') and current_user.openai_key:
        user_key = current_user.openai_key.strip()
        if user_key and len(user_key) > 50:
            logger.info(f"✅ Using user's personal OpenAI API key (user_id: {current_user.id})")
            return user_key
    
    # Priority 2: Global API key from system_settings
    if db:
        try:
            from models import SystemSettings
            global_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "openai_api_key"
            ).first()
            if global_setting and global_setting.setting_value:
                global_key = global_setting.setting_value.strip()
                if global_key and len(global_key) > 50:
                    logger.info("✅ Using global OpenAI API key from system_settings")
                    return global_key
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve global API key from system_settings: {e}")
    
    # Priority 3: Environment variable
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        env_key = env_key.strip()
        if env_key and len(env_key) > 50:
            logger.info("✅ Using OpenAI API key from environment variable")
            return env_key
    
    logger.error("❌ No valid OpenAI API key found (checked: user key, global key, env var)")
    return None

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

# CORS middleware - MUST be added FIRST to handle OPTIONS preflight requests
# Middleware executes in reverse order (last added = first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Guardrails blocking exception handler - returns clean HTTP 400
@app.exception_handler(GuardrailsBlocked)
async def guardrails_blocked_handler(request: Request, exc: GuardrailsBlocked):
    """Handle GuardrailsBlocked exceptions with clean HTTP 400 response"""
    origin = request.headers.get("Origin", "")
    cors_headers = {}
    if origin in ALLOWED_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "guardrails_blocked",
            "message": str(exc),
            "matched": getattr(exc, "matched", None),
        },
        headers=cors_headers,
    )

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
    
    # Re-raise GuardrailsBlocked so the specific handler catches it (not a 500)
    if isinstance(exc, GuardrailsBlocked):
        raise exc
    
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
    logger.info(f"📥 Headers: {redact_headers(dict(request.headers))}")
    
    # Read and log body, then restore it
    try:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body_str = body_bytes.decode('utf-8')
                parsed = try_parse_json(body_str)
                if parsed is not None:
                    safe_obj = redact_jsonish(parsed)
                    safe_str = redact_text(str(safe_obj))
                else:
                    safe_str = redact_text(body_str)
                logger.info(f"📥 Body (first 500 chars): {safe_str[:500]}")
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
    from auth_api import get_current_user, verify_campaign_ownership, get_admin_user, get_plugin_user
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
# MOVED TO: app/schemas/models.py
from app.schemas.models import (
    CampaignCreate,
    CampaignUpdate,
    AuthorPersonalityCreate,
    AuthorPersonalityUpdate,
    ExtractProfileRequest,
    GenerateContentRequest,
    BrandPersonalityCreate,
    BrandPersonalityUpdate,
    ResearchAgentRequest,
    AnalyzeRequest,
    TransferCampaignRequest
)

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
# MOVED TO: app/routes/health.py
from app.routes.health import health_router
app.include_router(health_router)

# Campaign endpoints with REAL database operations (EMERGENCY_NET: Multi-tenant scoped)
# Demo campaign ID - template campaign that will be copied for each user
# MOVED TO: app/services/campaigns.py
from app.services.campaigns import DEMO_CAMPAIGN_ID, create_user_demo_campaign

# MOVED TO: app/routes/campaigns.py
from app.routes.campaigns import campaigns_router
app.include_router(campaigns_router)

# MOVED TO: app/routes/admin.py
from app.routes.admin import admin_router
app.include_router(admin_router)

# MOVED TO: app/routes/author_personalities.py
from app.routes.author_personalities import author_personalities_router
app.include_router(author_personalities_router)

# MOVED TO: app/routes/brand_personalities.py
from app.routes.brand_personalities import brand_personalities_router
app.include_router(brand_personalities_router)

# MOVED TO: app/routes/platforms.py
from app.routes.platforms import platforms_router
app.include_router(platforms_router)

# MOVED TO: app/routes/campaigns_research.py
from app.routes.campaigns_research import campaigns_research_router
app.include_router(campaigns_research_router)

# MOVED TO: app/routes/content.py
from app.routes.content import content_router
app.include_router(content_router)

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
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
        
        # Check if force_refresh is requested (admin-only feature)
        force_refresh = getattr(request_data, 'force_refresh', False)
        if force_refresh:
            # Verify user is admin before allowing force refresh
            if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
                logger.warning(f"⚠️ Non-admin user {current_user.id} attempted force refresh - denied")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Force refresh is only available to admin users"
                )
            logger.info(f"🔄 Admin user {current_user.id} requested force refresh for {agent_type} insights - clearing cache")
            # Delete existing cached insights
            existing_insights = db.query(CampaignResearchInsights).filter(
                CampaignResearchInsights.campaign_id == campaign_id,
                CampaignResearchInsights.agent_type == agent_type
            ).first()
            if existing_insights:
                db.delete(existing_insights)
                db.commit()
                logger.info(f"✅ Cleared cached {agent_type} insights for campaign {campaign_id}")
        
        # Check if insights already exist in database (cache) - skip if force_refresh was used
        if not force_refresh:
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
            openai_key = get_openai_api_key(current_user=current_user, db=db)
            if openai_key:
                topic_tool = "llm"  # Use LLM for phrase generation
                logger.info("✅ Using LLM model for topics (from system settings)")
            else:
                topic_tool = "system"  # Fallback to system model if no API key
                logger.warning("⚠️ LLM selected but OpenAI API key not found, using system model")
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
        
        # Get API key with priority: user > global > env
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            logger.error("❌ OpenAI API key not found (checked: user key, global key, env var)")
            return {"status": "error", "message": "OpenAI API key not configured. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings."}
        
        # Log first few chars for debugging (without exposing full key)
        logger.info(f"✅ OpenAI API key present (length: {len(api_key)})")
        
        # Check key length (OpenAI keys are typically 200+ characters)
        if len(api_key) < 50:
            logger.error(f"❌ API key is too short ({len(api_key)} chars). OpenAI keys should be 200+ characters.")
            return {"status": "error", "message": f"API key is too short ({len(api_key)} characters). OpenAI keys should be 200+ characters. Please check your API key configuration."}
        
        if not api_key.startswith("sk-"):
            logger.warning(f"⚠️ API key doesn't start with 'sk-' - might be invalid format")
        
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0.4, max_tokens=1000)

            # Guardrails: sanitize prompt + check for injection (raises GuardrailsBlocked if blocking enabled)
            prompt, audit = guard_or_raise(prompt, max_len=12000)

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
            content_update = item.get("description") or item.get("content", "")
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
            
            if content_update and content_update.strip():
                update_fields.append("content = :content")
                update_values["content"] = content_update
            
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
            
            if update_fields:
                update_stmt = text(f"UPDATE content SET {', '.join(update_fields)} WHERE id = :id")
                db.execute(update_stmt, update_values)
                logger.info(f"✅ Updated existing content (ID: {existing_id}): week={week}, day={day}, platform={platform_db_value}, image={bool(image_url)}")
            
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

@app.get("/campaigns/{campaign_id}/content-items")
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
    uvicorn.run(app, host="0.0.0.0", port=8000)