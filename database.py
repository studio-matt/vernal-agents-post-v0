import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# ---- Import Base and any models that actually exist (optional imports) ----
Base = None
Agent = Task = Campaign = RawData = MachineContent = AuthorPersonality = None

# We avoid hard failures if some models aren't present
try:
    import models as _models
    Base = getattr(_models, "Base", None)
    Agent = getattr(_models, "Agent", None)
    Task = getattr(_models, "Task", None)
    Campaign = getattr(_models, "Campaign", None)
    RawData = getattr(_models, "RawData", None)
    MachineContent = getattr(_models, "MachineContent", None)
    AuthorPersonality = getattr(_models, "AuthorPersonality", None)
    if Base is None:
        raise ImportError("models.Base not found")
except Exception as e:
    raise ImportError(f"Failed importing models: {e}")

# ---- Build DATABASE_URL from env (systemd injects these) ----
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("DB_USER") or os.getenv("user")
    password = os.getenv("DB_PASSWORD") or os.getenv("password")
    host = os.getenv("DB_HOST") or os.getenv("host") or "127.0.0.1"
    port = os.getenv("DB_PORT") or "3306"
    name = os.getenv("DB_NAME") or os.getenv("database")
    if not all([user, password, host, name]):
        raise RuntimeError("DB config incomplete. Set DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME.")
    DATABASE_URL = f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{name}?charset=utf8mb4"

# ---- Engine & Session ----
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create tables for whatever models are defined on Base
Base.metadata.create_all(bind=engine)

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_db_session(self) -> Session:
        return self.SessionLocal()

    # -------- Agents (only if Agent model exists) --------
    def create_agent(self, name: str, role: str, goal: str, backstory: str, llm: str = "gpt-4o-mini"):
        if Agent is None:
            raise RuntimeError("Agent model is not available.")
        session = self.SessionLocal()
        try:
            agent = Agent(name=name, role=role, goal=goal, backstory=backstory, llm=llm)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_agent_by_name(self, name: str):
        if Agent is None:
            return None
        session = self.SessionLocal()
        try:
            return session.query(Agent).filter(Agent.name == name).first()
        finally:
            session.close()

    # -------- Tasks (only if Task model exists) --------
    def create_task(self, name: str, description: str, expected_output: str, agent_name: str | None = None):
        if Task is None:
            raise RuntimeError("Task model is not available.")
        session = self.SessionLocal()
        try:
            agent_id = None
            if Agent is not None and agent_name:
                a = session.query(Agent).filter(Agent.name == agent_name).first()
                agent_id = a.id if a else None
            task = Task(name=name, description=description, expected_output=expected_output, agent_id=agent_id)
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_task_by_name(self, name: str):
        if Task is None:
            return None
        session = self.SessionLocal()
        try:
            return session.query(Task).filter(Task.name == name).first()
        finally:
            session.close()

# Legacy alias some code expects
DatabaseManager1 = DatabaseManager

# Re-export only what truly exists
__all__ = ["engine", "SessionLocal", "Base", "DatabaseManager", "DatabaseManager1"]
for _n in ["Agent", "Task", "Campaign", "RawData", "MachineContent", "AuthorPersonality"]:
    if globals().get(_n) is not None:
        __all__.append(_n)
