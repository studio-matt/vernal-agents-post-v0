"""
Helper functions for integrating author voice into content generation.
Follows Content-Machine-Integration-Guide.md approach.
"""

from typing import Optional, Dict, Any, Tuple
from author_related import Planner, GeneratorHarness, AuthorProfile
from author_profile_service import AuthorProfileService
from database import SessionLocal
from langchain_openai import ChatOpenAI
import os
import logging

logger = logging.getLogger(__name__)

# Platform to adapter key mapping
# Based on adapters.json and common platform names
PLATFORM_TO_ADAPTER = {
    "linkedin": "linkedin",
    "twitter": "twitter",  # Will use blog adapter if twitter not in adapters.json
    "facebook": "facebook",  # Will use blog adapter if facebook not in adapters.json
    "instagram": "instagram",  # Will use blog adapter if instagram not in adapters.json
    "tiktok": "tiktok",  # Will use blog adapter if tiktok not in adapters.json
    "youtube": "youtube",  # Will use blog adapter if youtube not in adapters.json
    "blog": "blog",
    "wordpress": "blog",
    "email": "memo_email",
    "memo": "memo_email",
    "memo_email": "memo_email",
}

def get_adapter_key(platform: str) -> str:
    """
    Map platform name to adapter key.
    
    Args:
        platform: Platform name (e.g., "linkedin", "twitter", "blog")
        
    Returns:
        Adapter key for use with Planner (e.g., "linkedin", "blog", "memo_email")
    """
    platform_lower = platform.lower().strip()
    
    # Direct mapping
    if platform_lower in PLATFORM_TO_ADAPTER:
        adapter_key = PLATFORM_TO_ADAPTER[platform_lower]
        logger.info(f"Mapped platform '{platform}' to adapter '{adapter_key}'")
        return adapter_key
    
    # Default to blog for unknown platforms
    logger.warning(f"Unknown platform '{platform}', defaulting to 'blog' adapter")
    return "blog"

def generate_with_author_voice(
    content_prompt: str,
    author_personality_id: str,
    platform: str,
    goal: str = "content_generation",
    target_audience: str = "general",
    custom_modifications: Optional[str] = None,
    db: Optional[Any] = None
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Generate content using author personality profile.
    
    Follows Content-Machine-Integration-Guide.md:
    1. Load author profile from database
    2. Map platform to adapter key
    3. Use Planner to build STYLE_CONFIG
    4. Merge custom modifications (from content planner)
    5. Use GeneratorHarness with LLM
    6. Return generated text, style config, and metadata
    
    Integration Hierarchy:
    - Author Profile (base style)
    - Adapter Overlay (platform style adjustments)
    - Custom Modifications (user-defined per platform)
    - Final prompt → LLM
    
    Args:
        content_prompt: The topic/prompt to write about
        author_personality_id: ID of the author personality
        platform: Target platform (linkedin, twitter, blog, etc.)
        goal: Content goal (content_generation, mobilization, etc.)
        target_audience: Target audience (general, practitioner, scholar, live)
        custom_modifications: Optional custom instructions from content planner
        db: Database session (optional, will create if not provided)
        
    Returns:
        Tuple of (generated_text, style_config_block, metadata_dict)
        Returns (None, None, None) on error
    """
    try:
        # Get or create database session
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            # Step 1: Load author profile from database
            service = AuthorProfileService()
            profile = service.load_profile(author_personality_id, db)
            
            if not profile:
                logger.error(f"Profile not found for author_personality_id: {author_personality_id}")
                return None, None, None
            
            # Step 2: Map platform to adapter key
            adapter_key = get_adapter_key(platform)
            
            # Step 3: Use Planner to build STYLE_CONFIG
            planner = Planner()
            planner_output = planner.build_style_config(
                profile=profile,
                goal=goal,
                target_audience=target_audience,
                adapter_key=adapter_key,
                scaffold=content_prompt
            )
            
            logger.info(f"Built style config for platform '{platform}' (adapter: '{adapter_key}')")
            
            # Step 4: Merge custom modifications with scaffold if provided
            final_scaffold = content_prompt
            if custom_modifications and custom_modifications.strip():
                final_scaffold = f"""{content_prompt}

Additional Platform-Specific Instructions:
{custom_modifications.strip()}
"""
                logger.info(f"Included custom modifications for platform '{platform}'")
            
            # Update planner output with merged scaffold
            planner_output.scaffold = final_scaffold
            
            # Step 5: Use GeneratorHarness with existing LLM
            def invoke_llm(prompt: str) -> str:
                """Invoke LLM using existing ChatOpenAI setup"""
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=api_key
                )
                return llm.invoke(prompt).content
            
            harness = GeneratorHarness(invoke_llm)
            result = harness.run(planner_output)
            
            # Step 6: Return results
            metadata = {
                "prompt_id": result.prompt_id,
                "token_count": result.token_count,
                "adapter_key": adapter_key,
                "platform": platform,
                "goal": goal,
                "target_audience": target_audience,
            }
            
            logger.info(f"Generated content with author voice: {len(result.text)} chars, {result.token_count} tokens")
            
            return result.text, planner_output.style_config_block, metadata
            
        finally:
            if close_db:
                db.close()
                
    except Exception as e:
        logger.error(f"Error generating with author voice: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None

def should_use_author_voice(author_personality_id: Optional[str]) -> bool:
    """
    Check if author voice should be used.
    
    Args:
        author_personality_id: Optional author personality ID
        
    Returns:
        True if author_personality_id is provided and not empty
    """
    return author_personality_id is not None and author_personality_id.strip() != ""

