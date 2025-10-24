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

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
