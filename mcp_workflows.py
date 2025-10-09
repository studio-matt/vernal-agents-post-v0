"""
MCP Workflow Orchestrator for Vernal Contentum
Manages complex workflows using MCP tools
"""

from mcp import Workflow, WorkflowStep, WorkflowResult
from mcp_server import mcp_server
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ContentGenerationWorkflow(Workflow):
    """Complete content generation workflow using MCP tools"""
    
    def __init__(self):
        super().__init__("content_generation")
        self.steps = [
            WorkflowStep("script_research", required=True, description="Analyze content and extract themes"),
            WorkflowStep("quality_control", required=True, description="Review content for quality"),
            WorkflowStep("platform_generation", required=True, description="Generate platform-specific content"),
            WorkflowStep("content_storage", required=True, description="Store generated content")
        ]
    
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowResult:
        """Execute the complete content generation workflow"""
        try:
            logger.info("Starting content generation workflow")
            
            # Step 1: Script Research
            research_result = await self._call_tool("script_research", {
                "text": input_data.get("text", ""),
                "week": input_data.get("week", 1),
                "days_list": input_data.get("days_list", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            })
            
            if not research_result.success:
                return WorkflowResult(
                    success=False,
                    error=f"Script research failed: {research_result.error}",
                    steps_completed=["script_research"]
                )
            
            # Step 2: Quality Control
            qc_result = await self._call_tool("quality_control", {
                "content": research_result.data.get("content", ""),
                "platform": input_data.get("platform", "general"),
                "forbidden_words": input_data.get("forbidden_words", [])
            })
            
            if not qc_result.success:
                return WorkflowResult(
                    success=False,
                    error=f"Quality control failed: {qc_result.error}",
                    steps_completed=["script_research", "quality_control"]
                )
            
            # Step 3: Platform-Specific Generation
            platform = input_data.get("platform", "linkedin")
            platform_result = await self._call_tool(f"{platform}_generation", {
                "content": qc_result.data.get("content", ""),
                "platform": platform,
                "author_personality": input_data.get("author_personality", "")
            })
            
            if not platform_result.success:
                return WorkflowResult(
                    success=False,
                    error=f"Platform generation failed: {platform_result.error}",
                    steps_completed=["script_research", "quality_control", "platform_generation"]
                )
            
            # Step 4: Content Storage (placeholder)
            storage_result = await self._call_tool("content_storage", {
                "content": platform_result.data,
                "platform": platform,
                "campaign_id": input_data.get("campaign_id", "")
            })
            
            return WorkflowResult(
                success=True,
                data={
                    "research": research_result.data,
                    "quality_control": qc_result.data,
                    "platform_content": platform_result.data,
                    "storage": storage_result.data if storage_result.success else None
                },
                steps_completed=[step.name for step in self.steps]
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return WorkflowResult(
                success=False,
                error=str(e),
                steps_completed=[]
            )
    
    async def _call_tool(self, tool_name: str, input_data: Dict[str, Any]):
        """Call an MCP tool"""
        tool = mcp_server.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        return await tool.execute(input_data)

class ContentRegenerationWorkflow(Workflow):
    """Content regeneration workflow using MCP tools"""
    
    def __init__(self):
        super().__init__("content_regeneration")
        self.steps = [
            WorkflowStep("regenerate_content", required=True, description="Regenerate weekly content"),
            WorkflowStep("regenerate_subcontent", required=True, description="Regenerate daily subcontent"),
            WorkflowStep("quality_control", required=True, description="Review regenerated content"),
            WorkflowStep("platform_generation", required=True, description="Generate platform-specific versions")
        ]
    
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowResult:
        """Execute content regeneration workflow"""
        try:
            logger.info("Starting content regeneration workflow")
            
            # Determine regeneration type
            regeneration_type = input_data.get("type", "weekly")
            
            if regeneration_type == "weekly":
                # Regenerate weekly content
                content_result = await self._call_tool("regenerate_content", {
                    "content": input_data.get("content", ""),
                    "week": input_data.get("week", 1)
                })
            else:
                # Regenerate daily subcontent
                content_result = await self._call_tool("regenerate_subcontent", {
                    "subcontent": input_data.get("subcontent", ""),
                    "day": input_data.get("day", "Monday")
                })
            
            if not content_result.success:
                return WorkflowResult(
                    success=False,
                    error=f"Content regeneration failed: {content_result.error}",
                    steps_completed=["regenerate_content" if regeneration_type == "weekly" else "regenerate_subcontent"]
                )
            
            # Quality control
            qc_result = await self._call_tool("quality_control", {
                "content": content_result.data.get("regenerated_content", ""),
                "platform": input_data.get("platform", "general")
            })
            
            if not qc_result.success:
                return WorkflowResult(
                    success=False,
                    error=f"Quality control failed: {qc_result.error}",
                    steps_completed=["regenerate_content", "quality_control"]
                )
            
            # Platform generation
            platform = input_data.get("platform", "linkedin")
            platform_result = await self._call_tool(f"{platform}_generation", {
                "content": qc_result.data.get("content", ""),
                "platform": platform
            })
            
            return WorkflowResult(
                success=True,
                data={
                    "regenerated_content": content_result.data,
                    "quality_control": qc_result.data,
                    "platform_content": platform_result.data
                },
                steps_completed=[step.name for step in self.steps]
            )
            
        except Exception as e:
            logger.error(f"Regeneration workflow failed: {str(e)}")
            return WorkflowResult(
                success=False,
                error=str(e),
                steps_completed=[]
            )
    
    async def _call_tool(self, tool_name: str, input_data: Dict[str, Any]):
        """Call an MCP tool"""
        tool = mcp_server.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        return await tool.execute(input_data)

class WorkflowManager:
    """Manages MCP workflows and provides orchestration"""
    
    def __init__(self):
        self.workflows = {
            "content_generation": ContentGenerationWorkflow(),
            "content_regeneration": ContentRegenerationWorkflow()
        }
        logger.info("Workflow manager initialized")
    
    def get_workflow(self, name: str) -> Workflow:
        """Get a workflow by name"""
        if name not in self.workflows:
            raise ValueError(f"Workflow {name} not found")
        return self.workflows[name]
    
    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return list(self.workflows.keys())
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> WorkflowResult:
        """Execute a workflow with input data"""
        workflow = self.get_workflow(workflow_name)
        return await workflow.execute(input_data)

# Create workflow manager instance
workflow_manager = WorkflowManager()

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def test_workflow():
        result = await workflow_manager.execute_workflow("content_generation", {
            "text": "Sample text for analysis",
            "week": 1,
            "platform": "linkedin",
            "campaign_id": "test-123"
        })
        print(f"Workflow result: {result}")
    
    asyncio.run(test_workflow())
