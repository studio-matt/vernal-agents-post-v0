"""
Pydantic models for API request/response validation
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CampaignCreate(BaseModel):
    """Schema for creating a new campaign"""
    name: str
    type: str
    description: Optional[str] = None
    query: Optional[str] = None
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    trendingTopics: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    status: Optional[str] = "INCOMPLETE"
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None
    site_base_url: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    top_ideas_count: Optional[int] = None


class CampaignUpdate(BaseModel):
    """Schema for updating an existing campaign"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    keywords: Optional[List[str]] = None
    urls: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    status: Optional[str] = None
    extractionSettings: Optional[Dict[str, Any]] = None
    preprocessingSettings: Optional[Dict[str, Any]] = None
    entitySettings: Optional[Dict[str, Any]] = None
    modelingSettings: Optional[Dict[str, Any]] = None
    custom_keywords: Optional[List[str]] = None
    personality_settings_json: Optional[str] = None
    image_settings_json: Optional[str] = None
    scheduling_settings_json: Optional[str] = None
    content_queue_items_json: Optional[str] = None
    research_selections_json: Optional[str] = None

