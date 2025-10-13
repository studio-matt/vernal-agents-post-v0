from dotenv import load_dotenv
load_dotenv()

import os
import logging
import traceback
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime

try:
    from models import Base, Agent, Task
    logger = logging.getLogger(__name__)
    logger.info("Successfully imported Agent and Task models")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import models: {e}")
    raise

logging.basicConfig(level=logging.DEBUG)

def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(key) or default
    if required and not value:
        logger.error(f"Required environment variable {key} is missing!")
        return None
    if value:
        logger.debug(f"Environment variable {key} loaded successfully")
    else:
        logger.warning(f"Environment variable {key} not set, using default: {default}")
    return value

def build_database_url() -> str:
    try:
        user = get_env_var("DB_USER") or get_env_var("user")
        password = get_env_var("DB_PASSWORD") or get_env_var("password")
        host = get_env_var("DB_HOST") or get_env_var("host") or "127.0.0.1"
        port = get_env_var("DB_PORT") or get_env_var("port") or "3306"
        name = get_env_var("DB_NAME") or get_env_var("database") or get_env_var("name")
        
        if not all([user, password, host, name]):
            logger.warning("DB config incomplete - falling back to SQLite")
            return "sqlite:///./test.db"
        
        password_str = str(password).strip()
        encoded_password = quote_plus(password_str)
        mysql_url = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{name}?charset=utf8mb4"
        logger.info(f"Database URL built: mysql+pymysql://{user}:***@{host}:{port}/{name}")
        return mysql_url
    except Exception as e:
        logger.error(f"Error building database URL: {e}")
        traceback.print_exc()
        return "sqlite:///./test.db"

DATABASE_URL = build_database_url()
logger.info(f"Final DATABASE_URL: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    traceback.print_exc()
    DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(DATABASE_URL, echo=False)
    logger.info("Using SQLite fallback")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("Session factory created successfully")

try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    traceback.print_exc()

class DatabaseManager:
    def __init__(self):
        logger.info("Initializing DatabaseManager")
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_db(self) -> Session:
        try:
            db = self.SessionLocal()
            logger.debug("Database session created successfully")
            return db
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            traceback.print_exc()
            raise
    
    def get_db_session(self) -> Session:
        return self.get_db()
    
    def create_agent(self, name: str, role: str, goal: str, backstory: str, llm: str = "gpt-4o-mini"):
        session = self.SessionLocal()
        try:
            agent = Agent(name=name, role=role, goal=goal, backstory=backstory, llm=llm)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            logger.info(f"Created agent: {name}")
            return agent
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create agent: {e}")
            raise
        finally:
            session.close()
    
    def get_agent_by_name(self, name: str) -> Optional[Any]:
        session = self.SessionLocal()
        try:
            agent = session.query(Agent).filter(Agent.name == name).first()
            if agent:
                logger.debug(f"Found agent: {name}")
            else:
                logger.debug(f"Agent not found: {name}")
            return agent
        except Exception as e:
            logger.error(f"Error getting agent {name}: {e}")
            traceback.print_exc()
            return None
        finally:
            session.close()
    
    def create_task(self, name: str, description: str, expected_output: str, agent_name: Optional[str] = None):
        session = self.SessionLocal()
        try:
            agent_id = None
            if agent_name:
                agent = session.query(Agent).filter(Agent.name == agent_name).first()
                agent_id = agent.id if agent else None
            task = Task(name=name, description=description, expected_output=expected_output, agent_id=agent_id)
            session.add(task)
            session.commit()
            session.refresh(task)
            logger.info(f"Created task: {name}")
            return task
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create task: {e}")
            raise
        finally:
            session.close()
    
    def get_task_by_name(self, name: str):
        session = self.SessionLocal()
        try:
            return session.query(Task).filter(Task.name == name).first()
        finally:
            session.close()
    
    def get_all_campaigns(self) -> list:
        try:
            logger.debug("Campaigns lookup - returning empty list")
            return []
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return []
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Any]:
        try:
            logger.debug("Campaign creation - returning None")
            return None
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return None
    
    def create_tables(self):
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

try:
    db_manager = DatabaseManager()
    logger.info("DatabaseManager initialized")
except Exception as e:
    logger.error(f"Failed to initialize DatabaseManager: {e}")
    raise

# Additional models that were missing
class Campaign(Base):
    """Campaign model for content campaigns"""
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
class RawData(Base):
    """Raw data model for storing unprocessed content"""
    __tablename__ = "raw_data"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    source = Column(String(255))
    platform = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
class MachineContent(Base):
    """Machine-generated content model"""
    __tablename__ = "machine_content"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    content = Column(Text)
    platform = Column(String(100))
    status = Column(String(50), default="generated")
    created_at = Column(DateTime, default=datetime.utcnow)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    raw_data_id = Column(Integer, ForeignKey("raw_data.id"))

DatabaseManager1 = DatabaseManager
__all__ = ["engine", "SessionLocal", "Base", "DatabaseManager", "DatabaseManager1", "Agent", "Task", "Campaign", "RawData", "MachineContent", "db_manager"]
logger.info("Database module loaded")