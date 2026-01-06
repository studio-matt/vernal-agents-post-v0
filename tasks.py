from crewai import Task
# from tools import pdf_tool
# import tools
from tools import  PLATFORM_LIMITS
from agents import script_research_agent, qc_agent, script_rewriter_agent , regenrate_content_agent, regenrate_subcontent_agent, linkedin_agent, twitter_agent, facebook_agent, instagram_agent, tiktok_agent, youtube_agent, wordpress_agent
from database import DatabaseManager
from sqlalchemy.orm import Session
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re
from guardrails.sanitize import sanitize_user_text, detect_prompt_injection
import logging


load_dotenv()

logger = logging.getLogger(__name__)

db_manager = DatabaseManager()

# Define tasks with attributes fetched directly from the database
script_research_task = Task(
    description=db_manager.get_task_by_name("script_research_task").description,
    expected_output=db_manager.get_task_by_name("script_research_task").expected_output,
    tools=[],
    agent=script_research_agent
)

qc_task = Task(
    description=db_manager.get_task_by_name("qc_task").description,
    expected_output=db_manager.get_task_by_name("qc_task").expected_output,
    tools=[],
    agent=qc_agent
)

script_rewriter_task = Task(
    description=db_manager.get_task_by_name("script_rewriter_task").description,
    expected_output=db_manager.get_task_by_name("script_rewriter_task").expected_output,
    tools=[],
    agent=script_rewriter_agent
)

regenrate_content_task = Task(
    description=db_manager.get_task_by_name("regenrate_content_task").description,
    expected_output=db_manager.get_task_by_name("regenrate_content_task").expected_output,
    tools=[],
    agent=regenrate_content_agent
)

regenrate_subcontent_task = Task(
    description=db_manager.get_task_by_name("regenrate_subcontent_task").description,
    expected_output=db_manager.get_task_by_name("regenrate_subcontent_task").expected_output,
    tools=[],
    agent=regenrate_subcontent_agent
)

linkedin_task = Task(
    description=db_manager.get_task_by_name("linkedin_task").description,
    expected_output=db_manager.get_task_by_name("linkedin_task").expected_output,
    tools=[],
    agent=linkedin_agent
)

twitter_task = Task(
    description=db_manager.get_task_by_name("twitter_task").description,
    expected_output=db_manager.get_task_by_name("twitter_task").expected_output,
    tools=[],
    agent=twitter_agent
)

facebook_task = Task(
    description=db_manager.get_task_by_name("facebook_task").description,
    expected_output=db_manager.get_task_by_name("facebook_task").expected_output,
    tools=[],
    agent=facebook_agent
)

instagram_task = Task(
    description=db_manager.get_task_by_name("instagram_task").description,
    expected_output=db_manager.get_task_by_name("instagram_task").expected_output,
    tools=[],
    agent=instagram_agent
)

tiktok_task = Task(
    description=db_manager.get_task_by_name("tiktok_task").description,
    expected_output=db_manager.get_task_by_name("tiktok_task").expected_output,
    tools=[],
    agent=tiktok_agent
)

youtube_task = Task(
    description=db_manager.get_task_by_name("youtube_task").description,
    expected_output=db_manager.get_task_by_name("youtube_task").expected_output,
    tools=[],
    agent=youtube_agent
)

wordpress_task = Task(
    description=db_manager.get_task_by_name("wordpress_task").description,
    expected_output=db_manager.get_task_by_name("wordpress_task").expected_output,
    tools=[],
    agent=wordpress_agent
)



client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_prompt(text, week, days_list):
    """Create a prompt for the OpenAI model with description and JSON expected output."""
    m = len(days_list)
    days_str = ", ".join(days_list)

    # description = db_manager.get_task_by_name("script_research_task").description
    description_template = db_manager.get_task_by_name("script_research_task").description
    expected_output_template = db_manager.get_task_by_name("script_research_task").expected_output
    description = description_template.format(week=week, m=m, days_str=days_str)
    expected_output = expected_output_template.format(week=week)
    # Part 1: Description
#     description = f"""
# You are given text extracted from a PDF document. Your task is to:
# 1. Identify exactly 52 distinct topics from the text.
# 2. Rank these topics from 1 to 52 based on their frequency and importance (1 being the most prominent).
# 3. Select the topic ranked at position {week} for Week {week}.
# 4. For this topic, generate {m} subtopics corresponding to the days: {days_str}.
# 5. Provide one relevant quote from the text for the main topic and each subtopic.   
# 6. Ensure all topics, subtopics, and quotes are derived directly from the provided text.
# 7. Output the response as a valid JSON object, strictly following the structure shown in the Expected Output section.
# 8. Do not include any additional text, comments, or explanations outside the JSON object.
# """

    # expected_output = db_manager.get_task_by_name("script_research_task").expected_output
    # Part 2: Expected Output
#     expected_output = f"""
# Expected Output:
# Provide your response as a valid JSON object in the exact structure below, replacing placeholders with the actual content derived from the text. Do not deviate from this structure or add any extra content.

# {{
#   "Week {week}": {{
#     "topic": "[Insert Main Topic for Week {week} Here]",
#     "quote": "[Insert Quote for Main Topic Here]",
#     "content_by_days": {{
# """
    for j, day in enumerate(days_list, 1):
        expected_output += f'      "{day.capitalize()}": {{\n'
        expected_output += f'        "day": "{day.capitalize()}",\n'
        expected_output += f'        "subtopic": "[Insert Subtopic {week}.{j} Here]",\n'
        expected_output += f'        "quote": "[Insert Quote for Subtopic {week}.{j} Here]"\n'
        expected_output += f'      }}{"," if j < m else ""}\n'
    expected_output += f'    }}\n'
    expected_output += f'  }}\n'
    expected_output += f"}}"

    # Combine both parts with the text
    prompt = f"{description}\n{expected_output}\n\nHere is the extracted text from the PDF:\n{text}\n\nNow, analyze the text and provide the output as a valid JSON object in the specified format."

    return prompt

def analyze_text(prompt):
    """Send the prompt to the OpenAI model and return the parsed JSON response."""
    try:
        # Guardrails: sanitize prompt + basic prompt-injection heuristics
        prompt = sanitize_user_text(prompt, max_len=12000)
        is_injection, matched = detect_prompt_injection(prompt)
        block = os.getenv("GUARDRAILS_BLOCK_INJECTION", "0").strip() == "1"
        if is_injection:
            msg = f"Potential prompt injection detected: {matched}"
            if block:
                raise ValueError(msg)
            logger.warning(msg)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant tasked with analyzing documents and producing JSON output."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        output = response.choices[0].message.content.strip()
        # Try to parse the output as JSON
        try:
            parsed_output = json.loads(output)
            return parsed_output
        except json.JSONDecodeError:
            # Try to extract JSON from code block
            json_match = re.search(r'```json\n([\s\S]*?)\n```', output)
            if json_match:
                return json.loads(json_match.group(1))
            raise ValueError("Model output is not valid JSON")
    except Exception as e:
        raise Exception(f"Error analyzing text with OpenAI: {str(e)}")