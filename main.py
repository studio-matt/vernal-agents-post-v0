"""
Main FastAPI application entry point
Includes all routers and CORS configuration
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Vernal Agents API", version="1.0.0")

# Configure CORS - CRITICAL for frontend access
# NOTE: When allow_credentials=True, you CANNOT use allow_origins=["*"]
# Must specify exact origins (add Replit preview so campaigns/personalities load there)
_cors_origins = [
    "https://machine.vernalcontentum.com",
    "https://themachine.vernalcontentum.com",
    "http://localhost:3000",
    "http://localhost:3001",
    "https://vernal-post-v0.matt363.repl.co",  # Replit preview
    "https://replit.com",
]
_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra:
    _cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with error handling
try:
    from app.routes.admin import admin_router
    app.include_router(admin_router)
    logger.info("✅ Admin router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include admin router: {e}")

try:
    from auth_api import auth_router
    app.include_router(auth_router)
    logger.info("✅ Auth router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include auth router: {e}")

try:
    from app.routes.platforms import platforms_router
    app.include_router(platforms_router)
    logger.info("✅ Platforms router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include platforms router: {e}")

try:
    from app.routes.content import content_router
    app.include_router(content_router)
    logger.info("✅ Content router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include content router: {e}")

try:
    from app.routes.campaigns import campaigns_router
    app.include_router(campaigns_router)
    logger.info("✅ Campaigns router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include campaigns router: {e}")

try:
    from app.routes.campaigns_research import campaigns_research_router
    app.include_router(campaigns_research_router)
    logger.info("✅ Campaigns research router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include campaigns research router: {e}")

try:
    from app.routes.author_personalities import author_personalities_router
    app.include_router(author_personalities_router)
    logger.info("✅ Author personalities router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include author personalities router: {e}")

try:
    from app.routes.brand_personalities import brand_personalities_router
    app.include_router(brand_personalities_router)
    logger.info("✅ Brand personalities router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include brand personalities router: {e}")

try:
    from app.routes.generation_logs import generation_logs_router
    app.include_router(generation_logs_router)
    logger.info("✅ Generation logs router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include generation logs router: {e}")

try:
    from gas_meter.endpoint_code import router as gas_meter_router
    app.include_router(gas_meter_router)
    logger.info("✅ Gas meter router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include gas meter router: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Backend is running"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Vernal Agents Backend API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

