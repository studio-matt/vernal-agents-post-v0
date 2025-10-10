"""
Simple test router to verify router inclusion works
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create simple test router
test_router = APIRouter(prefix="/test", tags=["Test"])

@test_router.get("/health")
async def test_health():
    """Simple test health endpoint"""
    logger.info("Test health endpoint called")
    return {"status": "test_working", "message": "Test router is working"}

@test_router.get("/ping")
async def test_ping():
    """Simple test ping endpoint"""
    logger.info("Test ping endpoint called")
    return {"message": "pong"}

logger.info("Simple test router created successfully")
