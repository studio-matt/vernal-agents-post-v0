# from sqlalchemy import Column, Integer, String, Date, SmallInteger, Text
# from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

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
    is_admin = Column(Boolean, default=False, nullable=False)  # Admin role flag
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
    campaign_id = Column(String(255), nullable=True)  # Link to campaign
    is_draft = Column(Boolean, default=True)  # True until scheduled/published
    can_edit = Column(Boolean, default=True)  # True until sent out
    knowledge_graph_location = Column(Text, nullable=True)  # Knowledge graph node/location this content is based on
    parent_idea = Column(Text, nullable=True)  # Parent idea this content supports
    landing_page_url = Column(String(500), nullable=True)  # Landing page URL this content drives traffic to
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

class AuthorPersonality(Base):
    __tablename__ = 'author_personalities'
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = Column(String(255), nullable=True)  # Optional: for user-specific personalities
    
    def __repr__(self):
        return f"<AuthorPersonality(id={self.id}, name={self.name})>"

class BrandPersonality(Base):
    __tablename__ = 'brand_personalities'
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    guidelines = Column(Text, nullable=True)  # Brand voice guidelines text
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = Column(String(255), nullable=True)  # Optional: for user-specific personalities
    
    def __repr__(self):
        return f"<BrandPersonality(id={self.id}, name={self.name})>"

class Campaign(Base):
    """Campaign model for content campaigns"""
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String(255), unique=True, index=True)
    campaign_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    query = Column(Text, nullable=True)
    type = Column(String(50), default="keyword")
    keywords = Column(Text, nullable=True)  # Comma-separated keywords
    urls = Column(Text, nullable=True)  # Comma-separated URLs
    trending_topics = Column(Text, nullable=True)  # Comma-separated topics
    topics = Column(Text, nullable=True)  # Comma-separated topics
    status = Column(String(50), default="INCOMPLETE")  # Campaign status: INCOMPLETE, PROCESSING, READY_TO_ACTIVATE
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    # Settings stored as JSON in Text columns (MySQL doesn't have native JSON type in older versions)
    extraction_settings_json = Column(Text, nullable=True)  # JSON string for extractionSettings
    preprocessing_settings_json = Column(Text, nullable=True)  # JSON string for preprocessingSettings
    entity_settings_json = Column(Text, nullable=True)  # JSON string for entitySettings
    modeling_settings_json = Column(Text, nullable=True)  # JSON string for modelingSettings
    # Campaign scheduling and planning fields
    scheduling_settings_json = Column(Text, nullable=True)  # JSON string for scheduling: {weeks, posts_per_day, posts_per_week, start_date, day_frequency, post_frequency_type, post_frequency_value}
    campaign_plan_json = Column(Text, nullable=True)  # JSON string for campaign plan: {weeks: [{week_num, parent_ideas: [{idea, children: [...]}], knowledge_graph_locations: [...]}]}
    content_queue_items_json = Column(Text, nullable=True)  # JSON string for checked items from content queue
    custom_keywords_json = Column(Text, nullable=True)  # JSON string for custom keywords/ideas: ["keyword1", "keyword2"]
    personality_settings_json = Column(Text, nullable=True)  # JSON string for personality settings: {author_personality_id: string, brand_personality_id: string}
    # Site Builder campaign fields
    site_base_url = Column(String(500), nullable=True)  # Base URL for Site Builder campaigns
    target_keywords_json = Column(Text, nullable=True)  # JSON string for target keywords: ["keyword1", "keyword2"]
    gap_analysis_results_json = Column(Text, nullable=True)  # JSON string for gap analysis results
    top_ideas_count = Column(Integer, default=10)  # Number of top ideas to show (default: 10)
    
    def __repr__(self):
        return f"<Campaign(id={self.id}, campaign_id={self.campaign_id}, name={self.campaign_name})>"

# Raw scraped documents associated with a campaign
class CampaignRawData(Base):
    __tablename__ = "campaign_raw_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(255), index=True, nullable=False)  # stores Campaign.campaign_id UUID
    source_url = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=datetime.now)
    raw_html = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    meta_json = Column(Text, nullable=True)
    content_hash = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<CampaignRawData(id={self.id}, campaign_id={self.campaign_id}, url={self.source_url})>"

# Research insights generated by research agents (keyword, topical-map, hashtag-generator, etc.)
# These are cached to avoid re-calling the LLM for the same campaign/agent combination
class CampaignResearchInsights(Base):
    __tablename__ = "campaign_research_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(255), index=True, nullable=False)  # stores Campaign.campaign_id UUID
    agent_type = Column(String(50), nullable=False)  # e.g., "keyword", "topical-map", "hashtag-generator", "micro-sentiment", "knowledge-graph"
    insights_text = Column(Text, nullable=False)  # The generated insights/recommendations text
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Unique constraint: one insight per campaign/agent_type combination
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    def __repr__(self):
        return f"<CampaignResearchInsights(id={self.id}, campaign_id={self.campaign_id}, agent_type={self.agent_type})>"

# Cached research data (word cloud, topics, hashtags) for campaigns
# This stores the processed research data to avoid re-computation
class CampaignResearchData(Base):
    __tablename__ = "campaign_research_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(255), index=True, nullable=False, unique=True)  # One record per campaign
    word_cloud_json = Column(Text, nullable=True)  # JSON array of {term, count} objects
    topics_json = Column(Text, nullable=True)  # JSON array of {label, score} objects
    hashtags_json = Column(Text, nullable=True)  # JSON array of {id, name, category} objects
    entities_json = Column(Text, nullable=True)  # JSON object with persons, organizations, locations, etc.
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    def __repr__(self):
        return f"<CampaignResearchData(id={self.id}, campaign_id={self.campaign_id})>"

# System-wide settings (e.g., LLM prompts, configuration)
class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "topic_extraction_prompt"
    setting_value = Column(Text, nullable=False)  # JSON string or plain text
    description = Column(Text, nullable=True)  # Description of what this setting does
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SystemSettings(id={self.id}, key={self.setting_key})>"