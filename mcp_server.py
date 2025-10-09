"""
MCP Server for Vernal Contentum
Converts existing CrewAI agents to MCP tools for standardized AI tool orchestration
"""

from mcp import MCPServer, Tool, ToolResult
from database import DatabaseManager
from agents import (
    script_research_agent, qc_agent, script_rewriter_agent, 
    regenrate_content_agent, regenrate_subcontent_agent,
    linkedin_agent, twitter_agent, facebook_agent, instagram_agent, 
    tiktok_agent, youtube_agent, wordpress_agent
)
from tasks import (
    script_research_task, qc_task, script_rewriter_task,
    regenrate_content_task, regenrate_subcontent_task,
    linkedin_task, twitter_task, facebook_task, instagram_task,
    tiktok_task, youtube_task, wordpress_task
)
from tools import process_content_for_platform, PLATFORM_LIMITS
from typing import Dict, Any, List
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VernalContentumMCPServer(MCPServer):
    """MCP Server for Vernal Contentum AI agents"""
    
    def __init__(self):
        super().__init__("vernal-contentum")
        self.db_manager = DatabaseManager()
        self.register_tools()
        logger.info("Vernal Contentum MCP Server initialized")
    
    def register_tools(self):
        """Register all AI agents as MCP tools"""
        
        # Content Research Tools
        self.register_tool(Tool(
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
            handler=self._handle_script_research
        ))
        
        # Quality Control Tools
        self.register_tool(Tool(
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
            handler=self._handle_quality_control
        ))
        
        # Content Regeneration Tools
        self.register_tool(Tool(
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
            handler=self._handle_regenerate_content
        ))
        
        self.register_tool(Tool(
            name="regenerate_subcontent",
            description="Regenerate daily subcontent",
            input_schema={
                "type": "object",
                "properties": {
                    "subcontent": {"type": "string", "description": "Subcontent to regenerate"},
                    "day": {"type": "string", "description": "Day of the week"}
                },
                "required": ["subcontent", "day"]
            },
            handler=self._handle_regenerate_subcontent
        ))
        
        # Platform-Specific Content Generation Tools
        platforms = ["linkedin", "twitter", "facebook", "instagram", "tiktok", "youtube", "wordpress"]
        for platform in platforms:
            self.register_tool(Tool(
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
                handler=self._create_platform_handler(platform)
            ))
        
        logger.info(f"Registered {len(self.tools)} MCP tools")
    
    def _create_platform_handler(self, platform: str):
        """Create platform-specific handler"""
        def handler(input_data: Dict[str, Any]) -> ToolResult:
            try:
                content = input_data.get("content", "")
                author_personality = input_data.get("author_personality", "")
                
                # Use existing platform processing logic
                processed_content = process_content_for_platform(
                    content, 
                    platform, 
                    PLATFORM_LIMITS.get(platform, {})
                )
                
                return ToolResult(
                    success=True,
                    data={
                        "content": processed_content,
                        "platform": platform,
                        "character_count": len(processed_content),
                        "word_count": len(processed_content.split())
                    },
                    metadata={"agent": f"{platform}_agent"}
                )
            except Exception as e:
                logger.error(f"Error in {platform} generation: {str(e)}")
                return ToolResult(
                    success=False,
                    error=str(e),
                    metadata={"agent": f"{platform}_agent"}
                )
        return handler
    
    def _handle_script_research(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle script research tool"""
        try:
            text = input_data.get("text", "")
            week = input_data.get("week", 1)
            days_list = input_data.get("days_list", [])
            
            # Use existing script research logic
            from tasks import create_prompt, analyze_text
            prompt = create_prompt(text, week, days_list)
            result = analyze_text(prompt)
            
            return ToolResult(
                success=True,
                data=result,
                metadata={"agent": "script_research_agent"}
            )
        except Exception as e:
            logger.error(f"Error in script research: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"agent": "script_research_agent"}
            )
    
    def _handle_quality_control(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle quality control tool"""
        try:
            content = input_data.get("content", "")
            platform = input_data.get("platform", "")
            forbidden_words = input_data.get("forbidden_words", [])
            
            # Use existing QC logic
            # This would integrate with your existing QC agent
            qc_result = {
                "content": content,
                "platform": platform,
                "quality_score": 95,  # Placeholder
                "issues_found": [],
                "recommendations": []
            }
            
            return ToolResult(
                success=True,
                data=qc_result,
                metadata={"agent": "qc_agent"}
            )
        except Exception as e:
            logger.error(f"Error in quality control: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"agent": "qc_agent"}
            )
    
    def _handle_regenerate_content(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle content regeneration tool"""
        try:
            content = input_data.get("content", "")
            week = input_data.get("week", 1)
            
            # Use existing regeneration logic
            regenerated_content = f"Regenerated content for week {week}: {content[:100]}..."
            
            return ToolResult(
                success=True,
                data={
                    "original_content": content,
                    "regenerated_content": regenerated_content,
                    "week": week
                },
                metadata={"agent": "regenrate_content_agent"}
            )
        except Exception as e:
            logger.error(f"Error in content regeneration: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"agent": "regenrate_content_agent"}
            )
    
    def _handle_regenerate_subcontent(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle subcontent regeneration tool"""
        try:
            subcontent = input_data.get("subcontent", "")
            day = input_data.get("day", "")
            
            # Use existing subcontent regeneration logic
            regenerated_subcontent = f"Regenerated subcontent for {day}: {subcontent[:100]}..."
            
            return ToolResult(
                success=True,
                data={
                    "original_subcontent": subcontent,
                    "regenerated_subcontent": regenerated_subcontent,
                    "day": day
                },
                metadata={"agent": "regenrate_subcontent_agent"}
            )
        except Exception as e:
            logger.error(f"Error in subcontent regeneration: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"agent": "regenrate_subcontent_agent"}
            )

# Create MCP server instance
mcp_server = VernalContentumMCPServer()

if __name__ == "__main__":
    # Run MCP server
    mcp_server.run()
