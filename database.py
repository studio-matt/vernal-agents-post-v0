from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import Base, Content, Agent, Task
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
    "host": os.getenv('host'),
    "user": os.getenv('user'),
    "password": os.getenv('password'),
    "database": os.getenv('database'),
}

encoded_password = quote_plus(db_config["password"])
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





import os
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, Date, String, Time, text, ForeignKey, func, distinct
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, NoSuchTableError
from sqlalchemy import inspect
from dotenv import load_dotenv
from datetime import datetime
import logging
from urllib.parse import quote_plus
import json

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
db_config = {
    "host": os.getenv('host', 'localhost'),
    "user": os.getenv('user', 'myuser'),
    "password": os.getenv('password', 'mypassword'),
    "database": os.getenv('database', 'mydatabase'),
}

encoded_password = quote_plus(db_config["password"])
DATABASE_URL = f"mysql+pymysql://{db_config['user']}:{encoded_password}@{db_config['host']}/{db_config['database']}?charset=utf8mb4"
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define campaigns table
class Campaign(Base):
    __tablename__ = 'campaigns'
    campaign_id = Column(String(100), primary_key=True)
    campaign_name = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    urls = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Define raw_data table
class RawData(Base):
    __tablename__ = 'raw_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(100), ForeignKey('campaigns.campaign_id'), nullable=False)
    campaign_name = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)
    keywords = Column(Text, nullable=True)
    query = Column(Text, nullable=False)
    urls = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    stemmed_text = Column(Text, nullable=True)
    lemmatized_text = Column(Text, nullable=True)
    stopwords_removed_text = Column(Text, nullable=True)
    persons = Column(Text, nullable=True)
    organizations = Column(Text, nullable=True)
    locations = Column(Text, nullable=True)
    dates = Column(Text, nullable=True)
    topics = Column(Text, nullable=True)
    trending_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class MachineContent(Base):
    __tablename__ = 'machine_content'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = Column(Integer, primary_key=True)
    week = Column(Integer, default=1)
    day = Column(String(20), nullable=False)  # Adjusted to match Content
    content = Column(Text, nullable=False)  # Explicit collation not needed with table-level setting
    title = Column(String(255), nullable=False)  # Match Content
    status = Column(String(20), default='pending')
    date_of_upload = Column(Date, nullable=False)  # Renamed to match endpoint usage
    platform = Column(String(50), nullable=False)  # Match Content
    file_name = Column(String(255), nullable=False)  # Match Content
    file_type = Column(String(10), nullable=False)  # Match Content
    platform_post_no = Column(String(50), nullable=False)  # Match Content
    schedule_time = Column(DateTime, nullable=False)  # Changed to DateTime to match Content
    image_url = Column(String(255), nullable=True)  # Match Content

    def __repr__(self):
        return f"<MachineContent(id={self.id}, week={self.week}, day={self.day}, platform={self.platform})>"

