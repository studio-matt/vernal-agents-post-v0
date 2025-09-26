# from sqlalchemy import Column, Integer, String, Date, SmallInteger, Text
# from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base = declarative_base()

class PlatformEnum(str, enum.Enum):  # ✅ Store as string
    LINKEDIN = "LINKEDIN"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TWITTER = "TWITTER"
    WORDPRESS = "WORDPRESS"
    YOUTUBE = "YOUTUBE"
    TIKTOK = "TIKTOK"

    @classmethod
    def _missing_(cls, value):
        """✅ Allow case-insensitive lookup"""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return None

class ContentStatus(str, enum.Enum):  # ✅ Store as string
    pending = "pending"
    uploaded = "uploaded"



from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()

# class Content(Base):
#     __tablename__ = 'content'
#     __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     week = Column(Integer, nullable=False)
#     day = Column(String(20), nullable=False)
#     content = Column(Text, nullable=False)
#     title = Column(String(255), nullable=False)
#     status = Column(String(20), default="pending")
#     date_upload = Column(Date, nullable=False)
#     platform = Column(String(50), nullable=False)
#     file_name = Column(String(255), nullable=False)
#     file_type = Column(String(10), nullable=False)

#     def __repr__(self):
#         return f"<Content(id={self.id}, week={self.week}, day={self.day}, platform={self.platform})>"
# # Enum for platforms
# class PlatformEnum(str, Enum):
#     LINKEDIN = "linkedin"
#     TWITTER = "twitter"
#     INSTAGRAM = "instagram"
#     FACEBOOK = "facebook"

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    contact = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    platform_connections = relationship("PlatformConnection", back_populates="user")
    contents = relationship("Content", back_populates="user")
    openai_key = Column(String(255), nullable=True)
    midjourney_key = Column(String(255), nullable=True)
    elevenlabs_key = Column(String(255), nullable=True)
    claude_key = Column(String(255), nullable=True)

class PlatformConnection(Base):
    __tablename__ = 'platform_connection'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, default=datetime.now())
    disconnected_at = Column(DateTime, nullable=True)
    platform_user_id = Column(Text, nullable=True)
    user = relationship("User", back_populates="platform_connections")

class OTP(Base):
    __tablename__ = 'otp'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User")


class Content(Base):
    __tablename__ = 'content'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    week = Column(Integer, nullable=False)
    day = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    date_upload = Column(DateTime, nullable=False)
    platform = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    platform_post_no = Column(String(50), nullable=False)
    schedule_time = Column(DateTime, nullable=False)
    image_url = Column(String(255), nullable=True)
    user = relationship("User", back_populates="contents")    

    def __repr__(self):
        return f"<Content(id={self.id}, week={self.week}, day={self.day}, platform={self.platform})>"



class Agent(Base):
    __tablename__ = 'agent'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    role = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    backstory = Column(Text, nullable=False)
    llm = Column(String(50), nullable=False, default="gpt-4o-mini")
    tasks = relationship("Task", back_populates="agent")

class Task(Base):
    __tablename__ = 'task'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    agent_id = Column(Integer, ForeignKey('agent.id'))
    agent = relationship("Agent", back_populates="tasks")


# Assuming PlatformEnum is already defined as shown in your code
class StateToken(Base):
    __tablename__ = 'state_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    state = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    oauth_token = Column(String(255), nullable=True)  # For Twitter OAuth
    oauth_token_secret = Column(String(255), nullable=True)
    user = relationship("User")