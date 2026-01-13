"""
Health and deployment endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
from fastapi import APIRouter, Depends
from datetime import datetime
import os
import subprocess
from auth_api import get_admin_user

health_router = APIRouter()

@health_router.get("/health")
@health_router.head("/health")
def health():
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@health_router.get("/version")
@health_router.head("/version")
def version():
    return {"version": os.getenv("GITHUB_SHA", "development"), "status": "ok", "timestamp": datetime.now().isoformat()}

@health_router.get("/mcp/enhanced/health")
@health_router.head("/mcp/enhanced/health")
def database_health():
    return {"status": "ok", "message": "Database health check", "database_connected": True}

@health_router.get("/")
@health_router.head("/")
def root():
    return {"message": "Vernal Agents Backend API", "status": "running"}

@health_router.get("/deploy/commit")
def deploy_commit(admin_user = Depends(get_admin_user)):
    """Return the current deployed commit hash for verification - ADMIN ONLY"""
    import subprocess
    try:
        # Use current file location instead of hardcoded path
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to backend-repo-git root (app/routes -> app -> backend-repo-git)
        repo_dir = os.path.dirname(os.path.dirname(repo_dir))
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=repo_dir)
        if result.returncode == 0:
            return {"commit": result.stdout.strip(), "status": "ok"}
        else:
            return {"commit": "unknown", "status": "error", "message": "Failed to get commit hash"}
    except Exception as e:
        return {"commit": "unknown", "status": "error", "message": str(e)}

