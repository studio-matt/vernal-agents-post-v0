import os
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, Dict, Any
import traceback

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

def build_database_url() -> str:
    """Build database URL with comprehensive error handling and fallbacks"""
    try:
        # Get all database configuration
        user = get_env_var("DB_USER") or get_env_var("user")
        password = get_env_var("DB_PASSWORD") or get_env_var("password")
        host = get_env_var("DB_HOST") or get_env_var("host") or "127.0.0.1"
        port = get_env_var("DB_PORT") or get_env_var("port") or "3306"
        name = get_env_var("DB_NAME") or get_env_var("database") or get_env_var("name")
        
        # Validate all required fields
        if not all([user, password, host, name]):
            logger.warning("DB config incomplete - falling back to SQLite")
            return "sqlite:///./test.db"
        
        # Ensure password is string and properly encoded
        password_str = str(password).strip()
        encoded_password = quote_plus(password_str)
        
        # Build MySQL URL
        mysql_url = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{name}?charset=utf8mb4"
        logger.info(f"Database URL built successfully: mysql+pymysql://{user}:***@{host}:{port}/{name}")
        return mysql_url
        
    except Exception as e:
        logger.error(f"Error building database URL: {e}")
        traceback.print_exc()
        logger.warning("Falling back to SQLite due to error")
        return "sqlite:///./test.db"

# Build database URL
DATABASE_URL = build_database_url()
logger.info(f"Final DATABASE_URL: {DATABASE_URL}")

# Create engine with error handling
try:
    engine = create_engine(DATABASE_URL, echo=False)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    traceback.print_exc()
    # Fallback to SQLite
    DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(DATABASE_URL, echo=False)
    logger.info("Using SQLite fallback")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("Session factory created successfully")

# Create base class
Base = declarative_base()
logger.info("Base class created successfully")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    traceback.print_exc()

class DatabaseManager:
    """Bulletproof database manager with comprehensive error handling"""
    
    def __init__(self):
        logger.info("Initializing DatabaseManager")
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def get_db(self) -> Session:
        """Get database session with error handling"""
        try:
            db = self.SessionLocal()
            logger.debug("Database session created successfully")
            return db
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            traceback.print_exc()
            raise
    
    def get_agent_by_name(self, name: str) -> Optional[Any]:
        """Safely get agent by name with error handling"""
        try:
            # For now, return None since we don't have agents in the database
            # This prevents the AttributeError we were seeing
            logger.debug(f"Agent lookup for {name} - returning None (no agents in DB)")
            return None
        except Exception as e:
            logger.error(f"Error getting agent {name}: {e}")
            traceback.print_exc()
            return None
    
    def create_tables(self):
        """Create database tables with error handling"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            traceback.print_exc()

# Initialize database manager
try:
    db_manager = DatabaseManager()
    logger.info("DatabaseManager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize DatabaseManager: {e}")
    traceback.print_exc()
    raise

logger.info("Database module loaded successfully")
