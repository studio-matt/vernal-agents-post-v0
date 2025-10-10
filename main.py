import os
import logging
from fastapi import FastAPI
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Version endpoint
@app.get("/version")
async def version():
    logger.info("Version endpoint requested")
    return {"version": "2.0.0", "status": "debug", "message": "This is the debug version"}

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
