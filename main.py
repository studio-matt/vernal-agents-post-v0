#!/usr/bin/env python3
"""
Vernal Agents Backend - Production Ready
Real authentication with database backend
"""

import os
import sys
import logging
import traceback
from typing import Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger.info("Starting Vernal Agents Backend - Production Version")

# Import FastAPI and core dependencies
try:
    from fastapi import FastAPI, HTTPException, Depends, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from sqlalchemy.orm import Session
    logger.info("FastAPI imports successful")
except Exception as e:
    logger.error(f"Failed to import FastAPI: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import database with error handling
try:
    from database import DatabaseManager, SessionLocal
    logger.info("Database imports successful")
except Exception as e:
    logger.error(f"Failed to import database: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import models with error handling
try:
    from models import User, OTP, Content, PlatformConnection
    logger.info("Models imported successfully")
except Exception as e:
    logger.error(f"Failed to import models: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import utils with error handling
try:
    from utils import hash_password, verify_password, create_access_token, verify_token
    logger.info("Utils imported successfully")
except Exception as e:
    logger.error(f"Failed to import utils: {e}")
    traceback.print_exc()
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="Vernal Agents Backend API",
    description="Production backend for Vernal Agents content management system",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for lazy initialization
db_manager = None
scheduler = None

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_manager():
    """Lazy database manager initialization"""
    global db_manager
    if db_manager is None:
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
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        traceback.print_exc()

# REQUIRED ENDPOINTS FOR DEPLOYMENT
@app.get("/health")
def health():
    """Health check endpoint for monitoring and load balancers"""
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@app.get("/version")
def version():
    """Version endpoint for deployment verification"""
    return {
        "version": os.getenv("GITHUB_SHA", "development"),
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/mcp/enhanced/health")
def database_health():
    """Database health endpoint for deployment validation"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "ok", "message": "Database health check", "database_connected": True}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": "Database connection failed", "database_connected": False}

# Import and include authentication router
try:
    from auth_api import auth_router
    app.include_router(auth_router)
    logger.info("✅ Authentication router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include authentication router: {e}")
    traceback.print_exc()

# Import and include campaign router if available
try:
    from campaign_api import campaign_router
    app.include_router(campaign_router)
    logger.info("✅ Campaign router included successfully")
except Exception as e:
    logger.warning(f"Campaign router not available: {e}")

# Import and include content generation router if available
try:
    from content_api import content_router
    app.include_router(content_router)
    logger.info("✅ Content router included successfully")
except Exception as e:
    logger.warning(f"Content router not available: {e}")

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Vernal Agents Backend API", "status": "running", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with uvicorn")
    uvicorn.run(app, host="0.0.0.0", port=8000)