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

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

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
    author_personality: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create and execute a CrewAI workflow for content generation.
    
    Flow: Research Agent → Writing Agent → QC Agent
    
    Args:
        text: Input text to analyze
        week: Week number for content planning
        platform: Target platform (linkedin, twitter, etc.)
        days_list: List of days for subcontent
        author_personality: Author personality style
        
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
        
        if not all([research_task_desc, qc_task_desc, platform_task_desc]):
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
            agent=script_research_agent
        )
        
        # Task 2: Writing Agent - Create platform-specific content from research
        writing_description = platform_task_desc.description
        writing_expected_output = platform_task_desc.expected_output
        
        writing_task = Task(
            description=f"""{writing_description}
            
            Use the research output from the previous agent to create {platform}-specific content.
            Platform: {platform}
            Author personality: {author_personality or 'professional'}
            Week: {week}
            
            The research agent has already analyzed the text and extracted themes. Use that analysis to create engaging content.
            """,
            expected_output=writing_expected_output,
            agent=writing_agent
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
                    agent=qc_agent_obj
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
                agent=qc_agent
            )
            qc_tasks.append(qc_task)
        
        # Build agents list: research + writing + all QC agents
        all_agents = [script_research_agent, writing_agent] + qc_agents_list
        all_tasks = [research_task, writing_task] + qc_tasks
        
        # Create Crew with sequential process
        crew = Crew(
            agents=all_agents,
            tasks=all_tasks,
            process=Process.sequential,  # Research → Writing → QC
            verbose=True,
            memory=True  # Agents remember previous interactions
        )
        
        # Execute the crew
        # Note: Research agent runs ONCE at the start, then Writing → QC sequentially
        # CrewAI's sequential process ensures research is not re-engaged after QC feedback
        logger.info(f"🚀 Starting CrewAI workflow: Research (once) → {platform} Writing → QC")
        result = crew.kickoff(inputs={
            "text": text,
            "week": week,
            "platform": platform,
            "days_list": days_list,
            "author_personality": author_personality or "professional"
        })
        
        # Parse result
        # CrewAI returns a CrewOutput object with tasks_output
        final_output = None
        if hasattr(result, 'tasks_output'):
            # Get the last task output (QC agent's review)
            if result.tasks_output:
                final_output = result.tasks_output[-1]
        elif hasattr(result, 'raw'):
            final_output = result.raw
        else:
            final_output = str(result)
        
        # Extract outputs from each agent
        research_output = None
        writing_output = None
        qc_output = None
        
        if hasattr(result, 'tasks_output'):
            if len(result.tasks_output) >= 1:
                research_output = result.tasks_output[0]  # Research agent output
            if len(result.tasks_output) >= 2:
                writing_output = result.tasks_output[1]  # Writing agent output
            if len(result.tasks_output) >= 3:
                qc_output = result.tasks_output[2]  # QC agent output
        
        return {
            "success": True,
            "data": {
                "research": research_output,
                "writing": writing_output,
                "quality_control": qc_output,
                "final_content": final_output,
                "platform": platform,
                "week": week
            },
            "metadata": {
                "workflow": "crewai_content_generation",
                "agents_used": ["script_research_agent", f"{platform}_agent"] + [f"qc_{i}" for i in range(len(qc_agents_list))],
                "qc_agents_count": len(qc_agents_list),
                "process": "sequential"
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

