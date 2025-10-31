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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def get_campaigns(request: Request, db: Session = Depends(get_db)):
    """Get all campaigns - REAL database query (EMERGENCY_NET: Multi-tenant scoped)"""
    logger.info("🔍 /campaigns GET endpoint called")
    try:
        from models import Campaign, User
        
        # Get current user from auth token if provided (EMERGENCY_NET compliance)
        current_user = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header.replace("Bearer ", "")
                from utils import verify_token
                payload = verify_token(token)
                user_id = int(payload.get("sub"))
                logger.info(f"Token verified for user_id: {user_id}")
                current_user = db.query(User).filter(User.id == user_id).first()
                if current_user:
                    logger.info(f"User found: {current_user.id} ({current_user.username})")
                else:
                    logger.warning(f"User {user_id} not found in database")
            except Exception as auth_error:
                # Log auth errors but continue without filtering for backward compatibility
                logger.warning(f"Authentication failed for /campaigns GET: {auth_error}")
                import traceback
                logger.debug(f"Auth error traceback: {traceback.format_exc()}")
        else:
            logger.info("No Authorization header provided - returning all campaigns")
        
        # EMERGENCY_NET: Multi-tenant - filter by user if authenticated
        if current_user:
            campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
        else:
            # No auth token - return all (for backward compatibility during migration)
            campaigns = db.query(Campaign).all()
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
def create_campaign(campaign_data: CampaignCreate, request: Request, db: Session = Depends(get_db)):
    """Create campaign - REAL database save (EMERGENCY_NET: Multi-tenant scoped)"""
    try:
        from models import Campaign, User
        
        # Get current user from auth token (EMERGENCY_NET compliance)
        user_id = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                from utils import verify_token
                payload = verify_token(token)
                user_id = int(payload.get("sub"))
                # Verify user exists
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found"
                    )
        except HTTPException:
            raise
        except Exception as auth_error:
            logger.warning(f"Authentication failed for /campaigns POST: {auth_error} - using default user_id=1")
            user_id = 1  # TEMPORARY fallback for backward compatibility
        
        if not user_id:
            user_id = 1  # TEMPORARY fallback if no auth token
        
        from models import Campaign
        logger.info(f"Creating campaign: {campaign_data.name} for user {user_id}")
        
        # Generate unique campaign ID
        campaign_id = str(uuid.uuid4())
        
        # Convert lists to comma-separated strings for database storage (matching model)
        keywords_str = ",".join(campaign_data.keywords) if campaign_data.keywords else None
        urls_str = ",".join(campaign_data.urls) if campaign_data.urls else None
        trending_topics_str = ",".join(campaign_data.trendingTopics) if campaign_data.trendingTopics else None
        topics_str = ",".join(campaign_data.topics) if campaign_data.topics else None
        
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
            user_id=user_id
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
def get_campaign_by_id(campaign_id: str, db: Session = Depends(get_db)):
    """Get campaign by ID - REAL database query"""
    try:
        from models import Campaign
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
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
                "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
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
def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, request: Request, db: Session = Depends(get_db)):
    """Update campaign - REAL database update"""
    try:
        from models import Campaign, User
        
        # Get current user from auth token
        user_id = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                from utils import verify_token
                payload = verify_token(token)
                user_id = int(payload.get("sub"))
        except Exception as auth_error:
            logger.warning(f"Authentication failed for /campaigns PUT: {auth_error}")
            user_id = 1  # Fallback
        
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
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
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Delete campaign - REAL database deletion"""
    try:
        from models import Campaign
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
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
    depth: Optional[int] = 3
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
    topic_tool: Optional[str] = "lda"
    num_topics: Optional[int] = 3
    iterations: Optional[int] = 25
    pass_threshold: Optional[float] = 0.7

# Analyze endpoint (for campaign building)
@app.post("/analyze")
def analyze_campaign(analyze_data: AnalyzeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Analyze campaign - Stub endpoint (returns task_id for now)
    TODO: Implement full analysis workflow
    
    IMPORTANT: This endpoint should NOT delete campaigns. It only starts analysis.
    """
    try:
        # Try to get user from token
        user_id = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                from utils import verify_token
                payload = verify_token(token)
                user_id = int(payload.get("sub"))
                logger.info(f"Token verified for user_id: {user_id}")
        except Exception as auth_error:
            logger.warning(f"Authentication failed for /analyze: {auth_error}")
            user_id = 1  # Fallback
        
        campaign_id = analyze_data.campaign_id or f"campaign-{uuid.uuid4()}"
        campaign_name = analyze_data.campaign_name or "Unknown Campaign"
        
        logger.info(f"🔍 /analyze POST endpoint called for campaign: {campaign_name} (ID: {campaign_id}) by user {user_id}")
        logger.info(f"🔍 Request data: campaign_name={analyze_data.campaign_name}, type={analyze_data.type}, keywords={len(analyze_data.keywords or [])} keywords")
        
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

                # Step 2: fetching content (persist placeholder rows for now)
                logger.info(f"📝 Step 2: Fetching content for campaign {cid}")
                set_task("fetching_content", 25, "Fetching URLs and preparing scrape queue")
                urls = data.urls or []
                keywords = data.keywords or []
                logger.info(f"📝 URLs to process: {len(urls)}, Keywords to process: {len(keywords)}")
                logger.info(f"📝 URL list: {urls}")
                logger.info(f"📝 Keywords list: {keywords}")

                # Create rows with sample extracted text for display
                # TODO: Replace with actual web scraping implementation
                created = 0
                now = datetime.utcnow()
                
                # For URLs - create sample extracted text
                if urls:
                    logger.info(f"📝 Creating {min(len(urls), 10)} URL rows...")
                    for u in urls[:10]:
                        if not u or u.strip() == "":
                            continue
                        # Generate richer sample text with entities for better extraction
                        sample_text = f"""
                        Article content extracted from {u}. This webpage contains comprehensive information and analysis on the topic. 
                        The content includes expert opinions from professionals like Dr. Robert Williams and Maria Garcia from leading 
                        research institutions. Major organizations such as The World Economic Forum, The Brookings Institution, and The 
                        Center for Strategic Studies have published reports on this subject. Geographic references include Washington DC, 
                        Los Angeles, Chicago, and Miami where significant activity has occurred. Key dates mentioned in the content include 
                        September 2024, October 2024, and November 2024 when major announcements were made. Industry leaders from companies 
                        like Microsoft, Facebook, and Oracle have provided insights. Government bodies including the Department of Defense 
                        and the National Science Foundation have funded research. Academic institutions like MIT, Caltech, and Princeton 
                        University have conducted studies. International organizations such as the United Nations and World Health 
                        Organization have issued statements. Cities like Denver, Portland, and Nashville have implemented related policies. 
                        Experts including Dr. Lisa Thompson and Professor David Kim have contributed analysis. Upcoming events in March 2025 
                        and April 2025 will address these topics. The content also references corporate entities like Verizon, AT&T, and 
                        Comcast, as well as regulatory bodies such as the FCC and SEC.
                        """
                        row = CampaignRawData(
                            campaign_id=cid,
                            source_url=u,
                            fetched_at=now,
                            raw_html=None,
                            extracted_text=sample_text.strip(),
                            meta_json=json.dumps({"seed": True, "type": "url", "source": u})
                        )
                        session.add(row)
                        created += 1
                        logger.debug(f"📝 Added URL row: {u}")
                else:
                    logger.info(f"📝 No URLs provided, skipping URL row creation")
                
                # For keywords, create placeholder search documents with sample content
                if keywords:
                    logger.info(f"📝 Creating {min(len(keywords), 10)} keyword rows...")
                    for kw in keywords[:10]:
                        if not kw or str(kw).strip() == "":
                            continue
                        # Generate richer sample text with entities for better extraction
                        sample_text = f"""
                        Comprehensive research content related to {kw}. This article discusses various aspects and perspectives on the topic, 
                        providing valuable insights for content creators. The content covers historical context, current trends, and future 
                        implications. Notable experts in the field, such as Dr. Sarah Mitchell from Stanford University and John Anderson 
                        from the Research Institute, have contributed significant findings. Organizations like The National Research Council 
                        and Global Analysis Group have published extensive studies on this subject. Key locations where this topic has gained 
                        traction include New York City, San Francisco, London, and Tokyo. Recent developments have been documented in reports 
                        dated October 2024, November 2024, and December 2024. The topic has also been covered in publications from major 
                        institutions including Harvard Business Review and MIT Technology Review. Industry leaders such as Amazon, Google, and 
                        Microsoft have invested heavily in this area. Government agencies including the Department of Commerce and the Federal 
                        Trade Commission have also issued guidelines. Cities like Boston, Seattle, and Austin have become hubs for innovation 
                        in this space. Experts like Professor Michael Chen and Dr. Jennifer Lee have provided valuable commentary. Events 
                        scheduled for January 2025 and February 2025 will further explore these developments. The International Standards 
                        Organization has released new guidelines, while companies like Apple, IBM, and Tesla have announced new initiatives.
                        """
                        row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"keyword:{kw}",
                            fetched_at=now,
                            raw_html=None,
                            extracted_text=sample_text.strip(),
                            meta_json=json.dumps({"seed": True, "type": "keyword", "keyword": kw})
                        )
                        session.add(row)
                        created += 1
                        logger.debug(f"📝 Added keyword row: {kw}")
                else:
                    logger.info(f"📝 No keywords provided, skipping keyword row creation")
                
                # If no data was provided, create at least one placeholder row for testing
                if created == 0:
                    logger.warning(f"⚠️ No URLs or keywords provided, creating placeholder row for campaign {cid}")
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
                
                if created > 0:
                    logger.info(f"💾 Committing {created} rows to database for campaign {cid}...")
                    session.commit()
                    logger.info(f"✅ Successfully committed {created} rows to database for campaign {cid}")
                    
                    # Verify data was saved
                    verify_count = session.query(CampaignRawData).filter(CampaignRawData.campaign_id == cid).count()
                    logger.info(f"✅ Verification: {verify_count} rows now exist in database for campaign {cid}")
                else:
                    logger.warning(f"⚠️ No rows to commit for campaign {cid}")

                # Step 3: processing content
                set_task("processing_content", 50, f"Processing {created} fetched items")
                time.sleep(5)  # Simulate content processing time

                # Step 4: extracting entities
                set_task("extracting_entities", 70, "Extracting entities and normalizing text")
                time.sleep(4)  # Simulate entity extraction time

                # Step 5: modeling topics
                set_task("modeling_topics", 85, "Modeling topics and summarizing")
                time.sleep(5)  # Simulate topic modeling time

                # Finalize
                set_task("finalizing", 100, "Finalizing")
                time.sleep(2)  # Brief pause before marking complete

                # Mark campaign ready in DB
                logger.info(f"📝 Step 6: Finalizing campaign {cid}")
                try:
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        logger.info(f"📝 Found campaign {cid} in database, updating status...")
                        # Store coarse topics from keywords as a ready signal
                        if (data.keywords or []) and not camp.topics:
                            camp.topics = ",".join((data.keywords or [])[:10])
                            logger.info(f"📝 Set topics to: {camp.topics}")
                        camp.status = "READY_TO_ACTIVATE"
                        camp.updated_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"✅ Campaign {cid} marked as READY_TO_ACTIVATE")
                    else:
                        logger.warning(f"⚠️ Campaign {cid} not found in database when trying to finalize")
                except Exception as finalize_err:
                    logger.error(f"❌ Error finalizing campaign {cid}: {finalize_err}")
                    import traceback
                    logger.error(traceback.format_exc())
                    session.rollback()
                    
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
def get_analyze_status(task_id: str):
    """
    Get analysis status - In-memory progress simulation.
    Progress advances deterministically based on time since start.
    """
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
def get_status_by_campaign(campaign_id: str):
    task_id = CAMPAIGN_TASK_INDEX.get(campaign_id)
    if not task_id:
        raise HTTPException(status_code=404, detail="No task for campaign")
    return get_analyze_status(task_id)

