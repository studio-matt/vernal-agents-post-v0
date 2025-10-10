import os
import sys
import logging
import traceback
from typing import Optional, Dict, List, Union, Any
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Universal error handling for environment variables
def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Safely get environment variable with fallback and validation"""
    value = os.getenv(key) or default
    if required and not value:
        logger.error(f"Required environment variable {key} is missing!")
        sys.exit(1)
    if value:
        logger.debug(f"Environment variable {key} loaded successfully")
    else:
        logger.warning(f"Environment variable {key} not set, using default: {default}")
    return value

# Set up OpenAI API key with validation
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY", required=True)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"

logger.info("Starting Vernal Agents Backend with bulletproof error handling")

# Import FastAPI and core dependencies
try:
    from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Depends, Body, status
    from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
    from fastapi.encoders import jsonable_encoder
    from fastapi.staticfiles import StaticFiles
    from fastapi.security import OAuth2PasswordBearer
    from fastapi.middleware.cors import CORSMiddleware
    logger.info("FastAPI imports successful")
except Exception as e:
    logger.error(f"Failed to import FastAPI: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import other core dependencies
try:
    import json
    import asyncio
    import uuid
    from datetime import datetime, timedelta, time, timezone
    from pydantic import BaseModel, EmailStr, ValidationError, Field
    from sqlalchemy.orm import Session
    import secrets
    import requests
    from apscheduler.schedulers.background import BackgroundScheduler
    import tweepy
    import base64
    from ftplib import FTP
    import io
    import httpx
    import pdfplumber
    import time
    import random
    from threading import Timer
    import re
    from io import BytesIO
    from crewai import Crew, Process
    logger.info("Core dependencies imported successfully")
except Exception as e:
    logger.error(f"Failed to import core dependencies: {e}")
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

# Initialize database manager with error handling
try:
    db_manager = DatabaseManager()
    logger.info("Database manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database manager: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import models with error handling
try:
    from models import Content, User, PlatformConnection, OTP, PlatformEnum, Agent, Task, StateToken
    logger.info("Models imported successfully")
except Exception as e:
    logger.error(f"Failed to import models: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import utils with error handling
try:
    from utils import hash_password, verify_password, create_access_token, send_email, verify_token
    logger.info("Utils imported successfully")
except Exception as e:
    logger.error(f"Failed to import utils: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import tools with error handling
try:
    from tools import process_content_for_platform, extract_title_from_content, generate_unique_content, generate_different_content, FileProcessor, generate_image, PLATFORM_LIMITS, delete_image_from_ftp
    logger.info("Tools imported successfully")
except Exception as e:
    logger.error(f"Failed to import tools: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import agents with error handling
try:
    from agents import (
        script_research_agent, qc_agent, script_rewriter_agent, regenrate_content_agent, regenrate_subcontent_agent,
        linkedin_agent, facebook_agent, twitter_agent, instagram_agent, youtube_agent, tiktok_agent, wordpress_agent,
        PLATFORM_LIMITS
    )
    logger.info("Agents imported successfully")
except Exception as e:
    logger.error(f"Failed to import agents: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import tasks with error handling
try:
    from tasks import (
        script_research_task, qc_task, script_rewriter_task, regenrate_content_task, regenrate_subcontent_task,
        linkedin_task, facebook_task, twitter_task, instagram_task, youtube_task, tiktok_task, wordpress_task
    )
    logger.info("Tasks imported successfully")
except Exception as e:
    logger.error(f"Failed to import tasks: {e}")
    traceback.print_exc()
    sys.exit(1)

# Create FastAPI app
app = FastAPI(title="Vernal Agents API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router imports with explicit error handling and logging
try:
    from simple_mcp_api import simple_mcp_router
    app.include_router(simple_mcp_router, prefix="/mcp")
    logger.info("✅ simple_mcp_router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include simple_mcp_router: {e}")
    traceback.print_exc()

try:
    from debug_import import router as test_router
    app.include_router(test_router)
    logger.info("✅ test_router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include test_router: {e}")
    traceback.print_exc()

# Initialize background scheduler
try:
    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("Background scheduler started successfully")
except Exception as e:
    logger.error(f"Failed to start background scheduler: {e}")
    traceback.print_exc()

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {"ok": True}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint requested")
    return {"message": "Vernal Agents API is running"}

# Test endpoint
@app.get("/test-health")
async def test_health():
    """Test health endpoint"""
    logger.info("Test health endpoint requested")
    return {"status": "test_ok", "message": "Test endpoint is working"}

# Add all your existing endpoints here...
# (I'll add them in the next part to keep this manageable)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with uvicorn")
    uvicorn.run(app, host="0.0.0.0", port=8000)
