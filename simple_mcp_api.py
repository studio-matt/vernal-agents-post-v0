"""
Simple MCP API Endpoints for Vernal Contentum
Uses custom MCP implementation without external dependencies
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from simple_mcp import simple_mcp_server
import logging

logger = logging.getLogger(__name__)

# Create Simple MCP API router
simple_mcp_router = APIRouter(prefix="/mcp", tags=["MCP Tools"])

# Pydantic models for API requests
class SimpleMCPToolRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]

class SimpleMCPToolResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class GenerateContentRequest(BaseModel):
    text: str
    week: int = 1
    platform: str = "linkedin"
    campaign_id: Optional[str] = None
    author_personality: Optional[str] = None
    use_crewai: bool = False

# MCP Tool Endpoints
@simple_mcp_router.post("/tools/execute", response_model=SimpleMCPToolResponse)
async def execute_tool(request: SimpleMCPToolRequest):
    """Execute an MCP tool"""
    try:
        tool = simple_mcp_server.get_tool(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {request.tool_name} not found")
        
        result = await tool.execute(request.input_data)
        
        return SimpleMCPToolResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@simple_mcp_router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools():
    """List all available MCP tools"""
    try:
        tools = []
        for tool in simple_mcp_server.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@simple_mcp_router.get("/tools/{tool_name}", response_model=Dict[str, Any])
async def get_tool_info(tool_name: str):
    """Get information about a specific MCP tool"""
    try:
        tool = simple_mcp_server.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema
        }
    except Exception as e:
        logger.error(f"Error getting tool info for {tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Content Generation Endpoints (MCP-powered)
@simple_mcp_router.post("/generate-content", response_model=SimpleMCPToolResponse)
async def generate_content(request: GenerateContentRequest):
    """Generate content using MCP tools. Set use_crewai=True to use CrewAI orchestration."""
    try:
        # Extract parameters from request body
        text = request.text
        week = request.week
        platform = request.platform
        campaign_id = request.campaign_id
        author_personality = request.author_personality
        use_crewai = request.use_crewai
        
        # If CrewAI is requested, use CrewAI workflow
        if use_crewai:
            crewai_tool = simple_mcp_server.get_tool("crewai_content_generation")
            if crewai_tool:
                result = await crewai_tool.execute({
                    "text": text,
                    "week": week,
                    "platform": platform,
                    "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "author_personality": author_personality,
                    "use_qc": True
                })
                # Convert CrewAI result format to SimpleMCPToolResponse format
                if result.success:
                    return SimpleMCPToolResponse(
                        success=True,
                        data={
                            "research": result.data.get("research"),
                            "quality_control": result.data.get("quality_control"),
                            "platform_content": result.data.get("writing") or result.data.get("final_content"),
                            "crewai_metadata": result.metadata
                        },
                        metadata={
                            **result.metadata,
                            "workflow": "crewai_content_generation"
                        }
                    )
                else:
                    return SimpleMCPToolResponse(
                        success=False,
                        error=result.error,
                        metadata={"workflow": "crewai_content_generation"}
                    )
            else:
                logger.warning("CrewAI tool requested but not available, falling back to manual")
        
        # Manual orchestration (original flow)
        # Step 1: Script Research
        research_tool = simple_mcp_server.get_tool("script_research")
        research_result = await research_tool.execute({
            "text": text,
            "week": week,
            "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        })
        
        if not research_result.success:
            return SimpleMCPToolResponse(
                success=False,
                error=f"Script research failed: {research_result.error}"
            )
        
        # Step 2: Quality Control
        qc_tool = simple_mcp_server.get_tool("quality_control")
        qc_result = await qc_tool.execute({
            "content": str(research_result.data),
            "platform": platform
        })
        
        if not qc_result.success:
            return SimpleMCPToolResponse(
                success=False,
                error=f"Quality control failed: {qc_result.error}"
            )
        
        # Step 3: Platform Generation
        platform_tool = simple_mcp_server.get_tool(f"{platform}_generation")
        platform_result = await platform_tool.execute({
            "content": str(qc_result.data.get("content", "")),
            "platform": platform,
            "author_personality": author_personality or ""
        })
        
        return SimpleMCPToolResponse(
            success=platform_result.success,
            data={
                "research": research_result.data,
                "quality_control": qc_result.data,
                "platform_content": platform_result.data
            },
            error=platform_result.error,
            metadata={"workflow": "content_generation", "use_crewai": False}
        )
        
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@simple_mcp_router.post("/regenerate-content", response_model=SimpleMCPToolResponse)
async def regenerate_content(
    content: str,
    regeneration_type: str = "weekly",
    week: Optional[int] = None,
    day: Optional[str] = None,
    platform: str = "linkedin"
):
    """Regenerate content using MCP tools"""
    try:
        # Regenerate content
        regen_tool = simple_mcp_server.get_tool("regenerate_content")
        regen_result = await regen_tool.execute({
            "content": content,
            "week": week or 1
        })
        
        if not regen_result.success:
            return SimpleMCPToolResponse(
                success=False,
                error=f"Content regeneration failed: {regen_result.error}"
            )
        
        # Quality control
        qc_tool = simple_mcp_server.get_tool("quality_control")
        qc_result = await qc_tool.execute({
            "content": regen_result.data.get("regenerated_content", ""),
            "platform": platform
        })
        
        # Platform generation
        platform_tool = simple_mcp_server.get_tool(f"{platform}_generation")
        platform_result = await platform_tool.execute({
            "content": qc_result.data.get("content", ""),
            "platform": platform
        })
        
        return SimpleMCPToolResponse(
            success=platform_result.success,
            data={
                "regenerated_content": regen_result.data,
                "quality_control": qc_result.data,
                "platform_content": platform_result.data
            },
            error=platform_result.error,
            metadata={"workflow": "content_regeneration"}
        )
        
    except Exception as e:
        logger.error(f"Error regenerating content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Platform-Specific Content Generation
@simple_mcp_router.post("/generate/{platform}", response_model=SimpleMCPToolResponse)
async def generate_platform_content(
    platform: str,
    content: str,
    author_personality: Optional[str] = None
):
    """Generate platform-specific content using MCP tools"""
    try:
        if platform not in ["linkedin", "twitter", "facebook", "instagram", "tiktok", "youtube", "wordpress"]:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
        
        tool = simple_mcp_server.get_tool(f"{platform}_generation")
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {platform}_generation not found")
        
        result = await tool.execute({
            "content": content,
            "platform": platform,
            "author_personality": author_personality or ""
        })
        
        return SimpleMCPToolResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Error generating {platform} content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@simple_mcp_router.get("/health")
async def mcp_health():
    """MCP health check"""
    return {
        "status": "healthy",
        "tools_count": len(simple_mcp_server.tools),
        "server": "vernal-contentum-simple-mcp",
        "available_tools": list(simple_mcp_server.tools.keys())
    }
