import os
import logging
from datetime import datetime
from fastapi import FastAPI, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import database and models
from database import DatabaseManager, get_db
from models import User, Campaign
from auth_api import get_current_user

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your-api-key-here")
os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"

logger.info("Starting DEBUG FastAPI app - VERSION 2.0")

# Create FastAPI app
app = FastAPI(title="Vernal Agents API DEBUG", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://machine.vernalcontentum.com", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["content-type", "authorization", "accept", "ngrok-skip-browser-warning"],
    expose_headers=["*"],
)

# Manual CORS handler for OPTIONS requests
@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle OPTIONS requests manually to ensure CORS headers are set"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://machine.vernalcontentum.com",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600"
        }
    )

# Specific handler for auth endpoints
@app.options("/auth/{path:path}")
async def auth_options_handler(path: str):
    """Handle OPTIONS requests for auth endpoints specifically"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://machine.vernalcontentum.com",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600"
        }
    )

# Health endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check requested - DEBUG VERSION")
    return {"ok": True, "version": "2.0.0", "status": "debug"}

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint requested - DEBUG VERSION")
    return {"message": "Vernal Agents API DEBUG is running", "version": "2.0.0"}

# Test endpoint
@app.get("/test-health")
async def test_health():
    logger.info("Test health endpoint requested - DEBUG VERSION")
    return {"status": "test_ok", "message": "Test endpoint is working - DEBUG VERSION", "version": "2.0.0"}

# Version endpoint with git commit and build time
@app.get("/version")
async def version():
    import subprocess
    import datetime
    import os

    try:
        # Get git commit hash (more robust)
        result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, cwd=os.getcwd())
        commit = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Get git branch
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                              capture_output=True, text=True, cwd=os.getcwd())
        branch = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Get build time (when this process started)
        build_time = datetime.datetime.utcnow().isoformat()

        return {
            "commit": commit,
            "branch": branch,
            "build_time": build_time,
            "version": "2.0.0",
            "status": "debug",
            "working_dir": os.getcwd(),
            "deployment": "bulletproof-v22"  # Fixed CORS with proper Response objects
        }
    except Exception as e:
        logger.error(f"Error getting version info: {e}")
        return {
            "commit": "unknown",
            "branch": "unknown",
            "build_time": datetime.datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "status": "debug",
            "error": str(e),
            "working_dir": os.getcwd(),
            "deployment": "bulletproof-v22"  # Fixed CORS with proper Response objects
        }


# Simple test router
from fastapi import APIRouter
test_router = APIRouter(prefix="/test", tags=["Test"])

@test_router.get("/health")
async def test_router_health():
    logger.info("Test router health endpoint called")
    return {"status": "test_router_working", "message": "Test router is working", "version": "2.0.0"}

@test_router.get("/ping")
async def test_router_ping():
    logger.info("Test router ping endpoint called")
    return {"message": "pong", "version": "2.0.0"}

# Include the test router
app.include_router(test_router)
logger.info("✅ Test router included successfully")

# Enhanced MCP router
try:
    from enhanced_mcp_api import enhanced_mcp_router
    app.include_router(enhanced_mcp_router)
    logger.info("✅ Enhanced MCP router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include enhanced MCP router: {str(e)}")

# Simple MCP router (fallback)
try:
    from simple_mcp_api import simple_mcp_router
    app.include_router(simple_mcp_router)
    logger.info("✅ Simple MCP router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include simple MCP router: {str(e)}")

# Authentication router (real database version)
try:
    from auth_api import auth_router
    app.include_router(auth_router)
    logger.info("✅ Real database authentication router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include real database authentication router: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # Fallback to ultra minimal if database auth fails
    try:
        from auth_ultra_minimal import auth_router
        app.include_router(auth_router)
        logger.info("✅ Fallback to ultra minimal authentication router")
    except Exception as e2:
        logger.error(f"❌ Fallback also failed: {str(e2)}")

# Campaigns endpoint
@app.get("/campaigns")
async def get_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get campaigns for the authenticated user"""
    logger.info(f"Campaigns endpoint requested by user {current_user.id}")
    
    try:
        # Get campaigns for this user from database
        campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
        
        # Convert to response format
        campaign_list = []
        for campaign in campaigns:
            campaign_list.append({
                "id": campaign.campaign_id,
                "name": campaign.campaign_name,
                "description": campaign.description,
                "type": campaign.type,
                "keywords": campaign.keywords.split(',') if campaign.keywords else [],
                "urls": campaign.urls.split(',') if campaign.urls else [],
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
            })
        
        return {
            "status": "success",
            "campaigns": campaign_list,
            "message": f"Found {len(campaign_list)} campaigns for user {current_user.id}",
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Error fetching campaigns: {str(e)}")
        return {
            "status": "error",
            "campaigns": [],
            "message": f"Error fetching campaigns: {str(e)}",
            "version": "2.0.0"
        }

# Create campaign endpoint
@app.post("/campaigns", response_class=JSONResponse)
async def create_campaign(campaign_data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new campaign for the authenticated user"""
    try:
        # Extract campaign data
        campaign_name = campaign_data.get("name", "").strip()
        description = campaign_data.get("description", "")
        query = campaign_data.get("query", "").strip()
        campaign_type = campaign_data.get("type", "keyword")
        keywords = campaign_data.get("keywords", [])
        urls = campaign_data.get("urls", [])
        trending_topics = campaign_data.get("trendingTopics", [])
        topics = campaign_data.get("topics", [])
        
        # Validate required fields
        if not campaign_name:
            return JSONResponse(content={"error": "Campaign name is required"}, status_code=400)
        
        # Generate campaign ID
        campaign_id = f"campaign-{int(datetime.now().timestamp() * 1000)}"
        
        # Convert lists to comma-separated strings for database storage
        keywords_str = ','.join(keywords) if keywords else ""
        urls_str = ','.join(urls) if urls else ""
        trending_topics_str = ','.join(trending_topics) if trending_topics else ""
        topics_str = ','.join(topics) if topics else ""
        
        # Create campaign in database with user_id
        campaign = Campaign(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            description=description,
            query=query,
            type=campaign_type,
            keywords=keywords_str,
            urls=urls_str,
            trending_topics=trending_topics_str,
            topics=topics_str,
            user_id=current_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"Created campaign {campaign_id} for user {current_user.id}")
        
        return JSONResponse(content={
            "status": "success",
            "message": {
                "id": campaign_id,
                "name": campaign_name,
                "description": description,
                "type": campaign_type,
                "keywords": keywords,
                "urls": urls,
                "created_at": campaign.created_at.isoformat(),
                "updated_at": campaign.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        return JSONResponse(content={"error": f"Error creating campaign: {str(e)}"}, status_code=500)

# Debug endpoint to show all routes
@app.get("/debug/routes")
async def debug_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods)
            })
    return {"routes": routes, "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with uvicorn - DEBUG VERSION")
    uvicorn.run(app, host="0.0.0.0", port=8000)
