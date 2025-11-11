"""
CrewAI-based workflows for content generation
Enables agent-to-agent handoffs with automatic orchestration
"""

from crewai import Crew, Process, Task
from agents import script_research_agent, qc_agent
from agents import linkedin_agent, twitter_agent, facebook_agent, instagram_agent, tiktok_agent, youtube_agent, wordpress_agent
from database import DatabaseManager
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

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
        
        # Task 3: QC Agent - Review the written content
        qc_description = qc_task_desc.description
        qc_expected_output = qc_task_desc.expected_output
        
        qc_task = Task(
            description=f"""{qc_description}
            
            Review the content created by the writing agent for:
            - Quality and clarity
            - Platform-specific requirements ({platform})
            - Compliance with guidelines
            - Author personality match ({author_personality or 'professional'})
            - Accuracy and relevance to the original research
            
            The writing agent has created content based on the research. Review it thoroughly.
            """,
            expected_output=qc_expected_output,
            agent=qc_agent
        )
        
        # Create Crew with sequential process
        crew = Crew(
            agents=[script_research_agent, writing_agent, qc_agent],
            tasks=[research_task, writing_task, qc_task],
            process=Process.sequential,  # Research → Writing → QC
            verbose=True,
            memory=True  # Agents remember previous interactions
        )
        
        # Execute the crew
        logger.info(f"🚀 Starting CrewAI workflow: Research → {platform} Writing → QC")
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
                "agents_used": ["script_research_agent", f"{platform}_agent", "qc_agent"],
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

