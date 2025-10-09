"""
Direct MCP implementation in main.py
Simple MCP endpoints without separate modules
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from tools import process_content_for_platform, PLATFORM_LIMITS
import logging

logger = logging.getLogger(__name__)

# Create MCP API router
mcp_router = APIRouter(prefix="/mcp", tags=["MCP Tools"])

# Pydantic models
class MCPToolRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]

class MCPToolResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Simple MCP Tools
async def script_research_tool(input_data: Dict[str, Any]) -> MCPToolResponse:
    """Script research tool"""
    try:
        text = input_data.get("text", "")
        week = input_data.get("week", 1)
        days_list = input_data.get("days_list", [])
        
        # Simple research logic
        result = {
            "week": week,
            "theme": f"Week {week} Theme: AI and Technology",
            "days": {day: f"{day} content for week {week}" for day in days_list},
            "original_text": text[:100] + "..." if len(text) > 100 else text
        }
        
        return MCPToolResponse(
            success=True,
            data=result,
            metadata={"tool": "script_research"}
        )
    except Exception as e:
        return MCPToolResponse(
            success=False,
            error=str(e),
            metadata={"tool": "script_research"}
        )

async def quality_control_tool(input_data: Dict[str, Any]) -> MCPToolResponse:
    """Quality control tool"""
    try:
        content = input_data.get("content", "")
        platform = input_data.get("platform", "")
        
        # Simple QC logic
        result = {
            "content": content,
            "platform": platform,
            "quality_score": 95,
            "character_count": len(content),
            "word_count": len(content.split()),
            "issues_found": [],
            "recommendations": ["Content looks good!"]
        }
        
        return MCPToolResponse(
            success=True,
            data=result,
            metadata={"tool": "quality_control"}
        )
    except Exception as e:
        return MCPToolResponse(
            success=False,
            error=str(e),
            metadata={"tool": "quality_control"}
        )

async def platform_generation_tool(input_data: Dict[str, Any]) -> MCPToolResponse:
    """Platform generation tool"""
    try:
        content = input_data.get("content", "")
        platform = input_data.get("platform", "linkedin")
        
        # Use existing platform processing
        processed_content = process_content_for_platform(
            content, 
            platform, 
            PLATFORM_LIMITS.get(platform, {})
        )
        
        result = {
            "content": processed_content,
            "platform": platform,
            "character_count": len(processed_content),
            "word_count": len(processed_content.split())
        }
        
        return MCPToolResponse(
            success=True,
            data=result,
            metadata={"tool": f"{platform}_generation"}
        )
    except Exception as e:
        return MCPToolResponse(
            success=False,
            error=str(e),
            metadata={"tool": f"{platform}_generation"}
        )

# Tool registry
MCP_TOOLS = {
    "script_research": script_research_tool,
    "quality_control": quality_control_tool,
    "platform_generation": platform_generation_tool
}

# MCP Endpoints
@mcp_router.post("/tools/execute", response_model=MCPToolResponse)
async def execute_tool(request: MCPToolRequest):
    """Execute an MCP tool"""
    try:
        if request.tool_name not in MCP_TOOLS:
            raise HTTPException(status_code=404, detail=f"Tool {request.tool_name} not found")
        
        tool_func = MCP_TOOLS[request.tool_name]
        result = await tool_func(request.input_data)
        
        return result
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.get("/tools", response_model=List[str])
async def list_tools():
    """List available MCP tools"""
    return list(MCP_TOOLS.keys())

@mcp_router.post("/generate-content", response_model=MCPToolResponse)
async def generate_content(
    text: str,
    week: int = 1,
    platform: str = "linkedin"
):
    """Generate content using MCP workflow"""
    try:
        # Step 1: Script Research
        research_result = await script_research_tool({
            "text": text,
            "week": week,
            "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        })
        
        if not research_result.success:
            return research_result
        
        # Step 2: Quality Control
        qc_result = await quality_control_tool({
            "content": str(research_result.data),
            "platform": platform
        })
        
        if not qc_result.success:
            return qc_result
        
        # Step 3: Platform Generation
        platform_result = await platform_generation_tool({
            "content": str(qc_result.data.get("content", "")),
            "platform": platform
        })
        
        return MCPToolResponse(
            success=platform_result.success,
            data={
                "research": research_result.data,
                "quality_control": qc_result.data,
                "platform_content": platform_result.data
            },
            error=platform_result.error,
            metadata={"workflow": "content_generation"}
        )
        
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        return MCPToolResponse(
            success=False,
            error=str(e),
            metadata={"workflow": "content_generation"}
        )

@mcp_router.get("/health")
async def mcp_health():
    """MCP health check"""
    return {
        "status": "healthy",
        "tools_count": len(MCP_TOOLS),
        "server": "vernal-contentum-direct-mcp",
        "available_tools": list(MCP_TOOLS.keys())
    }
