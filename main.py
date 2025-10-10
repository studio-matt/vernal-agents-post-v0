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

logger.info("Starting minimal FastAPI app")

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

# Health endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check requested")
    return {"ok": True}

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint requested")
    return {"message": "Vernal Agents API is running"}

# Test endpoint
@app.get("/test-health")
async def test_health():
    logger.info("Test health endpoint requested")
    return {"status": "test_ok", "message": "Test endpoint is working"}

# Import and include routers with explicit error handling
try:
    logger.info("Attempting to import simple_test_router...")
    from simple_test_router import test_router
    app.include_router(test_router)
    logger.info("✅ simple_test_router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include simple_test_router: {e}")
    import traceback
    traceback.print_exc()

try:
    logger.info("Attempting to import simple_mcp_api...")
    from simple_mcp_api import simple_mcp_router
    app.include_router(simple_mcp_router, prefix="/mcp")
    logger.info("✅ simple_mcp_router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include simple_mcp_router: {e}")
    import traceback
    traceback.print_exc()

try:
    logger.info("Attempting to import debug_import...")
    from debug_import import router as debug_router
    app.include_router(debug_router)
    logger.info("✅ debug_router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include debug_router: {e}")
    import traceback
    traceback.print_exc()

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
    return {"routes": routes}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with uvicorn")
    uvicorn.run(app, host="0.0.0.0", port=8000)