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

def get_qc_agents_for_agent(tab: str, agent_id: str) -> List[Agent]:
    """
    Get QC agents for a specific agent.
    Returns: assigned QC agents + global QC agents (always included)
    
    Args:
        tab: The agent tab (research, writing)
        agent_id: The agent ID
        
    Returns:
        List of QC Agent objects
    """
    qc_agents: List[Agent] = []
    db = SessionLocal()
    
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
        
        # Step 2: Get all global QC agents (always included)
        # Get list of all QC agents
        qc_agents_list_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "qc_agents_list"
        ).first()
        
        if qc_agents_list_setting and qc_agents_list_setting.setting_value:
            try:
                qc_agent_ids = json.loads(qc_agents_list_setting.setting_value)
                for qc_agent_id in qc_agent_ids:
                    # Check if this QC agent is global
                    global_setting = db.query(SystemSettings).filter(
                        SystemSettings.setting_key == f"qc_agent_{qc_agent_id}_global"
                    ).first()
                    
                    # Also check alternative format (without "qc_" prefix in key)
                    if not global_setting:
                        global_setting = db.query(SystemSettings).filter(
                            SystemSettings.setting_key == f"qc_agent_{qc_agent_id.replace('qc_', '')}_global"
                        ).first()
                    
                    if global_setting and global_setting.setting_value == "true":
                        # Create agent from global QC agent ID
                        qc_agent_obj = _create_qc_agent_from_id(qc_agent_id)
                        if qc_agent_obj:
                            # Avoid duplicates (if assigned QC is also global)
                            if not any(agent.role == qc_agent_obj.role for agent in qc_agents):
                                qc_agents.append(qc_agent_obj)
                                logger.info(f"✅ Added global QC agent: {qc_agent_id}")
            except json.JSONDecodeError:
                logger.warning("⚠️ Could not parse qc_agents_list, skipping global QC agents")
        
        # Step 3: Fallback to default qc_agent if no QC agents found
        if not qc_agents:
            logger.info("⚠️ No QC agents found, using default qc_agent")
            qc_agents.append(qc_agent)
        
    except Exception as e:
        logger.error(f"❌ Error getting QC agents: {e}")
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
        
        # Task 2: Writing Agent - Create platform-specific content from research
        # CRITICAL: Retrieve writing agent configuration from SystemSettings (admin panel)
        db = SessionLocal()
        try:
            platform_lower = platform.lower()
            
            # Get expected_output from SystemSettings (admin panel configuration)
            expected_output_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"writing_agent_{platform_lower}_expected_output"
            ).first()
            
            # Get prompt from SystemSettings (admin panel configuration)
            prompt_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"writing_agent_{platform_lower}_prompt"
            ).first()
            
            # Get description from SystemSettings (admin panel configuration)
            description_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == f"writing_agent_{platform_lower}_description"
            ).first()
            
            # Use admin panel configuration if available, otherwise fall back to database task
            if expected_output_setting and expected_output_setting.setting_value:
                writing_expected_output = expected_output_setting.setting_value
                logger.info(f"✅ Using Instagram Writer expected_output from SystemSettings (admin panel)")
            elif platform_task_desc:
                writing_expected_output = platform_task_desc.expected_output
                logger.warning(f"⚠️ Using fallback expected_output from database task (admin panel config not found)")
            else:
                writing_expected_output = f"Create engaging {platform} content based on the research analysis."
                logger.warning(f"⚠️ Using default expected_output (no configuration found)")
            
            if description_setting and description_setting.setting_value:
                writing_description = description_setting.setting_value
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
            if prompt_setting and prompt_setting.setting_value:
                writing_task_description_base = f"""{writing_description}

CRITICAL OUTPUT CONTRACT - MUST FOLLOW EXACTLY:
{prompt_setting.setting_value}"""
                logger.info(f"✅ Using {platform} Writer prompt from SystemSettings (admin panel)")
            else:
                logger.warning(f"⚠️ No prompt found in SystemSettings for {platform} Writer (admin panel config not found)")
                
        finally:
            db.close()
        
        writing_description = writing_task_description_base
        
        writing_task = Task(
            description=f"""{writing_description}
            
            Use the research output from the previous agent to create {platform}-specific content.
            Platform: {platform}
            Author personality: {author_personality or 'professional'}
            Week: {week}
            
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
                        qc_agents_list = get_qc_agents_for_agent("writing", matching_agent_id)
                    else:
                        # Fallback: try platform name directly
                        qc_agents_list = get_qc_agents_for_agent("writing", platform_lower)
                except json.JSONDecodeError:
                    # Fallback: try platform name directly
                    qc_agents_list = get_qc_agents_for_agent("writing", platform_lower)
            else:
                # Fallback: try platform name directly
                qc_agents_list = get_qc_agents_for_agent("writing", platform_lower)
        except Exception as e:
            logger.warning(f"⚠️ Could not find agent_id for platform {platform}, using fallback: {e}")
            # Fallback: try platform name directly
            qc_agents_list = get_qc_agents_for_agent("writing", platform_lower)
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
            
            if update_task_status_callback:
                update_task_status_callback(
                    agent=f"{platform.capitalize()} Writing Agent",
                    task=f"Creating platform-specific content (Iteration {iteration_count})" + (f"\n\nQC Feedback:\n{qc_feedback_history[-1]}" if qc_feedback_history else ""),
                    progress=40 + (iteration_count * 5),
                    agent_status="running"
                )
            
            # Create writing task with research output and any QC feedback
            writing_task_iter = Task(
                description=f"""{writing_description}
                
                Use the research output from the research agent to create {platform}-specific content.
                Platform: {platform}
                Author personality: {author_personality or 'professional'}
                Week: {week}
                
                Research Output:
                {research_output}
                
                {f'QC Feedback from Previous Review:\n{qc_feedback_history[-1]}\n\nPlease address the feedback and revise the content accordingly.' if qc_feedback_history else 'The research agent has already analyzed the text and extracted themes. Use that analysis to create engaging content.'}
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
            logger.info(f"🔍 Iteration {iteration_count}: QC Agent reviewing content")
            
            # Get the first QC agent (for now, we'll use the primary QC agent)
            primary_qc_agent = qc_agents_list[0] if qc_agents_list else qc_agent
            primary_qc_agent_id = None
            
            # Find QC agent ID for rejection limit tracking
            db = SessionLocal()
            try:
                agents_list_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == "qc_agents_list"
                ).first()
                if agents_list_setting and agents_list_setting.setting_value:
                    try:
                        qc_agent_ids = json.loads(agents_list_setting.setting_value)
                        if qc_agent_ids:
                            primary_qc_agent_id = qc_agent_ids[0]
                    except json.JSONDecodeError:
                        pass
            finally:
                db.close()
            
            # Get rejection limit for this QC agent
            rejection_limit = qc_rejection_limits.get(primary_qc_agent_id, 5) if primary_qc_agent_id else 5
            current_rejection_count = rejection_counts.get(primary_qc_agent_id, 0)
            
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
            
            # Create QC task with structured output requirement
            qc_task_iter = Task(
                description=f"""{qc_task_desc.description}
                
                Review the content created by the writing agent for:
                - Quality and clarity
                - Platform-specific requirements ({platform})
                - Compliance with guidelines
                - Author personality match ({author_personality or 'professional'})
                - Accuracy and relevance to the original research
                
                Content to Review:
                {current_content}
                
                IMPORTANT: You must provide a structured response in the following format:
                
                STATUS: [APPROVED or REJECTED]
                
                If STATUS is APPROVED:
                Provide the final approved content below.
                
                If STATUS is REJECTED:
                Provide specific feedback on what needs to be changed, then provide the revised content.
                
                FEEDBACK: [Your detailed feedback on what needs improvement]
                
                REVISED_CONTENT: [The improved content addressing the feedback]
                
                The writing agent will use your feedback to revise the content in the next iteration.
                """,
                expected_output="A structured response with STATUS (APPROVED/REJECTED), FEEDBACK (if rejected), and content.",
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
            qc_output_str = str(qc_output_raw)
            is_approved = False
            feedback = None
            revised_content = None
            
            # Check for structured response
            if "STATUS:" in qc_output_str.upper():
                status_line = [line for line in qc_output_str.split('\n') if 'STATUS:' in line.upper()][0]
                if "APPROVED" in status_line.upper():
                    is_approved = True
                    revised_content = qc_output_str
                elif "REJECTED" in status_line.upper():
                    is_approved = False
                    # Extract feedback
                    if "FEEDBACK:" in qc_output_str.upper():
                        feedback_start = qc_output_str.upper().find("FEEDBACK:")
                        feedback_end = qc_output_str.upper().find("REVISED_CONTENT:", feedback_start)
                        if feedback_end > feedback_start:
                            feedback = qc_output_str[feedback_start + 9:feedback_end].strip()
                        else:
                            feedback = qc_output_str[feedback_start + 9:].strip()
                    # Extract revised content
                    if "REVISED_CONTENT:" in qc_output_str.upper():
                        revised_start = qc_output_str.upper().find("REVISED_CONTENT:")
                        revised_content = qc_output_str[revised_start + 16:].strip()
                    else:
                        revised_content = qc_output_str
            else:
                # Fallback: Try to detect approval/rejection from content
                # If QC output is very similar to input, likely approved
                # If QC output has significant changes or mentions issues, likely rejected
                qc_lower = qc_output_str.lower()
                rejection_keywords = ["reject", "fail", "issue", "problem", "needs", "improve", "revise", "change"]
                if any(keyword in qc_lower for keyword in rejection_keywords):
                    is_approved = False
                    feedback = "QC agent identified issues requiring revision"
                    revised_content = qc_output_str
                else:
                    is_approved = True
                    revised_content = qc_output_str
            
            if is_approved:
                logger.info(f"✅ Iteration {iteration_count}: QC Agent APPROVED content")
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"Content APPROVED after {iteration_count} iteration(s)",
                        progress=90,
                        agent_status="completed"
                    )
                # Break out of loop - content approved
                break
            else:
                logger.warning(f"⚠️ Iteration {iteration_count}: QC Agent REJECTED content")
                current_rejection_count += 1
                rejection_counts[primary_qc_agent_id] = current_rejection_count
                qc_feedback_history.append(feedback or "QC agent requested revisions")
                
                if update_task_status_callback:
                    update_task_status_callback(
                        agent=f"{platform.capitalize()} QC Agent",
                        task=f"Content REJECTED (Rejection {current_rejection_count}/{rejection_limit})\n\nFeedback: {feedback or 'Revision requested'}",
                        progress=70 + (iteration_count * 5),
                        agent_status="completed"
                    )
                
                # Continue loop - send feedback back to writing agent
                current_content = revised_content  # Use revised content as starting point for next iteration
        
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
        final_output = revised_content or current_content
        
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

