import os
import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "authorization", "accept", "ngrok-skip-browser-warning"],
    expose_headers=["*"],
)

# Manual CORS handler for OPTIONS requests
@app.options("/{path:path}")
async def options_handler(path: str, response: Response):
    """Handle OPTIONS requests manually to ensure CORS headers are set"""
    response.headers["Access-Control-Allow-Origin"] = "https://machine.vernalcontentum.com"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

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
            "deployment": "bulletproof-v18"  # Added bulletproof process cleanup
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
            "deployment": "bulletproof-v18"  # Added bulletproof process cleanup
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

# Authentication router (ultra minimal version for now)
try:
    from auth_ultra_minimal import auth_router
    app.include_router(auth_router)
    logger.info("✅ Ultra minimal authentication router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include ultra minimal authentication router: {str(e)}")
    import traceback
    traceback.print_exc()

# Campaigns endpoint
@app.get("/campaigns")
async def get_campaigns():
    logger.info("Campaigns endpoint requested")
    return {"campaigns": [], "message": "Campaigns endpoint working", "version": "2.0.0"}

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
