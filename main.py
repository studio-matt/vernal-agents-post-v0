# =============================================================================
# FOOLPROOF STARTUP VALIDATION - FAIL FAST ON MISSING MODULES
# =============================================================================
import sys
import traceback

def validate_critical_imports():
    """Validate all critical imports at startup - fail fast if any are missing"""
    critical_modules = [
        'fastapi',
        'agents', 
        'tasks',
        'tools',
        'database',
        'models',
        'utils',
        'crewai',
        'sqlalchemy',
        'pydantic',
        'tweepy',
        'requests',
        'paramiko'
    ]
    
    missing_modules = []
    for module in critical_modules:
        try:
            __import__(module)
        except ImportError as e:
            missing_modules.append(f"{module}: {e}")
    
    if missing_modules:
        print("=" * 80)
        print("FATAL ERROR: CRITICAL MODULES MISSING!")
        print("=" * 80)
        for module_error in missing_modules:
            print(f"❌ {module_error}")
        print("=" * 80)
        print("Backend cannot start - fix missing dependencies first!")
        print("=" * 80)
        sys.exit(1)
    
    print("✅ All critical imports validated successfully")

# Run validation immediately
validate_critical_imports()

# =============================================================================
# STANDARD IMPORTS (now safe to proceed)
# =============================================================================
import os
from fastapi import FastAPI, UploadFile, File, HTTPException , Query, Form, Depends, Body, status
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
import json
import asyncio
from typing import Optional, Dict, List, Union, Any
from pydantic import BaseModel, EmailStr, ValidationError, Field
import uuid
from datetime import datetime
from agents import (
    script_research_agent, qc_agent, script_rewriter_agent, regenrate_content_agent, regenrate_subcontent_agent,
    
    PLATFORM_LIMITS
)
from tasks import (
    script_research_task, qc_task, script_rewriter_task, regenrate_content_task, regenrate_subcontent_task,
    
)
from crewai import Crew, Process
from tools import process_content_for_platform, extract_title_from_content, generate_unique_content,generate_different_content, FileProcessor,generate_image, PLATFORM_LIMITS, delete_image_from_ftp
from database import DatabaseManager, SessionLocal
from pathlib import Path
from models import Content, User, PlatformConnection, OTP, PlatformEnum, Agent, Task, StateToken
from utils import hash_password, verify_password, create_access_token, send_email, verify_token
from fastapi.middleware.cors import CORSMiddleware
import random
from threading import Timer
import time as t
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
import re
from sqlalchemy.orm import Session
import secrets
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import tweepy
import base64
import logging
from ftplib import FTP
import io
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel
import pdfplumber
import os
import time
from datetime import datetime, timedelta
from tasks import create_prompt, analyze_text
from typing import Dict, List
import traceback
import paramiko



load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Startup event handler to create database tables
@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        db_mgr = get_db_manager()
        db_mgr.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        # Don't fail startup, but log the error

# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint for monitoring and load balancers"""
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

# In-memory storage for progress tracking
progress_storage: Dict[str, Dict[str, Any]] = {}

# Initialize database manager (lazy loading to prevent startup failures)
db_manager = None

def get_db_manager():
    """Get database manager instance, creating it if needed"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

# Initialize scheduler (lazy loading to prevent startup failures)
scheduler = None

def get_scheduler():
    """Get scheduler instance, creating it if needed"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("BackgroundScheduler started")
    return scheduler

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://machine.vernalcontentum.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Adjust this to specify allowed HTTP methods
    allow_headers=["*"],  # Adjust this to specify allowed headers
)

# Progress tracking storage
progress_storage: Dict[str, Dict[str, Any]] = {}

class ProgressStatus(BaseModel):
    task_id: str
    status: str  # "processing", "completed", "failed"
    progress: int  # 0-100
    current_step: str
    message: str
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Directory configuration
UPLOAD_DIR = './uploads'
OUTPUT_DIR = './outputs'
static_dir = './static'

def ensure_directories():
    """Ensure required directories exist"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)

class ContentResponse(BaseModel):
    week_day: str
    title: str
    content: str
    platform: str
    timestamp: str
    word_count: int
    char_count: int

class ContentResponse1(BaseModel):
    week: int
    day: str
    platform_post_no: str
    schedule_time: datetime
    title: str
    content: str
    platform: str
    timestamp: str
    word_count: int
    char_count: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def save_output_to_file(data: Dict, filename: str) -> str:
    """Save generated content to a JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{filename}_{timestamp}.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    return output_path


CACHE_EXPIRATION = 600

class ContentItem(BaseModel):
    type: str
    text: str


class MainContent(BaseModel):
    type: str
    text: str


    
class WeeklyContent(BaseModel):
    week: str
    content_by_days: Dict[str, List[ContentItem]]

class CacheEntry:
    def __init__(self, content: WeeklyContent):
        self.content = content
        self.timestamp = t.time()
        self.temp_id = str(int(self.timestamp))

def cleanup_expired_entries():
    current_time = t.time()
    expired_keys = [
        key for key, entry in temp_storage.items()
        if current_time - entry.timestamp > CACHE_EXPIRATION
    ]
    for key in expired_keys:
        del temp_storage[key]

# Storage for permanent and temporary content
content_storage: Dict[int, WeeklyContent] = {}
temp_storage: Dict[str, CacheEntry] = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")



async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print(f"Received token: {token}")
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


# User Registration
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    contact: str

def generate_and_send_otp(user: User, db: Session):
    # Delete any existing OTPs for the user
    db.query(OTP).filter(OTP.user_id == user.id).delete()
    
    # Generate a new 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # Create and store the new OTP
    new_otp = OTP(user_id=user.id, otp_code=otp_code, expires_at=expires_at)
    db.add(new_otp)
    db.commit()
    
    # Send the OTP via email
    send_email(user.email, "Verify your email", f"Your OTP code is {otp_code}. It expires in 10 minutes.")

@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # Check if a user with this email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="User is already registered and verified. Please login.")
        else:
            # User is registered but not verified, send a new OTP
            generate_and_send_otp(existing_user, db)
            return {"status": 200, "message": "User is already register but not verified, Please submit the OTP for verification. A new OTP has been sent to your email for verification."}
    else:
        # Create a new user
        hashed_password = hash_password(user.password)
        new_user = User(username=user.username, email=user.email, password=hashed_password, contact=user.contact)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Generate and send OTP for the new user
        generate_and_send_otp(new_user, db)
        return {"status": 200, "message": "User registered. Check your email for OTP."}

from pydantic import BaseModel, EmailStr, Field

# Email Verification
class VerifyOTP(BaseModel):
    email: EmailStr = Field(..., alias="username")
    otp_code: str

@app.post("/verify-email")
def verify_email(verify_data: VerifyOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == verify_data.email).first()
    if not user or user.is_verified:
        raise HTTPException(status_code=400, detail="User not found or already verified")
    otp = db.query(OTP).filter(OTP.user_id == user.id, OTP.otp_code == verify_data.otp_code).first()
    if not otp or datetime.now() > otp.expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    user.is_verified = True
    db.delete(otp)
    db.commit()
    return {"status": 200, "message": "Email verified successfully"}

# User Login
# class UserLogin(BaseModel):
#     email: EmailStr = Field(..., alias="username")
#     password: str

# @app.post("/login")
# def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
#     print(f"Received login data: {login_data}")
#     user = db.query(User).filter(User.email == login_data.email).first()
#     if not user or not user.is_verified or not verify_password(login_data.password, user.password):
#         raise HTTPException(status_code=400, detail="Invalid credentials")
#     access_token = create_access_token(data={"sub": str(user.id)})
#     return {"access_token": access_token, "token_type": "bearer"}


from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
class UserLogin(BaseModel):
    email: EmailStr = Field(..., alias="username")
    password: str

@app.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"Received form data: username={form_data.username}, password={form_data.password}")
    
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(status_code=400, detail="User does not exist. Please register first.")
    
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified. Please register with same credentials and then verify your email before logging in.")
    
    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password.")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


# Custom OpenAPI schema to modify the OAuth2 password flow
from fastapi.openapi.utils import get_openapi
def custom_openapi():
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="API with OAuth2 Authentication",
        routes=app.routes,
    )
    
    # Modify the OAuth2PasswordBearer security scheme
    if "components" in openapi_schema and "securitySchemes" in openapi_schema["components"]:
        oauth2_scheme = openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
        if "flows" in oauth2_scheme and "password" in oauth2_scheme["flows"]:
            # Keep only the tokenUrl, remove other fields
            oauth2_scheme["flows"]["password"] = {
                "tokenUrl": "/login",
                "scopes": {}  # No scopes needed for your use case
            }
    
    return openapi_schema

# Override the default }
# Platform Connection (LinkedIn Example)
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
LINKEDIN_REDIRECT_URI1 = os.getenv("LINKEDIN_REDIRECT_URI1")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_CALLBACK_URI = os.getenv("TWITTER_CALLBACK_URI")
TWITTER_CALLBACK_URI1 = os.getenv("TWITTER_CALLBACK_URI1")
FRONTEND_SUCCESS_URL = os.getenv("FRONTEND_SUCCESS_URL")
FRONTEND_SUCCESS_URL1 = os.getenv("FRONTEND_SUCCESS_URL1")
# FRONTEND_SUCCESS_URL1 = "https://machine-3-0.vercel.app/account-settings"

# Pydantic models for request validation
class ResendOTPRequest(BaseModel):
    email: EmailStr

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

