"""
CrewAI-based workflows for content generation
Enables agent-to-agent handoffs with automatic orchestration
"""

from crewai import Crew, Process, Task, Agent
from agents import script_research_agent, qc_agent, create_agent_safely
from agents import linkedin_agent, twitter_agent, facebook_agent, instagram_agent, tiktok_agent, youtube_agent, wordpress_agent
from database import DatabaseManager, SessionLocal
from models import SystemSettings
from typing import Dict, Any, Optional, List
import logging
import json
import threading
import hashlib
from functools import wraps

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

# Timeout for CrewAI operations (10 minutes)
CREWAI_TIMEOUT_SECONDS = 600


def run_with_timeout(func, timeout_seconds=CREWAI_TIMEOUT_SECONDS, *args, **kwargs):
    """
    Run a function with a timeout using threading.
    Returns the result or raises TimeoutError if the function doesn't complete in time.
    """
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"⚠️ Operation timed out after {timeout_seconds} seconds")
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

def truthy(v: str) -> bool:
    """
    Robust boolean parser for SystemSettings values.
    Returns True for: "true", "1", "yes", "y", "on" (case-insensitive)
    """
    if v is None:
        return False
    return str(v).strip().lower() in {"true", "1", "yes", "y", "on"}


def normalize_qc_agent_id(agent_id: str) -> str:
    """
    Normalize QC agent ID to match DB key format.
    Removes 'qc_' prefix if present and strips whitespace.
    """
    return agent_id.replace("qc_", "").strip()


def requires_legal_acknowledgment(content: str, qc_feedback: Optional[str] = None) -> bool:
    """
    Determine if content requires a legal-status + risk acknowledgment line.
    
    Returns True if content mentions:
    - Regulated substances/drugs (psilocybin, cannabis, etc.)
    - Medical/mental-health treatment guidance/claims
    - Other regulated goods (weapons, nicotine, etc.)
    
    Returns False for ordinary commerce (fish tanks, landscaping, apparel, SaaS, etc.)
    """
    if not content:
        return False
    
    content_lower = content.lower()
    qc_feedback_lower = (qc_feedback or "").lower()
    combined_text = f"{content_lower} {qc_feedback_lower}"
    
    # Regulated substances/drugs
    regulated_substances = [
        "psilocybin", "mushroom", "cannabis", "marijuana", "thc", "cbd",
        "cocaine", "heroin", "methamphetamine", "mdma", "lsd", "ketamine",
        "opioid", "opiate", "fentanyl", "amphetamine", "steroid"
    ]
    
    # Medical/mental health treatment claims
    medical_keywords = [
        "treat", "treatment", "cure", "heal", "therapeutic", "therapy",
        "diagnose", "diagnosis", "prescription", "medication", "medicinal",
        "mental health", "depression", "anxiety", "ptsd", "ptsd treatment",
        "medical advice", "health advice", "therapeutic use"
    ]
    
    # Other regulated goods
    regulated_goods = [
        "weapon", "firearm", "gun", "ammunition", "nicotine", "vape",
        "tobacco", "alcohol", "prescription drug"
    ]
    
    # Check if any regulated keywords appear
    all_keywords = regulated_substances + medical_keywords + regulated_goods
    
    for keyword in all_keywords:
        if keyword in combined_text:
            logger.info(f"🔍 Legal acknowledgment required: detected keyword '{keyword}' in content")
            return True
    
    return False


def get_qc_agents_for_agent(tab: str, agent_id: str, platform: Optional[str] = None) -> List[Agent]:
    """
    Get QC agents for a specific agent.
    Returns: assigned QC agents + global QC agents + platform-scoped QC agents (if platform matches)
    
    Args:
        tab: The agent tab (research, writing)
        agent_id: The agent ID
        platform: Optional platform name (e.g., "instagram") for platform-scoped QC agents
        
    Returns:
        List of QC Agent objects
    """
    qc_agents: List[Agent] = []
    db = SessionLocal()
    platform_lower = platform.lower() if platform else None
    
    # Platform tags for detecting platform-scoped agents
    platform_tags = ["instagram", "facebook", "youtube", "twitter", "linkedin", "tiktok", "wordpress"]
    
    try:
        # Step 1: Get assigned QC agent (if any)
        assigned_qc_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == f"{tab}_agent_{agent_id}_qc_agent"
        ).first()
        
        if assigned_qc_setting and assigned_qc_setting.setting_value:
            assigned_qc_id = assigned_qc_setting.setting_value.strip()
            if assigned_qc_id:
                # Create agent from assigned QC agent ID
                qc_agent_obj = _create_qc_agent_from_id(assigned_qc_id)
                if qc_agent_obj:
                    qc_agents.append(qc_agent_obj)
                    logger.info(f"✅ Added assigned QC agent: {assigned_qc_id}")
        
        # Step 2: Get global and platform-scoped QC agents
        # Get list of all QC agents
        qc_agents_list_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "qc_agents_list"
        ).first()
        
        if qc_agents_list_setting and qc_agents_list_setting.setting_value:
            try:
                qc_agent_ids = json.loads(qc_agents_list_setting.setting_value)
                logger.info(f"🔍 QC RESOLUTION: Found {len(qc_agent_ids)} QC agent IDs in qc_agents_list: {qc_agent_ids}")
                
                for qc_agent_id_raw in qc_agent_ids:
                    # Normalize the agent ID (remove qc_ prefix, strip whitespace)
                    qc_agent_id = normalize_qc_agent_id(qc_agent_id_raw)
                    
                    # Log the resolution attempt
                    logger.info(f"🔎 Resolving QC agent ID '{qc_agent_id}' (platform={platform_lower}, checking global/platform flags)")
                    
                    # Determine if this is a platform-scoped agent
                    is_platform_scoped = any(tag in qc_agent_id.lower() for tag in platform_tags)
                    
                    # If platform-scoped, check if it matches current platform
                    if is_platform_scoped:
                        if not platform_lower or platform_lower not in qc_agent_id.lower():
                            logger.info(f"⏭️  Skipped platform-scoped QC agent {qc_agent_id} (platform mismatch: {platform_lower} not in {qc_agent_id})")
                            continue
                        
                        # Platform-scoped agents are AUTOMATICALLY included when platform matches
                        # This is a platform override - we skip enable flag checks for platform-specific agents
                        # The platform match itself is the selector/enablement for platform-scoped agents
                        logger.info(f"🔄 AUTO-OVERRIDE: Platform-scoped QC agent {qc_agent_id} matches platform {platform_lower} - automatically including (ignoring enable flag)")
                        
                        # Create agent from QC agent ID (read-only operation - no DB writes)
                        qc_agent_obj = _create_qc_agent_from_id(qc_agent_id)
                        if qc_agent_obj:
                            # Avoid duplicates (if assigned QC is also in the list)
                            if not any(agent.role == qc_agent_obj.role for agent in qc_agents):
                                qc_agents.append(qc_agent_obj)
                                logger.info(f"✅ Added platform-scoped ({platform_lower}) QC agent: {qc_agent_id} [AUTO-OVERRIDE: platform match, enable flag ignored]")
                            else:
                                logger.info(f"⏭️  Skipped QC agent {qc_agent_id} (duplicate role)")
                        else:
                            logger.warning(f"⚠️  Failed to create QC agent from ID: {qc_agent_id} (check _create_qc_agent_from_id logs)")
                        continue  # Skip to next agent - platform-scoped handled
                    
                    # For non-platform-scoped agents, check global flag
                    # These are truly global QC agents that apply to all platforms
                    candidate_keys = [
                        f"qc_agent_{qc_agent_id}_qc_global",                     # matches your DB (e.g., qc_agent_agent_0_qc_qc_global)
                        f"qc_agent_{qc_agent_id}_global",                        # legacy
                        f"qc_agent_{qc_agent_id.replace('qc_', '')}_qc_global",  # legacy alt
                        f"qc_agent_{qc_agent_id.replace('qc_', '')}_global",     # legacy alt
                    ]
                    
                    global_setting = None
                    matched_key = None
                    for k in candidate_keys:
                        global_setting = db.query(SystemSettings).filter(
                            SystemSettings.setting_key == k
                        ).first()
                        if global_setting:
                            matched_key = k
                            break
                    
                    # Parse the value using robust boolean parser
                    is_enabled = truthy(global_setting.setting_value) if global_setting else False
                    
                    # Log the resolution details
                    if global_setting:
                        logger.info(f"🔍 QC Agent {qc_agent_id}: key={matched_key}, value={repr(global_setting.setting_value)}, parsed={is_enabled}, platform_scoped={is_platform_scoped}")
                    else:
                        logger.warning(f"⚠️  QC Agent {qc_agent_id}: no global key found (tried: {candidate_keys}), platform_scoped={is_platform_scoped}")
                    
                    if is_enabled:
                        # Create agent from QC agent ID (decisive log already above)
                        qc_agent_obj = _create_qc_agent_from_id(qc_agent_id)
                        if qc_agent_obj:
                            # Avoid duplicates (if assigned QC is also in the list)
                            if not any(agent.role == qc_agent_obj.role for agent in qc_agents):
                                qc_agents.append(qc_agent_obj)
                                logger.info(f"✅ Added global QC agent: {qc_agent_id}")
                            else:
                                logger.info(f"⏭️  Skipped QC agent {qc_agent_id} (duplicate role)")
                        else:
                            logger.warning(f"⚠️  Failed to create QC agent from ID: {qc_agent_id} (check _create_qc_agent_from_id logs)")
                    else:
                        logger.info(f"⏭️  Skipped QC agent {qc_agent_id} (not enabled: key={matched_key}, value={repr(global_setting.setting_value) if global_setting else 'None'})")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Could not parse qc_agents_list, skipping global QC agents: {e}")
        
        # Step 3: Fallback to default qc_agent if no QC agents found
        if not qc_agents:
            logger.info("⚠️ No QC agents found, using default qc_agent")
            qc_agents.append(qc_agent)
        
    except Exception as e:
        logger.error(f"❌ Error getting QC agents: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback to default
        if not qc_agents:
            qc_agents.append(qc_agent)
    finally:
        db.close()
    
    return qc_agents

def _create_qc_agent_from_id(qc_agent_id: str) -> Optional[Agent]:
    """
    Create a QC Agent object from a QC agent ID stored in system settings.
    
    Args:
        qc_agent_id: The QC agent ID (e.g., "agent_0_qc")
        
    Returns:
        Agent object or None if creation fails
    """
    try:
        db = SessionLocal()
        try:
            # Get agent data from system settings
            name_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_name"
            ).first()
            role_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_role"
            ).first()
            goal_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_goal"
            ).first()
            backstory_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_backstory"
            ).first()
            
            # Extract name
            agent_name = name_setting.setting_value if name_setting and name_setting.setting_value else qc_agent_id
            
            # Use settings if available, otherwise use defaults
            role = role_setting.setting_value if role_setting and role_setting.setting_value else "Quality Control Agent"
            goal = goal_setting.setting_value if goal_setting and goal_setting.setting_value else "Review and ensure quality of generated content"
            backstory = backstory_setting.setting_value if backstory_setting and backstory_setting.setting_value else "You are a meticulous quality control specialist who ensures all content meets high standards."
            
            # Create agent using the same method as agents.py
            agent = create_agent_safely(
                f"qc_{qc_agent_id}",
                role,
                goal,
                backstory
            )
            
            logger.debug(f"✅ Created QC agent from ID {qc_agent_id}: {agent_name}")
            return agent
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error creating QC agent from ID {qc_agent_id}: {e}")
        return None

