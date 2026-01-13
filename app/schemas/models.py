"""
Pydantic models/schemas extracted from main.py
Moved from main.py to preserve API contract parity
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    query: Optional[str] = None  # Added to match frontend payload
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    trendingTopics: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    status: Optional[str] = "INCOMPLETE"  # Campaign status: INCOMPLETE, PROCESSING, READY_TO_ACTIVATE, ACTIVE, NO_CHANGES
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None
    # Site Builder specific fields
    site_base_url: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    top_ideas_count: Optional[int] = None
    # Look Alike specific fields
    articles_url: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    status: Optional[str] = None
    topics: Optional[List[str]] = None
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None
    custom_keywords: Optional[List[str]] = None  # Custom keywords/ideas for content queue
    personality_settings_json: Optional[str] = None  # JSON string for personality settings: {author_personality_id: string, brand_personality_id: string}
    image_settings_json: Optional[str] = None  # JSON string for image generation settings: {style, prompt, color, additionalCreativeAgentId}
    scheduling_settings_json: Optional[str] = None  # JSON string for scheduling settings: {activeDays, activePlatforms, post_frequency_type, post_frequency_value, start_date, day_frequency, defaultPosts}
    content_queue_items_json: Optional[str] = None  # JSON string for content queue items: [{id, type, name, source, ...}]
    research_selections_json: Optional[str] = None  # JSON string for Research Assistant selections (raw ingredients): [{id, type, name, source, ...}]


# Pydantic models for author personalities endpoints
class AuthorPersonalityCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AuthorPersonalityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_config_json: Optional[str] = None  # JSON string for model configuration
    baseline_adjustments_json: Optional[str] = None  # JSON string for baseline adjustments
    selected_features_json: Optional[str] = None  # JSON string for selected features
    configuration_preset: Optional[str] = None  # Configuration preset name
    writing_samples_json: Optional[str] = None  # JSON string for writing samples (array of strings or objects with {text, domain})


# Pydantic models for author profile endpoints
class ExtractProfileRequest(BaseModel):
    writing_samples: List[str]
    sample_metadata: Optional[List[dict]] = None  # Optional list of {mode, audience, path} for each sample


class GenerateContentRequest(BaseModel):
    goal: str
    target_audience: str = "general"
    adapter_key: str = "blog"  # linkedin, blog, memo_email, etc.
    scaffold: str  # The content prompt/topic


class BrandPersonalityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    guidelines: Optional[str] = None


class BrandPersonalityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    guidelines: Optional[str] = None


class ResearchAgentRequest(BaseModel):
    agent_type: str
    force_refresh: Optional[bool] = False  # Admin-only: force re-run even if cached


class AnalyzeRequest(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    keywords: Optional[List[str]] = []
    urls: Optional[List[str]] = []
    trendingTopics: Optional[List[str]] = []
    topics: Optional[List[str]] = []
    type: Optional[str] = "keyword"
    # Site Builder specific fields
    site_base_url: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    top_ideas_count: Optional[int] = 10
    most_recent_urls: Optional[int] = None  # Number of most recent URLs to scrape (date-based)
    depth: Optional[int] = 1
    max_pages: Optional[int] = 10
    batch_size: Optional[int] = 1
    include_links: Optional[bool] = True
    include_images: Optional[bool] = False
    stem: Optional[bool] = False
    lemmatize: Optional[bool] = False
    remove_stopwords_toggle: Optional[bool] = False
    extract_persons: Optional[bool] = False
    extract_organizations: Optional[bool] = False
    extract_locations: Optional[bool] = False
    extract_dates: Optional[bool] = False
    extract_money: Optional[bool] = False
    extract_percent: Optional[bool] = False
    extract_time: Optional[bool] = False
    extract_facility: Optional[bool] = False
    topic_tool: Optional[str] = "lda"
    num_topics: Optional[int] = 3
    iterations: Optional[int] = 25
    pass_threshold: Optional[float] = 0.7


class TransferCampaignRequest(BaseModel):
    target_user_id: int