class DatabaseManager1:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.create_tables()

    def create_tables(self):
        try:
            Base.metadata.create_all(bind=self.engine)
            self.ensure_columns()
            logger.info("Database tables (campaigns, raw_data, machine_content) and columns ensured successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def ensure_columns(self):
        inspector = inspect(self.engine)
        
        # Campaigns table
        table_name = 'campaigns'
        try:
            existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
        except NoSuchTableError:
            logger.info(f"Table {table_name} does not exist yet.")
            existing_columns = []
        required_columns = ['campaign_id', 'campaign_name', 'query', 'urls', 'keywords', 'description', 'type', 'created_at', 'updated_at']
        for column in required_columns:
            if column not in existing_columns:
                with self.engine.connect() as connection:
                    column_type = 'DATETIME' if column in ['created_at', 'updated_at'] else 'TEXT' if column != 'type' else 'VARCHAR(50)'
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"))
                    logger.info(f"Added column {column} to {table_name}")

        # Raw_data table
        table_name = 'raw_data'
        try:
            existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
        except NoSuchTableError:
            logger.info(f"Table {table_name} does not exist yet.")
            existing_columns = []
        required_columns = [
            'id', 'campaign_id', 'campaign_name', 'type', 'keywords', 'query', 'urls', 'text', 
            'stemmed_text', 'lemmatized_text', 'stopwords_removed_text', 'persons', 
            'organizations', 'locations', 'dates', 'topics', 'trending_content', 'created_at'
        ]
        for column in required_columns:
            if column not in existing_columns:
                with self.engine.connect() as connection:
                    column_type = (
                        'INTEGER AUTO_INCREMENT' if column == 'id' else
                        'DATETIME' if column == 'created_at' else 
                        'TEXT' if column not in ['type', 'campaign_id'] else 
                        'VARCHAR(50)' if column == 'type' else 
                        'VARCHAR(100)'
                    )
                    nullable = 'NOT NULL' if column in ['id', 'campaign_id', 'campaign_name', 'query', 'urls', 'text'] else ''
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type} {nullable}"))
                    logger.info(f"Added column {column} to {table_name}")

        # Machine_content table
        table_name = 'machine_content'
        try:
            existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
        except NoSuchTableError:
            logger.info(f"Table {table_name} does not exist yet.")
            existing_columns = []
        required_columns = [
            'id', 'week', 'day', 'content', 'title', 'status', 'date_of_upload',
            'platform', 'file_name', 'file_type', 'platform_post_no', 'schedule_time', 'image_url'
        ]
        for column in required_columns:
            if column not in existing_columns:
                with self.engine.connect() as connection:
                    column_type = (
                        'INTEGER AUTO_INCREMENT' if column == 'id' else
                        'INTEGER' if column == 'week' else 
                        'DATE' if column == 'date_of_upload' else 
                        'TIME' if column == 'schedule_time' else 
                        'TEXT' if column not in ['status', 'platform', 'file_type', 'platform_post_no'] else
                        'VARCHAR(20)' if column in ['status', 'platform', 'platform_post_no'] else
                        'VARCHAR(10)'
                    )
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"))
                    logger.info(f"Added column {column} to {table_name}")

    def get_db_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def store_raw_texts(self, query: str, urls: str, processed_posts, campaign_name: str, campaign_id: str, keywords: list, description: str = None, type: str = None):
        from text_processing import ProcessedPosts
        session = next(self.get_db_session())
        try:
            # Validate inputs
            if not isinstance(urls, str):
                logger.error(f"URLs must be a string, got: {urls}")
                raise ValueError("URLs must be a comma-separated string")
            if not all(isinstance(k, str) for k in keywords):
                logger.error(f"Keywords must be a list of strings, got: {keywords}")
                raise ValueError("Keywords must be a list of strings")
            if not campaign_name:
                logger.error(f"Campaign name is empty for campaign {campaign_id}")
                campaign_name = f"Campaign {campaign_id}"  # Default name
            if not query:
                logger.error(f"Query is empty for campaign {campaign_id}")
                raise ValueError("Query is required")

            # Validate URLs format
            url_list = [url.strip() for url in urls.split(',') if url.strip()] if urls else []

            # Store campaign (unchanged)
            campaign = Campaign(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                query=query,
                urls=urls or "",
                keywords=','.join(keywords) if keywords else "",
                description=description,
                type=type or "url",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.merge(campaign)

            # Store raw_data
            for post in processed_posts.posts:
                raw_data = RawData(
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    type=type or "url",
                    keywords=','.join(keywords) if keywords else "",
                    query=query,
                    urls=urls or "",
                    text=post.text,
                    stemmed_text=post.stemmed_text,
                    lemmatized_text=post.lemmatized_text,
                    stopwords_removed_text=post.stopwords_removed_text,
                    persons=json.dumps(post.persons) if post.persons else None,
                    organizations=json.dumps(post.organizations) if post.organizations else None,
                    locations=json.dumps(post.locations) if post.locations else None,
                    dates=json.dumps(post.dates) if post.dates else None,
                    topics=json.dumps(post.topics) if post.topics and isinstance(post.topics, (list, str)) else None,
                    trending_content=None
                )
                session.add(raw_data)
            
            session.commit()
            logger.info(f"Stored campaign {campaign_id} with {len(processed_posts.posts)} raw_data entries, campaign_name: {campaign_name}, type: {type}, keywords: {keywords}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise Exception(f"Error storing raw data: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing raw texts: {e}")
            raise
        finally:
            session.close()

    def get_all_campaigns(self):
        session = next(self.get_db_session())
        try:
            campaigns = (
                session.query(
                    Campaign,
                    func.count(RawData.id).label('post_count'),
                    func.group_concat(distinct(RawData.topics)).label('all_topics')
                )
                .outerjoin(RawData, Campaign.campaign_id == RawData.campaign_id)
                .group_by(Campaign.campaign_id)
                .all()
            )
            result = []
            for campaign, post_count, all_topics in campaigns:
                topics = []
                if all_topics:
                    for topic in all_topics.split(','):
                        if topic and topic.strip():
                            try:
                                parsed_topics = json.loads(topic)
                                if isinstance(parsed_topics, list):
                                    topics.extend(t for t in parsed_topics if t)
                                elif parsed_topics:
                                    topics.append(parsed_topics)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Invalid JSON in topics for campaign {campaign.campaign_id}: {topic}, error: {e}")
                                continue
                topics = list(set(topics))

                urls = []
                if campaign.urls and campaign.urls.strip():
                    urls = [url.strip() for url in campaign.urls.split(',') if url.strip()]

                keywords = []
                if campaign.keywords and campaign.keywords.strip():
                    keywords = [kw.strip() for kw in campaign.keywords.split(',') if kw.strip()]

                result.append({
                    'id': campaign.campaign_id,
                    'name': campaign.campaign_name or "Unknown Campaign",
                    'description': campaign.description or f"Analysis for {campaign.query}",
                    'type': campaign.type or "url",
                    'urls': urls,
                    'keywords': keywords,
                    'trendingTopics': topics,
                    'createdAt': campaign.created_at.isoformat() if campaign.created_at else None,
                    'updatedAt': campaign.updated_at.isoformat() if campaign.updated_at else None
                })
            logger.info(f"Retrieved {len(result)} campaigns")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving campaigns: {e}")
            raise Exception(f"Error retrieving campaigns: {str(e)}")
        finally:
            session.close()

    def update_campaign(self, campaign_id: str, campaign_name: str, query: str, urls: str, processed_posts, keywords: list, description: str = None, type: str = None):
        session = next(self.get_db_session())
        try:
            if not isinstance(urls, str):
                logger.error(f"URLs must be a string, got: {urls}")
                raise ValueError("URLs must be a comma-separated string")
            if not all(isinstance(k, str) for k in keywords):
                logger.error(f"Keywords must be a list of strings, got: {keywords}")
                raise ValueError("Keywords must be a list of strings")
            if not campaign_name:
                logger.error(f"Campaign name is empty for campaign {campaign_id}")
                campaign_name = f"Campaign {campaign_id}"  # Default name
            if not query:
                logger.error(f"Query is empty for campaign {campaign_id}")
                raise ValueError("Query is required")

            url_list = [url.strip() for url in urls.split(',') if url.strip()]
            if not url_list:
                logger.error(f"No valid URLs provided: {urls}")
                raise ValueError("At least one valid URL is required")

            # Update campaign
            campaign = Campaign(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                query=query,
                urls=urls,
                keywords=','.join(keywords) if keywords else "",
                description=description,
                type=type or "url",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.merge(campaign)

            # Delete old raw_data
            session.query(RawData).filter(RawData.campaign_id == campaign_id).delete()

            # Store new raw_data
            for post in processed_posts.posts:
                raw_data = RawData(
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    type=type or "url",
                    keywords=','.join(keywords) if keywords else "",
                    query=query,
                    urls=urls,
                    text=post.text,
                    stemmed_text=post.stemmed_text,
                    lemmatized_text=post.lemmatized_text,
                    stopwords_removed_text=post.stopwords_removed_text,
                    persons=json.dumps(post.persons) if post.persons else None,
                    organizations=json.dumps(post.organizations) if post.organizations else None,
                    locations=json.dumps(post.locations) if post.locations else None,
                    dates=json.dumps(post.dates) if post.dates else None,
                    topics=json.dumps(post.topics) if post.topics and isinstance(post.topics, (list, str)) else None,
                    trending_content=None
                )
                session.add(raw_data)
            
            session.commit()
            logger.info(f"Updated campaign {campaign_id} with {len(processed_posts.posts)} raw_data entries, campaign_name: {campaign_name}, type: {type}, keywords: {keywords}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise Exception(f"Error updating campaign: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating campaign: {e}")
            raise
        finally:
            session.close()

    def delete_campaign(self, campaign_id: str):
        session = next(self.get_db_session())
        try:
            campaign = session.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found")
                raise Exception(f"Campaign {campaign_id} not found")

            session.query(RawData).filter(RawData.campaign_id == campaign_id).delete()
            session.query(Campaign).filter(Campaign.campaign_id == campaign_id).delete()
            session.commit()
            logger.info(f"Deleted campaign {campaign_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise Exception(f"Error deleting campaign: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error: {e}")
            raise
        finally:
            session.close()

    def get_raw_data_by_campaign(self, campaign_id: str):
        session = next(self.get_db_session())
        try:
            logger.debug(f"Querying raw_data for campaign_id: {campaign_id}")
            raw_data_entries = session.query(RawData, Campaign.description).join(
                Campaign,
                RawData.campaign_id == Campaign.campaign_id
            ).filter(
                RawData.campaign_id == campaign_id
            ).all()
            logger.debug(f"Found {len(raw_data_entries)} entries for campaign_id: {campaign_id}")
            
            result = []
            for entry, description in raw_data_entries:
                urls = []
                if entry.urls and entry.urls.strip():
                    urls = [url.strip() for url in entry.urls.split(',') if url.strip()]
                
                keywords = []
                if entry.keywords and entry.keywords.strip():
                    keywords = [kw.strip() for kw in entry.keywords.split(',') if kw.strip()]
                
                topics = []
                if entry.topics and entry.topics.strip():
                    try:
                        parsed_topics = json.loads(entry.topics)
                        if isinstance(parsed_topics, list):
                            topics = parsed_topics
                        else:
                            topics = [parsed_topics]
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in topics for campaign {campaign_id}: {entry.topics}, error: {e}")
                
                raw_data_entry = {
                    'id': entry.id,
                    'campaign_id': entry.campaign_id,
                    'campaign_name': entry.campaign_name or f"Campaign {entry.campaign_id}",
                    'type': entry.type or "url",
                    'keywords': keywords,
                    'query': entry.query,
                    'urls': urls,
                    'text': entry.text,
                    'stemmed_text': entry.stemmed_text,
                    'lemmatized_text': entry.lemmatized_text,
                    'stopwords_removed_text': entry.stopwords_removed_text,
                    'persons': json.loads(entry.persons) if entry.persons else [],
                    'organizations': json.loads(entry.organizations) if entry.organizations else [],
                    'locations': json.loads(entry.locations) if entry.locations else [],
                    'dates': json.loads(entry.dates) if entry.dates else [],
                    'topics': topics,
                    'trending_content': json.loads(entry.trending_content) if entry.trending_content else None,
                    'created_at': entry.created_at.isoformat() if entry.created_at else None,
                    'description': description if description else ""
                }
                result.append(raw_data_entry)
                logger.debug(f"Processed raw_data entry: {raw_data_entry}")
            
            logger.info(f"Retrieved {len(result)} raw data entries for campaign {campaign_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving raw data for campaign {campaign_id}: {e}")
            raise Exception(f"Error retrieving raw data: {str(e)}")
        finally:
            session.close()

    def check_campaign_exists(self, campaign_id: str):
        session = next(self.get_db_session())
        try:
            campaign = session.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            exists = campaign is not None
            logger.debug(f"Campaign {campaign_id} exists: {exists}")
            return exists
        except SQLAlchemyError as e:
            logger.error(f"Database error checking campaign {campaign_id}: {e}")
            raise Exception(f"Error checking campaign: {str(e)}")
        finally:
            session.close()

    def get_campaign_details(self, campaign_id: str):
        session = next(self.get_db_session())
        try:
            campaign = session.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found")
                return None

            logger.debug(f"Campaign {campaign_id} raw fields: campaign_name={campaign.campaign_name}, type={campaign.type}, keywords={campaign.keywords}, urls={campaign.urls}")

            urls = []
            if campaign.urls and campaign.urls.strip():
                urls = [url.strip() for url in campaign.urls.split(',') if url.strip()]

            keywords = []
            if campaign.keywords and campaign.keywords.strip():
                keywords = [kw.strip() for kw in campaign.keywords.split(',') if kw.strip()]

            all_topics = session.query(func.group_concat(distinct(RawData.topics)))\
                .filter(RawData.campaign_id == campaign_id).scalar()
            topics = []
            if all_topics:
                for topic in all_topics.split(','):
                    if topic and topic.strip():
                        try:
                            parsed_topics = json.loads(topic)
                            if isinstance(parsed_topics, list):
                                topics.extend(t for t in parsed_topics if t)
                            elif parsed_topics:
                                topics.append(parsed_topics)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in topics for campaign {campaign_id}: {topic}, error: {e}")
                            continue
            topics = list(set(topics))

            result = {
                'name': campaign.campaign_name or "Unknown Campaign",
                'type': campaign.type or "url",
                'urls': urls,
                'keywords': keywords,
                'trendingTopics': topics
            }
            logger.info(f"Returning campaign details for {campaign_id}: {result}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving campaign details for {campaign_id}: {e}")
            return None
        finally:
            session.close()