# Platform agent mapping
PLATFORM_AGENTS = {
    "linkedin": linkedin_agent,
    "twitter": twitter_agent,
    "facebook": facebook_agent,
    "instagram": instagram_agent,
    "tiktok": tiktok_agent,
    "youtube": youtube_agent,
    "wordpress": wordpress_agent,
}

def create_content_generation_crew(
    text: str,
    week: int = 1,
    platform: str = "linkedin",
    days_list: Optional[list] = None,
    author_personality: Optional[str] = None,
    update_task_status_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Create and execute an ITERATIVE CrewAI workflow for content generation.
    
    Flow: Research Agent → Writing Agent → QC Agent (iterative loop)
    - Research runs once
    - Writing creates content
    - QC reviews and can REJECT with feedback, sending back to Writing
    - Loop continues until QC APPROVES or rejection limit reached
    
    Args:
        text: Input text to analyze
        week: Week number for content planning
        platform: Target platform (linkedin, twitter, etc.)
        days_list: List of days for subcontent
        author_personality: Author personality style
        update_task_status_callback: Optional callback to update task status (for progress tracking)
        
    Returns:
        Dict with success status, data, and metadata
    """
    try:
        if days_list is None:
            days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        # Get platform-specific writing agent
        writing_agent = PLATFORM_AGENTS.get(platform.lower())
        if not writing_agent:
            return {
                "success": False,
                "error": f"Platform {platform} not supported",
                "data": None
            }
        
        # Get task descriptions from database
        research_task_desc = db_manager.get_task_by_name("script_research_task")
        qc_task_desc = db_manager.get_task_by_name("qc_task")
        platform_task_desc = db_manager.get_task_by_name(f"{platform}_task")
        
        if not all([research_task_desc, qc_task_desc]):
            return {
                "success": False,
                "error": "Required tasks not found in database",
                "data": None
            }
        
        # Format task descriptions with context
        days_str = ", ".join(days_list)
        m = len(days_list)
        
        # Task 1: Research Agent - Analyze text and extract themes
        research_description = research_task_desc.description.format(
            week=week,
            m=m,
            days_str=days_str
        )
        research_expected_output = research_task_desc.expected_output.format(week=week)
        
        research_task = Task(
            description=f"""{research_description}
            
            Input text to analyze:
            {text}
            """,
            expected_output=research_expected_output,
            agent=script_research_agent,
            verbose=True  # Enable verbose logging for this task
        )
        
        # Helper function to replace template variables with actual values or escape them
        def format_template_string(template_str: str, **kwargs) -> str:
            """Format template string, replacing known variables and escaping unknown ones"""
            if not template_str:
                return ""
            try:
                # Try to format with provided variables
                formatted = template_str.format(**kwargs)
                return formatted
            except KeyError as e:
                # If a variable is missing, replace it with empty string or the variable name
                import re
                # Find all template variables
                pattern = r'\{([^}]+)\}'
                matches = re.findall(pattern, template_str)
                for var in matches:
                    if var not in kwargs:
                        # Replace unknown variables with empty string or descriptive text
                        if var == 'context':
                            # Replace {context} with actual context from research output
                            template_str = template_str.replace(f'{{{var}}}', 'the research output and content queue items provided above')
                        else:
                            # For other unknown variables, just remove them
                            template_str = template_str.replace(f'{{{var}}}', '')
                return template_str
        
        # Task 2: Writing Agent - Create platform-specific content from research
        # CRITICAL: Retrieve writing agent configuration from SystemSettings (admin panel)
        db = SessionLocal()
        try:
            platform_lower = platform.lower()
            
            # First, find the agent ID for this platform from writing_agents_list
            # Agent IDs are like "agent_0_instagram", "agent_1_facebook", etc.
            agent_id = None
            agents_list_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "writing_agents_list"
            ).first()
            
            if agents_list_setting and agents_list_setting.setting_value:
                try:
                    agent_ids = json.loads(agents_list_setting.setting_value)
                    # Find agent ID that matches this platform
                    for aid in agent_ids:
                        # Check if agent name matches platform
                        name_setting = db.query(SystemSettings).filter(
                            SystemSettings.setting_key == f"writing_agent_{aid}_name"
                        ).first()
                        if name_setting and name_setting.setting_value:
                            agent_name_lower = name_setting.setting_value.lower()
                            # Check if platform name is in agent name (e.g., "instagram" in "Instagram Writer")
                            if platform_lower in agent_name_lower or agent_name_lower.replace(" writer", "").replace(" content", "") == platform_lower:
                                agent_id = aid
                                logger.info(f"✅ Found agent ID for {platform}: {agent_id}")
                                break
                        
                        # Also check if agent ID itself contains platform name
                        if platform_lower in aid.lower():
                            agent_id = aid
                            logger.info(f"✅ Found agent ID for {platform} by ID match: {agent_id}")
                            break
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Could not parse writing_agents_list")
            
            # Try to get configuration using agent_id if found, otherwise try platform name directly
            if agent_id:
                # Get expected_output from SystemSettings using agent_id
                expected_output_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{agent_id}_expected_output"
                ).first()
                
                # Get prompt from SystemSettings using agent_id
                prompt_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{agent_id}_prompt"
                ).first()
                
                # Get description from SystemSettings using agent_id
                description_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{agent_id}_description"
                ).first()
            else:
                # Fallback: try platform name directly (for backward compatibility)
                logger.warning(f"⚠️ Could not find agent_id for {platform}, trying platform name directly")
                expected_output_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{platform_lower}_expected_output"
                ).first()
                
                prompt_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{platform_lower}_prompt"
                ).first()
                
                description_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == f"writing_agent_{platform_lower}_description"
                ).first()
            
            # Extract campaign context from text parameter
            # The text parameter contains "Campaign Context:" section with the formatted context
            # that matches the instructional copy (query, keywords, topics, scraped text, etc.)
            campaign_context_section = ""
            if "Campaign Context:" in text:
                # Extract the campaign context section
                context_start = text.find("Campaign Context:")
                context_end = text.find("\n\nGenerate content", context_start)
                if context_end == -1:
                    context_end = len(text)
                campaign_context_section = text[context_start:context_end].replace("Campaign Context:", "").strip()
            
            # Build the actual context string that will be passed to {context} placeholder
            # This should match the instructional copy format:
            # - Campaign query and keywords
            # - Top keywords found in scraped content
            # - Topics identified from content
            # - Number of scraped texts
            # - Sample text (first 500 characters)
            if campaign_context_section:
                context_string = campaign_context_section
            else:
                # Fallback: use the full text if campaign context section not found
                context_string = text
            
            # Helper function to replace template variables with actual values or escape them
            def format_template_string(template_str: str, **kwargs) -> str:
                """Format template string, replacing known variables and escaping unknown ones"""
                if not template_str:
                    return ""
                try:
                    # Try to format with provided variables
                    formatted = template_str.format(**kwargs)
                    return formatted
                except KeyError as e:
                    # If a variable is missing, replace it with empty string or the variable name
                    import re
                    # Find all template variables
                    pattern = r'\{([^}]+)\}'
                    matches = re.findall(pattern, template_str)
                    for var in matches:
                        if var not in kwargs:
                            # Replace unknown variables with empty string or descriptive text
                            if var == 'context':
                                # Replace {context} with actual context from text parameter
                                # This includes content queue, brand guidelines, parent idea, etc.
                                template_str = template_str.replace(f'{{{var}}}', context_string)
                            else:
                                # For other unknown variables, just remove them
                                template_str = template_str.replace(f'{{{var}}}', '')
                    return template_str
            
            # Use admin panel configuration if available, otherwise fall back to database task
            if expected_output_setting and expected_output_setting.setting_value:
                # Format template variables in expected_output
                writing_expected_output = format_template_string(
                    expected_output_setting.setting_value,
                    week=week,
                    platform=platform,
                    context=context_string
                )
                logger.info(f"✅ Using {platform.capitalize()} Writer expected_output from SystemSettings (admin panel)")
            elif platform_task_desc:
                writing_expected_output = platform_task_desc.expected_output
                logger.warning(f"⚠️ Using fallback expected_output from database task (admin panel config not found)")
            else:
                writing_expected_output = f"Create engaging {platform} content based on the research analysis."
                logger.warning(f"⚠️ Using default expected_output (no configuration found)")
            
            if description_setting and description_setting.setting_value:
                # Format template variables in description
                writing_description = format_template_string(
                    description_setting.setting_value,
                    week=week,
                    platform=platform,
                    context=context_string
                )
                logger.info(f"✅ Using {platform} Writer description from SystemSettings (admin panel)")
            elif platform_task_desc:
                writing_description = platform_task_desc.description
                logger.warning(f"⚠️ Using fallback description from database task (admin panel config not found)")
            else:
                writing_description = f"Create {platform}-specific content based on the research output."
                logger.warning(f"⚠️ Using default description (no configuration found)")
            
            # Build the writing task description with prompt if available
            writing_task_description_base = writing_description
            
            # Add prompt (CRITICAL OUTPUT CONTRACT) if configured in admin panel
            # The prompt should be VERY prominent and clear
            if prompt_setting and prompt_setting.setting_value:
                # Format template variables in prompt
                formatted_prompt = format_template_string(
                    prompt_setting.setting_value,
                    week=week,
                    platform=platform,
                    context=context_string
                )
                writing_task_description_base = f"""{writing_description}

═══════════════════════════════════════════════════════════════
CRITICAL OUTPUT CONTRACT - YOU MUST FOLLOW THIS EXACTLY:
═══════════════════════════════════════════════════════════════
{formatted_prompt}
═══════════════════════════════════════════════════════════════

REMEMBER: {formatted_prompt}
═══════════════════════════════════════════════════════════════"""
                logger.info(f"✅ Using {platform} Writer prompt from SystemSettings (admin panel)")
                logger.info(f"📝 Prompt preview (first 200 chars): {formatted_prompt[:200]}")
            else:
                logger.warning(f"⚠️ No prompt found in SystemSettings for {platform} Writer (admin panel config not found)")
                logger.warning(f"⚠️ Looking for key: writing_agent_{agent_id if agent_id else platform_lower}_prompt")
                
        finally:
            db.close()
        
        writing_description = writing_task_description_base
        
        writing_task = Task(
            description=f"""{writing_description}
            
            Use the research output from the previous agent to create {platform}-specific content.
            Platform: {platform}
            Author personality: {author_personality or 'professional'}
            Week: {week}
            
            Original Context (Content Queue, Brand Guidelines, Parent Idea, etc.):
            {text}
            
            The research agent has already analyzed the text and extracted themes. Use that analysis to create engaging content.
            """,
            expected_output=writing_expected_output,
            agent=writing_agent,
            verbose=True  # Enable verbose logging for this task
        )
        
        # Task 3: QC Agent(s) - Review the written content
        # Get QC agents (assigned + global)
        # For now, use writing agent's QC assignment (we'll need to pass agent_id in the future)
        # For now, we'll use a default approach: get QC agents for the platform writing agent
        # In the future, we can pass agent_id as a parameter
        
        # Get QC agents - try to get from writing agent assignment
        # First, try to find the agent_id for this platform
        # Agent IDs are stored like "agent_0_linkedin", "agent_1_facebook", etc.
        # We'll search for agents with this platform name
        qc_agents_list = []
        db = SessionLocal()
        try:
            # Try to find the agent_id for this platform
            platform_lower = platform.lower()
            agents_list_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "writing_agents_list"
            ).first()
            
            if agents_list_setting and agents_list_setting.setting_value:
                try:
                    agent_ids = json.loads(agents_list_setting.setting_value)
                    # Find agent_id that matches this platform
                    matching_agent_id = None
                    for agent_id in agent_ids:
                        # Check if this agent's name matches the platform
                        name_setting = db.query(SystemSettings).filter(
                            SystemSettings.setting_key == f"writing_agent_{agent_id}_name"
                        ).first()
                        if name_setting and name_setting.setting_value:
                            agent_name_lower = name_setting.setting_value.lower()
                            # Check if platform name is in agent name (e.g., "LinkedIn" in "LinkedIn Writer")
                            if platform_lower in agent_name_lower or agent_name_lower.replace(" writer", "").replace(" content", "") == platform_lower:
                                matching_agent_id = agent_id
                                break
                    
                    if matching_agent_id:
                        logger.info(f"🔍 Resolving QC agents for writing agent: {matching_agent_id}, platform: {platform}")
                        qc_agents_list = get_qc_agents_for_agent("writing", matching_agent_id, platform=platform)
                    else:
                        # Fallback: try platform name directly
                        logger.info(f"🔍 No matching agent_id found, using platform name: {platform_lower}")
                        qc_agents_list = get_qc_agents_for_agent("writing", platform_lower, platform=platform)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Could not parse writing_agents_list: {e}")
                    # Fallback: try platform name directly
                    qc_agents_list = get_qc_agents_for_agent("writing", platform_lower, platform=platform)
            else:
                # Fallback: try platform name directly
                logger.info(f"🔍 No writing_agents_list found, using platform name: {platform_lower}")
                qc_agents_list = get_qc_agents_for_agent("writing", platform_lower, platform=platform)
        except Exception as e:
            logger.warning(f"⚠️ Could not find agent_id for platform {platform}, using fallback: {e}")
            # Fallback: try platform name directly
            qc_agents_list = get_qc_agents_for_agent("writing", platform_lower, platform=platform)
        finally:
            db.close()
        
        # Create QC tasks for ALL QC agents (not just the first one)
        qc_tasks = []
        if qc_agents_list:
            for idx, qc_agent_obj in enumerate(qc_agents_list):
                qc_description = qc_task_desc.description
                qc_expected_output = qc_task_desc.expected_output
                
                # Get platform-friendly name for QC agent
                platform_name = platform.capitalize()
                # Use agent role if available, otherwise create descriptive name
                base_name = qc_agent_obj.role or "QC Agent"
                # Always prefix with platform name for clarity
                if not base_name.startswith(platform_name):
                    qc_agent_name = f"{platform_name} {base_name}"
                else:
                    qc_agent_name = base_name
                
                # If multiple QC agents, add number
                if len(qc_agents_list) > 1:
                    qc_agent_name = f"{qc_agent_name} {idx + 1}"
                
                # For multiple QC agents, each reviews the previous output
                if idx == 0:
                    # First QC agent reviews writing agent output
                    qc_input_description = "the content created by the writing agent"
                else:
                    # Subsequent QC agents review previous QC agent output
                    qc_input_description = f"the content reviewed by the previous QC agent"
                
                qc_task = Task(
                    description=f"""{qc_description}
                    
                    Review {qc_input_description} for:
                    - Quality and clarity
                    - Platform-specific requirements ({platform})
                    - Compliance with guidelines
                    - Author personality match ({author_personality or 'professional'})
                    - Accuracy and relevance to the original research
                    
                    The content is based on the research output. Review it thoroughly and provide refined content.
                    If the content passes all quality checks, return it as-is. If issues are found, provide specific feedback and revised content.
                    """,
                    expected_output=qc_expected_output,
                    agent=qc_agent_obj,
                    verbose=True  # Enable verbose logging for this task
                )
                qc_tasks.append(qc_task)
        else:
            # Fallback to default QC agent
            qc_task = Task(
                description=f"""{qc_task_desc.description}
                
                Review the content created by the writing agent for:
                - Quality and clarity
                - Platform-specific requirements ({platform})
                - Compliance with guidelines
                - Author personality match ({author_personality or 'professional'})
                - Accuracy and relevance to the original research
                
                The writing agent has created content based on the research. Review it thoroughly.
                """,
                expected_output=qc_task_desc.expected_output,
                agent=qc_agent,
                verbose=True  # Enable verbose logging for this task
            )
            qc_tasks.append(qc_task)
        
        # STEP 1: Run Research Agent ONCE (never re-engaged)
        logger.info(f"🔬 Step 1: Running Research Agent (one-time)")
        if update_task_status_callback:
            update_task_status_callback(
                agent="Research Agent",
                task="Analyzing content and extracting themes",
                progress=20,
                agent_status="running"
            )
        
        research_crew = Crew(
            agents=[script_research_agent],
            tasks=[research_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
        try:
            research_result = run_with_timeout(
                research_crew.kickoff,
                timeout_seconds=CREWAI_TIMEOUT_SECONDS,
                inputs={
                    "text": text,
                    "week": week,
                    "platform": platform,
                    "days_list": days_list,
                    "author_personality": author_personality or "professional"
                }
            )
        except TimeoutError as te:
            logger.error(f"❌ Research agent timed out after {CREWAI_TIMEOUT_SECONDS} seconds")
            if update_task_status_callback:
                update_task_status_callback(
                    agent="Research Agent",
                    task=f"TIMEOUT: Operation exceeded {CREWAI_TIMEOUT_SECONDS} seconds",
                    error=str(te),
                    agent_status="error"
                )
            raise
        except Exception as e:
            logger.error(f"❌ Research agent error: {e}")
            if update_task_status_callback:
                update_task_status_callback(
                    agent="Research Agent",
                    task=f"ERROR: {str(e)}",
                    error=str(e),
                    agent_status="error"
                )
            raise
        
        # Extract research output
        research_output = None
        if hasattr(research_result, 'tasks_output') and research_result.tasks_output:
            research_output = research_result.tasks_output[0]
        elif hasattr(research_result, 'raw'):
            research_output = research_result.raw
        else:
            research_output = str(research_result)
        
        if update_task_status_callback:
            update_task_status_callback(
                agent="Research Agent",
                task="Content analysis completed",
                progress=30,
                agent_status="completed"
            )
        
        # STEP 2: ITERATIVE Writing → QC Loop
        # Get rejection limits for QC agents
        db = SessionLocal()
        qc_rejection_limits = {}
        try:
            # Get QC agent IDs to look up rejection limits
            agents_list_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "qc_agents_list"
            ).first()
            if agents_list_setting and agents_list_setting.setting_value:
                try:
                    qc_agent_ids = json.loads(agents_list_setting.setting_value)
                    for qc_agent_id in qc_agent_ids:
                        reject_after_setting = db.query(SystemSettings).filter(
                            SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_reject_after"
                        ).first()
                        if reject_after_setting and reject_after_setting.setting_value:
                            qc_rejection_limits[qc_agent_id] = int(reject_after_setting.setting_value)
                        else:
                            qc_rejection_limits[qc_agent_id] = 5  # Default limit
                except json.JSONDecodeError:
                    pass
        finally:
            db.close()
        
        # Initialize iteration tracking
        iteration_count = 0
        max_iterations = max(qc_rejection_limits.values()) if qc_rejection_limits else 5
        current_content = None
        qc_feedback_history = []
        rejection_counts = {}  # Track rejections per QC agent
        
        logger.info(f"🔄 Starting iterative Writing → QC loop (max {max_iterations} iterations)")
        
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"📝 Iteration {iteration_count}/{max_iterations}: Writing Agent creating content")
            
            # Check if content requires legal acknowledgment (conditional, not global)
            # Check current content, QC feedback, and original text input
            needs_legal_ack = False
            if current_content:
                needs_legal_ack = requires_legal_acknowledgment(str(current_content), qc_feedback_history[-1] if qc_feedback_history else None)
            elif qc_feedback_history:
                # Check QC feedback for regulated content indicators
                needs_legal_ack = requires_legal_acknowledgment("", qc_feedback_history[-1])
            elif text:
                # Check original text input for regulated content (first iteration)
                needs_legal_ack = requires_legal_acknowledgment(text, None)
            
            if update_task_status_callback:
                task_description = f"Creating platform-specific content (Iteration {iteration_count}/{max_iterations})"
                if qc_feedback_history:
                    task_description += f"\n\n🔄 RETRY WITH QC FEEDBACK:\n{qc_feedback_history[-1][:300]}{'...' if len(qc_feedback_history[-1]) > 300 else ''}"
                # Conditional requirement: Only require legal acknowledgment for regulated content
                if needs_legal_ack:
                    task_description += f"\n\n⚠️ CONDITIONAL REQUIREMENT (Regulated Content Detected):\nBecause QC is explicitly demanding it, you MUST include one neutral legal-status + risk line in your content.\n\nThis applies because your content mentions regulated substances, medical treatment claims, or other regulated goods."
                update_task_status_callback(
                    agent=f"{platform.capitalize()} Writing Agent",
                    task=task_description,
                    progress=40 + (iteration_count * 5),
                    agent_status="running"
                )
            
            # VERIFICATION: Log platform formatting contract checks before writer retry
            if qc_feedback_history:
                logger.info(f"🔐 WRITER RETRY VERIFICATION: Platform: {platform.upper()}")
                logger.info(f"🔐 WRITER RETRY VERIFICATION: Iteration: {iteration_count}")
                
                # Check platform formatting contract preservation
                if platform.lower() == "instagram":
                    # IG formatting checks
                    content_str = str(current_content)
                    has_hashtag_line = "#" in content_str and any(line.strip().startswith("#") for line in content_str.split("\n")[-3:])
                    hashtag_count = len([line for line in content_str.split("\n") if line.strip().startswith("#")])
                    has_headings = "##" in content_str or "**" in content_str or "Post Idea:" in content_str or "STATUS:" in content_str
                    emoji_count = sum(1 for char in content_str if ord(char) > 127 and char in "😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾")
                    
                    logger.info(f"🔐 WRITER RETRY VERIFICATION: IG Format Checks:")
                    logger.info(f"  - Has hashtag line (last 3 lines): {has_hashtag_line}")
                    logger.info(f"  - Hashtag count: {hashtag_count}")
                    logger.info(f"  - Has headings (##, **, Post Idea, STATUS): {has_headings}")
                    logger.info(f"  - Emoji count: {emoji_count}")
                    
                    if has_headings:
                        logger.warning(f"⚠️ WRITER RETRY VERIFICATION: IG content contains headings - should not have headings")
                    if not has_hashtag_line or hashtag_count < 3:
                        logger.warning(f"⚠️ WRITER RETRY VERIFICATION: IG content missing hashtag line or insufficient hashtags")
                    if emoji_count > 4:
                        logger.info(f"ℹ️ WRITER RETRY VERIFICATION: IG content has {emoji_count} emojis (acceptable, but note if >4)")
            
            # Create writing task with research output and any QC feedback
            # Include the full context (content queue, brand guidelines, etc.) in the description
            # CRITICAL: Platform constraints and brand voice remain authoritative; QC feedback is secondary
            if qc_feedback_history:
                logger.info(f"📝 WRITER TASK CREATION: Including QC feedback in writer retry task (Iteration {iteration_count})")
                logger.info(f"📝 WRITER TASK CREATION: QC feedback preview: {qc_feedback_history[-1][:200]}...")
            else:
                logger.info(f"📝 WRITER TASK CREATION: No QC feedback - first iteration (Iteration {iteration_count})")
            
            # Conditional acknowledgment requirement - only for regulated content
            conditional_acknowledgment_instruction = ""
            if needs_legal_ack:
                conditional_acknowledgment_instruction = """
═══════════════════════════════════════════════════════════════
CONDITIONAL ACKNOWLEDGMENT REQUIREMENT (Regulated Content Detected):
═══════════════════════════════════════════════════════════════
Because QC is explicitly demanding it, you MUST include one neutral legal-status + risk line in your content.

This requirement applies because your content mentions regulated substances, medical/mental-health treatment guidance/claims, or other regulated goods.

Include a neutral acknowledgment line that addresses legal, regulatory, or risk considerations relevant to the content topic. The acknowledgment should be factual, neutral, and appropriate to the context.

Example formats:
- For regulated substances: "[Substance] is a controlled substance in many jurisdictions. Consult legal and medical professionals before considering any use."
- For medical/mental health claims: "This content is for informational purposes only and is not medical advice. Consult healthcare professionals for medical guidance."
- For other regulated goods: Include appropriate legal status and risk acknowledgment.

You must include this acknowledgment line in your content.
═══════════════════════════════════════════════════════════════
"""
            
            writing_task_iter = Task(
                description=f"""{writing_description}
                
                Use the research output from the research agent to create {platform}-specific content.
                Platform: {platform}
                Author personality: {author_personality or 'professional'}
                Week: {week}
                
                Original Context (Content Queue, Brand Guidelines, Parent Idea, etc.):
                {text}
                
                Research Output:
                {research_output}
                
                {f'''
═══════════════════════════════════════════════════════════════
QC COMPLIANCE FEEDBACK (Secondary Constraints):
═══════════════════════════════════════════════════════════════
{qc_feedback_history[-1]}

CRITICAL PRECEDENCE RULES:
1. Platform formatting rules (emojis, headings, structure, hashtags) are MANDATORY and must be preserved
2. Brand voice guidelines are MANDATORY and must be preserved
3. Author personality style is MANDATORY and must be preserved
4. Address QC constraints ONLY within the bounds of platform/brand/author requirements
5. If QC constraint conflicts with platform rule, platform rule takes precedence (unless it's a safety/legal violation)

You must satisfy BOTH the original platform/brand/author constraints AND the QC constraints.
If they conflict on stylistic grounds, prioritize platform/brand/author. If QC identifies a safety/legal violation, address it while maintaining platform formatting where possible.
═══════════════════════════════════════════════════════════════
{conditional_acknowledgment_instruction}
''' if qc_feedback_history else f'''The research agent has already analyzed the text and extracted themes. Use that analysis to create engaging content.

{conditional_acknowledgment_instruction}
'''}
                """,
                expected_output=writing_expected_output,
                agent=writing_agent,
                verbose=True
            )
            
            # Execute writing agent with timeout protection
            writing_crew = Crew(
                agents=[writing_agent],
                tasks=[writing_task_iter],
                process=Process.sequential,
                verbose=True,
                memory=True
            )
            try:
                writing_result = run_with_timeout(
                    writing_crew.kickoff,
                    timeout_seconds=CREWAI_TIMEOUT_SECONDS,
                    inputs={
                        "text": text,
                        "week": week,
                        "platform": platform,
                        "days_list": days_list,
                        "author_personality": author_personality or "professional"
                    }
                )
            except TimeoutError as te:
                logger.error(f"❌ Writing agent timed out after {CREWAI_TIMEOUT_SECONDS} seconds")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} Writing Agent",
                        task=f"TIMEOUT: Operation exceeded {CREWAI_TIMEOUT_SECONDS} seconds",
                        error=str(te),
                        agent_status="error"
                    )
                raise
            except Exception as e:
                logger.error(f"❌ Writing agent error: {e}")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} Writing Agent",
                        task=f"ERROR: {str(e)}",
                        error=str(e),
                        agent_status="error"
                    )
                raise
            
            # Extract writing output
            if hasattr(writing_result, 'tasks_output') and writing_result.tasks_output:
                current_content = writing_result.tasks_output[0]
            elif hasattr(writing_result, 'raw'):
                current_content = writing_result.raw
            else:
                current_content = str(writing_result)
            
            if update_task_status_callback:
                update_task_status_callback(
                    agent=f"{platform.capitalize()} Writing Agent",
                    task="Content created, sending to QC for review",
                    progress=50 + (iteration_count * 5),
                    agent_status="completed"
                )
            
            # STEP 3: QC Agent Review (with structured approval/rejection)
            # Get the first QC agent (for now, we'll use the primary QC agent)
            primary_qc_agent = qc_agents_list[0] if qc_agents_list else qc_agent
            if not qc_agents_list:
                logger.warning("⚠️ QC GATE: qc_agents_list empty; using default qc_agent as primary")
            primary_qc_agent_role = getattr(primary_qc_agent, "role", "QC Agent")
            
            logger.info(f"🔍 Iteration {iteration_count}: QC Agent reviewing content")
            logger.info(
                f"🚪 QC GATE: Executing QC agent '{primary_qc_agent_role}' - "
                f"content will be blocked if policy violation detected"
            )
            
            # VERIFICATION: Log hash of writer output before QC review
            content_hash_before_qc = hashlib.sha256(str(current_content).encode('utf-8')).hexdigest()
            logger.info(f"🔐 QC VERIFICATION: Writer output hash (before QC): {content_hash_before_qc[:16]}...")
            logger.info(f"📊 QC VERIFICATION: Writer output length: {len(str(current_content))} chars")
            
            primary_qc_agent_id = None
            
            # Find QC agent ID for rejection limit tracking
            # CRITICAL: Find the QC agent ID that matches the platform (e.g., agent_1_instagram_qc for Instagram)
            db = SessionLocal()
            try:
                agents_list_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == "qc_agents_list"
                ).first()
                if agents_list_setting and agents_list_setting.setting_value:
                    try:
                        qc_agent_ids = json.loads(agents_list_setting.setting_value)
                        platform_lower = platform.lower()
                        
                        # First, try to find platform-scoped QC agent (e.g., agent_1_instagram_qc for Instagram)
                        for qc_agent_id in qc_agent_ids:
                            normalized_id = normalize_qc_agent_id(qc_agent_id)
                            # Check if this QC agent ID contains the platform name
                            if platform_lower in normalized_id.lower():
                                primary_qc_agent_id = normalized_id
                                logger.info(f"✅ Found platform-scoped QC agent ID for {platform}: {primary_qc_agent_id}")
                                break
                        
                        # Fallback: if no platform-scoped agent found, use first agent in list
                        if not primary_qc_agent_id and qc_agent_ids:
                            primary_qc_agent_id = normalize_qc_agent_id(qc_agent_ids[0])
                            logger.info(f"⚠️ No platform-scoped QC agent found, using first in list: {primary_qc_agent_id}")
                    except json.JSONDecodeError:
                        pass
            finally:
                db.close()
            
            # Get rejection limit for this QC agent
            rejection_limit = qc_rejection_limits.get(primary_qc_agent_id, 5) if primary_qc_agent_id else 5
            current_rejection_count = rejection_counts.get(primary_qc_agent_id, 0)
            
            # Log QC agent resolution and rejection limit
            logger.info(f"🔍 QC AGENT RESOLUTION: Using QC agent ID '{primary_qc_agent_id}' for platform '{platform}'")
            logger.info(f"🔍 QC REJECTION LIMIT: {rejection_limit} (current rejections: {current_rejection_count})")
            if primary_qc_agent_id and primary_qc_agent_id not in qc_rejection_limits:
                logger.warning(f"⚠️ QC agent ID '{primary_qc_agent_id}' not found in qc_rejection_limits, using default limit of 5")
            
            # Update status with QC agent resolution details
            if update_task_status_callback:
                qc_agent_info = f"QC Agent: {primary_qc_agent_role} (ID: {primary_qc_agent_id or 'default'})\nRejection Limit: {rejection_limit} (Current: {current_rejection_count})"
                update_task_status_callback(
                    agent=f"{platform.capitalize()} QC Agent",
                    task=f"Reviewing content with {primary_qc_agent_role}\n{qc_agent_info}",
                    progress=60 + (iteration_count * 5),
                    agent_status="running"
                )
            
            if current_rejection_count >= rejection_limit:
                error_msg = f"QC Agent rejection limit ({rejection_limit}) reached. Content failed quality checks after {iteration_count} iterations."
                logger.error(f"❌ {error_msg}")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"FAILURE: {error_msg}",
                        error=error_msg,
                        agent_status="error"
                    )
                return {
                    "success": False,
                    "error": error_msg,
                    "data": {
                        "research": research_output,
                        "writing": current_content,
                        "quality_control": None,
                        "final_content": None,
                        "platform": platform,
                        "week": week,
                        "iterations": iteration_count,
                        "rejection_count": current_rejection_count
                    },
                    "metadata": {
                        "workflow": "crewai_content_generation_iterative",
                        "agents_used": ["script_research_agent", f"{platform}_agent", "qc_agent"],
                        "iterations": iteration_count,
                        "rejection_limit_reached": True
                    }
                }
            
            # Create QC task - QC is a GATE, not a rewriter
            # QC must pass writer output unchanged if safe, or reject with minimal constraints only
            qc_task_iter = Task(
                description=f"""{qc_task_desc.description}
                
                You are a COMPLIANCE GATE, not a content rewriter.
                
                Review the content created by the writing agent ONLY for:
                - Explicit policy violations (safety, legal, brand policy)
                - Critical factual errors
                - Platform-specific policy requirements (not stylistic preferences)
                
                Content to Review:
                {current_content}
                
                CRITICAL RULES:
                1. If content is SAFE (no policy violations): You MUST approve it UNCHANGED.
                   - Do NOT suggest stylistic improvements
                   - Do NOT rewrite for "better quality" or "clarity"
                   - Do NOT modify platform formatting (emojis, headings, structure) unless it violates platform policy
                   - Platform formatting rules and brand voice are set by the writing agent and must be preserved
                
                2. If content is UNSAFE (policy violation detected): Reject with minimal constraints only.
                   - Identify the specific policy violation category
                   - Provide minimal safety constraints to fix it
                   - Do NOT provide a full rewrite
                   - Do NOT override platform formatting or brand voice unless directly violating policy
                
                IMPORTANT: You must provide a structured response in the following format:
                
                STATUS: [APPROVED or REJECTED]
                
                If STATUS is APPROVED:
                - Return the content EXACTLY as provided (unchanged)
                - Do not modify, improve, or rewrite
                
                If STATUS is REJECTED:
                - POLICY_VIOLATION: [Category: safety/legal/brand/factual]
                - MINIMAL_CONSTRAINTS: [Only the specific constraints needed to fix the violation, no full rewrite]
                - Do NOT provide REVISED_CONTENT - the writer will fix it based on constraints only
                
                FEEDBACK: [Only if rejected: policy violation category and minimal constraints]
                """,
                expected_output="STATUS: APPROVED (return content unchanged) or REJECTED (policy violation + minimal constraints only, no rewrite).",
                agent=primary_qc_agent,
                verbose=True
            )
            
            if update_task_status_callback:
                update_task_status_callback(
                    agent=f"{platform.capitalize()} QC Agent",
                    task=f"Reviewing content quality (Iteration {iteration_count}, Rejections: {current_rejection_count}/{rejection_limit})",
                    progress=60 + (iteration_count * 5),
                    agent_status="running"
                )
            
            # Execute QC agent with timeout protection
            qc_crew = Crew(
                agents=[primary_qc_agent],
                tasks=[qc_task_iter],
                process=Process.sequential,
                verbose=True,
                memory=True
            )
            
            # Log which QC agent is executing
            logger.info(f"🚪 QC GATE EXECUTION: Executing QC agent '{primary_qc_agent_role}' (ID: {primary_qc_agent_id}) for platform '{platform}'")
            logger.info(f"🚪 QC GATE EXECUTION: QC agent role: {primary_qc_agent.role if hasattr(primary_qc_agent, 'role') else 'Unknown'}")
            
            try:
                qc_result = run_with_timeout(
                    qc_crew.kickoff,
                    timeout_seconds=CREWAI_TIMEOUT_SECONDS,
                    inputs={
                        "text": text,
                        "week": week,
                        "platform": platform,
                        "days_list": days_list,
                        "author_personality": author_personality or "professional"
                    }
                )
            except TimeoutError as te:
                logger.error(f"❌ QC agent timed out after {CREWAI_TIMEOUT_SECONDS} seconds")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"TIMEOUT: Operation exceeded {CREWAI_TIMEOUT_SECONDS} seconds",
                        error=str(te),
                        agent_status="error"
                    )
                raise
            except Exception as e:
                logger.error(f"❌ QC agent error: {e}")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"ERROR: {str(e)}",
                        error=str(e),
                        agent_status="error"
                    )
                raise
            
            # Extract QC output
            qc_output_raw = None
            if hasattr(qc_result, 'tasks_output') and qc_result.tasks_output:
                qc_output_raw = qc_result.tasks_output[0]
            elif hasattr(qc_result, 'raw'):
                qc_output_raw = qc_result.raw
            else:
                qc_output_raw = str(qc_result)
            
            # Parse QC response for approval/rejection
            # QC is a GATE: if approved, use writer output unchanged; if rejected, extract only constraints
            qc_output_str = str(qc_output_raw)
            is_approved = False
            feedback = None
            policy_violation = None
            minimal_constraints = None
            
            # Check for structured response
            if "STATUS:" in qc_output_str.upper():
                status_line = [line for line in qc_output_str.split('\n') if 'STATUS:' in line.upper()][0]
                if "APPROVED" in status_line.upper():
                    is_approved = True
                    # QC approved - we will use writer output unchanged (current_content)
                    # Do NOT use QC's output as it may have rewritten the content
                    logger.info(f"✅ QC approved - using writer output unchanged")
                elif "REJECTED" in status_line.upper():
                    is_approved = False
                    # Extract policy violation category
                    if "POLICY_VIOLATION:" in qc_output_str.upper():
                        violation_start = qc_output_str.upper().find("POLICY_VIOLATION:")
                        violation_end = qc_output_str.upper().find("MINIMAL_CONSTRAINTS:", violation_start)
                        if violation_end > violation_start:
                            policy_violation = qc_output_str[violation_start + 17:violation_end].strip()
                        else:
                            policy_violation = qc_output_str[violation_start + 17:].strip()
                    
                    # Extract minimal constraints (not full rewrite)
                    if "MINIMAL_CONSTRAINTS:" in qc_output_str.upper():
                        constraints_start = qc_output_str.upper().find("MINIMAL_CONSTRAINTS:")
                        constraints_end = qc_output_str.upper().find("FEEDBACK:", constraints_start)
                        if constraints_end > constraints_start:
                            minimal_constraints = qc_output_str[constraints_start + 19:constraints_end].strip()
                        else:
                            minimal_constraints = qc_output_str[constraints_start + 19:].strip()
                    
                    # Extract feedback (fallback if MINIMAL_CONSTRAINTS not found)
                    if not minimal_constraints and "FEEDBACK:" in qc_output_str.upper():
                        feedback_start = qc_output_str.upper().find("FEEDBACK:")
                        feedback = qc_output_str[feedback_start + 9:].strip()
                    elif minimal_constraints:
                        feedback = minimal_constraints
                    else:
                        feedback = "Policy violation detected - requires revision"
                    
                    # Build structured feedback with policy category and constraints
                    if policy_violation:
                        feedback = f"Policy Violation: {policy_violation}\n\nConstraints: {minimal_constraints or feedback}"
            else:
                # Fallback: Try to detect approval/rejection from content
                # If QC output mentions rejection keywords, reject; otherwise approve
                qc_lower = qc_output_str.lower()
                rejection_keywords = ["reject", "fail", "violation", "policy", "unsafe", "inappropriate"]
                if any(keyword in qc_lower for keyword in rejection_keywords):
                    is_approved = False
                    feedback = "Policy violation detected - requires revision"
                else:
                    is_approved = True
                    logger.info(f"✅ QC approved (fallback detection) - using writer output unchanged")
            
            if is_approved:
                logger.info(f"✅ Iteration {iteration_count}: QC Agent APPROVED content - using writer output unchanged")
                
                # VERIFICATION: Assert that final output matches writer output (QC is a gate, not rewriter)
                content_hash_after_qc = hashlib.sha256(str(current_content).encode('utf-8')).hexdigest()
                logger.info(f"🔐 QC VERIFICATION: Writer output hash (after QC approval): {content_hash_after_qc[:16]}...")
                
                if content_hash_before_qc != content_hash_after_qc:
                    logger.error(f"❌ QC VERIFICATION FAILED: Hash changed after QC approval! Before: {content_hash_before_qc[:16]}..., After: {content_hash_after_qc[:16]}...")
                    logger.error(f"❌ QC should be a gate - output must be unchanged when approved")
                else:
                    logger.info(f"✅ QC VERIFICATION PASSED: Hash unchanged - QC correctly acting as gate")
                
                if update_task_status_callback:
                    qc_approval_info = f"QC Agent: {primary_qc_agent_role} (ID: {primary_qc_agent_id or 'default'})\nContent APPROVED after {iteration_count} iteration(s)\nWriter output preserved unchanged"
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"✅ APPROVED\n\n{qc_approval_info}",
                        progress=90,
                        agent_status="completed"
                    )
                # Break out of loop - content approved
                # current_content (writer output) will be used as final_output
                break
            else:
                logger.warning(f"⚠️ Iteration {iteration_count}: QC Agent REJECTED content - policy violation detected")
                
                # VERIFICATION: Log extracted policy violation and constraints
                logger.info(f"🔐 QC VERIFICATION: Policy Violation Category: {policy_violation or 'Not specified'}")
                logger.info(f"🔐 QC VERIFICATION: Minimal Constraints: {minimal_constraints or feedback or 'Not specified'}")
                
                # VERIFICATION: Assert current_content is unchanged (QC didn't rewrite it)
                content_hash_after_rejection = hashlib.sha256(str(current_content).encode('utf-8')).hexdigest()
                logger.info(f"🔐 QC VERIFICATION: Writer output hash (after QC rejection): {content_hash_after_rejection[:16]}...")
                
                if content_hash_before_qc != content_hash_after_rejection:
                    logger.error(f"❌ QC VERIFICATION FAILED: Writer output changed after QC rejection! Before: {content_hash_before_qc[:16]}..., After: {content_hash_after_rejection[:16]}...")
                    logger.error(f"❌ QC should not modify writer output - it should only provide constraints")
                else:
                    logger.info(f"✅ QC VERIFICATION PASSED: Writer output unchanged - QC correctly providing constraints only")
                
                # Verify QC did not provide rewritten content
                if "REVISED_CONTENT:" in qc_output_str.upper():
                    logger.warning(f"⚠️ QC VERIFICATION WARNING: QC provided REVISED_CONTENT - this should not happen. QC should only provide constraints.")
                
                current_rejection_count += 1
                rejection_counts[primary_qc_agent_id] = current_rejection_count
                
                # Store only the feedback/constraints (not rewritten content)
                qc_feedback_history.append(feedback or "Policy violation - requires revision")
                
                if update_task_status_callback:
                    # Include the actual content text that was rejected (first 500 chars for visibility)
                    content_preview = str(current_content)[:500] + ("..." if len(str(current_content)) > 500 else "")
                    qc_rejection_info = f"QC Agent: {primary_qc_agent_role} (ID: {primary_qc_agent_id or 'default'})\nRejection {current_rejection_count}/{rejection_limit}\n\nPolicy Violation: {policy_violation or 'Detected'}\nConstraints: {minimal_constraints or feedback or 'Revision requested'}\n\n📄 REJECTED CONTENT (Preview):\n{content_preview}"
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"Content REJECTED\n\n{qc_rejection_info}",
                        progress=70 + (iteration_count * 5),
                        agent_status="completed"
                    )
                
                # CRITICAL: Do NOT overwrite current_content with QC's revised content
                # Keep writer output as baseline - writer will retry with original constraints + QC feedback
                # current_content remains unchanged (writer's output)
                logger.info(f"📝 Keeping writer output as baseline for retry - QC feedback: {feedback[:100] if feedback else 'N/A'}")
                logger.info(f"📝 QC FEEDBACK TO WRITER: Policy Violation: {policy_violation or 'N/A'}")
                logger.info(f"📝 QC FEEDBACK TO WRITER: Minimal Constraints: {minimal_constraints[:200] if minimal_constraints else feedback[:200] if feedback else 'N/A'}")
        
        # If we exited loop due to max iterations, fail
        if iteration_count >= max_iterations and not is_approved:
            error_msg = f"Maximum iterations ({max_iterations}) reached without QC approval. Content failed quality checks."
            logger.error(f"❌ {error_msg}")
            if update_task_status_callback:
                update_task_status_callback(
                    agent=f"{platform.capitalize()} QC Agent",
                    task=f"FAILURE: {error_msg}",
                    error=error_msg,
                    agent_status="error"
                )
            return {
                "success": False,
                "error": error_msg,
                "data": {
                    "research": research_output,
                    "writing": current_content,
                    "quality_control": None,
                    "final_content": None,
                    "platform": platform,
                    "week": week,
                    "iterations": iteration_count,
                    "rejection_count": current_rejection_count
                },
                "metadata": {
                    "workflow": "crewai_content_generation_iterative",
                    "agents_used": ["script_research_agent", f"{platform}_agent", "qc_agent"],
                    "iterations": iteration_count,
                    "max_iterations_reached": True
                }
            }
        
        # Success - content approved
        # CRITICAL: Use writer output (current_content) unchanged, NOT QC's revised_content
        # QC is a gate - if approved, writer output passes through unchanged
        final_output = current_content
        
        # VERIFICATION: Final output hash check
        final_hash = hashlib.sha256(str(final_output).encode('utf-8')).hexdigest()
        if current_content:
            writer_hash = hashlib.sha256(str(current_content).encode('utf-8')).hexdigest()
            if final_hash != writer_hash:
                logger.error(f"❌ FINAL OUTPUT VERIFICATION FAILED: Final hash {final_hash[:16]}... != Writer hash {writer_hash[:16]}...")
                logger.error(f"❌ QC approved content should be unchanged - final output must equal writer output")
            else:
                logger.info(f"✅ FINAL OUTPUT VERIFICATION PASSED: Final hash matches writer output hash")
        logger.info(f"✅ Final output: Using writer output unchanged (QC approved as gate)")
        logger.info(f"🔐 FINAL OUTPUT VERIFICATION: Final hash: {final_hash[:16]}...")
        
        # Helper function to extract text from CrewAI TaskOutput objects
        def extract_task_output(task_output):
            """Extract text content from CrewAI TaskOutput object"""
            if task_output is None:
                return None
            # TaskOutput objects have .raw property
            if hasattr(task_output, 'raw'):
                raw = task_output.raw
                if isinstance(raw, str):
                    return raw
                elif isinstance(raw, dict):
                    # Try common content keys
                    return raw.get('content') or raw.get('text') or raw.get('output') or str(raw)
                else:
                    return str(raw)
            # Fallback to string conversion
            if isinstance(task_output, str):
                return task_output
            return str(task_output)
        
        # Extract final content from string or TaskOutput
        if isinstance(final_output, str):
            final_content_text = final_output
        else:
            final_content_text = extract_task_output(final_output) if final_output else str(current_content)
        
        return {
            "success": True,
            "data": {
                "research": research_output,
                "writing": current_content,
                "quality_control": final_content_text,
                "final_content": final_content_text,
                "platform": platform,
                "week": week
            },
            "metadata": {
                "workflow": "crewai_content_generation_iterative",
                "agents_used": ["script_research_agent", f"{platform}_agent"] + [f"qc_{i}" for i in range(len(qc_agents_list))],
                "qc_agents_count": len(qc_agents_list),
                "iterations": iteration_count,
                "rejection_counts": rejection_counts,
                "process": "iterative"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in CrewAI content generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

def create_research_to_writing_crew(
    text: str,
    week: int = 1,
    platform: str = "linkedin",
    days_list: Optional[list] = None
) -> Dict[str, Any]:
    """
    Simplified CrewAI workflow: Research → Writing (no QC)
    Useful for faster content generation when QC is not needed.
    """
    try:
        if days_list is None:
            days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        writing_agent = PLATFORM_AGENTS.get(platform.lower())
        if not writing_agent:
            return {
                "success": False,
                "error": f"Platform {platform} not supported",
                "data": None
            }
        
        # Get task descriptions
        research_task_desc = db_manager.get_task_by_name("script_research_task")
        platform_task_desc = db_manager.get_task_by_name(f"{platform}_task")
        
        if not all([research_task_desc, platform_task_desc]):
            return {
                "success": False,
                "error": "Required tasks not found in database",
                "data": None
            }
        
        days_str = ", ".join(days_list)
        m = len(days_list)
        
        # Research task
        research_description = research_task_desc.description.format(
            week=week, m=m, days_str=days_str
        )
        research_expected_output = research_task_desc.expected_output.format(week=week)
        
        research_task = Task(
            description=f"""{research_description}
            
            Input text:
            {text}
            """,
            expected_output=research_expected_output,
            agent=script_research_agent
        )
        
        # Writing task
        writing_task = Task(
            description=f"""{platform_task_desc.description}
            
            Create {platform}-specific content based on the research output from the previous agent.
            Platform: {platform}
            Week: {week}
            
            The research agent has analyzed the text. Use that analysis to create engaging content.
            """,
            expected_output=platform_task_desc.expected_output,
            agent=writing_agent
        )
        
        # Create Crew
        crew = Crew(
            agents=[script_research_agent, writing_agent],
            tasks=[research_task, writing_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
        
        logger.info(f"🚀 Starting CrewAI workflow: Research → {platform} Writing")
        result = crew.kickoff(inputs={
            "text": text,
            "week": week,
            "platform": platform
        })
        
        # Extract outputs
        research_output = None
        writing_output = None
        
        if hasattr(result, 'tasks_output'):
            if len(result.tasks_output) >= 1:
                research_output = result.tasks_output[0]
            if len(result.tasks_output) >= 2:
                writing_output = result.tasks_output[1]
        else:
            writing_output = str(result)
        
        return {
            "success": True,
            "data": {
                "research": research_output,
                "writing": writing_output,
                "platform": platform,
                "week": week
            },
            "metadata": {
                "workflow": "crewai_research_to_writing",
                "agents_used": ["script_research_agent", f"{platform}_agent"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in CrewAI research-to-writing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

