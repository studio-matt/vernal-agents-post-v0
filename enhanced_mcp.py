"""
Enhanced MCP Implementation for Vernal Contentum
Improved error handling, validation, and workflow orchestration
"""

from typing import Dict, Any, List, Optional, Callable, Union
import json
import logging
import asyncio
from datetime import datetime
from enum import Enum
from database import DatabaseManager
from tools import process_content_for_platform, PLATFORM_LIMITS
from agents import get_agent_data

logger = logging.getLogger(__name__)

class ToolStatus(Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ValidationError(Exception):
    """Custom validation error"""
    pass

class ToolResult:
    """Enhanced tool result class with metadata"""
    def __init__(
        self, 
        success: bool, 
        data: Any = None, 
        error: str = None, 
        metadata: Dict[str, Any] = None,
        execution_time: float = None,
        status: ToolStatus = ToolStatus.COMPLETED
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.execution_time = execution_time
        self.status = status
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "status": self.status.value,
            "timestamp": self.timestamp
        }

class EnhancedTool:
    """Enhanced tool class with validation and error handling"""
    def __init__(
        self, 
        name: str, 
        description: str, 
        handler: Callable, 
        input_schema: Dict[str, Any],
        timeout: int = 300,
        retry_count: int = 3
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema
        self.timeout = timeout
        self.retry_count = retry_count
        self.usage_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data against schema"""
        try:
            # Check required fields
            required_fields = self.input_schema.get("required", [])
            for field in required_fields:
                if field not in input_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Basic type validation
            properties = self.input_schema.get("properties", {})
            for field, value in input_data.items():
                if field in properties:
                    field_schema = properties[field]
                    expected_type = field_schema.get("type")
                    
                    if expected_type == "string" and not isinstance(value, str):
                        raise ValidationError(f"Field '{field}' must be a string")
                    elif expected_type == "integer" and not isinstance(value, int):
                        raise ValidationError(f"Field '{field}' must be an integer")
                    elif expected_type == "array" and not isinstance(value, list):
                        raise ValidationError(f"Field '{field}' must be an array")
            
            return True
        except Exception as e:
            logger.error(f"Validation error for tool {self.name}: {str(e)}")
            raise ValidationError(str(e))
    
    async def execute(self, input_data: Dict[str, Any]) -> ToolResult:
        """Execute the tool with enhanced error handling"""
        start_time = datetime.utcnow()
        self.usage_count += 1
        
        try:
            # Validate input
            self.validate_input(input_data)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.handler(input_data),
                timeout=self.timeout
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.success_count += 1
            
            return ToolResult(
                success=True,
                data=result,
                execution_time=execution_time,
                status=ToolStatus.COMPLETED,
                metadata={"tool": self.name, "usage_count": self.usage_count}
            )
            
        except ValidationError as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.error_count += 1
            logger.error(f"Validation error in tool {self.name}: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}",
                execution_time=execution_time,
                status=ToolStatus.FAILED,
                metadata={"tool": self.name, "error_type": "validation"}
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.error_count += 1
            logger.error(f"Timeout error in tool {self.name}")
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {self.timeout} seconds",
                execution_time=execution_time,
                status=ToolStatus.FAILED,
                metadata={"tool": self.name, "error_type": "timeout"}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.error_count += 1
            logger.error(f"Error in tool {self.name}: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                status=ToolStatus.FAILED,
                metadata={"tool": self.name, "error_type": "execution"}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        return {
            "name": self.name,
            "description": self.description,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(self.usage_count, 1) * 100
        }

class WorkflowStep:
    """Workflow step definition"""
    def __init__(
        self, 
        tool_name: str, 
        required: bool = True, 
        description: str = "",
        depends_on: List[str] = None
    ):
        self.tool_name = tool_name
        self.required = required
        self.description = description
        self.depends_on = depends_on or []
        self.status = ToolStatus.PENDING
        self.result = None

class WorkflowResult:
    """Workflow execution result"""
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = ToolStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.total_time = None
        self.errors = []
        self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_time": self.total_time,
            "errors": self.errors,
            "data": self.data,
            "steps": {name: {
                "status": step.status.value,
                "required": step.required,
                "description": step.description,
                "result": step.result.to_dict() if step.result else None
            } for name, step in self.steps.items()}
        }

class EnhancedMCPServer:
    """Enhanced MCP server with workflow orchestration"""
    
    def __init__(self):
        self.tools: Dict[str, EnhancedTool] = {}
        self.db_manager = DatabaseManager()
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self._register_tools()
        self._register_workflows()
        logger.info("Enhanced MCP Server initialized")
    
    def _register_tools(self):
        """Register all enhanced tools"""
        
        # Script Research Tool
        self.register_tool(EnhancedTool(
            name="script_research",
            description="Analyze text content and extract themes for weekly content planning",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text content to analyze"},
                    "week": {"type": "integer", "description": "Week number for content planning"},
                    "days_list": {"type": "array", "items": {"type": "string"}, "description": "List of days for subcontent"}
                },
                "required": ["text", "week", "days_list"]
            },
            handler=self._handle_script_research,
            timeout=120
        ))
        
        # Quality Control Tool
        self.register_tool(EnhancedTool(
            name="quality_control",
            description="Review and validate content for quality standards and compliance",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to review"},
                    "platform": {"type": "string", "description": "Target platform for content"},
                    "forbidden_words": {"type": "array", "items": {"type": "string"}, "description": "List of forbidden words"}
                },
                "required": ["content", "platform"]
            },
            handler=self._handle_quality_control,
            timeout=60
        ))
        
        # Content Regeneration Tool
        self.register_tool(EnhancedTool(
            name="regenerate_content",
            description="Regenerate weekly content with fresh perspective",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to regenerate"},
                    "week": {"type": "integer", "description": "Week number"}
                },
                "required": ["content", "week"]
            },
            handler=self._handle_regenerate_content,
            timeout=180
        ))
        
        # Platform Generation Tools
        platforms = ["linkedin", "twitter", "facebook", "instagram", "tiktok", "youtube", "wordpress"]
        for platform in platforms:
            self.register_tool(EnhancedTool(
                name=f"{platform}_generation",
                description=f"Generate {platform}-specific content optimized for the platform",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Base content to adapt"},
                        "platform": {"type": "string", "description": "Target platform"},
                        "author_personality": {"type": "string", "description": "Author personality style"}
                    },
                    "required": ["content", "platform"]
                },
                handler=self._create_platform_handler(platform),
                timeout=90
            ))
        
        logger.info(f"Registered {len(self.tools)} enhanced tools")
    
    def _register_workflows(self):
        """Register predefined workflows"""
        
        # Content Generation Workflow
        self.workflows["content_generation"] = [
            WorkflowStep("script_research", required=True, description="Analyze content and extract themes"),
            WorkflowStep("quality_control", required=True, description="Review content for quality"),
            WorkflowStep("linkedin_generation", required=True, description="Generate LinkedIn content"),
            WorkflowStep("twitter_generation", required=True, description="Generate Twitter content"),
            WorkflowStep("facebook_generation", required=True, description="Generate Facebook content")
        ]
        
        # Platform-Specific Workflow
        self.workflows["platform_content"] = [
            WorkflowStep("script_research", required=True, description="Analyze content"),
            WorkflowStep("quality_control", required=True, description="Quality check"),
            WorkflowStep("linkedin_generation", required=False, description="LinkedIn content"),
            WorkflowStep("twitter_generation", required=False, description="Twitter content"),
            WorkflowStep("instagram_generation", required=False, description="Instagram content"),
            WorkflowStep("tiktok_generation", required=False, description="TikTok content"),
            WorkflowStep("youtube_generation", required=False, description="YouTube content"),
            WorkflowStep("wordpress_generation", required=False, description="WordPress content")
        ]
        
        logger.info(f"Registered {len(self.workflows)} workflows")
    
    def register_tool(self, tool: EnhancedTool):
        """Register an enhanced tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[EnhancedTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics for all tools"""
        return {name: tool.get_stats() for name, tool in self.tools.items()}
    
    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return list(self.workflows.keys())
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> WorkflowResult:
        """Execute a workflow with enhanced orchestration"""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow {workflow_name} not found")
        
        workflow_steps = self.workflows[workflow_name]
        result = WorkflowResult(workflow_name)
        result.start_time = datetime.utcnow().isoformat()
        
        try:
            # Initialize workflow steps
            for step in workflow_steps:
                result.steps[step.tool_name] = step
            
            # Execute steps in order
            for step in workflow_steps:
                if step.status == ToolStatus.PENDING:
                    step.status = ToolStatus.RUNNING
                    
                    try:
                        tool = self.get_tool(step.tool_name)
                        if not tool:
                            raise ValueError(f"Tool {step.tool_name} not found")
                        
                        step_result = await tool.execute(input_data)
                        step.result = step_result
                        
                        if step_result.success:
                            step.status = ToolStatus.COMPLETED
                            result.data[step.tool_name] = step_result.data
                        else:
                            step.status = ToolStatus.FAILED
                            if step.required:
                                result.errors.append(f"Required step {step.tool_name} failed: {step_result.error}")
                                break
                            else:
                                result.errors.append(f"Optional step {step.tool_name} failed: {step_result.error}")
                    
                    except Exception as e:
                        step.status = ToolStatus.FAILED
                        step.result = ToolResult(success=False, error=str(e))
                        if step.required:
                            result.errors.append(f"Required step {step.tool_name} failed: {str(e)}")
                            break
                        else:
                            result.errors.append(f"Optional step {step.tool_name} failed: {str(e)}")
            
            # Determine overall workflow status
            if any(step.status == ToolStatus.FAILED and step.required for step in workflow_steps):
                result.status = ToolStatus.FAILED
            else:
                result.status = ToolStatus.COMPLETED
            
        except Exception as e:
            result.status = ToolStatus.FAILED
            result.errors.append(f"Workflow execution failed: {str(e)}")
        
        finally:
            result.end_time = datetime.utcnow().isoformat()
            if result.start_time and result.end_time:
                start = datetime.fromisoformat(result.start_time)
                end = datetime.fromisoformat(result.end_time)
                result.total_time = (end - start).total_seconds()
        
        return result
    
    def _create_platform_handler(self, platform: str):
        """Create platform-specific handler"""
        async def handler(input_data: Dict[str, Any]) -> ToolResult:
            try:
                content = input_data.get("content", "")
                author_personality = input_data.get("author_personality", "")
                
                # Use existing platform processing logic
                processed_content = process_content_for_platform(
                    content, 
                    platform, 
                    author_personality
                )
                
                return ToolResult(
                    success=True,
                    data={
                        "platform": platform,
                        "content": processed_content,
                        "character_count": len(processed_content),
                        "limit": PLATFORM_LIMITS.get(platform, {}).get("max_length", 0)
                    },
                    metadata={"platform": platform, "handler": "platform_specific"}
                )
                
            except Exception as e:
                logger.error(f"Error in {platform} generation: {str(e)}")
                return ToolResult(
                    success=False,
                    error=str(e),
                    metadata={"platform": platform, "error": "generation_failed"}
                )
        
        return handler
    
    async def _handle_script_research(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle script research tool execution"""
        try:
            text = input_data.get("text", "")
            week = input_data.get("week", 1)
            days_list = input_data.get("days_list", [])
            
            # Get agent data safely
            agent_data = get_agent_data("script_research_agent")
            
            # Simulate script research (replace with actual agent call)
            themes = {
                "main_themes": ["content strategy", "audience engagement", "brand storytelling"],
                "sub_themes": ["social media trends", "content optimization", "user experience"],
                "week": week,
                "days": days_list,
                "analysis_summary": f"Analyzed {len(text)} characters for week {week}"
            }
            
            return ToolResult(
                success=True,
                data=themes,
                metadata={"agent": agent_data.get("role", "Script Research Agent"), "text_length": len(text)}
            )
            
        except Exception as e:
            logger.error(f"Error in script research: {str(e)}")
            return ToolResult(success=False, error=str(e))
    
    async def _handle_quality_control(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle quality control tool execution"""
        try:
            content = input_data.get("content", "")
            platform = input_data.get("platform", "")
            forbidden_words = input_data.get("forbidden_words", [])
            
            # Get agent data safely
            agent_data = get_agent_data("qc_agent")
            
            # Simulate quality control (replace with actual agent call)
            quality_report = {
                "content_length": len(content),
                "platform": platform,
                "quality_score": 85,
                "issues_found": [],
                "recommendations": ["Consider adding more engaging visuals", "Optimize for mobile viewing"],
                "compliance_check": "passed",
                "forbidden_words_detected": []
            }
            
            return ToolResult(
                success=True,
                data=quality_report,
                metadata={"agent": agent_data.get("role", "Quality Control Agent"), "platform": platform}
            )
            
        except Exception as e:
            logger.error(f"Error in quality control: {str(e)}")
            return ToolResult(success=False, error=str(e))
    
    async def _handle_regenerate_content(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle content regeneration tool execution"""
        try:
            content = input_data.get("content", "")
            week = input_data.get("week", 1)
            
            # Get agent data safely
            agent_data = get_agent_data("regenrate_content_agent")
            
            # Simulate content regeneration (replace with actual agent call)
            regenerated_content = f"Regenerated content for week {week}: {content[:100]}... [Fresh perspective applied]"
            
            return ToolResult(
                success=True,
                data={
                    "original_content": content,
                    "regenerated_content": regenerated_content,
                    "week": week,
                    "improvements": ["Enhanced engagement", "Better structure", "Fresh perspective"]
                },
                metadata={"agent": agent_data.get("role", "Content Regeneration Agent"), "week": week}
            )
            
        except Exception as e:
            logger.error(f"Error in content regeneration: {str(e)}")
            return ToolResult(success=False, error=str(e))

# Create enhanced MCP server instance
enhanced_mcp_server = EnhancedMCPServer()
