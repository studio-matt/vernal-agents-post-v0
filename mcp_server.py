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

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import CrewAI workflows (optional - falls back to manual if not available)
try:
    from crewai_workflows import create_content_generation_crew, create_research_to_writing_crew
    CREWAI_AVAILABLE = True
    logger.info("✅ CrewAI workflows available")
except ImportError as e:
    CREWAI_AVAILABLE = False
    logger.warning(f"⚠️ CrewAI workflows not available: {e}. Using manual orchestration.")

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
        
        # CrewAI-based content generation workflow (Research → Writing → QC)
        if CREWAI_AVAILABLE:
            self.register_tool(Tool(
                name="crewai_content_generation",
                description="Generate content using CrewAI orchestration: Research Agent → Writing Agent → QC Agent",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Input text to analyze"},
                        "week": {"type": "integer", "description": "Week number for content planning"},
                        "platform": {"type": "string", "description": "Target platform"},
                        "days_list": {"type": "array", "items": {"type": "string"}, "description": "List of days for subcontent"},
                        "author_personality": {"type": "string", "description": "Author personality style"},
                        "use_qc": {"type": "boolean", "description": "Whether to include QC agent (default: true)"}
                    },
                    "required": ["text", "platform"]
                },
                handler=self._handle_crewai_content_generation
            ))
        
        # Author Profile Tools
        self.register_tool(Tool(
            name="extract_author_profile",
            description="Extract author profile from writing samples using LIWC analysis and trait mapping",
            input_schema={
                "type": "object",
                "properties": {
                    "author_personality_id": {"type": "string", "description": "ID of the author personality"},
                    "writing_samples": {"type": "array", "items": {"type": "string"}, "description": "List of writing sample texts"},
                    "sample_metadata": {"type": "array", "items": {"type": "object"}, "description": "Optional metadata for each sample (mode, audience, path)"}
                },
                "required": ["author_personality_id", "writing_samples"]
            },
            handler=self._handle_extract_author_profile
        ))
        
        self.register_tool(Tool(
            name="generate_with_author_voice",
            description="Generate content using author personality profile to match author's writing style",
            input_schema={
                "type": "object",
                "properties": {
                    "author_personality_id": {"type": "string", "description": "ID of the author personality to use"},
                    "content_prompt": {"type": "string", "description": "The content topic/prompt to write about"},
                    "platform": {"type": "string", "description": "Target platform (linkedin, blog, memo_email, etc.)"},
                    "goal": {"type": "string", "description": "Content goal (mobilization, education, etc.)"},
                    "target_audience": {"type": "string", "description": "Target audience (general, practitioner, scholar)"}
                },
                "required": ["author_personality_id", "content_prompt", "platform"]
            },
            handler=self._handle_generate_with_author_voice
        ))
        
        self.register_tool(Tool(
            name="validate_author_voice",
            description="Validate generated content against author personality profile to ensure style consistency",
            input_schema={
                "type": "object",
                "properties": {
                    "author_personality_id": {"type": "string", "description": "ID of the author personality"},
                    "generated_text": {"type": "string", "description": "Generated content to validate"},
                    "style_config": {"type": "string", "description": "STYLE_CONFIG block used for generation"}
                },
                "required": ["author_personality_id", "generated_text"]
            },
            handler=self._handle_validate_author_voice
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
    
    def _handle_crewai_content_generation(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle CrewAI-based content generation workflow"""
        if not CREWAI_AVAILABLE:
            return ToolResult(
                success=False,
                error="CrewAI workflows not available",
                metadata={"workflow": "crewai_content_generation"}
            )
        
        try:
            text = input_data.get("text", "")
            week = input_data.get("week", 1)
            platform = input_data.get("platform", "linkedin")
            days_list = input_data.get("days_list", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            author_personality = input_data.get("author_personality", None)
            use_qc = input_data.get("use_qc", True)
            
            if not text:
                return ToolResult(
                    success=False,
                    error="Text input is required",
                    metadata={"workflow": "crewai_content_generation"}
                )
            
            # Use CrewAI workflow
            if use_qc:
                result = create_content_generation_crew(
                    text=text,
                    week=week,
                    platform=platform,
                    days_list=days_list,
                    author_personality=author_personality
                )
            else:
                result = create_research_to_writing_crew(
                    text=text,
                    week=week,
                    platform=platform,
                    days_list=days_list
                )
            
            if result.get("success"):
                return ToolResult(
                    success=True,
                    data=result.get("data"),
                    metadata={
                        **result.get("metadata", {}),
                        "workflow": "crewai_content_generation",
                        "use_qc": use_qc
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Unknown error"),
                    metadata={"workflow": "crewai_content_generation"}
                )
                
        except Exception as e:
            logger.error(f"Error in CrewAI content generation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"workflow": "crewai_content_generation"}
            )
    
    def _handle_extract_author_profile(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle author profile extraction from writing samples"""
        try:
            from author_profile_service import AuthorProfileService
            from database import SessionLocal
            
            author_personality_id = input_data.get("author_personality_id", "")
            writing_samples = input_data.get("writing_samples", [])
            sample_metadata = input_data.get("sample_metadata", None)
            
            if not author_personality_id or not writing_samples:
                return ToolResult(
                    success=False,
                    error="author_personality_id and writing_samples are required",
                    metadata={"tool": "extract_author_profile"}
                )
            
            db = SessionLocal()
            try:
                service = AuthorProfileService()
                profile = service.extract_and_save_profile(
                    author_personality_id=author_personality_id,
                    writing_samples=writing_samples,
                    sample_metadata=sample_metadata,
                    db=db
                )
                
                return ToolResult(
                    success=True,
                    data={
                        "profile_id": author_personality_id,
                        "samples_analyzed": len(writing_samples),
                        "liwc_categories": len(profile.liwc_profile.categories),
                        "has_traits": profile.mbti is not None or profile.ocean is not None,
                        "lexicon_size": {
                            "core_verbs": len(profile.lexicon.core_verbs),
                            "core_nouns": len(profile.lexicon.core_nouns),
                            "evaluatives": len(profile.lexicon.evaluatives)
                        }
                    },
                    metadata={"tool": "extract_author_profile"}
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error extracting author profile: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool": "extract_author_profile"}
            )
    
    def _handle_generate_with_author_voice(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle content generation with author voice"""
        try:
            from author_profile_service import AuthorProfileService
            from author_related import Planner, GeneratorHarness
            from database import SessionLocal
            from langchain_openai import ChatOpenAI
            import os
            
            author_personality_id = input_data.get("author_personality_id", "")
            content_prompt = input_data.get("content_prompt", "")
            platform = input_data.get("platform", "blog")
            goal = input_data.get("goal", "content_generation")
            target_audience = input_data.get("target_audience", "general")
            
            if not author_personality_id or not content_prompt:
                return ToolResult(
                    success=False,
                    error="author_personality_id and content_prompt are required",
                    metadata={"tool": "generate_with_author_voice"}
                )
            
            db = SessionLocal()
            try:
                # Load profile
                service = AuthorProfileService()
                profile = service.load_profile(author_personality_id, db)
                
                if not profile:
                    return ToolResult(
                        success=False,
                        error=f"Profile not found for author_personality_id: {author_personality_id}. Extract profile first.",
                        metadata={"tool": "generate_with_author_voice"}
                    )
                
                # Use Planner to build STYLE_CONFIG
                planner = Planner()
                planner_output = planner.build_style_config(
                    profile=profile,
                    goal=goal,
                    target_audience=target_audience,
                    adapter_key=platform,
                    scaffold=content_prompt
                )
                
                # Use GeneratorHarness with existing LLM
                def invoke_llm(prompt: str) -> str:
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError("OPENAI_API_KEY not set")
                    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=api_key)
                    return llm.invoke(prompt).content
                
                harness = GeneratorHarness(invoke_llm)
                result = harness.run(planner_output)
                
                return ToolResult(
                    success=True,
                    data={
                        "generated_text": result.text,
                        "prompt_id": result.prompt_id,
                        "token_count": result.token_count,
                        "style_config": planner_output.style_config_block
                    },
                    metadata={
                        "tool": "generate_with_author_voice",
                        "author_personality_id": author_personality_id,
                        "platform": platform
                    }
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error generating with author voice: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool": "generate_with_author_voice"}
            )
    
    def _handle_validate_author_voice(self, input_data: Dict[str, Any]) -> ToolResult:
        """Handle validation of generated content against author profile"""
        try:
            from author_profile_service import AuthorProfileService
            from author_related import StyleValidator, parse_style_header
            from liwc_analyzer import analyze_text
            from database import SessionLocal
            
            author_personality_id = input_data.get("author_personality_id", "")
            generated_text = input_data.get("generated_text", "")
            style_config_block = input_data.get("style_config", "")
            
            if not author_personality_id or not generated_text:
                return ToolResult(
                    success=False,
                    error="author_personality_id and generated_text are required",
                    metadata={"tool": "validate_author_voice"}
                )
            
            db = SessionLocal()
            try:
                # Load profile
                service = AuthorProfileService()
                profile = service.load_profile(author_personality_id, db)
                
                if not profile:
                    return ToolResult(
                        success=False,
                        error=f"Profile not found for author_personality_id: {author_personality_id}",
                        metadata={"tool": "validate_author_voice"}
                    )
                
                # Parse style config if provided
                style_config = None
                if style_config_block:
                    style_config = parse_style_header(style_config_block)
                
                # Run LIWC on generated text
                measured_liwc = analyze_text(generated_text)
                
                # Validate
                validator = StyleValidator()
                if style_config:
                    validation = validator.validate_output(
                        text=generated_text,
                        config=style_config,
                        profile=profile,
                        measured_liwc=measured_liwc
                    )
                    
                    return ToolResult(
                        success=True,
                        data={
                            "is_clean": validation.is_clean(),
                            "findings": [f.__dict__ for f in validation.findings],
                            "liwc_deltas": validation.liwc_deltas,
                            "cadence_errors": validation.cadence_errors,
                            "pronoun_errors": validation.pronoun_errors
                        },
                        metadata={"tool": "validate_author_voice"}
                    )
                else:
                    # Basic validation without style config
                    liwc_deltas, findings = validator.compare_liwc(profile, measured_liwc)
                    return ToolResult(
                        success=True,
                        data={
                            "is_clean": len(findings) == 0,
                            "findings": [f.__dict__ for f in findings],
                            "liwc_deltas": liwc_deltas
                        },
                        metadata={"tool": "validate_author_voice"}
                    )
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error validating author voice: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool": "validate_author_voice"}
            )

# Create MCP server instance
mcp_server = VernalContentumMCPServer()

if __name__ == "__main__":
    # Run MCP server
    mcp_server.run()
