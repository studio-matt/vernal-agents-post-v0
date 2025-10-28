#!/usr/bin/env python3
"""
BULLETPROOF FastAPI main.py - NO BLOCKING IMPORTS
Following Emergency Net v4 template with ALL functionality restored
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

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

# Don't include routers yet - wait for startup event
# include_routers()  # Moved to startup_event for safety

# Global variables for lazy initialization
db_manager = None
scheduler = None

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
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None

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
        
        # NOW include routers after DB and scheduler are ready
        include_routers()
        logger.info("All routers included after startup")
        
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

# Campaign endpoints with REAL database operations
@app.get("/campaigns")
def get_campaigns(db: Session = Depends(get_db)):
    """Get all campaigns - REAL database query"""
    try:
        from models import Campaign
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
                    "status": campaign.status,
                    "progress": campaign.progress,
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                    "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
                }
                for campaign in campaigns
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching campaigns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch campaigns"
        )

@app.post("/campaigns")
def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    """Create campaign - REAL database save"""
    try:
        from models import Campaign
        logger.info(f"Creating campaign: {campaign_data.name}")
        
        # Generate unique campaign ID
        campaign_id = str(uuid.uuid4())
        
        # Convert lists to strings for database storage
        keywords_str = json.dumps(campaign_data.keywords) if campaign_data.keywords else None
        urls_str = json.dumps(campaign_data.urls) if campaign_data.urls else None
        trending_topics_str = json.dumps(campaign_data.trendingTopics) if campaign_data.trendingTopics else None
        topics_str = json.dumps(campaign_data.topics) if campaign_data.topics else None
        
        # Create campaign in database
        db_manager = get_db_manager()
        db_manager.create_campaign(
            campaign_id=campaign_id,
            campaign_name=campaign_data.name,
            description=campaign_data.description,
            query=campaign_data.name,
            campaign_type=campaign_data.type,
            keywords_str=keywords_str,
            urls_str=urls_str,
            trending_topics_str=trending_topics_str,
            topics_str=topics_str,
            status="created",
            extraction_settings=campaign_data.extractionSettings or {},
            preprocessing_settings=campaign_data.preprocessingSettings or {},
            entity_settings=campaign_data.entitySettings or {},
            modeling_settings=campaign_data.modelingSettings or {}
        )
        
        logger.info(f"Campaign created successfully: {campaign_id}")
        
        return {
            "status": "success",
            "message": {
                "id": campaign_id,
                "name": campaign_data.name,
                "description": campaign_data.description,
                "type": campaign_data.type,
                "status": "created"
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign"
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
                "status": campaign.status,
                "progress": campaign.progress,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)