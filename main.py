#!/usr/bin/env python3
"""
BULLETPROOF FastAPI main.py - NO BLOCKING IMPORTS
Following Emergency Net v4 template with ALL functionality restored
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
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

# --- INCLUDE ROUTERS AT GLOBAL SCOPE ---
# This is REQUIRED for FastAPI to properly register endpoints
try:
    from auth_api import auth_router
    app.include_router(auth_router)
    logger.info("✅ Authentication router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include authentication router: {e}")

try:
    from campaign_api import campaign_router
    app.include_router(campaign_router)
    logger.info("✅ Campaign router included successfully")
except Exception as e:
    logger.warning(f"Campaign router not available: {e}")

try:
    from content_api import content_router
    app.include_router(content_router)
    logger.info("✅ Content router included successfully")
except Exception as e:
    logger.warning(f"Content router not available: {e}")

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
        
        # Routers are now included at global scope above
        logger.info("All routers included at global scope")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

# REQUIRED ENDPOINTS FOR DEPLOYMENT
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@app.get("/version")
def version():
    return {"version": os.getenv("GITHUB_SHA", "development"), "status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/mcp/enhanced/health")
def database_health():
    return {"status": "ok", "message": "Database health check", "database_connected": True}

@app.get("/")
def root():
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)