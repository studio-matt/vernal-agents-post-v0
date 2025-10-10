"""
Ultra Minimal FastAPI App for Testing
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Vernal Agents API",
    description="Ultra minimal API for testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health endpoint
@app.get("/health")
async def health():
    logger.info("Health check called")
    return {"ok": True, "status": "healthy", "version": "1.0.0"}

# Include ultra minimal auth router
try:
    from auth_ultra_minimal import auth_router
    app.include_router(auth_router)
    logger.info("✅ Ultra minimal authentication router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include ultra minimal authentication router: {str(e)}")
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
    return {"routes": routes, "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
