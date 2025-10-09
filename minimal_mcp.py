"""
Minimal MCP test - just health endpoint
"""

from fastapi import APIRouter

# Create minimal MCP router
minimal_mcp_router = APIRouter(prefix="/mcp", tags=["MCP Test"])

@minimal_mcp_router.get("/health")
async def mcp_health():
    """Minimal MCP health check"""
    return {
        "status": "healthy",
        "message": "MCP is working!",
        "server": "vernal-contentum-minimal-mcp"
    }
