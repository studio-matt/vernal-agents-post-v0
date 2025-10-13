import os
import logging
import traceback
from crewai import Agent, Task, Crew
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Safely get environment variable with fallback and validation"""
    value = os.getenv(key) or default
    if required and not value:
        logger.error(f"Required environment variable {key} is missing!")
        return None
    if value:
        logger.debug(f"Environment variable {key} loaded successfully")
    else:
        logger.warning(f"Environment variable {key} not set, using default: {default}")
    return value

# Set OpenAI API key with validation
try:
    OPENAI_API_KEY = get_env_var("OPENAI_API_KEY", required=True)
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"
    logger.info("OpenAI API key configured successfully")
except Exception as e:
    logger.error(f"Failed to configure OpenAI API key: {e}")
    traceback.print_exc()
    raise

# Import database manager with error handling
try:
    from database import db_manager
    logger.info("Database manager imported successfully")
except Exception as e:
    logger.error(f"Failed to import database manager: {e}")
    traceback.print_exc()
    # Create a mock db_manager for fallback
    class MockDBManager:
        def get_agent_by_name(self, name):
            return None
    db_manager = MockDBManager()
    logger.warning("Using mock database manager")

def get_agent_data(agent_name: str, default_role: str, default_goal: str, default_backstory: str) -> Tuple[str, str, str]:
    """Get agent data with comprehensive error handling (alias for safe_get_agent_data)"""
    return safe_get_agent_data(agent_name, default_role, default_goal, default_backstory)

def safe_get_agent_data(agent_name: str, default_role: str, default_goal: str, default_backstory: str) -> Tuple[str, str, str]:
    """Safely get agent data with comprehensive error handling"""
    try:
        agent = db_manager.get_agent_by_name(agent_name) if db_manager else None
        if agent and hasattr(agent, 'role') and hasattr(agent, 'goal') and hasattr(agent, 'backstory'):
            logger.debug(f"Retrieved agent data for {agent_name} from database")
            return agent.role, agent.goal, agent.backstory
        else:
            logger.debug(f"Using default data for {agent_name} (not found in database)")
            return default_role, default_goal, default_backstory
    except Exception as e:
        logger.error(f"Error getting agent data for {agent_name}: {e}")
        traceback.print_exc()
        logger.debug(f"Using default data for {agent_name} due to error")
        return default_role, default_goal, default_backstory

def create_agent_safely(agent_name: str, default_role: str, default_goal: str, default_backstory: str) -> Agent:
    """Create agent with comprehensive error handling"""
    try:
        role, goal, backstory = safe_get_agent_data(agent_name, default_role, default_goal, default_backstory)
        
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm="gpt-4o-mini",
            memory=True,
            verbose=True,
        )
        logger.info(f"Agent {agent_name} created successfully")
        return agent
    except Exception as e:
        logger.error(f"Failed to create agent {agent_name}: {e}")
        traceback.print_exc()
        # Return a minimal agent as fallback
        return Agent(
            role=default_role,
            goal=default_goal,
            backstory=default_backstory,
            llm="gpt-4o-mini",
            memory=True,
            verbose=True,
        )

# Create all agents with error handling
try:
    script_research_agent = create_agent_safely(
        "script_research_agent",
        "Script Research Agent",
        "Research and analyze content for script generation",
        "You are an expert content researcher who analyzes information and creates detailed research reports."
    )
    logger.info("✅ script_research_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create script_research_agent: {e}")
    traceback.print_exc()

try:
    qc_agent = create_agent_safely(
        "qc_agent",
        "Quality Control Agent",
        "Review and ensure quality of generated content",
        "You are a meticulous quality control specialist who ensures all content meets high standards."
    )
    logger.info("✅ qc_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create qc_agent: {e}")
    traceback.print_exc()

try:
    linkedin_agent = create_agent_safely(
        "linkedin_agent",
        "LinkedIn Content Agent",
        "Create professional LinkedIn content",
        "You are a LinkedIn content specialist who creates engaging professional posts."
    )
    logger.info("✅ linkedin_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create linkedin_agent: {e}")
    traceback.print_exc()

try:
    facebook_agent = create_agent_safely(
        "facebook_agent",
        "Facebook Content Agent",
        "Create engaging Facebook content",
        "You are a Facebook content specialist who creates viral and engaging posts."
    )
    logger.info("✅ facebook_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create facebook_agent: {e}")
    traceback.print_exc()

try:
    twitter_agent = create_agent_safely(
        "twitter_agent",
        "Twitter Content Agent",
        "Create concise Twitter content",
        "You are a Twitter specialist who creates impactful tweets within character limits."
    )
    logger.info("✅ twitter_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create twitter_agent: {e}")
    traceback.print_exc()

try:
    instagram_agent = create_agent_safely(
        "instagram_agent",
        "Instagram Content Agent",
        "Create visual Instagram content",
        "You are an Instagram specialist who creates visually appealing and engaging posts."
    )
    logger.info("✅ instagram_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create instagram_agent: {e}")
    traceback.print_exc()

try:
    youtube_agent = create_agent_safely(
        "youtube_agent",
        "YouTube Content Agent",
        "Create YouTube video content",
        "You are a YouTube specialist who creates engaging video scripts and descriptions."
    )
    logger.info("✅ youtube_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create youtube_agent: {e}")
    traceback.print_exc()

try:
    tiktok_agent = create_agent_safely(
        "tiktok_agent",
        "TikTok Content Agent",
        "Create viral TikTok content",
        "You are a TikTok specialist who creates short-form viral content."
    )
    logger.info("✅ tiktok_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create tiktok_agent: {e}")
    traceback.print_exc()

try:
    wordpress_agent = create_agent_safely(
        "wordpress_agent",
        "WordPress Content Agent",
        "Create WordPress blog content",
        "You are a WordPress specialist who creates SEO-optimized blog posts."
    )
    logger.info("✅ wordpress_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create wordpress_agent: {e}")
    traceback.print_exc()

try:
    script_rewriter_agent = create_agent_safely(
        "script_rewriter_agent",
        "Script Rewriter Agent",
        "Rewrite and improve existing scripts",
        "You are a script rewriting specialist who improves and optimizes existing content."
    )
    logger.info("✅ script_rewriter_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create script_rewriter_agent: {e}")
    traceback.print_exc()

try:
    regenrate_content_agent = create_agent_safely(
        "regenrate_content_agent",
        "Content Regeneration Agent",
        "Regenerate and refresh existing content",
        "You are a content regeneration specialist who refreshes and updates existing content."
    )
    logger.info("✅ regenrate_content_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create regenrate_content_agent: {e}")
    traceback.print_exc()

try:
    regenrate_subcontent_agent = create_agent_safely(
        "regenrate_subcontent_agent",
        "Subcontent Regeneration Agent",
        "Regenerate subcontent and variations",
        "You are a subcontent specialist who creates variations and subcontent from main content."
    )
    logger.info("✅ regenrate_subcontent_agent created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create regenrate_subcontent_agent: {e}")
    traceback.print_exc()

# Platform limits
PLATFORM_LIMITS = {
    "linkedin": {"max_length": 3000, "min_length": 50},
    "facebook": {"max_length": 63206, "min_length": 50},
    "twitter": {"max_length": 280, "min_length": 10},
    "instagram": {"max_length": 2200, "min_length": 50},
    "youtube": {"max_length": 5000, "min_length": 100},
    "tiktok": {"max_length": 2200, "min_length": 50},
    "wordpress": {"max_length": 10000, "min_length": 100}
}

logger.info("All agents created successfully")
logger.info("Agents module loaded successfully")