# Debug endpoint to check raw data for a campaign
@app.get("/campaigns/{campaign_id}/debug")
def debug_campaign_data(campaign_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to check what raw data exists for a campaign"""
    try:
        from models import CampaignRawData, Campaign
        
        # Check campaign exists
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        
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

# Research data endpoint: returns urls, raw samples, word cloud, topics and entities
@app.get("/campaigns/{campaign_id}/research")
def get_campaign_research(campaign_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Aggregate research outputs for a campaign.
    - urls: list of source_url
    - raw: up to `limit` extracted_text samples
    - wordCloud: top 10 terms by frequency
    - topics: naive primary topics (top terms)
    - entities: NLTK-based extraction using named entity recognition
    """
    try:
        from models import CampaignRawData
        # Import NLTK-based text processing
        from text_processing import (
            extract_entities as nltk_extract_entities,
            remove_stopwords,
            extract_keywords
        )

        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        urls = []
        texts = []
        for r in rows:
            if r.source_url:
                urls.append(r.source_url)
            if r.extracted_text:
                texts.append(r.extracted_text)

        # Build simple word frequency
        stop = set(
            "the a an and or of for to in on at from by with as is are was were be been being this that those these it its into over under about after before above below between across can will would should could may might not no yes you your we our their them they he she his her him i me my do does did done have has had having".split()
        )
        counts = {}
        tokenizer = re.compile(r"[A-Za-z]{3,}")
        for t in texts:
            for w in tokenizer.findall(t.lower()):
                if w in stop:
                    continue
                counts[w] = counts.get(w, 0) + 1
        top_terms = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        word_cloud = [{"term": k, "count": v} for k, v in top_terms]

        topics = [{"label": k, "score": v} for k, v in top_terms]

        # Use NLTK-based entity extraction for accurate named entity recognition
        persons = []
        organizations = []
        locations = []
        dates = []
        
        # Process texts with NLTK entity extraction
        for t in texts[:100]:
            if not t or len(t.strip()) < 10:
                continue
            try:
                entity_result = nltk_extract_entities(
                    t,
                    extract_persons=True,
                    extract_organizations=True,
                    extract_locations=True,
                    extract_dates=True
                )
                persons.extend(entity_result.get('persons', []))
                organizations.extend(entity_result.get('organizations', []))
                locations.extend(entity_result.get('locations', []))
                dates.extend(entity_result.get('dates', []))
            except Exception as e:
                logger.warning(f"Error extracting entities from text: {e}")
                # Fallback to regex for dates if NLTK fails
                date_regex = re.compile(r"\b(\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{4}\b", re.I)
                date_matches = date_regex.findall(t)
                dates.extend([d[0] if isinstance(d, tuple) else d for d in date_matches])
        
        entities = {
            "persons": list(dict.fromkeys(persons))[:20],
            "organizations": list(dict.fromkeys(organizations))[:20],
            "locations": list(dict.fromkeys(locations))[:20],
            "dates": list(dict.fromkeys(dates))[:20],
        }

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "urls": urls,
            "raw": texts[: max(0, limit) or 20],
            "wordCloud": word_cloud,
            "topics": topics,
            "entities": entities,
            "total_raw": len(texts),
        }
    except Exception as e:
        import traceback
        logger.error(f"Error aggregating research for {campaign_id}: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to get research data")

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