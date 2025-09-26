from crewai import Agent
from dotenv import load_dotenv
import os
from tools import PLATFORM_LIMITS
from database import DatabaseManager
from sqlalchemy.orm import Session
# import tools
# from main import PLATFORM_LIMITS

db_manager = DatabaseManager()


PLATFORM_LIMITS = {
    "twitter": {"chars": 280, "words": None},
    "instagram": {"chars": None, "words": 400},
    "linkedin": {"chars": None, "words": 600},
    "facebook": {"chars": None, "words": 1000},
    "wordpress": {"chars": None, "words": 2000},
    "youtube": {"chars": None, "words": 2000},
    "tiktok": {"chars": None, "words": 400}
}


load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"

script_research_agent = Agent(
    role=db_manager.get_agent_by_name("script_research_agent").role,
    goal=db_manager.get_agent_by_name("script_research_agent").goal,
    backstory=db_manager.get_agent_by_name("script_research_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=True
)

qc_agent = Agent(
    role=db_manager.get_agent_by_name("qc_agent").role,
    goal=db_manager.get_agent_by_name("qc_agent").goal,
    backstory=db_manager.get_agent_by_name("qc_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

linkedin_agent = Agent(
    role=db_manager.get_agent_by_name("linkedin_agent").role,
    goal=db_manager.get_agent_by_name("linkedin_agent").goal,
    backstory=db_manager.get_agent_by_name("linkedin_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

facebook_agent = Agent(
    role=db_manager.get_agent_by_name("facebook_agent").role,
    goal=db_manager.get_agent_by_name("facebook_agent").goal,
    backstory=db_manager.get_agent_by_name("facebook_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

twitter_agent = Agent(
    role=db_manager.get_agent_by_name("twitter_agent").role,
    goal=db_manager.get_agent_by_name("twitter_agent").goal,
    backstory=db_manager.get_agent_by_name("twitter_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

instagram_agent = Agent(
    role=db_manager.get_agent_by_name("instagram_agent").role,
    goal=db_manager.get_agent_by_name("instagram_agent").goal,
    backstory=db_manager.get_agent_by_name("instagram_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

youtube_agent = Agent(
    role=db_manager.get_agent_by_name("youtube_agent").role,
    goal=db_manager.get_agent_by_name("youtube_agent").goal,
    backstory=db_manager.get_agent_by_name("youtube_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

tiktok_agent = Agent(
    role=db_manager.get_agent_by_name("tiktok_agent").role,
    goal=db_manager.get_agent_by_name("tiktok_agent").goal,
    backstory=db_manager.get_agent_by_name("tiktok_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)

wordpress_agent = Agent(
    role=db_manager.get_agent_by_name("wordpress_agent").role,
    goal=db_manager.get_agent_by_name("wordpress_agent").goal,
    backstory=db_manager.get_agent_by_name("wordpress_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=False
)


script_rewriter_agent = Agent(
    role=db_manager.get_agent_by_name("script_rewriter_agent").role,
    goal=db_manager.get_agent_by_name("script_rewriter_agent").goal,
    backstory=db_manager.get_agent_by_name("script_rewriter_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=True
)

regenrate_content_agent = Agent(
    role=db_manager.get_agent_by_name("regenrate_content_agent").role,
    goal=db_manager.get_agent_by_name("regenrate_content_agent").goal,
    backstory=db_manager.get_agent_by_name("regenrate_content_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=True
)

regenrate_subcontent_agent = Agent(
    role=db_manager.get_agent_by_name("regenrate_subcontent_agent").role,
    goal=db_manager.get_agent_by_name("regenrate_subcontent_agent").goal,
    backstory=db_manager.get_agent_by_name("regenrate_subcontent_agent").backstory,
    llm="gpt-4o-mini",
    memory=True,
    verbose=True,
    tools=[],
    allow_delegation=True
)


def generate_script(content, week, day):
    return {
        "title": f"Week {week} {day}",
        "content": f"Day {day}: Here's a thought-provoking idea for you: {content[:100]}... #Inspiration"
    }

def script_writer(content, weeks):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    scripts = []
    for week in range(1, weeks + 1):
        for day in days:
            script = generate_script(content, week, day)
            scripts.append(script)
    return scripts



# regenrate_content_agent = Agent(
#     role="""Content Regenerator""",
#     goal="""Regenrate the weekly content for the given week.""",
#     backstory="""You're a content regeneration specialist who excels at transforming existing content into fresh, engaging material. Your goal is to revitalize the weekly content theme and create compelling content for week. The content regenrated in this format:
#     - content- If content is regenrate only regenerate the content of the week. The content would be wisdom, ideas, or quotes alond with a line defining the content.""",
#     llm="gpt-4o-mini",
#     memory=True,
#     verbose=True,
#     tools=[],
#     allow_delegation=True
# )


# regenrate_subcontent_agent = Agent(
#     role="""Subcontent Regenerator """,
#     goal="""Regenerate the subcontent for the given day.""",
#     backstory="""You're a subcontent regeneration specialist who excels at transforming existing subcontent into fresh, engaging material. Your goal is to revitalize the subcontent theme and create compelling subcontent for day. The content regenrated in this format:
#      - subcontent- If subcontent is regenrate only regenrate teh subcontent of the day.
#      - Do not include any JSON formatting, extra newlines, or additional metadata.""",
#     llm="gpt-4o-mini",
#     memory=True,
#     verbose=True,
#     tools=[],
#     allow_delegation=True
# )




# # regenrate_subcontent_agent = Agent(
# #     role="Subcontent Regenerator",
# #     goal="Regenerate the subcontent for the given day.",
# #     backstory="""You're a subcontent regeneration specialist who excels at transforming existing subcontent into fresh, engaging material. Your goal is to revitalize the subcontent theme and create compelling subcontent for day. The content regenrated in this format:
# #     - subcontent- If subcontent is regenrate only regenrate teh subcontent of the day.
# #     - Do not include any JSON formatting, extra newlines, or additional metadata.""",
# #     llm="gpt-4o-mini",
# #     memory=True,
# #     verbose=True,
# #     tools=[],
# #     allow_delegation=True
# # )