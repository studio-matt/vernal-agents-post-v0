"""
Enhanced MCP API Endpoints
Advanced workflow orchestration and tool management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enhanced_mcp import enhanced_mcp_server, WorkflowResult, ToolResult
import logging

logger = logging.getLogger(__name__)

# Create router
enhanced_mcp_router = APIRouter(prefix="/mcp/enhanced", tags=["Enhanced MCP"])

# Pydantic models
class ToolRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]

class WorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Dict[str, Any]

class ToolStatsResponse(BaseModel):
    tool_stats: Dict[str, Any]
    total_tools: int
    active_tools: int

class WorkflowListResponse(BaseModel):
    workflows: List[str]
    total_workflows: int

# Health and Info Endpoints
@enhanced_mcp_router.get("/health")
async def enhanced_mcp_health():
    """Enhanced MCP server health check"""
    try:
        tool_count = len(enhanced_mcp_server.tools)
        workflow_count = len(enhanced_mcp_server.workflows)
        
        return {
            "status": "healthy",
            "server": "vernal-contentum-enhanced-mcp",
            "tools_count": tool_count,
            "workflows_count": workflow_count,
            "features": [
                "enhanced_error_handling",
                "workflow_orchestration", 
                "tool_validation",
                "execution_timeout",
                "usage_statistics"
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.get("/tools")
async def list_enhanced_tools():
    """List all available enhanced tools"""
    try:
        tools = {}
        for name, tool in enhanced_mcp_server.tools.items():
            tools[name] = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "timeout": tool.timeout,
                "usage_count": tool.usage_count,
                "success_rate": tool.success_count / max(tool.usage_count, 1) * 100
            }
        
        return {
            "tools": tools,
            "total_tools": len(tools),
            "available_tools": list(tools.keys())
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Get detailed information about a specific tool"""
    try:
        tool = enhanced_mcp_server.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "timeout": tool.timeout,
            "retry_count": tool.retry_count,
            "statistics": tool.get_stats()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.get("/stats")
async def get_tool_stats():
    """Get comprehensive tool usage statistics"""
    try:
        stats = enhanced_mcp_server.get_tool_stats()
        total_usage = sum(tool["usage_count"] for tool in stats.values())
        total_success = sum(tool["success_count"] for tool in stats.values())
        overall_success_rate = (total_success / max(total_usage, 1)) * 100
        
        return ToolStatsResponse(
            tool_stats=stats,
            total_tools=len(stats),
            active_tools=len([t for t in stats.values() if t["usage_count"] > 0])
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Tool Execution Endpoints
@enhanced_mcp_router.post("/tools/execute")
async def execute_tool(request: ToolRequest):
    """Execute a specific tool with enhanced error handling"""
    try:
        tool = enhanced_mcp_server.get_tool(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
        
        result = await tool.execute(request.input_data)
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.post("/tools/{tool_name}/execute")
async def execute_tool_by_name(tool_name: str, input_data: Dict[str, Any]):
    """Execute a tool by name with input data"""
    try:
        tool = enhanced_mcp_server.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        result = await tool.execute(input_data)
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Workflow Endpoints
@enhanced_mcp_router.get("/workflows")
async def list_workflows():
    """List all available workflows"""
    try:
        workflows = enhanced_mcp_server.list_workflows()
        return WorkflowListResponse(
            workflows=workflows,
            total_workflows=len(workflows)
        )
    except Exception as e:
        logger.error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.get("/workflows/{workflow_name}")
async def get_workflow_info(workflow_name: str):
    """Get detailed information about a specific workflow"""
    try:
        if workflow_name not in enhanced_mcp_server.workflows:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
        
        workflow_steps = enhanced_mcp_server.workflows[workflow_name]
        steps_info = []
        
        for step in workflow_steps:
            steps_info.append({
                "tool_name": step.tool_name,
                "required": step.required,
                "description": step.description,
                "depends_on": step.depends_on
            })
        
        return {
            "workflow_name": workflow_name,
            "steps": steps_info,
            "total_steps": len(steps_info),
            "required_steps": len([s for s in steps_info if s["required"]]),
            "optional_steps": len([s for s in steps_info if not s["required"]])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.post("/workflows/execute")
async def execute_workflow(request: WorkflowRequest):
    """Execute a workflow with enhanced orchestration"""
    try:
        result = await enhanced_mcp_server.execute_workflow(
            request.workflow_name, 
            request.input_data
        )
        return result.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.post("/workflows/{workflow_name}/execute")
async def execute_workflow_by_name(workflow_name: str, input_data: Dict[str, Any]):
    """Execute a workflow by name with input data"""
    try:
        result = await enhanced_mcp_server.execute_workflow(workflow_name, input_data)
        return result.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Convenience Endpoints for Common Operations
@enhanced_mcp_router.post("/content/generate")
async def generate_content_workflow(
    text: str,
    week: int = 1,
    platforms: List[str] = ["linkedin", "twitter", "facebook"],
    author_personality: Optional[str] = None
):
    """Generate content using the content generation workflow"""
    try:
        input_data = {
            "text": text,
            "week": week,
            "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "platforms": platforms,
            "author_personality": author_personality or "professional"
        }
        
        result = await enhanced_mcp_server.execute_workflow("content_generation", input_data)
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Content generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.post("/content/regenerate")
async def regenerate_content_workflow(
    content: str,
    week: int = 1,
    platforms: List[str] = ["linkedin", "twitter"]
):
    """Regenerate content using the regeneration workflow"""
    try:
        input_data = {
            "content": content,
            "week": week,
            "platforms": platforms
        }
        
        result = await enhanced_mcp_server.execute_workflow("platform_content", input_data)
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Content regeneration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Testing and Validation Endpoints
@enhanced_mcp_router.post("/test/tool")
async def test_tool(tool_name: str, test_data: Dict[str, Any]):
    """Test a tool with sample data"""
    try:
        tool = enhanced_mcp_server.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Validate input first
        try:
            tool.validate_input(test_data)
            validation_result = {"valid": True, "message": "Input validation passed"}
        except Exception as e:
            validation_result = {"valid": False, "message": str(e)}
        
        # Execute tool
        result = await tool.execute(test_data)
        
        return {
            "tool_name": tool_name,
            "validation": validation_result,
            "execution_result": result.to_dict(),
            "test_data": test_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@enhanced_mcp_router.get("/test/workflow/{workflow_name}")
async def test_workflow(workflow_name: str):
    """Test a workflow with sample data"""
    try:
        if workflow_name not in enhanced_mcp_server.workflows:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
        
        # Create sample test data
        test_data = {
            "text": "Sample content for testing workflow execution",
            "week": 1,
            "days_list": ["Monday", "Tuesday", "Wednesday"],
            "content": "Sample content to process",
            "platform": "linkedin",
            "author_personality": "professional"
        }
        
        result = await enhanced_mcp_server.execute_workflow(workflow_name, test_data)
        
        return {
            "workflow_name": workflow_name,
            "test_data": test_data,
            "execution_result": result.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
