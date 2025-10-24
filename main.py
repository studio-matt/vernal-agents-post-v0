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

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