# Resend OTP Endpoint
@app.post("/resend-otp")
def resend_otp(request: ResendOTPRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified")
    
    # Generate new OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # Update or create OTP record
    existing_otp = db.query(OTP).filter(OTP.user_id == user.id).first()
    if existing_otp:
        existing_otp.otp_code = otp_code
        existing_otp.expires_at = expires_at
    else:
        new_otp = OTP(user_id=user.id, otp_code=otp_code, expires_at=expires_at)
        db.add(new_otp)
    
    db.commit()
    
    # Send OTP via email
    send_email(user.email, "Your New OTP", f"Your new OTP code is {otp_code}. It expires in 10 minutes.")
    return {"status": 200, "message": "New OTP sent successfully"}

# Forget Password Endpoint (Step 1: Request OTP)
@app.post("/forget-password")
def forget_password(request: ForgetPasswordRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # Update or create OTP record
    existing_otp = db.query(OTP).filter(OTP.user_id == user.id).first()
    if existing_otp:
        existing_otp.otp_code = otp_code
        existing_otp.expires_at = expires_at
    else:
        new_otp = OTP(user_id=user.id, otp_code=otp_code, expires_at=expires_at)
        db.add(new_otp)
    
    db.commit()
    
    # Send OTP via email
    send_email(user.email, "Password Reset OTP", f"Your OTP code for password reset is {otp_code}. It expires in 10 minutes.")
    return {"status": 200, "message": "OTP sent for password reset"}

# Reset Password Endpoint (Step 2: Verify OTP and Reset Password)
@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify OTP
    otp = db.query(OTP).filter(OTP.user_id == user.id, OTP.otp_code == request.otp_code).first()
    if not otp or datetime.now() > otp.expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Hash and update the new password
    hashed_password = hash_password(request.new_password)
    user.password = hashed_password
    
    # Delete the used OTP
    db.delete(otp)
    db.commit()
    
    return {"status": 200, "message": "Password reset successfully"}

@app.get("/linkedin/auth")
async def linkedin_auth(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = secrets.token_urlsafe(32)
    db.add(StateToken(user_id=current_user.id, state=state, platform=PlatformEnum.LINKEDIN))
    db.commit()
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={LINKEDIN_REDIRECT_URI}&scope=openid profile w_member_social&state={state}"
    )
    return {"auth_url": auth_url}

@app.get("/linkedin/callback")
async def linkedin_callback(code: str, state: str, db: Session = Depends(get_db)):
    # Verify the state token
    state_token = db.query(StateToken).filter(StateToken.state == state).first()
    if not state_token:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=invalid_state")
    
    # Delete the state token immediately after verification to prevent reuse
    db.delete(state_token)
    db.commit()
    
    # Get the user associated with the state token
    user = db.query(User).filter(User.id == state_token.user_id).first()
    
    # Exchange the authorization code for an access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    print(f"Requesting LinkedIn token with data: {data}")
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        print(f"Failed to get LinkedIn token: {response.text}")
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=token_request_failed")
    
    token_data = response.json()
    access_token = token_data["access_token"]
    
    # Fetch LinkedIn user profile to get ID
    profile_url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = requests.get(profile_url, headers=headers)
    if profile_response.status_code != 200:
        print(f"Failed to get LinkedIn user profile: {profile_response.text}")
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=profile_request_failed")
    
    profile_data = profile_response.json()
    linkedin_id = profile_data.get("sub")
    
    # Check for existing LinkedIn connection
    existing_connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == user.id,
        PlatformConnection.platform == PlatformEnum.LINKEDIN
    ).first()
    
    if existing_connection:
        # Update existing connection with new credentials
        existing_connection.access_token = access_token
        existing_connection.expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        existing_connection.platform_user_id = linkedin_id
        existing_connection.disconnected_at = None  # Mark as active
        logger.info(f"Updated LinkedIn connection for user {user.id}")
    else:
        # Create a new connection if none exists
        new_connection = PlatformConnection(
            user_id=user.id,
            platform=PlatformEnum.LINKEDIN,
            access_token=access_token,
            expires_at=datetime.now() + timedelta(seconds=token_data["expires_in"]),
            platform_user_id=linkedin_id,
            disconnected_at=None
        )
        db.add(new_connection)
        logger.info(f"Created new LinkedIn connection for user {user.id}")
    
    db.commit()
    
    # Redirect to frontend with success indicator
    return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?linkedin_connected=true")

# Twitter Authentication
@app.get("/twitter/auth")
async def twitter_auth(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = secrets.token_urlsafe(32)
    db.add(StateToken(user_id=current_user.id, state=state, platform=PlatformEnum.TWITTER))
    db.commit()
    
    auth = tweepy.OAuth1UserHandler(
        TWITTER_CLIENT_ID,
        TWITTER_CLIENT_SECRET,
        callback=TWITTER_CALLBACK_URI
    )
    try:
        auth_url = auth.get_authorization_url()
        db.add(StateToken(
            user_id=current_user.id,
            state=state,  # Optional, for consistency with LinkedIn
            platform=PlatformEnum.TWITTER,
            oauth_token=auth.request_token["oauth_token"],
            oauth_token_secret=auth.request_token["oauth_token_secret"]
        ))
        db.commit()
        return {"redirect_url": auth_url}
    except tweepy.TweepyException as e:
        raise HTTPException(status_code=500, detail=f"Error starting Twitter auth: {e}")


@app.get("/twitter/callback")
async def twitter_callback(oauth_token: str, oauth_verifier: str, db: Session = Depends(get_db)):
    # Find StateToken using oauth_token
    state_token = db.query(StateToken).filter(
        StateToken.oauth_token == oauth_token,
        StateToken.platform == PlatformEnum.TWITTER
    ).first()
    if not state_token:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=invalid_oauth_token")
    
    # Get the user
    user = db.query(User).filter(User.id == state_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set request token with stored oauth_token and oauth_token_secret
    auth = tweepy.OAuth1UserHandler(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    auth.request_token = {
        "oauth_token": state_token.oauth_token,
        "oauth_token_secret": state_token.oauth_token_secret
    }
    try:
        auth.get_access_token(oauth_verifier)
        access_token = auth.access_token
        access_token_secret = auth.access_token_secret
    except tweepy.TweepyException as e:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=twitter_auth_failed")
    
    # Fetch Twitter user ID
    client = tweepy.Client(
        consumer_key=TWITTER_CLIENT_ID,
        consumer_secret=TWITTER_CLIENT_SECRET,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    try:
        user_info = client.get_me().data
        twitter_id = user_info.id
    except tweepy.TweepyException as e:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?error=twitter_user_info_failed")
    
    # Check for existing Twitter connection
    existing_connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == user.id,
        PlatformConnection.platform == PlatformEnum.TWITTER
    ).first()
    
    if existing_connection:
        # Update existing connection with new credentials
        existing_connection.access_token = access_token
        existing_connection.refresh_token = access_token_secret  # Using refresh_token to store access_token_secret
        existing_connection.platform_user_id = str(twitter_id)
        existing_connection.disconnected_at = None  # Mark as active
        logger.info(f"Updated Twitter connection for user {user.id}")
    else:
        # Create a new connection if none exists
        new_connection = PlatformConnection(
            user_id=user.id,
            platform=PlatformEnum.TWITTER,
            access_token=access_token,
            refresh_token=access_token_secret,
            expires_at=None,  # Twitter tokens don't expire in OAuth 1.0a
            platform_user_id=str(twitter_id),
            disconnected_at=None
        )
        db.add(new_connection)
        logger.info(f"Created new Twitter connection for user {user.id}")
    
    db.commit()
    db.delete(state_token)
    db.commit()
    return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}?twitter_connected=true")

# WordPress Authentication
@app.post("/wordpress/auth")
async def wordpress_auth(
    site_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    site_url = site_url.strip('/')
    if not all([site_url, username, password]):
        raise HTTPException(status_code=400, detail="All fields are required")

    # Test authentication with WordPress REST API
    api_url = f"{site_url}/wp-json/wp/v2/users/me"
    auth_string = f"{username}:{password}"
    auth_header = "Basic " + base64.b64encode(auth_string.encode()).decode()
    headers = {"Authorization": auth_header}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            error_message = response.json().get('message', 'Unknown error')
            raise HTTPException(status_code=401, detail=f"Authentication failed: {error_message} (Status: {response.status_code})")
        
        # Fetch WordPress user ID
        user_info = response.json()
        wordpress_id = str(user_info.get("id"))
        
        # Check for existing WordPress connection
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if existing_connection:
            # Update existing connection with new credentials
            existing_connection.access_token = auth_header
            existing_connection.refresh_token = site_url
            existing_connection.platform_user_id = wordpress_id
            existing_connection.disconnected_at = None  # Mark as active
            logger.info(f"Updated WordPress connection for user {current_user.id}")
        else:
            # Create a new connection if none exists
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.WORDPRESS,
                access_token=auth_header,
                refresh_token=site_url,
                expires_at=None,  # Basic Auth doesn't expire
                platform_user_id=wordpress_id,
                disconnected_at=None
            )
            db.add(new_connection)
            logger.info(f"Created new WordPress connection for user {current_user.id}")
        
        db.commit()
        return {"message": "WordPress connected successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to WordPress: {str(e)}")

def post_to_linkedin(content: Content, connection: PlatformConnection, session: Session) -> bool:
    """Post content to LinkedIn with optional image, based on reference function."""
    # Check if content is in a postable state
    if content.status not in ['pending']:
        logger.warning(f"Content ID {content.id} not in pending status: {content.status}")
        return False

    # Extract required data from objects
    access_token = connection.access_token
    linkedin_id = connection.platform_user_id
    image_url = content.image_url  # This may be None if no image
    text = content.content

    # Set up headers as per the reference function
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # Handle image posting if an image URL is provided
    if image_url:
        try:
            # Download the image
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                image_content = response.content

                # Register the image upload
                register_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
                register_body = {
                    'registerUploadRequest': {
                        'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                        'owner': f'urn:li:person:{linkedin_id}',
                        'serviceRelationships': [
                            {'relationshipType': 'OWNER', 'identifier': 'urn:li:userGeneratedContent'}
                        ]
                    }
                }
                register_response = requests.post(register_url, headers=headers, json=register_body)
                if register_response.status_code == 200:
                    upload_data = register_response.json()['value']
                    upload_url = upload_data['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                    asset = upload_data['asset']

                    # Upload the image
                    upload_headers = {'Authorization': f'Bearer {access_token}'}
                    upload_response = requests.put(upload_url, headers=upload_headers, data=image_content)
                    if upload_response.status_code == 201:
                        # Post with the image
                        api_url = 'https://api.linkedin.com/v2/ugcPosts'
                        post_body = {
                            'author': f'urn:li:person:{linkedin_id}',
                            'lifecycleState': 'PUBLISHED',
                            'specificContent': {
                                'com.linkedin.ugc.ShareContent': {
                                    'shareCommentary': {'text': text},
                                    'shareMediaCategory': 'IMAGE',
                                    'media': [{'status': 'READY', 'media': asset}]
                                }
                            },
                            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
                        }
                        response = requests.post(api_url, headers=headers, json=post_body)
                        if response.status_code == 201:
                            logger.info(f"LinkedIn post with image successful for content ID {content.id}")
                            session.delete(content)
                            session.commit()
                            if image_url:  # Delete image even for text-only post if it exists
                                delete_image_from_ftp(image_url)
                            return True
                        else:
                            logger.error(f"LinkedIn image post failed: {response.status_code} - {response.text}")
                    else:
                        logger.error(f"Image upload failed: {upload_response.status_code} - {upload_response.text}")
                else:
                    logger.error(f"Upload registration failed: {register_response.status_code} - {register_response.text}")
            else:
                logger.error(f"Image download failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Image posting error for LinkedIn: {e}")

        # If image posting failed, proceed to text-only post (mirroring reference logic)

    # Text-only post (either no image or fallback after image failure)
    api_url = 'https://api.linkedin.com/v2/ugcPosts'
    post_body = {
        'author': f'urn:li:person:{linkedin_id}',
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {'text': text},
                'shareMediaCategory': 'NONE'
            }
        },
        'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
    }
    response = requests.post(api_url, headers=headers, json=post_body)
    if response.status_code == 201:
        logger.info(f"LinkedIn text post successful for content ID {content.id}")
        session.delete(content)
        session.commit()
        return True
    else:
        logger.error(f"LinkedIn text post failed: {response.status_code} - {response.text}")
        if response.status_code == 401:
            logger.error(f"Invalid LinkedIn token for user {connection.user_id}")
            connection.disconnected_at = datetime.now()
            session.commit()
        return False

def post_to_twitter(content: Content, connection: PlatformConnection, session: Session) -> bool:
    try:
        client = tweepy.Client(
            consumer_key=TWITTER_CLIENT_ID,
            consumer_secret=TWITTER_CLIENT_SECRET,
            access_token=connection.access_token,
            access_token_secret=connection.refresh_token
        )
        print("twitter_access_token", connection.access_token)
        print("twitter_refresh_token", connection.refresh_token)
        if content.image_url:
            response = requests.get(content.image_url, timeout=10)
            if response.status_code == 200:
                image_content = BytesIO(response.content)
                api = tweepy.API(tweepy.OAuth1UserHandler(
                    TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET,
                    connection.access_token, connection.refresh_token
                ))
                media = api.media_upload(filename="image", file=image_content)
                response = client.create_tweet(text=content.content, media_ids=[media.media_id])
                if response.data.get("id"):
                    logger.info(f"Twitter post with image successful for content ID {content.id}")
                    session.delete(content)
                    session.commit()
                    if content.image_url:  # Delete image even for text-only post if it exists
                        delete_image_from_ftp(content.image_url)
                    return True
                else:
                    logger.error("Twitter post with image failed: No tweet ID returned")
            else:
                logger.error(f"Image download failed: {response.status_code}")
        
        # Text-only post
        response = client.create_tweet(text=content.content)
        if response.data.get("id"):
            logger.info(f"Twitter text post successful for content ID {content.id}")
            session.delete(content)
            session.commit()
            return True
        else:
            logger.error("Twitter text post failed: No tweet ID returned")
            return False
    except tweepy.TweepyException as e:
        logger.error(f"Twitter posting error: {e}")
        return False

def post_to_wordpress(content: Content, connection: PlatformConnection, session: Session) -> bool:
    api_url = f"{connection.refresh_token}/wp-json/wp/v2/posts"  # Assuming refresh_token stores site_url
    headers = {
        "Authorization": connection.access_token,  # Assuming access_token is the auth header
        "Content-Type": "application/json"
    }
    data = {
        "title": "Scheduled Post",  # You might want to add a title field to Content
        "content": content.content,
        "status": "publish"
    }
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        if response.status_code == 201:
            logger.info(f"WordPress post successful for content ID {content.id}")
            session.delete(content)
            session.commit()
            if content.image_url:  # Delete image from FTP if it exists
                delete_image_from_ftp(content.image_url)
            return True
        else:
            logger.error(f"WordPress post failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"WordPress posting error: {e}")
        return False

# Scheduler Logic
# def check_and_post_due_content():
#     session = SessionLocal()
 #    try:
#         now = datetime.now()  # Local time
#         logger.info(f"Checking for due content at {now}")
#         due_contents = session.query(Content).filter(
#             Content.schedule_time <= now,
#             Content.status == "pending"
#         ).all()
#         logger.info(f"Found {len(due_contents)} due content items")
#         for content in due_contents:
#            logger.info(f"Processing content ID {content.id} for platform {content.platform}")
#             connection = session.query(PlatformConnection).filter(
#                 PlatformConnection.user_id == content.user_id,
#                 PlatformConnection.platform == content.platform,
#                 PlatformConnection.disconnected_at == None
#             ).first()
#             if not connection:
#                 logger.warning(f"No active connection for user {content.user_id} on {content.platform}")
#                 content.status = "failed"
#                 session.commit()
#                 continue
#             # Normalize platform comparison
#             platform_str = str(content.platform).lower()
#             if platform_str == "linkedin":
#                 success = post_to_linkedin(content, connection, session)
#             elif platform_str == "twitter":
#                 success = post_to_twitter(content, connection, session)
#             elif platform_str == "wordpress":
#                 success = post_to_wordpress(content, connection, session)
#             else:
#                 logger.warning(f"Unsupported platform: {platform_str}")
#                 content.status = "failed"
#                 session.commit()
#                 continue
#             if not success:
#                 content.status = "failed"
#                 session.commit()
#                 logger.info(f"Failed to post content ID {content.id} to {platform_str}")
#             else:
#                 logger.info(f"Successfully posted and deleted content ID {content.id} to {platform_str}")
#     except Exception as e:
#         session.rollback()
#         logger.error(f"Error in check_and_post_due_content: {e}")
#     finally:
#         session.close()

# # Initialize scheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(check_and_post_due_content, "interval", minutes=1)
# scheduler.start()





# Configuration
UPLOAD_DIR = "./uploads"
CACHE_EXPIRATION = 3600  # Cache expiration in seconds
temp_storage: Dict[str, 'CacheEntry'] = {}
content_storage: Dict[int, Dict] = {}

class DayContent(BaseModel):
    day: str
    subtopic: str
    quote: str

class WeeklyContent(BaseModel):
    week: str
    topic: str
    quote: str
    content_by_days: Dict[str, DayContent]

class CacheEntry:
    def __init__(self, content: Dict):
        self.temp_id = str(int(t.time()))
        self.content = content
        self.created_at = datetime.now()

def cleanup_expired_entries():
    """Remove expired cache entries."""
    current_time = datetime.now()
    expired_keys = [
        key for key, entry in temp_storage.items()
        if current_time - entry.created_at > timedelta(seconds=CACHE_EXPIRATION)
    ]
    for key in expired_keys:
        temp_storage.pop(key, None)
        content_storage.pop(int(key), None)

@app.post("/extract_content")
async def extract_content(
    file: UploadFile = File(...),
    week: int = Form(...),
    days: str = Form(...)
):
    file_path = None
    try:
        if week < 1:
            raise HTTPException(status_code=400, detail="Week must be a positive integer.")

        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_list = [day.strip().lower() for day in days.split(",")]
        
        invalid_days = [day for day in day_list if day not in valid_days]
        if invalid_days:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid day(s): {', '.join(invalid_days)}")

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        timestamp = int(t.time())
        file_path = os.path.join(UPLOAD_DIR, f"{timestamp}_{file.filename}")
        file_content = await file.read()
        
        # Save PDF file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        # Extract text from PDF
        try:
            with pdfplumber.open(file_path) as pdf:
                extracted_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
            if not extracted_text.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

        all_weeks_content = {}
        for current_week in range(1, week + 1):
            try:
                # Call the agent to analyze the text for the current week
                prompt = create_prompt(extracted_text, current_week, day_list)
                research_result = analyze_text(prompt)
                
                # Ensure the result is in the expected format
                week_key = f"Week {current_week}"
                if week_key not in research_result:
                    print(f"Warning: Week {current_week} not found in research result")
                    continue
                
                week_data = research_result[week_key]
                week_content = {
                    "topic": week_data["topic"],
                    "quote": week_data["quote"],
                    "content_by_days": {}
                }
                for day in day_list:
                    day_cap = day.capitalize()
                    if day_cap in week_data["content_by_days"]:
                        week_content["content_by_days"][day_cap] = DayContent(
                            day=day_cap,
                            subtopic=week_data["content_by_days"][day_cap]["subtopic"],
                            quote=week_data["content_by_days"][day_cap]["quote"]
                        )
                
                if week_content["content_by_days"]:
                    all_weeks_content[week_key] = WeeklyContent(
                        week=week_key,
                        topic=week_content["topic"],
                        quote=week_content["quote"],
                        content_by_days=week_content["content_by_days"]
                    )
            except Exception as e:
                print(f"Error processing week {current_week}: {str(e)}")
                continue

        if not all_weeks_content:
            raise HTTPException(status_code=500, detail="No content could be extracted for any week.")

        cache_entry = CacheEntry(all_weeks_content)
        temp_storage[cache_entry.temp_id] = cache_entry
        content_storage[int(cache_entry.temp_id)] = all_weeks_content
        cleanup_expired_entries()

        return {
            "status": "success",
            "message": "Content extracted successfully",
            "content": all_weeks_content,
            "temp_id": cache_entry.temp_id,
            "content_storage_key": int(cache_entry.temp_id),
            "timestamp": datetime.now().isoformat(),
            "expiration": (datetime.now() + timedelta(seconds=CACHE_EXPIRATION)).isoformat()
        }
    
    except Exception as e:
        print(f"Error during content extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Content extraction failed: {str(e)}")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
            except Exception as e:
                print(f"Error cleaning up file: {str(e)}")




@app.post("/regenerate_content")
async def regenerate_content(
    week_content: str | None = None,
):
    """Regenerate extracted content using the specified agent and task.
    Accepts only week_content as input.
    """
    try:
        if week_content is None:
            raise HTTPException(
                status_code=400,
                detail="week_content must be provided"
            )
            
        regenerated_content = {}
        
        regenerate_crew = Crew(
            agents=[regenrate_content_agent],
            tasks=[regenrate_content_task],
            process=Process.sequential
        )
        
        try:
            # Create inputs dictionary based on provided parameters
            inputs = {}
            if week_content is not None:
                inputs["week_content"] = week_content
            
            regenerate_result = regenerate_crew.kickoff(inputs=inputs)
            
            if isinstance(regenerate_result, dict) and 'output' in regenerate_result:
                regenerated_content = regenerate_result['output']
            elif regenerate_result:
                regenerated_content = str(regenerate_result)
        except Exception as e:
            print(f"Error regenerating content: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error regenerating content: {str(e)}"
            )
        
        # Create cache entry with only the provided content
        cache_data = {"week_content": week_content}
        new_cache_entry = CacheEntry(cache_data)
        temp_storage[new_cache_entry.temp_id] = new_cache_entry
        content_storage[int(new_cache_entry.temp_id)] = regenerated_content
        
        # Build response with only the relevant fields
        response = {
            "status": "success",
            "message": "Content regenerated successfully",
            # "temp_id": new_cache_entry.temp_id,
            # "content_storage_key": int(new_cache_entry.temp_id),
            # "timestamp": datetime.now().isoformat(),
            # "expiration": datetime.now() + timedelta(seconds=CACHE_EXPIRATION)
        }
        
        # Add the regenerated weekly content to the response
        response["week_content"] = regenerated_content
        
        return response
    
    except Exception as e:
        print(f"Error during content regeneration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Content regeneration failed: {str(e)}"
        )

    


@app.post("/regenerate_subcontent")
async def regenerate_subcontent(
    subcontent: str | None = None
):
    """Regenerate extracted subcontent using the specified agent and task.
    Accepts only subcontent as input.
    """
    try:
        if subcontent is None:
            raise HTTPException(
                status_code=400,
                detail="subcontent must be provided"
            )
            
        regenerated_content = {}
        
        regenerate_crew = Crew(
            agents=[regenrate_content_agent],
            tasks=[regenrate_content_task],
            process=Process.sequential
        )
        
        try:
            # Create inputs dictionary with the provided subcontent
            inputs = {}
            if subcontent is not None:
                inputs["subcontent"] = subcontent
            
            regenerate_result = regenerate_crew.kickoff(inputs=inputs)
            
            if isinstance(regenerate_result, dict) and 'output' in regenerate_result:
                regenerated_content = regenerate_result['output']
            elif regenerate_result:
                regenerated_content = str(regenerate_result)
        except Exception as e:
            print(f"Error regenerating subcontent: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error regenerating subcontent: {str(e)}"
            )
        
        # Create cache entry with the regenerated subcontent
        cache_data = {"subcontent": regenerated_content}
        new_cache_entry = CacheEntry(cache_data)
        temp_storage[new_cache_entry.temp_id] = new_cache_entry
        content_storage[int(new_cache_entry.temp_id)] = regenerated_content
        
        # Build response with the regenerated subcontent
        response = {
            "status": "success",
            "message": "Subcontent regenerated successfully",
            # "temp_id": new_cache_entry.temp_id,
            # "content_storage_key": int(new_cache_entry.temp_id),
            # "timestamp": datetime.now().isoformat(),
            # "expiration": datetime.now() + timedelta(seconds=CACHE_EXPIRATION)
        }
        
        response["subcontent"] = regenerated_content
        
        return response
    
    except Exception as e:
        print(f"Error during subcontent regeneration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Subcontent regeneration failed: {str(e)}"
        )






# Store default values from agents and tasks
DEFAULT_AGENTS = {
    "script_research_agent": {
        "role": f"""Script Researcher""",
        "goal": f"""
        Extract main theme and subcontent for each week. Identify most prominent content type "
        "(wisdom, ideas, or quotes) as main content, then derive relevant daily subcontents. "
        "Maintain consistent theme across week while varying daily applications."
        "Skip the Introduction page and about this book page and start from the first chapter."
    """,
        "backstory": f"""
        "Expert content analyst specializing in thematic extraction and content organization. "
        "Skilled at identifying core themes and deriving meaningful daily applications."
    """
    },
    "qc_agent": {
        "role": "Quality Control Specialist",
        "goal": """
        "Review and validate the temp_storage, ensuring compliance with the following:"
        " - Strict prohibition of specific forbidden words, phrases, and concepts (see list below)."
        " - Adherence to tone, language, and structural guidelines outlined in the company's quality standards."
        " - Elimination of plagiarism or content that does not align with professional, factual, and neutral style."
        "\n\nFORBIDDEN ELEMENTS (DO NOT USE UNDER ANY CIRCUMSTANCES):\n"
        "Strap, strap in, buckle, buckle up\n"
        "Delve, prepare, tapestry, vibrant\n"
        "Landscape, realm, embark\n"
        "Dive into, revolutionize\n"
        "Navigate/navigating (in any context)\n"
        "Any phrase starting with 'Delving into...'\n"
        "'In the rapidly changing' or 'ever-evolving'\n"
        "Taken by storm\n"
        "In the realm of\n"
        "Wild ride\n"
        "Hilarious (as an adjective)\n"
        "Get ready, be prepared (especially to open paragraphs)\n"
        "Brace yourself/yourselves\n"
        "Captivating, fascinating (as descriptors)\n"
        "Quest, adventure, journey (in any context)\n"
        "\nMANDATORY STYLE GUIDELINES:\n"
        " - Tone: Neutral, factual, and professional. Avoid all sensationalism.\n"
        " - Language: Clear, direct, and free of embellishment or dramatic flair.\n"
        " - Structure: Informative and concise, focusing on content rather than excitement.\n"
        " - Perspective: Objective, avoiding personal bias or emotional appeals.\n"
        "\nFINAL WARNING:\n"
        "Before approving content, ensure ZERO instances of forbidden words or concepts."
    """,
        "backstory": """
        "As a Quality Control Specialist, you ensure all content is compliant with strict company standards. "
        "Your focus is on identifying forbidden words and concepts, maintaining tone compliance, and ensuring "
        "content quality meets the highest professional standards."
    """
    },
    "script_rewriter_agent": {
        "role": """Platform-Specific Script Writer""",
        "goal": """Regenerate and enhance the given script while maintaining the platform's style and format, and incorporating any additional instructions such as desired tone or emotion.""",
        "backstory": """You're a specialized content creator who crafts platform-perfect content. You understand each platform's unique voice:
    - Instagram's visual storytelling with engaging captions
    - LinkedIn's professional and insightful tone
    - Twitter's concise and impactful messaging, complete the sentence in meaningful way.
    - Facebook's conversational engagement
    - WordPress's detailed and structured blogging
    - Youtube's ready-to-give tools for image or video generation
    - TikTok's ready-to-give tools for image or video generation
    
    You improve content while naturally matching each platform's style and adhering to its character/word limits. Additionally, you are adept at adjusting the tone and style based on specific instructions, such as making it funny, sad, inspirational, or any other desired emotion or characteristic."""
    },
    "regenrate_content_agent": {
        "role": """Content Regenerator""",
        "goal": """Regenrate the weekly content for the given week.""",
        "backstory": """You're a content regeneration specialist who excels at transforming existing content into fresh, engaging material. Your goal is to revitalize the weekly content theme and create compelling content for week. The content regenrated in this format:
    - content- If content is regenrate only regenerate the content of the week. The content would be wisdom, ideas, or quotes alond with a line defining the content."""
    },
    "regenrate_subcontent_agent": {
        "role": """Subcontent Regenerator """,
        "goal": """Regenerate the subcontent for the given day.""",
        "backstory": """You're a subcontent regeneration specialist who excels at transforming existing subcontent into fresh, engaging material. Your goal is to revitalize the subcontent theme and create compelling subcontent for day. The content regenrated in this format:
     - subcontent- If subcontent is regenrate only regenrate teh subcontent of the day.
     - Do not include any JSON formatting, extra newlines, or additional metadata."""
    },
    
    # Add other agents similarly
}

DEFAULT_TASKS = {
    "script_research_task": {
        "description": """
        "1.Analyze the provided text to identify the main theme and extract wisdom, quotes, or ideas 
        as the primary content type. Skip introductory or peripheral sections (e.g., author bios, 
        introductions) and focus on the core content. Organize the extracted content into weekly 
        themes and daily subcontents that vary in application while maintaining thematic consistency."
        "2. Skip Introduction page and also skip the about the author page. Start from fist chapter.\n"
        "3. Extract ONLY the chosen type of content.\n"
        "4. Process the content for week {week} and day {day}.\n"
        "5. Return the extracted content in a structured format.\n"
        "6. Extract the content on the basis of week and divide it into subcontents on the basis of days.\n"
        "7. Generate the subcontents on the basis of given days only which is provided in the input.\n"
    """,
        "expected_output": """
        "A object containing the extracted content divided by weeks and days. "
        "Week always contain the week number."
        "Dont generate metadata before the week."
        "Here is an example of the expected output format:"
        "week : content (A line defining the content.)\n"
        "  day : subcontent(generated from content of the week.)\n"
        "  day : subcontent(generated from content of the week.)\n"
        "first agent will chose the content type and then extract the content based on the content type."
        "first the content extracted on the basis of week will show in front of week "
        "then the subcontents will be generated on the basis of days which is divided from week content. only one subcontent in a day."
        "Each week will include maximum 6 daily entries, give only one subcontent for choosen day in output, each entry containing bullet points with brief explanations."
        "Remark never give subcontents for the days which are not provided in the input."
        "The output should be free of unnecessary metadata, bullet points, or other formatting."
    """
    },
    "qc_task": {
        "description": """
        "Review the scripts generated by the Script Researcher and Script Writer with a focus on the following:\n"
        " - Strict adherence to quality standards, including prohibition of forbidden words and phrases.\n"
        " - Compliance with mandatory tone and style guidelines (neutral, factual, and professional).\n"
        " - Ensuring content is plagiarism-free and adheres to the company's policy on clear and concise communication.\n"
        "\nThe review process must:\n"
        "1. Identify and flag any usage of forbidden words or phrases.\n"
        "2. Ensure the content's tone and style align with guidelines.\n"
        "3. Highlight any areas requiring revision, with specific corrective instructions.\n"
        "4. Provide clear feedback to the Script Writer for immediate revision.\n"
        "\nExpected Output:\n"
        " - A validation report that includes:\n"
        "   * Identified issues with specific references to flagged words or phrases.\n"
        "   * Recommendations for corrections or rewrites.\n"
        "   * A final decision to either approve or reject the script."
    """,
        "expected_output": """
        "A comprehensive QC validation report, listing identified issues, feedback for corrections, and a final verdict "
        "on whether the content is approved or rejected. The report must include specific points where content deviates from "
        "guidelines and provide actionable recommendations."
        "cleaned_content : The content after removing the forbidden words and phrases."
        "cleaned_content will pass to next agent for further processing."
        "have to pass the content to the next agent after removing the forbidden words and phrases.Make it a proper script and well sctructure format , in that I get a final output as script."
        "The output should be free of unnecessary metadata, bullet points, or other formatting."
    """
    },
    "script_rewriter_task": {
        "description": """Generate an improved version of the content following the platform's natural format and incorporating the additional instructions provided.

    Content to improve: '{text}'
    Target platform: {platform}
    Character/word limits: {limits}
    Additional instructions: {query}

    Platform Style Guidelines:
    Instagram: Engaging captions, emojis, spaced paragraphs, 3-5 hashtags, call-to-action. Make sure to keep the character and word limit for Instagram.
    LinkedIn: Professional hook, insights, clean formatting, thought-provoking close, 2-3 hashtags. Make sure to keep the character and word limit for LinkedIn.
    Twitter: Concise message within 280 chars, 1-2 hashtags. Make sure to keep the character and word limit for Twitter. Complete the sentence in meaningful way.
    Facebook: Conversational style, story elements, emoticons, engagement prompt. Make sure to keep the character and word limit for Facebook.
    WordPress: Blog structure with headers, intro, body, conclusion. Make sure to keep the character and word limit for WordPress.
    Youtube: A detailed post which further gives tools for image or video generation ready to upload on YouTube.
    TikTok: A detailed post which further gives tools for image or video generation ready to upload on TikTok.

    Output the content directly in the appropriate style without platform labels or section markers. The content should flow naturally while following platform conventions and reflecting the additional instructions.""",
        "expected_output": """A naturally formatted script that seamlessly incorporates the platform's style requirements and the additional instructions while improving the content quality and engagement potential."""
    },
    "regenrate_content_task": {
        "description": """Regenrate the weekly content according to the given input.""",
        "expected_output": """An object containing the regenerated content of  weeks .
    if weekly content provided only generated the week content.
    Here is an example of the expected output format:
    week : regenrated content (new content and if content is regenrated then subcontent will also be regenrated.)
    Generate only one content.
    NOTE: Don't generate the subcontent if the content is regenrated.
    here is an e.g. of how i want the output :
         "week: Embrace Change: The winds of change may be unsettling at first, but they often bring the seeds of growth and transformation."""""
    },
    "regenrate_subcontent_task": {
        "description": """Regenerate the subcontent according to the given input. """,
        "expected_output": """An object containing the regenerated subcontent of the day .
    if day subcontent provided only generated the day subcontent.
    Here is an example of the expected output format:
    day : regenrated subcontent (new subcontent and if subcontent is regenrated then content will not be regenrated.)
    Generate only one subcontent.
    NOTE: Don't generate the content if the subcontent is regenrated.
    here is an e.g. of how i want the output :
         "day: Embrace Change: The winds of change may be unsettling at first, but they often bring the seeds of growth and transformation."""""
    },
    # Add other tasks similarly
}




# Mutable current configurations that can be updated
# CURRENT_AGENTS = copy.deepcopy(DEFAULT_AGENTS)
# CURRENT_TASKS = copy.deepcopy(DEFAULT_TASKS)
current_agents = DEFAULT_AGENTS.copy()
current_tasks = DEFAULT_TASKS.copy()

class UpdateRequest(BaseModel):
    role: str = None
    goal: str = None
    backstory: str = None
    description: str = None
    expected_output: str = None


@app.get("/config/{name}")
def get_config(name: str, session: Session = Depends(get_db)):
    """
    Retrieve the current and default configurations for an agent or task by name.
    Fetches current configuration directly from the database.
    """
    # Try fetching an agent first
    from models import Agent, Task  # Import models here to avoid circular dependency
    agent = session.query(Agent).filter(Agent.name == name).first()
    if agent:
        # Fetch current configuration directly from the database
        current_agent = {
            "role": agent.role,
            "goal": agent.goal,
            "backstory": agent.backstory
        }
        # Default configuration from DEFAULT_AGENTS (assumed to be a predefined dict)
        default_agent = DEFAULT_AGENTS.get(name, {})
        return {"current": current_agent, "default": default_agent}

    # If not an agent, try fetching a task
    task = session.query(Task).filter(Task.name == name).first()
    if task:
        # Fetch current configuration directly from the database
        current_task = {
            "description": task.description,
            "expected_output": task.expected_output
        }
        # Default configuration from DEFAULT_TASKS (assumed to be a predefined dict)
        default_task = DEFAULT_TASKS.get(name, {})
        return {"current": current_task, "default": default_task}

    # If neither agent nor task is found, raise a 404 error
    raise HTTPException(status_code=404, detail="Agent or Task not found")


#-------------------------------------------------------------------------------------------


# Function to update specific class attributes in a Python file
def update_python_file(file_path: str, task_name: str, updates: dict):
    """
    Update the task definition in the specified Python file with new attribute values.
    
    Args:
        file_path (str): Path to the tasks.py file
        task_name (str): Name of the task to update
        updates (dict): Dictionary of attribute names and their new values
    """
    try:
        # Read the current content of the file
        with open(file_path, 'r') as file:
            content = file.read()

        # Define a regex pattern to match the task definition
        # This assumes tasks are defined like: task_name = Task(description="...", expected_output="...")
        pattern = rf'{task_name}\s*=\s*Task\(([\s\S]*?)\)'
        match = re.search(pattern, content)
        
        if not match:
            raise ValueError(f"Task '{task_name}' not found in {file_path}")

        # Extract the task’s attribute block
        task_block = match.group(0)
        attributes_content = match.group(1)

        # Update each attribute in the updates dictionary
        for key, value in updates.items():
            if value is not None:
                # Pattern to match an attribute like description="""..."""
                attr_pattern = rf'{key}\s*=\s*"""([\s\S]*?)"""'
                def replace_attr(match):
                    return f'{key}="""{value}"""'
                attributes_content = re.sub(attr_pattern, replace_attr, attributes_content, count=1)

        # Reconstruct the updated task block
        updated_task_block = f'{task_name} = Task({attributes_content})'

        # Replace the old task block with the updated one in the file content
        updated_content = content.replace(task_block, updated_task_block)

        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(updated_content)

        print(f"Successfully updated {task_name} in {file_path}")

    except Exception as e:
        print(f"Error updating {task_name} in {file_path}: {str(e)}")
        raise



# File paths
AGENTS_FILE = "agents.py"
TASKS_FILE = "tasks.py"

class AgentUpdateRequest(BaseModel):
    role: Optional[str] = None
    goal: Optional[str] = None
    backstory: Optional[str] = None

    @classmethod
    def from_raw_string(cls, raw_string: str):
        """Parse raw string into an instance of AgentUpdateRequest."""
        try:
            # Assume the raw string is formatted as key-value pairs separated by newlines
            data = {}
            lines = raw_string.strip().split("\n")
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ["role", "goal", "backstory"]:
                        data[key] = value
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse raw string: {str(e)}")


class TaskUpdateRequest(BaseModel):
    description: Optional[str] = None
    expected_output: Optional[str] = None

    @classmethod
    def from_raw_string(cls, raw_string: str):
        """Parse raw string into an instance of TaskUpdateRequest."""
        try:
            # Assume the raw string is formatted as key-value pairs separated by newlines
            data = {}
            lines = raw_string.strip().split("\n")
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ["description", "expected_output"]:
                        data[key] = value
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse raw string: {str(e)}")


# Utility functions to update Python files
def update_agent_attribute(file_path: str, agent_name: str, attribute: str, new_value: str):
    """Update an agent's attribute in the specified Python file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern to find the entire agent definition
    agent_pattern = rf'{agent_name}\s*=\s*Agent\(([\s\S]*?)\)'
    match = re.search(agent_pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError(f"Agent '{agent_name}' not found in {file_path}")

    agent_def = match.group(1)
    
    # Pattern to find the specific attribute, capturing 'f' if present
    attr_pattern = rf'{attribute}\s*=\s*(f?)"""\s*([\s\S]*?)\s*"""'
    def replace_attr(match):
        f_prefix = match.group(1)  # 'f' if present
        return f'{attribute}={f_prefix}"""{new_value}"""'
    
    updated_agent_def = re.sub(attr_pattern, replace_attr, agent_def, count=1)
    updated_content = content.replace(agent_def, updated_agent_def)
    
    with open(file_path, 'w') as f:
        f.write(updated_content)

def update_task_attribute(file_path: str, task_name: str, attribute: str, new_value: str):
    """Update a task's attribute in the specified Python file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern to find the entire task definition
    task_pattern = rf'{task_name}\s*=\s*Task\(([\s\S]*?)\)'
    match = re.search(task_pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError(f"Task '{task_name}' not found in {file_path}")

    task_def = match.group(1)
    
    # Pattern to find the specific attribute, capturing 'f' if present
    attr_pattern = rf'{attribute}\s*=\s*(f?)"""\s*([\s\S]*?)\s*"""'
    def replace_attr(match):
        f_prefix = match.group(1)  # 'f' if present
        return f'{attribute}={f_prefix}"""{new_value}"""'
    
    updated_task_def = re.sub(attr_pattern, replace_attr, task_def, count=1)
    updated_content = content.replace(task_def, updated_task_def)
    
    with open(file_path, 'w') as f:
        f.write(updated_content)

# New API Endpoints


# PUT endpoint with proper session management
@app.put("/agents/{agent_name}")
def update_agent(agent_name: str, update: AgentUpdateRequest = Body(...), session: Session = Depends(get_db)):
    # Fetch the agent using the same session
    agent = session.query(Agent).filter(Agent.name == agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update the agent’s attributes
    if update.role is not None:
        agent.role = update.role
    if update.goal is not None:
        agent.goal = update.goal
    if update.backstory is not None:
        agent.backstory = update.backstory

    # Commit the changes
    session.commit()
    
    return {"message": "Agent updated successfully"}

# Assuming get_db is a dependency that provides a database session
@app.put("/tasks/{task_name}")
def update_task(
    task_name: str,
    update: TaskUpdateRequest = Body(...),
    session: Session = Depends(get_db)
):
    """
    Update a task's attributes in the database using a JSON body.
    """
    print(update)
    # Fetch the task from the database
    task = session.query(Task).filter(Task.name == task_name).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update only the provided fields
    if update.description is not None:
        task.description = update.description
    if update.expected_output is not None:
        task.expected_output = update.expected_output

    # Commit the changes to the database
    session.commit()

    return {"message": "Task updated successfully"}


# Define day offsets for date calculation
day_offsets = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}


# Pydantic model for input validation
class UpdateScheduleTime(BaseModel):
    new_time: str  # Expected format: "HH:MM", e.g., "14:30"

@app.patch("/content/schedule-time")
async def update_schedule_time_by_content(content: str, update_data: UpdateScheduleTime):
    # Get a database session
    session = next(get_db_manager().get_db_session())
    try:
        # Find the content by its full text
        db_content = session.query(Content).filter(Content.content == content).first()
        if not db_content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Parse the new time string into a time object
        try:
            new_time = datetime.strptime(update_data.new_time, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

        # Extract the existing date and combine it with the new time
        existing_date = db_content.schedule_time.date()
        new_schedule_time = datetime.combine(existing_date, new_time)

        # Update the content's schedule_time
        db_content.schedule_time = new_schedule_time
        session.commit()

        # Return a success message
        return {"message": "Schedule time updated successfully"}

    except HTTPException as e:
        # Re-raise HTTP exceptions (e.g., 404, 400)
        raise e
    except Exception as e:
        # Roll back the session on unexpected errors
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating schedule time: {str(e)}")
    finally:
   
        session.close()



# Pydantic model for request validation
class DuplicateScheduleTimeRequest(BaseModel):
    source_week: int       
    source_day: str        
    platform: str          

# API endpoint to duplicate schedule times
@app.post("/duplicate-schedule-times")
async def duplicate_schedule_times(request: DuplicateScheduleTimeRequest):
    session = next(get_db_manager().get_db_session())
    try:
        # Normalize input
        source_week = request.source_week
        source_day = request.source_day.title() 
        platform = request.platform.upper()   


        source_posts = session.query(Content).filter(
            Content.week == source_week,
            Content.day == source_day,
            Content.platform == platform
        ).order_by(Content.platform_post_no).all()

        if not source_posts:
            raise HTTPException(
                status_code=404,
                detail="No posts found for the specified source week, day, and platform"
            )


        source_times = [post.schedule_time.time() for post in source_posts]

        distinct_days = session.query(Content.week, Content.day).filter(
            Content.platform == platform
        ).distinct().all()

        # Step 3: Update all posts for the platform across all days and weeks
        for week, day in distinct_days:
            target_posts = session.query(Content).filter(
                Content.week == week,
                Content.day == day,
                Content.platform == platform
            ).order_by(Content.platform_post_no).all()

            # Update each post's time to match the corresponding source post
            for i, post in enumerate(target_posts):
                if i < len(source_times):
                    new_time = source_times[i]
                    existing_date = post.schedule_time.date()
                    post.schedule_time = datetime.combine(existing_date, new_time)

        # Step 4: Commit changes
        session.commit()
        return {"message": "Schedule times duplicated successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error duplicating schedule times: {str(e)}"
        )
    finally:
        session.close()



@app.put("/regenerate_script_v1")
async def regenerate_script(content: str, query: str, platform: str, db: Session = Depends(lambda: get_db_manager().get_db_session())):
    """
    Regenerate a script by its content using the script writer agent, guided by a provided query and target platform.

    Args:
        content (str): The content of the script to regenerate.
        query (str): The prompt or instruction to guide the script regeneration (e.g., "make it more engaging").
        platform (str): The target platform for the regenerated script (e.g., "twitter", "facebook").
        db (Session): The database session dependency.

    Returns:
        dict: A dictionary containing the status, message, and details of the regenerated script.

    Raises:
        HTTPException: If the content is not found, the platform is invalid, or regeneration fails.
    """
    session = next(get_db_manager().get_db_session())
    
    try:
        # Retrieve the existing content from the database
        existing_content = session.query(Content).filter(Content.content == content).first()
        if not existing_content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Normalize and validate the platform
        platform = platform.lower()
        if platform not in PLATFORM_LIMITS:
            raise HTTPException(status_code=400, detail="Invalid platform specified")

        # Create a crew with the script rewriter agent
        script_crew = Crew(
            agents=[script_rewriter_agent],
            tasks=[script_rewriter_task],
            process=Process.sequential
        )

        # Pass the platform and query to the agent for script regeneration
        crew_result = script_crew.kickoff(
            inputs={
                "text": existing_content.content,
                "day": existing_content.day,
                "week": existing_content.week,
                "platform": platform,
                "limits": PLATFORM_LIMITS[platform],
                "query": query
            }
        )

        # Extract the regenerated content from the crew result
        if isinstance(crew_result, dict):
            new_content = str(crew_result.get('output', ''))
        elif hasattr(crew_result, 'raw_output'):
            new_content = str(crew_result.raw_output)
        elif hasattr(crew_result, 'output'):
            new_content = str(crew_result.output)
        else:
            new_content = str(crew_result)

        # Ensure content was generated
        if not new_content:
            raise HTTPException(status_code=500, detail="Failed to generate new content")

        # Process the new content for the specified platform
        processed_content = process_content_for_platform(
            new_content,
            platform,
            PLATFORM_LIMITS[platform]
        )

        # Generate a new title from the processed content
        new_title = extract_title_from_content(processed_content)

        # Update the existing content in the database
        existing_content.content = processed_content
        existing_content.title = new_title
        existing_content.platform = platform  # Update to the new platform
        existing_content.date_upload = datetime.now()  # Update timestamp
        session.commit()

        # Return the updated content details
        return {
            "status": "success",
            "message": "Script regenerated successfully",
            "content": {
                "id": existing_content.id,
                "week": existing_content.week,
                "day": existing_content.day,
                "title": new_title,
                "content": processed_content,
                "platform": existing_content.platform,  # Reflects the new platform
                "date_upload": existing_content.date_upload.isoformat(),
                "file_name": existing_content.file_name
            }
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate script: {str(e)}"
        )
    finally:
        session.close()

# app.mount("/static", StaticFiles(directory="static"), name="static")

# @app.post("/generate_image")
# async def generate_image_endpoint(content: str, query: str, db: Session = Depends(lambda: get_db_manager().get_db_session())):
#     """
#     Generate an image based on provided content and a query string, store it in FTP, and save the permanent URL.

#     Args:
#         content (str): The content to fetch from the database and use for image generation.
#         query (str): A string to guide the image generation (e.g., "in watercolor style").
#         db (Session): The database session dependency.

#     Returns:
#         dict: A dictionary with status, message, and the generated image URL.

#     Raises:
#         HTTPException: If content is not found or image generation fails.
#     """
#     session = next(get_db_manager().get_db_session())
#     try:
#         # Retrieve the content from the database
#         existing_content = session.query(Content).filter(Content.content == content).first()
#         if not existing_content:
#             raise HTTPException(status_code=404, detail="Content not found")

#         # Generate the image using the content and query
#         temp_image_url = generate_image(query, existing_content.content)

#         # Download the temporary image asynchronously
#         async with httpx.AsyncClient() as client:
#             response = await client.get(temp_image_url)
#             if response.status_code != 200:
#                 raise HTTPException(status_code=500, detail="Failed to download temporary image")
#             image_data = response.content

#         # FTP credentials and configuration
#         ftp_host = os.getenv("ftp_host")
#         ftp_user = os.getenv("ftp_user")
#         ftp_pass = os.getenv("ftp_pass")
#         filename = f"image_{existing_content.id}.png"  # Unique filename using content ID

#         # Upload the image to FTP
#         with FTP(ftp_host) as ftp:
#             ftp.login(user=ftp_user, passwd=ftp_pass)
#             ftp.storbinary(f"STOR {filename}", io.BytesIO(image_data))

#         # Construct the permanent URL
#         permanent_url = f"https://lookwhatwemadeyou.com/nishant/{filename}"

#         # Update the database with the permanent URL instead of the temporary one
#         existing_content.image_url = permanent_url
#         session.commit()

#         return {
#             "status": "success",
#             "message": "Image generated successfully",
#             "image_url": permanent_url
#         }

#     except Exception as e:
#         session.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to generate image: {str(e)}"
#         )
#     finally:
#         session.close()


@app.post("/generate_image")
async def generate_image_endpoint(content: str, query: str, db: Session = Depends(lambda: get_db_manager().get_db_session())):
    """
    Generate an image based on provided content and a query string, store it in SFTP, and save the permanent URL.

    Args:
        content (str): The content to fetch from the database and use for image generation.
        query (str): A string to guide the image generation (e.g., "in watercolor style").
        db (Session): The database session dependency.

    Returns:
        dict: A dictionary with status, message, and the generated image URL.

    Raises:
        HTTPException: If content is not found or image generation fails.
    """
    session = next(get_db_manager().get_db_session())
    try:
        # Retrieve the content from the database
        existing_content = session.query(Content).filter(Content.content == content).first()
        if not existing_content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Generate the image using the content and query
        temp_image_url = generate_image(query, existing_content.content)

        # Download the temporary image asynchronously
        async with httpx.AsyncClient() as client:
            response = await client.get(temp_image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to download temporary image")
            image_data = response.content

        # SFTP credentials and configuration
        sftp_host = os.getenv("SFTP_HOST")
        sftp_user = os.getenv("SFTP_USER")
        sftp_pass = os.getenv("SFTP_PASS")
        sftp_port = int(os.getenv("SFTP_PORT", "22"))  # Default to 22 if not specified
        filename = f"image_{existing_content.id}.png"  # Unique filename using content ID
        remote_path = f"/home/{sftp_user}/public_html/nishant/{filename}"

        # Upload the image to SFTP
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=sftp_host, port=sftp_port, username=sftp_user, password=sftp_pass)
            sftp = ssh_client.open_sftp()

            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                try:
                    sftp.mkdir(remote_dir)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to create SFTP directory {remote_dir}: {str(e)}")

            # Upload the image
            with sftp.open(remote_path, 'wb') as remote_file:
                remote_file.write(image_data)
            sftp.close()
            ssh_client.close()

        except paramiko.AuthenticationException:
            raise HTTPException(status_code=500, detail="SFTP authentication failed. Check credentials.")
        except paramiko.SSHException as ssh_e:
            raise HTTPException(status_code=500, detail=f"SFTP error: {str(ssh_e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image to SFTP: {str(e)}")

        # Construct the permanent URL
        permanent_url = f"https://vernalcontentum.com/nishant/{filename}"

        # Update the database with the permanent URL instead of the temporary one
        existing_content.image_url = permanent_url
        session.commit()

        return {
            "status": "success",
            "message": "Image generated successfully",
            "image_url": permanent_url
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate image: {str(e)}"
        )
    finally:
        session.close()



@app.post("/generate_custom_scripts_v2")
async def generate_custom_scripts(
    file: UploadFile = File(...),
    weeks: int = 1,
    days: str = "Monday,Wednesday,Friday",
    platform_posts: str = "instagram:3,facebook:2,twitter:1,linkedin:1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_path = None
    try:
        # Validate and save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        file_type = Path(file.filename).suffix.lstrip('.')

        # Validate days
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        selected_days = [day.strip().title() for day in days.split(",")]
        invalid_days = [day for day in selected_days if day.lower() not in valid_days]
        if invalid_days:
            raise HTTPException(status_code=400, detail=f"Invalid day(s): {', '.join(invalid_days)}")

        # Parse and validate platform posts
        platform_post_counts = {}
        for p in platform_posts.split(","):
            try:
                platform, count = p.split(":")
                platform = platform.lower()
                count = int(count)
                if platform not in PLATFORM_LIMITS:
                    raise ValueError(f"Invalid platform: {platform}")
                platform_post_counts[platform] = count
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid platform_posts format: {str(e)}")

        # Extract text from the file
        processor = FileProcessor()
        extracted_text = processor.extract_text_from_file(file_path)
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

        # Calculate the starting Monday for Week 1
        week1_monday = datetime.now().date() + timedelta(days=(7 - datetime.now().weekday()) % 7)

        async def generate_responses():
            yield "["
            first_item = True
            for platform, post_count in platform_post_counts.items():
                for week in range(1, weeks + 1):
                    for day in selected_days:
                        try:
                            # Step 1: Generate content using create_prompt and analyze_text
                            prompt = create_prompt(extracted_text, week, [day.lower()])
                            research_result = analyze_text(prompt)

                            # Step 2: Extract content from research_result
                            week_key = f"Week {week}"
                            researched_content = extracted_text  # Fallback
                            if isinstance(research_result, dict) and week_key in research_result:
                                week_data = research_result[week_key]
                                day_cap = day.capitalize()
                                if isinstance(week_data, dict) and "content_by_days" in week_data and day_cap in week_data["content_by_days"]:
                                    day_data = week_data["content_by_days"][day_cap]
                                    researched_content = (
                                        f"Topic: {week_data.get('topic', 'N/A')}\n"
                                        f"Quote: {week_data.get('quote', 'N/A')}\n"
                                        f"Subtopic: {day_data.get('subtopic', 'N/A')}\n"
                                        f"Subtopic Quote: {day_data.get('quote', 'N/A')}"
                                    )
                                else:
                                    print(f"Warning: Day {day_cap} not found in content_by_days for platform {platform}, Week {week}")
                            else:
                                print(f"Warning: Week {week} not found in research result for platform {platform}")

                            # Step 3: Quality control
                            qc_crew = Crew(agents=[qc_agent], tasks=[qc_task], process=Process.sequential)
                            qc_result = qc_crew.kickoff(inputs={"text": researched_content})
                            cleaned_content = qc_result.get('output', researched_content) if isinstance(qc_result, dict) else researched_content

                            # Step 4: Platform-specific content generation
                            rewriter_crew = Crew(agents=[script_rewriter_agent], tasks=[script_rewriter_task], process=Process.sequential)
                            for post_index in range(post_count):
                                crew_result = rewriter_crew.kickoff(
                                    inputs={
                                        "text": cleaned_content,
                                        "day": day,
                                        "week": week,
                                        "platform": platform,
                                        "limits": PLATFORM_LIMITS[platform],
                                        "query": f"Generate engaging content for {platform}"
                                    }
                                )
                                # Extract the regenerated content
                                base_content = ""
                                if isinstance(crew_result, dict):
                                    base_content = str(crew_result.get('output', ''))
                                elif hasattr(crew_result, 'raw_output'):
                                    base_content = str(crew_result.raw_output)
                                elif hasattr(crew_result, 'output'):
                                    base_content = str(crew_result.output)
                                else:
                                    base_content = str(crew_result)

                                # Fallback to cleaned_content if no new content is generated
                                if not base_content.strip():
                                    base_content = cleaned_content
                                    print(f"Warning: No content generated by rewriter_crew for {platform}, Week {week}, Day {day}, Post {post_index + 1}")

                                # Process content for the platform
                                processed_content = process_content_for_platform(base_content, platform, PLATFORM_LIMITS[platform])
                                title = f"{platform} - Week {week}, {day} - Post {post_index + 1}"
                                # Fixed: Correct usage of time(9, 0)
                                from datetime import datetime, timedelta, time
                                schedule_time = datetime.combine(
                                    week1_monday + timedelta(days=7*(week-1) + day_offsets[day]),
                                    time(9, 0)  # Correctly instantiate time object
                                ) + timedelta(hours=3*post_index)

                                # Step 5: Save to database
                                content_obj = Content(
                                    user_id=current_user.id,
                                    week=week,
                                    day=day,
                                    content=processed_content,
                                    title=title,
                                    date_upload=datetime.now(),
                                    platform=platform,
                                    file_name=file.filename,
                                    file_type=file_type,
                                    platform_post_no=f"{platform} {post_index + 1}",
                                    schedule_time=schedule_time
                                )
                                db.add(content_obj)
                                db.commit()

                                # Step 6: Prepare response
                                post = ContentResponse1(
                                    week=week,
                                    day=day,
                                    platform_post_no=f"{platform} {post_index + 1}",
                                    schedule_time=schedule_time,
                                    title=title,
                                    content=processed_content,
                                    platform=platform,
                                    timestamp=datetime.now().isoformat(),
                                    word_count=len(processed_content.split()),
                                    char_count=len(processed_content)
                                )
                                if not first_item:
                                    yield ","
                                first_item = False
                                yield post.json()
                                await asyncio.sleep(0.1)  # Reduced sleep for better performance
                        except Exception as e:
                            print(f"Error processing Week {week}, Day {day}, Post {post_index + 1} for platform {platform}: {str(e)}")
                            traceback.print_exc()
                            continue
            yield "]"

        return StreamingResponse(generate_responses(), media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up file: {str(e)}")


# initialize_database()

# # FastAPI Endpoint (for manual triggering or monitoring, optional)
# @app.get("/check-scheduled-posts")
# def check_scheduled_posts(db: Session = Depends(get_db)):
#     check_and_post_due_content()
#     return {"message": "Scheduled posts checked"}




import asyncio
import os
import subprocess
import sys
import logging
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller, BrowserConfig, Browser
from dotenv import load_dotenv
from database import DatabaseManager1, engine, Base, Campaign, RawData, MachineContent
from text_processing import Posts, ProcessedPosts, ProcessedPost, lemmatize_text, stem_text, remove_stopwords, extract_entities, extract_topics, extract_keywords
from sqlalchemy.exc import SQLAlchemyError
from utilities import process_tweets
from datetime import datetime, time
from machine_agent import ContentGeneratorAgent, IdeaGeneratorAgent
import requests

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def ensure_playwright_installed():
    playwright_installed_flag = os.path.join(os.path.expanduser("~"), ".playwright_installed")
    if not os.path.exists(playwright_installed_flag):
        try:
            logger.info("Installing Playwright dependencies...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            #subprocess.check_call([sys.executable, "-m", "playwright", "install", ""])
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            subprocess.check_call(["playwright", "install"])
            with open(playwright_installed_flag, "w") as f:
                f.write("Playwright installed")
            logger.info("Playwright installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Playwright: {e}")
            sys.exit(1)
    else:
        logger.info("Playwright is already installed, skipping installation.")

ensure_playwright_installed()
db_manager = DatabaseManager1()

class AnalyzeInput(BaseModel):
    campaign_name: str
    campaign_id: str
    urls: Optional[List[str]] = None
    query: str
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    type: Optional[str] = None
    depth: int = 3
    max_pages: int = 10
    batch_size: int = 1
    include_links: bool = True
    stem: bool = False
    lemmatize: bool = False
    remove_stopwords_toggle: bool = False
    extract_persons: bool = False
    extract_organizations: bool = False
    extract_locations: bool = False
    extract_dates: bool = False
    topic_tool: str
    num_topics: int = 3
    iterations: int = 25
    pass_threshold: float = 0.7

class ProgressStatus(BaseModel):
    task_id: str
    status: str  # "processing", "completed", "failed"
    progress: int  # 0-100
    current_step: str
    message: str
    created_at: datetime
    updated_at: datetime

@app.post("/analyze")
async def analyze_websites(input_data: AnalyzeInput):
    # Generate task ID for progress tracking
    task_id = str(uuid.uuid4())
    
    # Initialize progress tracking
    progress_storage[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "current_step": "starting",
        "message": "Initializing analysis...",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "result": None,
        "error": None
    }
    
    # Start background task
    asyncio.create_task(process_analysis_background(task_id, input_data))
    
    return {
        "status": "started",
        "task_id": task_id,
        "message": "Analysis started, use task_id to check progress"
    }

async def process_analysis_background(task_id: str, input_data: AnalyzeInput):
    try:
        # Generate task ID for progress tracking
        task_id = str(uuid.uuid4())
        
        # Initialize progress storage
        progress_storage[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "current_step": "starting",
            "message": "Initializing analysis...",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "result": None,
            "error": None
        }
        
        # Start background processing
        asyncio.create_task(process_analysis_background(task_id, input_data))
        
        return {
            "status": "started",
            "task_id": task_id,
            "message": "Analysis started, use task_id to check progress"
        }
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

async def process_analysis_background(task_id: str, input_data: AnalyzeInput):
    try:
        campaign_name = input_data.campaign_name.strip()
        campaign_id = input_data.campaign_id.strip()
        urls = input_data.urls or []
        query = input_data.query.strip()
        keywords = input_data.keywords or []
        description = input_data.description
        type = input_data.type or "url"
        depth = input_data.depth
        max_pages = input_data.max_pages
        batch_size = input_data.batch_size
        include_links = input_data.include_links
        stem = input_data.stem
        lemmatize = input_data.lemmatize
        remove_stopwords_toggle = input_data.remove_stopwords_toggle
        extract_persons = input_data.extract_persons
        extract_organizations = input_data.extract_organizations
        extract_locations = input_data.extract_locations
        extract_dates = input_data.extract_dates
        topic_tool = input_data.topic_tool
        num_topics = input_data.num_topics
        iterations = input_data.iterations
        pass_threshold = input_data.pass_threshold

        # Update progress: Validation
        progress_storage[task_id].update({
            "progress": 5,
            "current_step": "validating",
            "message": "Validating input parameters...",
            "updated_at": datetime.now()
        })

        # Validate inputs
        if not campaign_name:
            logger.error("Campaign name is empty")
            progress_storage[task_id].update({
                "status": "failed",
                "error": "Campaign name cannot be empty",
                "updated_at": datetime.now()
            })
            return
        if not campaign_id:
            logger.error("Campaign ID is empty")
            progress_storage[task_id].update({
                "status": "failed",
                "error": "Campaign ID cannot be empty",
                "updated_at": datetime.now()
            })
            return
        if not all(isinstance(url, str) and url.strip() for url in urls):
            logger.error(f"Invalid URLs provided: {urls}")
            progress_storage[task_id].update({
                "status": "failed",
                "error": "All URLs must be non-empty strings",
                "updated_at": datetime.now()
            })
            return
        if not query:
            logger.error("Query is empty")
            progress_storage[task_id].update({
                "status": "failed",
                "error": "Query cannot be empty",
                "updated_at": datetime.now()
            })
            return

        # Update progress: Web scraping setup
        progress_storage[task_id].update({
            "progress": 15,
            "current_step": "scraping_setup",
            "message": "Setting up web scraping...",
            "updated_at": datetime.now()
        })

        logger.info(
            f"Received request for campaign: {campaign_name} (ID: {campaign_id}), "
            f"num_topics: {num_topics}, iterations: {iterations}, pass_threshold: {pass_threshold}, "
            f"topic_tool: {topic_tool}, urls: {urls}, keywords: {keywords}, depth: {depth}, max_pages: {max_pages}"
        )

        # Update progress: Web scraping setup
        progress_storage[task_id].update({
            "progress": 15,
            "current_step": "scraping_setup",
            "message": "Setting up web scraping...",
            "updated_at": datetime.now()
        })

        task = (
            f"{query} for this: {urls}. "
            f"Keywords: {', '.join(keywords) if keywords else 'None'}. "
            f"Web scraping depth was {depth}, "
            f"no. of pages to extract {max_pages}, "
            f"batch size should be {batch_size}, "
            f"{'include 1-2 links' if include_links else 'exclude links'}."
        )

        # Update progress: Web scraping in progress
        progress_storage[task_id].update({
            "progress": 25,
            "current_step": "scraping",
            "message": f"Scraping {len(urls)} URLs...",
            "updated_at": datetime.now()
        })

        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        config = BrowserConfig(headless=True, disable_security=True)
        browser = Browser(config=config)
        controller = Controller(output_model=Posts)
        agent = Agent(
            task=task,
            llm=llm,
            controller=controller,
            browser=browser,
        )

        # Update progress: Web scraping in progress
        progress_storage[task_id].update({
            "progress": 25,
            "current_step": "scraping",
            "message": f"Scraping {len(urls)} URLs...",
            "updated_at": datetime.now()
        })

        history = await agent.run()
        result = history.final_result()

        if result:
            parsed_posts: Posts = Posts.model_validate_json(result)
            logger.info(f"Scraped {len(parsed_posts.posts)} posts")
            
            # Update progress: Scraping completed
            progress_storage[task_id].update({
                "progress": 50,
                "current_step": "scraping_complete",
                "message": f"Successfully scraped {len(parsed_posts.posts)} posts",
                "updated_at": datetime.now()
            })
        else:
            logger.warning("No results found from scraping")
            progress_storage[task_id].update({
                "status": "completed",
                "progress": 100,
                "current_step": "completed",
                "message": "No results found from scraping",
                "updated_at": datetime.now()
            })
            return

        # Update progress: Content processing
        progress_storage[task_id].update({
            "progress": 60,
            "current_step": "processing_content",
            "message": "Processing scraped content...",
            "updated_at": datetime.now()
        })

        texts = [post.text for post in parsed_posts.posts]
        logger.info(f"Processing {len(texts)} texts for topic modeling")
        
        # Update progress: Topic modeling
        progress_storage[task_id].update({
            "progress": 70,
            "current_step": "topic_modeling",
            "message": "Analyzing topics and extracting entities...",
            "updated_at": datetime.now()
        })
        
        topics = extract_topics(texts, topic_tool, num_topics, iterations, query, keywords, urls)
        if not topics:
            logger.warning("No topics generated; using fallback keyword extraction")
            topics = extract_keywords(texts, num_keywords=num_topics * 5)
            message = "No topics generated; used keyword extraction as fallback"
        else:
            message = None

        # Update progress: Entity extraction
        progress_storage[task_id].update({
            "progress": 80,
            "current_step": "entity_extraction",
            "message": "Extracting entities and processing text...",
            "updated_at": datetime.now()
        })

        processed_posts = ProcessedPosts(posts=[
            ProcessedPost(
                text=post.text,
                lemmatized_text=lemmatize_text(post.text) if lemmatize else None,
                stemmed_text=stem_text(post.text) if stem else None,
                stopwords_removed_text=remove_stopwords(post.text) if remove_stopwords_toggle else None,
                **extract_entities(post.text, extract_persons, extract_organizations, extract_locations, extract_dates),
                topics=topics
            ) for post in parsed_posts.posts
        ])

        # Update progress: Database storage
        progress_storage[task_id].update({
            "progress": 90,
            "current_step": "storing_data",
            "message": "Storing results in database...",
            "updated_at": datetime.now()
        })

        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            get_db_manager().store_raw_texts,
            query,
            ','.join(urls) if urls else '',
            processed_posts,
            campaign_name,
            campaign_id,
            keywords,
            description,
            type
        )

        response_data = {
            "status": "success",
            "campaign_name": campaign_name,
            "campaign_id": campaign_id,
            "task": task,
            "keywords": keywords,
            "posts": [post.model_dump() for post in processed_posts.posts],
            "topics": topics
        }
        if message:
            response_data["message"] = message

        # Update progress: Completed
        progress_storage[task_id].update({
            "status": "completed",
            "progress": 100,
            "current_step": "completed",
            "message": "Analysis completed successfully!",
            "result": response_data,
            "updated_at": datetime.now()
        })
        
        logger.info(f"Analysis completed for task {task_id}")
        
    except Exception as e:
        logger.error(f"Error in background analysis: {str(e)}")
        progress_storage[task_id].update({
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.now()
        })

@app.get("/analyze/status/{task_id}")
async def get_analysis_status(task_id: str):
    """Get the current status of an analysis task"""
    if task_id not in progress_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return progress_storage[task_id]

class GenerateIdeasInput(BaseModel):
    topics: List[str]
    posts: List[str]  # Scraped post texts from analyze_websites
    days: List[str]


# Updated /generate-ideas endpoint
@app.post("/generate-ideas")
async def generate_ideas(
    topics: str = Form(...),  # Comma-separated string, e.g., "topic1, topic2"
    posts: str = Form(...),   # Single post text as a string
    days: str = Form(...)     # Comma-separated string, e.g., "Monday, Tuesday"
):
    try:
        # Parse comma-separated strings
        topics_list = [t.strip() for t in topics.split(",") if t.strip()]
        posts_list = [posts.strip()] if posts.strip() else []
        days_list = [d.strip() for d in days.split(",") if d.strip()]

        # Validate inputs
        if not topics_list:
            logger.error("Topics string is empty or invalid")
            raise HTTPException(status_code=400, detail="Topics cannot be empty")
        if not posts_list:
            logger.error("Posts string is empty")
            raise HTTPException(status_code=400, detail="Posts cannot be empty")
        if not days_list:
            logger.error("Days string is empty or invalid")
            raise HTTPException(status_code=400, detail="Days cannot be empty")
        if not all(isinstance(t, str) for t in topics_list):
            logger.error("Topics must all be strings")
            raise HTTPException(status_code=400, detail="All topics must be strings")
        if not all(isinstance(d, str) for d in days_list):
            logger.error("Days must all be strings")
            raise HTTPException(status_code=400, detail="All days must be strings")

        logger.info(f"Received idea generation request: {len(topics_list)} topics, 1 post, {len(days_list)} days")

        # Initialize LLM and agent
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.5  # Moderate temperature for creative ideas
        )
        agent = IdeaGeneratorAgent(llm=llm)

        # Generate ideas (number of ideas equals number of days)
        ideas = await agent.generate_ideas(topics_list, posts_list, days_list)
        
        response_data = {
            "status": "success",
            "topics": topics_list,
            "days": days_list,
            "ideas": ideas
        }
        logger.info(f"Generated {len(ideas)} ideas: {ideas}")
        return response_data

    except Exception as e:
        logger.error(f"Error in generate-ideas endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/campaigns", response_class=JSONResponse)
async def get_campaigns():
    try:
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        campaigns = await loop.run_in_executor(None, db_manager.get_all_campaigns)
        logger.info(f"Retrieved {len(campaigns)} campaigns")
        return JSONResponse(content={"status": "success", "campaigns": campaigns})
    except Exception as e:
        logger.error(f"Error in get_campaigns: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/campaigns", response_class=JSONResponse)
async def create_campaign(campaign_data: dict):
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
        status = campaign_data.get("status", "INCOMPLETE")
        extraction_settings = campaign_data.get("extractionSettings", {})
        preprocessing_settings = campaign_data.get("preprocessingSettings", {})
        entity_settings = campaign_data.get("entitySettings", {})
        modeling_settings = campaign_data.get("modelingSettings", {})
        
        # Validate required fields
        if not campaign_name:
            return JSONResponse(content={"error": "Campaign name is required"}, status_code=400)
        
        # Generate campaign ID
        campaign_id = f"campaign-{int(datetime.now().timestamp() * 1000)}"
        
        # Create campaign in database
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        
        # Convert lists to comma-separated strings for database storage
        keywords_str = ','.join(keywords) if keywords else ""
        urls_str = ','.join(urls) if urls else ""
        trending_topics_str = ','.join(trending_topics) if trending_topics else ""
        topics_str = ','.join(topics) if topics else ""
        
        # Store campaign
        await loop.run_in_executor(
            None,
            db_manager.create_campaign,
            campaign_id,
            campaign_name,
            description,
            query,
            campaign_type,
            keywords_str,
            urls_str,
            trending_topics_str,
            topics_str,
            status,
            extraction_settings,
            preprocessing_settings,
            entity_settings,
            modeling_settings
        )
        
        logger.info(f"Created campaign: {campaign_id} - {campaign_name}")
        
        return JSONResponse(content={
            "status": "success",
            "message": {
                "id": campaign_id,
                "name": campaign_name,
                "description": description,
                "type": campaign_type,
                "keywords": keywords,
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in create_campaign: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.put("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, input_data: AnalyzeInput):
    try:
        campaign_name = input_data.campaign_name.strip()
        urls = input_data.urls
        query = input_data.query.strip()
        keywords = input_data.keywords or []
        description = input_data.description
        type = input_data.type or "url"
        depth = input_data.depth
        max_pages = input_data.max_pages
        batch_size = input_data.batch_size
        include_links = input_data.include_links
        stem = input_data.stem
        lemmatize = input_data.lemmatize
        remove_stopwords_toggle = input_data.remove_stopwords_toggle
        extract_persons = input_data.extract_persons
        extract_organizations = input_data.extract_organizations
        extract_locations = input_data.extract_locations
        extract_dates = input_data.extract_dates
        topic_tool = input_data.topic_tool
        num_topics = input_data.num_topics
        iterations = input_data.iterations
        pass_threshold = input_data.pass_threshold

        # Validate inputs
        if not campaign_name:
            logger.error("Campaign name is empty")
            return {"error": "Campaign name cannot be empty"}
        if not query:
            logger.error("Query is empty")
            return {"error": "Query cannot be empty"}

        task = (
            f"{query} for this: {urls}. "
            f"Keywords: {', '.join(keywords) if keywords else 'None'}. "
            f"Web scraping depth was {depth}, "
            f"no. of pages to extract {max_pages}, "
            f"batch size should be {batch_size}, "
            f"{'include 1-2 links' if include_links else 'exclude links'}."
        )

        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        config = BrowserConfig(headless=True, disable_security=True)
        browser = Browser(config=config)
        controller = Controller(output_model=Posts)
        agent = Agent(
            task=task,
            llm=llm,
            controller=controller,
            browser=browser,
        )

        history = await agent.run()
        result = history.final_result()

        if result:
            parsed_posts: Posts = Posts.model_validate_json(result)
            logger.info(f"Scraped {len(parsed_posts.posts)} posts for campaign update")
        else:
            logger.warning("No results found from scraping for campaign update")
            return {
                "status": "success",
                "campaign_name": campaign_name,
                "campaign_id": campaign_id,
                "task": task,
                "result": "No results found.",
                "topics": []
            }

        texts = [post.text for post in parsed_posts.posts]
        topics = extract_topics(texts, topic_tool, num_topics, iterations)
        if not topics:
            topics = extract_keywords(texts, num_keywords=num_topics * 5)
            message = "No topics generated; used keyword extraction as fallback"
        else:
            message = None

        processed_posts = ProcessedPosts(posts=[
            ProcessedPost(
                text=post.text,
                lemmatized_text=lemmatize_text(post.text) if lemmatize else None,
                stemmed_text=stem_text(post.text) if stem else None,
                stopwords_removed_text=remove_stopwords(post.text) if remove_stopwords_toggle else None,
                **extract_entities(post.text, extract_persons, extract_organizations, extract_locations, extract_dates),
                topics=topics
            ) for post in parsed_posts.posts
        ])

        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            db_manager.update_campaign,
            campaign_id,
            campaign_name,
            query,
            ','.join(urls),
            processed_posts,
            keywords,
            description,
            type
        )

        response_data = {
            "status": "success",
            "campaign_name": campaign_name,
            "campaign_id": campaign_id,
            "task": task,
            "keywords": keywords,
            "posts": [post.model_dump() for post in processed_posts.posts],
            "topics": topics
        }
        if message:
            response_data["message"] = message
        logger.info(f"Campaign {campaign_id} updated: {response_data}")
        return response_data
    except Exception as e:
        logger.error(f"Error in update_campaign: {str(e)}")
        return {"error": str(e)}

@app.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    try:
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, db_manager.delete_campaign, campaign_id)
        logger.info(f"Campaign {campaign_id} deleted")
        return {"status": "success", "message": f"Campaign {campaign_id} deleted"}
    except Exception as e:
        logger.error(f"Error in delete_campaign: {str(e)}")
        return {"error": str(e)}


from pydantic import validator
from pydantic import ValidationError
# Pydantic model for validation
class GenerateContentInput(BaseModel):
    topics: List[str] = Field(..., min_items=1)
    text: str = Field(..., min_length=1)
    no_of_posts_per_day: int = Field(..., ge=1, le=10)
    platforms: List[str] = Field(..., min_items=1)
    days: List[str] = Field(..., min_items=1)
    author: Optional[str] = None
    sample_text: Optional[str] = None
    lexical_features: bool = False
    syntactic_patterns: bool = False
    structural_elements: bool = False
    semantic_characteristics: bool = False
    rhetorical_devices: bool = False
    configuration_preset: str = Field(..., pattern="^(custom|configuration|balanced|high fidelity|creative adaptation|simplified style|complex elaboration)$")
    sample_size: int = Field(..., ge=10, le=100)
    feature_weight: float = Field(..., ge=0.1, le=1.0)
    complexity_level: str = Field(..., pattern="^(simple|medium|complex|very complex)$")
    creativity_level: float = Field(..., ge=0.1, le=1.0)
    max_tokens: int = Field(..., ge=125, le=2000)

    class Config:
        str_strip_whitespace = True

    @validator('topics', 'platforms', 'days', each_item=True)
    def check_non_empty_strings(cls, v):
        if not v.strip():
            raise ValueError("Items cannot be empty strings")
        return v

# Placeholder sanitize_text
def sanitize_text(text: str) -> str:
    text = re.sub(r'\n+', '\n', text).strip()
    return text

# Updated /generate_content endpoint
@app.post("/generate_content")
async def generate_content(
    topics: str = Form(...),
    text: str = Form(...),
    no_of_posts_per_day: int = Form(..., ge=1, le=10),
    platforms: str = Form(...),
    days: str = Form(...),
    author: Optional[str] = Form(None),
    sample_text: Optional[str] = Form(None),
    lexical_features: bool = Form(False),
    syntactic_patterns: bool = Form(False),
    structural_elements: bool = Form(False),
    semantic_characteristics: bool = Form(False),
    rhetorical_devices: bool = Form(False),
    configuration_preset: str = Form(...),
    sample_size: int = Form(..., ge=10, le=100),
    feature_weight: float = Form(...),
    complexity_level: str = Form(...),
    creativity_level: float = Form(...),
    max_tokens: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Convert comma-separated strings to lists
        topics_list = [t.strip() for t in topics.split(",") if t.strip()]
        platforms_list = [p.strip() for p in platforms.split(",") if p.strip()]
        days_list = [d.strip() for d in days.split(",") if d.strip()]

        # Validate input using Pydantic
        input_data = GenerateContentInput(
            topics=topics_list,
            text=sanitize_text(text),
            no_of_posts_per_day=no_of_posts_per_day,
            platforms=platforms_list,
            days=days_list,
            author=author,
            sample_text=sample_text,
            lexical_features=lexical_features,
            syntactic_patterns=syntactic_patterns,
            structural_elements=structural_elements,
            semantic_characteristics=semantic_characteristics,
            rhetorical_devices=rhetorical_devices,
            configuration_preset=configuration_preset,
            sample_size=sample_size,
            feature_weight=feature_weight,
            complexity_level=complexity_level,
            creativity_level=creativity_level,
            max_tokens=max_tokens
        )

        # Validate platforms and days
        valid_platforms = {"Instagram", "Facebook", "Twitter", "TikTok", "LinkedIn"}
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        if not all(platform in valid_platforms for platform in input_data.platforms):
            raise HTTPException(status_code=400, detail="Invalid platform specified")
        if not all(day in valid_days for day in input_data.days):
            raise HTTPException(status_code=400, detail="Invalid day specified")

        logger.debug(f"Received input: {input_data.dict()}")

        generated_content = []
        agent = ContentGeneratorAgent()
        for topic in input_data.topics:
            for day in input_data.days:
                for platform in input_data.platforms:
                    for post_num in range(1, input_data.no_of_posts_per_day + 1):  # Generate multiple posts
                        title, content = agent.generate_content(
                            topic=topic,
                            text=input_data.text,
                            platform=platform,
                            author=input_data.author,
                            sample_text=input_data.sample_text,
                            lexical_features=input_data.lexical_features,
                            syntactic_patterns=input_data.syntactic_patterns,
                            structural_elements=input_data.structural_elements,
                            semantic_characteristics=input_data.semantic_characteristics,
                            rhetorical_devices=input_data.rhetorical_devices,
                            configuration_preset=input_data.configuration_preset,
                            sample_size=input_data.sample_size,
                            feature_weight=input_data.feature_weight,
                            complexity_level=input_data.complexity_level,
                            creativity_level=input_data.creativity_level
                        )
                        if title and content:
                            schedule_time = datetime.combine(datetime.now().date(), time(9, 0))
                            platform_post_no = f"{platform.lower()}{post_num}"  # e.g., twitter1, twitter2
                            file_name = "web_scrape_ref"
                            file_type = "text"

                            # Create Content object
                            content_obj = Content(
                                user_id=current_user.id,
                                week=1,
                                day=day,
                                content=content,
                                title=title,
                                date_upload=datetime.now().date(),
                                platform=platform,
                                platform_post_no=platform_post_no,
                                schedule_time=schedule_time,
                                file_name=file_name,
                                file_type=file_type
                            )
                            # Add and commit to database
                            db.add(content_obj)
                            db.commit()
                            db.refresh(content_obj)
                            logger.info(f"Stored content for {platform} on {day} with topic '{topic}' and ID '{content_obj.id}'")

                            generated_content.append({
                                "id": content_obj.id,
                                "topic": topic,
                                "day": day,
                                "platform": platform,
                                "post_number": post_num,  # Include post number in response
                                "title": title,
                                "content": content
                            })
                        else:
                            logger.warning(f"Failed to generate content for {platform} on {day} with topic '{topic}' for post {post_num}")

        return {
            "generated_content": generated_content,
            "status": "success",
            "message": "Content generated and stored successfully"
        }
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Error storing content in database")
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_scheduled_posts")
async def get_scheduled_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Query the Content table for posts belonging to the current user
        posts = db.query(Content).filter(Content.user_id == current_user.id).all()

        if not posts:
            logger.info(f"No scheduled posts found for user ID {current_user.id}")
            return {
                "status": "success",
                "message": "No scheduled posts found",
                "posts": []
            }

        # Format the response, including image_url
        scheduled_posts = [
            {
                "id": post.id,
                "topic": post.title,  # Assuming title reflects the topic
                "day": post.day,
                "platform": post.platform,
                "title": post.title,
                "content": post.content,
                "schedule_time": post.schedule_time.isoformat() if post.schedule_time else None,
                "image_url": post.image_url  # Add image_url here
            }
            for post in posts
        ]

        logger.info(f"Retrieved {len(scheduled_posts)} scheduled posts for user ID {current_user.id}")
        return {
            "status": "success",
            "message": f"Retrieved {len(scheduled_posts)} scheduled posts",
            "posts": scheduled_posts
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving posts from database")
    except Exception as e:
        logger.error(f"Error retrieving scheduled posts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Query the Content table for the post with the given ID and belonging to the current user
        post = db.query(Content).filter(
            Content.id == post_id,
            Content.user_id == current_user.id
        ).first()

        if not post:
            logger.info(f"No post found with ID {post_id} for user ID {current_user.id}")
            raise HTTPException(status_code=404, detail="Post not found or does not belong to the current user")

        # Delete the post
        db.delete(post)
        db.commit()

        logger.info(f"Post with ID {post_id} deleted for user ID {current_user.id}")
        return {
            "status": "success",
            "message": f"Post with ID {post_id} deleted successfully"
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while deleting post ID {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting post from database")
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting post ID {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/search")
async def search_tweets(
    query: str,
    campaign_id: Optional[str] = None,
    campaign_name: Optional[str] = None,
    description: Optional[str] = None
):
    """Handle tweet search via query parameter and store all trending content in a single row if campaign_id is provided."""
    formatted_query = query.replace(' ', '+')
    
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    params = {
        "query": formatted_query,
        "search_type": "Top"
    }
    headers = {
        'x-rapidapi-key': "968719bd37msh744ae8950e4299ep1b2a49jsnc8988573c190",
        'x-rapidapi-host': "twitter-api45.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            filtered_tweets = process_tweets(data)
            
            # Prepare campaign details
            final_campaign_name = campaign_name.strip() if campaign_name and campaign_name.strip() else f"Twitter search: {query}"
            final_description = description.strip() if description and description.strip() else f"Twitter search for {query}"
            
            if campaign_id:
                db_manager = DatabaseManager1()
                session = next(get_db_manager().get_db_session())
                try:
                    campaign_exists = db_manager.check_campaign_exists(campaign_id)
                    db_type = "twitter"  # Use "twitter" for database storage
                    keywords = [query.strip()]  # Use query as default keyword
                    
                    logger.info(
                        f"Storing campaign {campaign_id} with campaign_name: {final_campaign_name}, "
                        f"description: {final_description}, type: {db_type}, keywords: {keywords}"
                    )

                    if not campaign_exists:
                        campaign = Campaign(
                            campaign_id=campaign_id,
                            campaign_name=final_campaign_name,
                            query=query,
                            urls="",
                            keywords=','.join(keywords),
                            description=final_description,
                            type=db_type,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(campaign)
                        session.commit()
                        logger.info(f"Created new campaign {campaign_id} for query {query}")
                    
                    trending_content = json.dumps(filtered_tweets)
                    
                    raw_data = RawData(
                        campaign_id=campaign_id,
                        campaign_name=final_campaign_name,
                        type=db_type,
                        keywords=','.join(keywords),
                        query=query,
                        urls="",
                        text="",
                        trending_content=trending_content,
                        created_at=datetime.now()
                    )
                    session.add(raw_data)
                    session.commit()
                    logger.info(
                        f"Stored {len(filtered_tweets)} trending tweets for campaign {campaign_id} with "
                        f"campaign_name: {final_campaign_name}, type: {db_type}, keywords: {keywords}"
                    )
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Database error storing trending content or creating campaign: {e}")
                    raise HTTPException(status_code=500, detail=f"Error storing trending content: {str(e)}")
                finally:
                    session.close()
            
            return {
                "status": "success",
                "campaign": {
                    "name": final_campaign_name,
                    "id": campaign_id,
                    "description": final_description,
                    "type": "trending x",
                    "trending_content": filtered_tweets
                }
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=f"API Error: {response.status_code}")
    except Exception as e:
        logger.error(f"Error in search_tweets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
@app.get("/campaigns/{campaign_id}/raw_data", response_class=JSONResponse)
async def get_raw_data_by_campaign(campaign_id: str):
    """Retrieve all raw data entries for a given campaign ID with details from raw_data table."""
    try:
        logger.debug(f"Processing request for campaign_id: {campaign_id}")
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        
        # Retrieve raw data
        raw_data = await loop.run_in_executor(None, db_manager.get_raw_data_by_campaign, campaign_id)
        if not raw_data:
            logger.warning(f"No raw data found for campaign {campaign_id}")
            response = {
                "status": "success",
                "campaign_id": campaign_id,
                "name": "",
                "type": "",
                "description": "",
                "urls": [],
                "keywords": [],
                "trendingTopics": [],
                "raw_data": [],
                "message": "No raw data found for this campaign"
            }
            logger.debug(f"Response for no raw data: {response}")
            return JSONResponse(content=response)
        
        # Log raw data for debugging
        logger.debug(f"Raw data entries: {raw_data}")
        
        # Use the first raw_data entry for campaign details (assuming consistency)
        first_entry = raw_data[0]
        # Aggregate trendingTopics from all raw_data entries
        trending_topics = set()
        for entry in raw_data:
            if entry.get("topics"):
                for topic in entry["topics"]:
                    trending_topics.add(topic)
        
        response = {
            "status": "success",
            "campaign_id": campaign_id,
            "name": first_entry.get("campaign_name", ""),
            "type": first_entry.get("type", "url"),
            "description": first_entry.get("description", ""),
            "urls": first_entry.get("urls", []),
            "keywords": first_entry.get("keywords", []),
            "trendingTopics": list(trending_topics),
            "raw_data": jsonable_encoder(raw_data),
            "message": f"Retrieved {len(raw_data)} raw data entries"
        }
        
        logger.info(f"Completed request for campaign {campaign_id} with {len(raw_data)} raw data entries")
        logger.debug(f"Final response: {response}")
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error processing request for {campaign_id}: {str(e)}")
        response = {
            "status": "error",
            "campaign_id": campaign_id,
            "name": "",
            "type": "",
            "urls": [],
            "description": "",
            "keywords": [],
            # "trendingTopics": [],
            "raw_data": [],
            "message": f"Failed to retrieve raw data: {str(e)}"
        }
        logger.debug(f"Error response: {response}")
        return JSONResponse(content=response, status_code=500)
    

db_manager1 = DatabaseManager1()

# @app.post("/generate_image_machine_content")
# async def generate_image_machine_content_endpoint(
#     id: int,
#     query: str,
#     db: Session = Depends(get_db)  # Use injected session
# ):
#     """
#     Generate an image based on the provided ID and a query string from the content table, store it in FTP, and save the permanent URL.

#     Args:
#         id (int): The ID of the record in the content table to use for image generation.
#         query (str): A string to guide the image generation (e.g., "in watercolor style").
#         db (Session): The database session dependency.

#     Returns:
#         dict: A dictionary with status, message, and the generated image URL.

#     Raises:
#         HTTPException: If the record is not found, already processed, or image generation fails.
#     """
#     try:
#         # Validate input
#         if id <= 0:
#             raise HTTPException(status_code=400, detail="Invalid ID provided")

#         logger.debug(f"Querying content with ID: {id}")

#         # Retrieve the record by ID with a lock to prevent concurrent modifications
#         existing_content = db.query(Content).filter(
#             Content.id == id,
#             Content.status.in_(["pending", "posted"])  # Only process pending or posted content
#         ).with_for_update().first()  # Lock the row

#         if not existing_content:
#             logger.debug(f"No record found for ID: {id} or status is not pending/posted")
#             raise HTTPException(status_code=404, detail="Record not found or already processed")

#         logger.info(f"Found content with ID: {existing_content.id}, content: {existing_content.content[:100]}...")

#         # Generate the image using the content and query
#         temp_image_url = generate_image(query, existing_content.content)
#         if not temp_image_url:
#             raise HTTPException(status_code=500, detail="Failed to generate image")

#         # Download the temporary image asynchronously
#         async with httpx.AsyncClient() as client:
#             response = await client.get(temp_image_url)
#             if response.status_code != 200:
#                 raise HTTPException(status_code=500, detail="Failed to download temporary image")
#             image_data = response.content

#         # FTP credentials and configuration
#         ftp_host = os.getenv("ftp_host")
#         ftp_user = os.getenv("ftp_user")
#         ftp_pass = os.getenv("ftp_pass")
#         filename = f"image_{existing_content.id}.png"

#         # Upload the image to FTP
#         with FTP(ftp_host) as ftp:
#             ftp.login(user=ftp_user, passwd=ftp_pass)
#             ftp.storbinary(f"STOR {filename}", io.BytesIO(image_data))

#         # Construct the permanent URL
#         permanent_url = f"https://lookwhatwemadeyou.com/nishant/{filename}"

#         # Update the database with the permanent URL and status
#         existing_content.image_url = permanent_url
#         existing_content.status = "image_generated"  # Update status
#         db.commit()
#         db.refresh(existing_content)  # Refresh to ensure data consistency

#         logger.info(f"Successfully generated and stored image for content ID: {existing_content.id}")

#         return {
#             "status": "success",
#             "message": "Image generated successfully",
#             "image_url": permanent_url
#         }

#     except SQLAlchemyError as e:
#         db.rollback()
#         logger.error(f"Database error for content ID {id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to generate image for content ID {id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")
    


@app.post("/generate_image_machine_content")
async def generate_image_machine_content_endpoint(
    id: int,
    query: str,
    db: Session = Depends(get_db)  # Use injected session
):
    """
    Generate an image based on the provided ID and a query string from the content table, store it in SFTP, and save the permanent URL.

    Args:
        id (int): The ID of the record in the content table to use for image generation.
        query (str): A string to guide the image generation (e.g., "in watercolor style").
        db (Session): The database session dependency.

    Returns:
        dict: A dictionary with status, message, and the generated image URL.

    Raises:
        HTTPException: If the record is not found, already processed, or image generation fails.
    """
    try:
        # Validate input
        if id <= 0:
            raise HTTPException(status_code=400, detail="Invalid ID provided")

        logger.debug(f"Querying content with ID: {id}")

        # Retrieve the record by ID with a lock to prevent concurrent modifications
        existing_content = db.query(Content).filter(
            Content.id == id,
            Content.status.in_(["pending", "posted"])  # Only process pending or posted content
        ).with_for_update().first()  # Lock the row

        if not existing_content:
            logger.debug(f"No record found for ID: {id} or status is not pending/posted")
            raise HTTPException(status_code=404, detail="Record not found or already processed")

        logger.info(f"Found content with ID: {existing_content.id}, content: {existing_content.content[:100]}...")

        # Generate the image using the content and query
        temp_image_url = generate_image(query, existing_content.content)
        if not temp_image_url:
            raise HTTPException(status_code=500, detail="Failed to generate image")

        # Download the temporary image asynchronously
        async with httpx.AsyncClient() as client:
            response = await client.get(temp_image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to download temporary image")
            image_data = response.content

        # SFTP credentials and configuration
        sftp_host = os.getenv("SFTP_HOST")
        sftp_user = os.getenv("SFTP_USER")
        sftp_pass = os.getenv("SFTP_PASS")
        sftp_port = int(os.getenv("SFTP_PORT", "22"))  # Default to 22 if not specified
        filename = f"image_{existing_content.id}.png"
        remote_path = f"/home/{sftp_user}/public_html/nishant/{filename}"

        # Upload the image to SFTP
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=sftp_host, port=sftp_port, username=sftp_user, password=sftp_pass)
            sftp = ssh_client.open_sftp()

            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                try:
                    sftp.mkdir(remote_dir)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to create SFTP directory {remote_dir}: {str(e)}")

            # Upload the image
            with sftp.open(remote_path, 'wb') as remote_file:
                remote_file.write(image_data)
            sftp.close()
            ssh_client.close()

        except paramiko.AuthenticationException:
            raise HTTPException(status_code=500, detail="SFTP authentication failed. Check credentials.")
        except paramiko.SSHException as ssh_e:
            raise HTTPException(status_code=500, detail=f"SFTP error: {str(ssh_e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image to SFTP: {str(e)}")

        # Construct the permanent URL
        permanent_url = f"https://vernalcontentum.com/nishant/{filename}"

        # Update the database with the permanent URL and status
        existing_content.image_url = permanent_url
        existing_content.status = "image_generated"  # Update status
        db.commit()
        db.refresh(existing_content)  # Refresh to ensure data consistency

        logger.info(f"Successfully generated and stored image for content ID: {existing_content.id}")

        return {
            "status": "success",
            "message": "Image generated successfully",
            "image_url": permanent_url
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error for content ID {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate image for content ID {id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")


@app.put("/regenerate_script_machine_content")
async def regenerate_script_machine_content_endpoint(id: int, query: str, platform: str, db: Session = Depends(lambda: get_db_manager().get_db_session())):
    """
    Regenerate a script by its ID in the machine_content table using the script writer agent, guided by a provided query and target platform.

    Args:
        id (int): The ID of the record in the machine_content table to regenerate.
        query (str): The prompt or instruction to guide the script regeneration (e.g., "make it more engaging").
        platform (str): The target platform for the regenerated script (e.g., "twitter", "facebook").
        db (Session): The database session dependency.

    Returns:
        dict: A dictionary containing the status, message, and details of the regenerated script.

    Raises:
        HTTPException: If the record is not found, the platform is invalid, or regeneration fails.
    """
    session = next(get_db_manager().get_db_session())
    
    try:
        # Validate input
        if id <= 0:
            raise HTTPException(status_code=400, detail="Invalid ID provided")

        # Normalize and validate the platform
        platform = platform.lower()
        if platform not in PLATFORM_LIMITS:
            raise HTTPException(status_code=400, detail="Invalid platform specified")

        # Retrieve the existing content from the machine_content table
        existing_content = session.query(Content).filter(Content.id == id).first()
        if not existing_content:
            logger.debug(f"No record found for ID: {id}")
            raise HTTPException(status_code=404, detail="Record not found in machine_content table")

        logger.info(f"Found content with ID: {existing_content.id}, content: {existing_content.content[:100]}...")

        # Create a crew with the script rewriter agent
        script_crew = Crew(
            agents=[script_rewriter_agent],
            tasks=[script_rewriter_task],
            process=Process.sequential
        )

        # Pass the platform and query to the agent for script regeneration
        crew_result = script_crew.kickoff(
            inputs={
                "text": existing_content.content,
                "day": existing_content.day,
                "week": existing_content.week,
                "platform": platform,
                "limits": PLATFORM_LIMITS[platform],
                "query": query
            }
        )

        # Extract the regenerated content from the crew result
        if isinstance(crew_result, dict):
            new_content = str(crew_result.get('output', ''))
        elif hasattr(crew_result, 'raw_output'):
            new_content = str(crew_result.raw_output)
        elif hasattr(crew_result, 'output'):
            new_content = str(crew_result.output)
        else:
            new_content = str(crew_result)

        # Ensure content was generated
        if not new_content:
            raise HTTPException(status_code=500, detail="Failed to generate new content")

        # Process the new content for the specified platform
        processed_content = process_content_for_platform(
            new_content,
            platform,
            PLATFORM_LIMITS[platform]
        )

        # Generate a new title from the processed content
        new_title = extract_title_from_content(processed_content)

        # Update the existing content in the database
        existing_content.content = processed_content
        existing_content.title = new_title
        existing_content.platform = platform.upper()  # Match machine_content table's platform format
        existing_content.date_upload = datetime.now().date()  # Update timestamp
        session.commit()

        # Return the updated content details
        return {
            "status": "success",
            "message": "Script regenerated successfully",
            "content": {
                "id": existing_content.id,
                "week": existing_content.week,
                "day": existing_content.day,
                "title": new_title,
                "content": processed_content,
                "platform": existing_content.platform,
                "date_of_upload": existing_content.date_upload.isoformat(),
                "file_name": existing_content.file_name
            }
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to regenerate script: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate script: {str(e)}"
        )
    finally:
        session.close()

@app.get("/linkedin/auth-v2")
async def linkedin_auth(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = secrets.token_urlsafe(32)
    db.add(StateToken(user_id=current_user.id, state=state, platform=PlatformEnum.LINKEDIN))
    db.commit()
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={LINKEDIN_REDIRECT_URI1}&scope=openid profile w_member_social&state={state}"
    )
    return {"auth_url": auth_url}

@app.get("/linkedin/callback-v2")
async def linkedin_callback(code: str, state: str, db: Session = Depends(get_db)):
    # Verify the state token
    state_token = db.query(StateToken).filter(StateToken.state == state).first()
    if not state_token:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=invalid_state")
    
    # Delete the state token immediately after verification to prevent reuse
    db.delete(state_token)
    db.commit()
    
    # Get the user associated with the state token
    user = db.query(User).filter(User.id == state_token.user_id).first()
    
    # Exchange the authorization code for an access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI1,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    print(f"Requesting LinkedIn token with data: {data}")
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        print(f"Failed to get LinkedIn token: {response.text}")
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=token_request_failed")
    
    token_data = response.json()
    access_token = token_data["access_token"]
    
    # Fetch LinkedIn user profile to get ID
    profile_url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = requests.get(profile_url, headers=headers)
    if profile_response.status_code != 200:
        print(f"Failed to get LinkedIn user profile: {profile_response.text}")
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=profile_request_failed")
    
    profile_data = profile_response.json()
    linkedin_id = profile_data.get("sub")
    
    # Check for existing LinkedIn connection
    existing_connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == user.id,
        PlatformConnection.platform == PlatformEnum.LINKEDIN
    ).first()
    
    if existing_connection:
        # Update existing connection with new credentials
        existing_connection.access_token = access_token
        existing_connection.expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        existing_connection.platform_user_id = linkedin_id
        existing_connection.disconnected_at = None  # Mark as active
        logger.info(f"Updated LinkedIn connection for user {user.id}")
    else:
        # Create a new connection if none exists
        new_connection = PlatformConnection(
            user_id=user.id,
            platform=PlatformEnum.LINKEDIN,
            access_token=access_token,
            expires_at=datetime.now() + timedelta(seconds=token_data["expires_in"]),
            platform_user_id=linkedin_id,
            disconnected_at=None
        )
        db.add(new_connection)
        logger.info(f"Created new LinkedIn connection for user {user.id}")
    
    db.commit()
    
    # Redirect to frontend with success indicator
    return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?linkedin_connected=true")

# Twitter Authentication
@app.get("/twitter/auth-v2")
async def twitter_auth(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = secrets.token_urlsafe(32)
    db.add(StateToken(user_id=current_user.id, state=state, platform=PlatformEnum.TWITTER))
    db.commit()
    
    auth = tweepy.OAuth1UserHandler(
        TWITTER_CLIENT_ID,
        TWITTER_CLIENT_SECRET,
        callback=TWITTER_CALLBACK_URI1
    )
    try:
        auth_url = auth.get_authorization_url()
        db.add(StateToken(
            user_id=current_user.id,
            state=state,  # Optional, for consistency with LinkedIn
            platform=PlatformEnum.TWITTER,
            oauth_token=auth.request_token["oauth_token"],
            oauth_token_secret=auth.request_token["oauth_token_secret"]
        ))
        db.commit()
        return {"redirect_url": auth_url}
    except tweepy.TweepyException as e:
        raise HTTPException(status_code=500, detail=f"Error starting Twitter auth: {e}")


@app.get("/twitter/callback-v2")
async def twitter_callback(oauth_token: str, oauth_verifier: str, db: Session = Depends(get_db)):
    # Find StateToken using oauth_token
    state_token = db.query(StateToken).filter(
        StateToken.oauth_token == oauth_token,
        StateToken.platform == PlatformEnum.TWITTER
    ).first()
    if not state_token:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=invalid_oauth_token")
    
    # Get the user
    user = db.query(User).filter(User.id == state_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set request token with stored oauth_token and oauth_token_secret
    auth = tweepy.OAuth1UserHandler(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    auth.request_token = {
        "oauth_token": state_token.oauth_token,
        "oauth_token_secret": state_token.oauth_token_secret
    }
    try:
        auth.get_access_token(oauth_verifier)
        access_token = auth.access_token
        access_token_secret = auth.access_token_secret
    except tweepy.TweepyException as e:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=twitter_auth_failed")
    
    # Fetch Twitter user ID
    client = tweepy.Client(
        consumer_key=TWITTER_CLIENT_ID,
        consumer_secret=TWITTER_CLIENT_SECRET,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    try:
        user_info = client.get_me().data
        twitter_id = user_info.id
    except tweepy.TweepyException as e:
        return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?error=twitter_user_info_failed")
    
    # Check for existing Twitter connection
    existing_connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == user.id,
        PlatformConnection.platform == PlatformEnum.TWITTER
    ).first()
    
    if existing_connection:
        # Update existing connection with new credentials
        existing_connection.access_token = access_token
        existing_connection.refresh_token = access_token_secret  # Using refresh_token to store access_token_secret
        existing_connection.platform_user_id = str(twitter_id)
        existing_connection.disconnected_at = None  # Mark as active
        logger.info(f"Updated Twitter connection for user {user.id}")
    else:
        # Create a new connection if none exists
        new_connection = PlatformConnection(
            user_id=user.id,
            platform=PlatformEnum.TWITTER,
            access_token=access_token,
            refresh_token=access_token_secret,
            expires_at=None,  # Twitter tokens don't expire in OAuth 1.0a
            platform_user_id=str(twitter_id),
            disconnected_at=None
        )
        db.add(new_connection)
        logger.info(f"Created new Twitter connection for user {user.id}")
    
    db.commit()
    db.delete(state_token)
    db.commit()
    return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL1}?twitter_connected=true")

# WordPress Authentication
@app.post("/wordpress/auth-v2")
async def wordpress_auth(
    site_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    site_url = site_url.strip('/')
    if not all([site_url, username, password]):
        raise HTTPException(status_code=400, detail="All fields are required")

    # Test authentication with WordPress REST API
    api_url = f"{site_url}/wp-json/wp/v2/users/me"
    auth_string = f"{username}:{password}"
    auth_header = "Basic " + base64.b64encode(auth_string.encode()).decode()
    headers = {"Authorization": auth_header}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            error_message = response.json().get('message', 'Unknown error')
            raise HTTPException(status_code=401, detail=f"Authentication failed: {error_message} (Status: {response.status_code})")
        
        # Fetch WordPress user ID
        user_info = response.json()
        wordpress_id = str(user_info.get("id"))
        
        # Check for existing WordPress connection
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if existing_connection:
            # Update existing connection with new credentials
            existing_connection.access_token = auth_header
            existing_connection.refresh_token = site_url
            existing_connection.platform_user_id = wordpress_id
            existing_connection.disconnected_at = None  # Mark as active
            logger.info(f"Updated WordPress connection for user {current_user.id}")
        else:
            # Create a new connection if none exists
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.WORDPRESS,
                access_token=auth_header,
                refresh_token=site_url,
                expires_at=None,  # Basic Auth doesn't expire
                platform_user_id=wordpress_id,
                disconnected_at=None
            )
            db.add(new_connection)
            logger.info(f"Created new WordPress connection for user {current_user.id}")
        
        db.commit()
        return {"message": "WordPress connected successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to WordPress: {str(e)}")

# Pydantic models for API key inputs
class APIKeyInput(BaseModel):
    api_key: str


# Endpoint to store OpenAI key
@app.post("/store_openai_key")
async def store_openai_key(
    api_key: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.openai_key = api_key
        db.commit()
        db.refresh(current_user)
        return {
            "status": "success",
            "message": "OpenAI key stored successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing OpenAI key: {str(e)}")

# Endpoint to store MidJourney key
@app.post("/store_midjourney_key")
async def store_midjourney_key(
    api_key: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.midjourney_key = api_key
        db.commit()
        db.refresh(current_user)
        return {
            "status": "success",
            "message": "MidJourney key stored successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing MidJourney key: {str(e)}")

# Endpoint to store ElevenLabs key
@app.post("/store_elevenlabs_key")
async def store_elevenlabs_key(
    api_key: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.elevenlabs_key = api_key
        db.commit()
        db.refresh(current_user)
        return {
            "status": "success",
            "message": "ElevenLabs key stored successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing ElevenLabs key: {str(e)}")

# Endpoint to store Claude key
@app.post("/store_claude_key")
async def store_claude_key(
    api_key: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.claude_key = api_key
        db.commit()
        db.refresh(current_user)
        return {
            "status": "success",
            "message": "Claude key stored successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing Claude key: {str(e)}")

# Endpoint to get user credentials
@app.get("/get_user_credentials")
async def get_user_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        credentials = {
            "openai_key": current_user.openai_key,
            "claude_key": current_user.claude_key,
            "midjourney_key": current_user.midjourney_key,
            "elevenlabs_key": current_user.elevenlabs_key,
        }
        return {
            "status": "success",
            "credentials": credentials
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching credentials: {str(e)}")


# Author Personalities API Endpoints
@app.get("/api/author_personalities", response_class=JSONResponse)
async def get_author_personalities():
    try:
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        personalities = await loop.run_in_executor(None, db_manager.get_all_author_personalities)
        logger.info(f"Retrieved {len(personalities)} author personalities")
        return JSONResponse(content={"status": "success", "message": {"personalities": personalities}})
    except Exception as e:
        logger.error(f"Error in get_author_personalities: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/author_personalities", response_class=JSONResponse)
async def create_author_personality(personality_data: dict):
    try:
        name = personality_data.get("name", "").strip()
        description = personality_data.get("description", "").strip()
        
        # Validate required fields
        if not name:
            return JSONResponse(content={"error": "Name is required"}, status_code=400)
        
        # Generate personality ID
        personality_id = f"personality-{int(datetime.now().timestamp() * 1000)}"
        
        # Create personality in database
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        
        await loop.run_in_executor(
            None,
            db_manager.create_author_personality,
            personality_id,
            name,
            description
        )
        
        logger.info(f"Created author personality: {personality_id} - {name}")
        
        return JSONResponse(content={
            "status": "success",
            "message": {
                "id": personality_id,
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in create_author_personality: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.put("/api/author_personalities/{personality_id}", response_class=JSONResponse)
async def update_author_personality(personality_id: str, personality_data: dict):
    try:
        name = personality_data.get("name", "").strip()
        description = personality_data.get("description", "").strip()
        
        # Validate required fields
        if not name:
            return JSONResponse(content={"error": "Name is required"}, status_code=400)
        
        # Update personality in database
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        
        await loop.run_in_executor(
            None,
            db_manager.update_author_personality,
            personality_id,
            name,
            description
        )
        
        logger.info(f"Updated author personality: {personality_id} - {name}")
        
        return JSONResponse(content={
            "status": "success",
            "message": {
                "id": personality_id,
                "name": name,
                "description": description,
                "updated_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in update_author_personality: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.delete("/api/author_personalities/{personality_id}", response_class=JSONResponse)
async def delete_author_personality(personality_id: str):
    try:
        # Delete personality from database
        db_manager = DatabaseManager1()
        loop = asyncio.get_running_loop()
        
        await loop.run_in_executor(
            None,
            db_manager.delete_author_personality,
            personality_id
        )
        
        logger.info(f"Deleted author personality: {personality_id}")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Author personality {personality_id} deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in delete_author_personality: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


# Note: This file is designed to be run by uvicorn via systemd
# The app = FastAPI() instance is defined at module level (line 114)
# All endpoints are attached to this app instance
# No if __name__ == "__main__" block needed for production deployment
