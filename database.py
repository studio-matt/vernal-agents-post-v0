from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import Base, Content, Agent, Task, AuthorPersonality
import os
from datetime import datetime
import pymysql
from urllib.parse import quote_plus
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union
from sqlalchemy.orm import joinedload
from crewai import Agent as CrewAgent, Task as CrewTask
from sqlalchemy.orm import Session

load_dotenv()

db_config = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME'),
}

encoded_password = quote_plus(str(db_config["password"]))
DATABASE_URL = f"mysql+pymysql://{db_config['user']}:{encoded_password}@{db_config['host']}/{db_config['database']}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        self.create_tables()

    def create_tables(self):
        """Create tables if they do not exist."""
        Base.metadata.create_all(self.engine)

    def get_db_session(self):
        """Yield a database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # # Content methods
    # def store_content(self, content_data: dict, file_name: str, file_type: str):
    #     """Store generated content in the database."""
    #     session = next(self.get_db_session())
    #     stored_contents = []

    #     try:
    #         for platform, posts in content_data.items():
    #             for post in posts:
    #                 week_day_parts = post['week_day'].split(' - ')
    #                 week = int(week_day_parts[0].split(' ')[1])
    #                 day = week_day_parts[1]

    #                 content_entry = Content(
    #                     week=week,
    #                     day=day,
    #                     content=str(post['content']),
    #                     title=post['title'],
    #                     status="pending",
    #                     date_upload=datetime.now().date(),
    #                     platform=platform.upper(),
    #                     file_name=file_name,
    #                     file_type=file_type
    #                 )
    #                 session.add(content_entry)
    #                 stored_contents.append(content_entry)

    #         session.commit()
    #         return stored_contents

    #     except SQLAlchemyError as e:
    #         session.rollback()
    #         raise Exception(f"Error storing content in database: {str(e)}")
    #     finally:
    #         session.close()

    def store_content(self, content_data: dict, file_name: str, file_type: str):
        """Store generated content in the database."""
        session = next(self.get_db_session())
        stored_contents = []

        try:
            for platform, posts in content_data.items():
                for post in posts:
                    schedule_time = post['schedule_time']
                    content_entry = Content(
                        week=post['week'],
                        day=post['day'],
                        content=post['content'],
                        title=post['title'],
                        status="pending",
                        date_upload=datetime.now().date(),  # Generation date; could use schedule_time.date()
                        platform=platform.upper(),
                        file_name=file_name,
                        file_type=file_type,
                        platform_post_no=post['platform_post_no'],
                        schedule_time=schedule_time,
                        image_url=None
                    )
                    session.add(content_entry)
                    stored_contents.append(content_entry)

            session.commit()
            return stored_contents

        except SQLAlchemyError as e:
            session.rollback()
            raise Exception(f"Error storing content in database: {str(e)}")
        finally:
            session.close()
            
    def create_agent(self, name: str, role: str, goal: str, backstory: str, llm: str = "gpt-4o-mini") -> Agent:
        session = next(self.get_db_session())
        try:
            agent = Agent(name=name, role=role, goal=goal, backstory=backstory, llm=llm)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent
        except SQLAlchemyError as e:
            session.rollback()
            raise Exception(f"Error creating agent: {str(e)}")
        finally:
            session.close()

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        session = next(self.get_db_session())
        try:
            return session.query(Agent).filter(Agent.name == name).first()
        except SQLAlchemyError as e:
            raise Exception(f"Error fetching agent: {str(e)}")
        finally:
            session.close()

    def get_task_by_name(self, name: str) -> Optional[Task]:
        session = next(self.get_db_session())
        try:
            return session.query(Task).filter(Task.name == name).first()
        except SQLAlchemyError as e:
            raise Exception(f"Error fetching task: {str(e)}")
        finally:
            session.close()

    def initialize_from_code(self, agents_dict: Dict, tasks_dict: Dict) -> Dict:
        session = next(self.get_db_session())
        stats = {"agents_created": 0, "agents_updated": 0, "tasks_created": 0, "tasks_updated": 0, "errors": []}
        try:
            agent_name_to_id = {}
            # Process agents
            for name, agent_data in agents_dict.items():
                try:
                    role = self._extract_string_content(agent_data.get("role", ""))
                    goal = self._extract_string_content(agent_data.get("goal", ""))
                    backstory = self._extract_string_content(agent_data.get("backstory", ""))
                    llm = agent_data.get("llm", "gpt-4o-mini")
                    
                    # Check if agent exists
                    agent = session.query(Agent).filter(Agent.name == name).first()
                    if agent:
                        # Update existing agent
                        agent.role = role
                        agent.goal = goal
                        agent.backstory = backstory
                        agent.llm = llm
                        stats["agents_updated"] += 1
                    else:
                        # Create new agent
                        agent = Agent(name=name, role=role, goal=goal, backstory=backstory, llm=llm)
                        session.add(agent)
                        stats["agents_created"] += 1
                    session.flush()
                    agent_name_to_id[name] = agent.id
                except Exception as e:
                    stats["errors"].append(f"Error processing agent {name}: {str(e)}")

            # Process tasks
            for name, task_data in tasks_dict.items():
                try:
                    description = self._extract_string_content(task_data.get("description", ""))
                    expected_output = self._extract_string_content(task_data.get("expected_output", ""))
                    agent_name = task_data.get("agent", "")
                    agent_id = agent_name_to_id.get(agent_name) if agent_name else None
                    
                    # Check if task exists
                    task = session.query(Task).filter(Task.name == name).first()
                    if task:
                        # Update existing task
                        task.description = description
                        task.expected_output = expected_output
                        task.agent_id = agent_id
                        stats["tasks_updated"] += 1
                    else:
                        # Create new task
                        task = Task(name=name, description=description, expected_output=expected_output, agent_id=agent_id)
                        session.add(task)
                        stats["tasks_created"] += 1
                except Exception as e:
                    stats["errors"].append(f"Error processing task {name}: {str(e)}")

            session.commit()
            return stats
        except SQLAlchemyError as e:
            session.rollback()
            raise Exception(f"Error initializing from code: {str(e)}")
        finally:
            session.close()

    def _extract_string_content(self, text: str) -> str:
        if not text:
            return ""
        if not (text.startswith('f"""') or text.startswith('"""') or text.startswith("f'''") or text.startswith("'''")):
            return text
        if text.startswith('f'):
            text = text[1:]
        if text.startswith('"""') and text.endswith('"""'):
            return text[3:-3]
        elif text.startswith("'''") and text.endswith("'''"):
            return text[3:-3]
        return text
    
    

def get_crewai_agent(name: str, session: Session) -> CrewAgent:
    """Fetch an agent from the database and return a crewai.Agent object."""
    db_agent = session.query(Agent).filter(Agent.name == name).first()
    if not db_agent:
        raise ValueError(f"Agent {name} not found in database")
    return CrewAgent(
        role=db_agent.role,              # Use database value
        goal=db_agent.goal,              # Use database value
        backstory=db_agent.backstory,    # Use database value
        llm=db_agent.llm or "gpt-4o-mini",
        memory=True,
        verbose=True,
        tools=[],
        allow_delegation=True
    )

def get_crewai_task(name: str, session: Session) -> CrewTask:
    """Fetch a task from the database and return a crewai.Task object."""
    db_task = session.query(Task).filter(Task.name == name).first()
    if not db_task:
        raise ValueError(f"Task {name} not found in database")
    agent = get_crewai_agent(db_task.agent_name, session) if db_task.agent_name else None
    return CrewTask(
        description=db_task.description,      # Use database value
        expected_output=db_task.expected_output,  # Use database value
        agent=agent,
        tools=[]
    )






# Initialize database manager instance
db_manager = DatabaseManager()
