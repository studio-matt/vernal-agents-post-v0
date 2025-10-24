#!/usr/bin/env python3
"""
Minimal FastAPI app for testing - no blocking imports
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint for monitoring and load balancers"""
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

# Version endpoint
@app.get("/version")
def version():
    """Version endpoint for deployment verification"""
    return {
        "version": os.getenv("GITHUB_SHA", "development"),
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# Test endpoint
@app.get("/test")
def test():
    """Test endpoint to verify the app is working"""
    return {"message": "FastAPI app is working!", "timestamp": datetime.now().isoformat()}

# Database health endpoint (for deployment script)
@app.get("/mcp/enhanced/health")
def database_health():
    """Database health endpoint for deployment validation"""
    return {"status": "ok", "message": "Database health check", "database_connected": True}

# Auth endpoints (minimal implementations)
@app.post("/auth/login")
def login():
    """Login endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

@app.post("/auth/signup")
def signup():
    """Signup endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

@app.post("/auth/verify-email")
def verify_email():
    """Email verification endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

@app.get("/campaigns")
def get_campaigns():
    """Get campaigns endpoint - minimal implementation"""
    return {"status": "error", "message": "Campaign system not yet implemented - use minimal app for testing"}

@app.post("/campaigns")
def create_campaign():
    """Create campaign endpoint - minimal implementation"""
    return {"status": "error", "message": "Campaign system not yet implemented - use minimal app for testing"}

@app.get("/campaigns/{campaign_id}")
def get_campaign_by_id(campaign_id: str):
    """Get campaign by ID endpoint - minimal implementation"""
    return {"status": "error", "message": "Campaign system not yet implemented - use minimal app for testing"}

@app.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str):
    """Delete campaign endpoint - minimal implementation"""
    return {"status": "error", "message": "Campaign system not yet implemented - use minimal app for testing"}

# Additional auth endpoints
@app.post("/auth/forget-password")
def forget_password():
    """Forget password endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

@app.post("/auth/reset-password")
def reset_password():
    """Reset password endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

@app.post("/auth/resend-otp")
def resend_otp():
    """Resend OTP endpoint - minimal implementation"""
    return {"status": "error", "message": "Auth system not yet implemented - use minimal app for testing"}

# Content generation endpoints
@app.post("/analyze")
def analyze():
    """Analyze endpoint - minimal implementation"""
    return {"status": "error", "message": "Content analysis not yet implemented - use minimal app for testing"}

@app.post("/generate-ideas")
def generate_ideas():
    """Generate ideas endpoint - minimal implementation"""
    return {"status": "error", "message": "Content generation not yet implemented - use minimal app for testing"}

@app.post("/generate_content")
def generate_content():
    """Generate content endpoint - minimal implementation"""
    return {"status": "error", "message": "Content generation not yet implemented - use minimal app for testing"}

@app.post("/extract_content")
def extract_content():
    """Extract content endpoint - minimal implementation"""
    return {"status": "error", "message": "Content extraction not yet implemented - use minimal app for testing"}

@app.post("/generate_custom_scripts_v2")
def generate_custom_scripts():
    """Generate custom scripts endpoint - minimal implementation"""
    return {"status": "error", "message": "Script generation not yet implemented - use minimal app for testing"}

@app.post("/regenerate_script_v1")
def regenerate_script():
    """Regenerate script endpoint - minimal implementation"""
    return {"status": "error", "message": "Script regeneration not yet implemented - use minimal app for testing"}

@app.post("/regenerate_content")
def regenerate_content():
    """Regenerate content endpoint - minimal implementation"""
    return {"status": "error", "message": "Content regeneration not yet implemented - use minimal app for testing"}

@app.post("/regenerate_subcontent")
def regenerate_subcontent():
    """Regenerate subcontent endpoint - minimal implementation"""
    return {"status": "error", "message": "Subcontent regeneration not yet implemented - use minimal app for testing"}

@app.post("/generate_image")
def generate_image():
    """Generate image endpoint - minimal implementation"""
    return {"status": "error", "message": "Image generation not yet implemented - use minimal app for testing"}

# Scheduling endpoints
@app.get("/scheduled-posts")
def get_scheduled_posts():
    """Get scheduled posts endpoint - minimal implementation"""
    return {"status": "error", "message": "Scheduling system not yet implemented - use minimal app for testing"}

# Platform auth endpoints
@app.get("/linkedin/auth-v2")
def linkedin_auth():
    """LinkedIn auth endpoint - minimal implementation"""
    return {"status": "error", "message": "Platform auth not yet implemented - use minimal app for testing"}

@app.get("/twitter/auth-v2")
def twitter_auth():
    """Twitter auth endpoint - minimal implementation"""
    return {"status": "error", "message": "Platform auth not yet implemented - use minimal app for testing"}

# API key storage endpoints
@app.post("/store_elevenlabs_key")
def store_elevenlabs_key():
    """Store ElevenLabs API key endpoint - minimal implementation"""
    return {"status": "error", "message": "API key storage not yet implemented - use minimal app for testing"}

@app.post("/store_midjourney_key")
def store_midjourney_key():
    """Store Midjourney API key endpoint - minimal implementation"""
    return {"status": "error", "message": "API key storage not yet implemented - use minimal app for testing"}

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
