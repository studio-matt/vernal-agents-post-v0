"""
MCP API Endpoints for Vernal Contentum
Integrates MCP tools with FastAPI endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from mcp_server import mcp_server
from mcp_workflows import workflow_manager
import logging

logger = logging.getLogger(__name__)

# Create MCP API router
mcp_router = APIRouter(prefix="/mcp", tags=["MCP Tools"])

# Pydantic models for API requests
class MCPToolRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]

class MCPWorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Dict[str, Any]

class MCPToolResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MCPWorkflowResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: Optional[List[str]] = None

# MCP Tool Endpoints
@mcp_router.post("/tools/execute", response_model=MCPToolResponse)
async def execute_tool(request: MCPToolRequest):
    """Execute an MCP tool"""
    try:
        tool = mcp_server.get_tool(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {request.tool_name} not found")
        
        result = await tool.execute(request.input_data)
        
        return MCPToolResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools():
    """List all available MCP tools"""
    try:
        tools = []
        for tool in mcp_server.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.get("/tools/{tool_name}", response_model=Dict[str, Any])
async def get_tool_info(tool_name: str):
    """Get information about a specific MCP tool"""
    try:
        tool = mcp_server.get_tool(tool_name)
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

# MCP Workflow Endpoints
@mcp_router.post("/workflows/execute", response_model=MCPWorkflowResponse)
async def execute_workflow(request: MCPWorkflowRequest):
    """Execute an MCP workflow"""
    try:
        result = await workflow_manager.execute_workflow(request.workflow_name, request.input_data)
        
        return MCPWorkflowResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            steps_completed=result.steps_completed
        )
    except Exception as e:
        logger.error(f"Error executing workflow {request.workflow_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.get("/workflows", response_model=List[str])
async def list_workflows():
    """List all available MCP workflows"""
    try:
        return workflow_manager.list_workflows()
    except Exception as e:
        logger.error(f"Error listing workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.get("/workflows/{workflow_name}", response_model=Dict[str, Any])
async def get_workflow_info(workflow_name: str):
    """Get information about a specific MCP workflow"""
    try:
        workflow = workflow_manager.get_workflow(workflow_name)
        return {
            "name": workflow.name,
            "steps": [
                {
                    "name": step.name,
                    "required": step.required,
                    "description": step.description
                }
                for step in workflow.steps
            ]
        }
    except Exception as e:
        logger.error(f"Error getting workflow info for {workflow_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Content Generation Endpoints (MCP-powered)
@mcp_router.post("/generate-content", response_model=MCPWorkflowResponse)
async def generate_content(
    text: str,
    week: int = 1,
    platform: str = "linkedin",
    campaign_id: Optional[str] = None,
    author_personality: Optional[str] = None
):
    """Generate content using MCP workflow"""
    try:
        input_data = {
            "text": text,
            "week": week,
            "platform": platform,
            "campaign_id": campaign_id or "",
            "author_personality": author_personality or "",
            "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        }
        
        result = await workflow_manager.execute_workflow("content_generation", input_data)
        
        return MCPWorkflowResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            steps_completed=result.steps_completed
        )
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@mcp_router.post("/regenerate-content", response_model=MCPWorkflowResponse)
async def regenerate_content(
    content: str,
    regeneration_type: str = "weekly",
    week: Optional[int] = None,
    day: Optional[str] = None,
    platform: str = "linkedin"
):
    """Regenerate content using MCP workflow"""
    try:
        input_data = {
            "type": regeneration_type,
            "content": content,
            "platform": platform
        }
        
        if regeneration_type == "weekly" and week:
            input_data["week"] = week
        elif regeneration_type == "daily" and day:
            input_data["day"] = day
        
        result = await workflow_manager.execute_workflow("content_regeneration", input_data)
        
        return MCPWorkflowResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            steps_completed=result.steps_completed
        )
    except Exception as e:
        logger.error(f"Error regenerating content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Platform-Specific Content Generation
@mcp_router.post("/generate/{platform}", response_model=MCPToolResponse)
async def generate_platform_content(
    platform: str,
    content: str,
    author_personality: Optional[str] = None
):
    """Generate platform-specific content using MCP tools"""
    try:
        if platform not in ["linkedin", "twitter", "facebook", "instagram", "tiktok", "youtube", "wordpress"]:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
        
        tool_name = f"{platform}_generation"
        tool = mcp_server.get_tool(tool_name)
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        result = await tool.execute({
            "content": content,
            "platform": platform,
            "author_personality": author_personality or ""
        })
        
        return MCPToolResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Error generating {platform} content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@mcp_router.get("/health")
async def mcp_health():
    """MCP health check"""
    return {
        "status": "healthy",
        "tools_count": len(mcp_server.tools),
        "workflows_count": len(workflow_manager.workflows),
        "server": "vernal-contentum-mcp"
    }
