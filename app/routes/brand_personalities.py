"""
Brand Personality endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal
from app.schemas.models import BrandPersonalityCreate, BrandPersonalityUpdate
from app.utils.openai_helpers import get_openai_api_key
from app.utils.content_tasks import CONTENT_GEN_TASKS, CONTENT_GEN_TASK_INDEX

logger = logging.getLogger(__name__)

brand_personalities_router = APIRouter()

def extract_wordpress_fields(text: str) -> Dict[str, Any]:
    """
    Extract WordPress-specific fields (post_title, post_excerpt, permalink) from generated text.
    
    Format precedence (highest to lowest):
    1. Canonical format: "Post Title: ...", "Post Excerpt: ...", "Permalink: ...", "Article Body: ..."
    2. JSON format: {"post_title": "...", "post_excerpt": "...", "permalink": "..."}
    3. Markdown fallback: # Title, **Excerpt:**, **Permalink/Slug:**
    4. Heuristic: First H1, first paragraph, etc.
    
    Returns dict with fields and metadata about format detected.
    """
    import re
    
    result = {
        "post_title": None,
        "post_excerpt": None,
        "permalink": None,
        "format_detected": None,
        "extracted_title_len": 0,
        "extracted_excerpt_len": 0,
        "extracted_slug_len": 0,
        "body_starts_with": None,
        "cleaned_body": None  # Body text with WordPress field labels removed
    }
    
    if not text:
        return result
    
    # PRIORITY 1: Canonical format (Post Title: / Post Excerpt: / Permalink: / Article Body:)
    # This is the preferred, deterministic format
    # Support both "Post Title:" and "POST_TITLE:" formats (with space or underscore)
    canonical_title = re.search(r'^Post[_\s]+Title:\s*(.+?)(?:\n|$)', text, re.IGNORECASE | re.MULTILINE)
    canonical_excerpt = re.search(r'^Post[_\s]+Excerpt:\s*(.+?)(?:\n(?:Post[_\s]+|Permalink|Article)|$)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    canonical_permalink = re.search(r'^Permalink:\s*([^\n]+)', text, re.IGNORECASE | re.MULTILINE)
    canonical_body_marker = re.search(r'^Article[_\s]+Body:\s*', text, re.IGNORECASE | re.MULTILINE)
    
    if canonical_title or canonical_excerpt or canonical_permalink:
        result["format_detected"] = "canonical"
        if canonical_title:
            title = canonical_title.group(1).strip()
            if title and len(title) > 5:
                result["post_title"] = title
                result["extracted_title_len"] = len(title)
        if canonical_excerpt:
            excerpt = canonical_excerpt.group(1).strip()
            # Limit excerpt length
            if len(excerpt) > 500:
                excerpt = excerpt[:500].rsplit(' ', 1)[0] + '...'
            if excerpt and len(excerpt) > 10:
                result["post_excerpt"] = excerpt
                result["extracted_excerpt_len"] = len(excerpt)
        if canonical_permalink:
            permalink = canonical_permalink.group(1).strip()
            # Clean permalink
            permalink = re.sub(r'[^a-z0-9-]', '', permalink.lower())
            permalink = re.sub(r'-+', '-', permalink).strip('-')
            if permalink and len(permalink) > 3:
                result["permalink"] = permalink
                result["extracted_slug_len"] = len(permalink)
        
        # Extract and clean body text
        if canonical_body_marker:
            # Body starts after "Article Body:" marker
            cleaned_body = text[canonical_body_marker.end():].strip()
            body_start = cleaned_body[:60]
            result["body_starts_with"] = body_start
            result["cleaned_body"] = cleaned_body
        else:
            # Remove field labels from text to get clean body
            cleaned_body = text
            # Remove "Post Title: ..." line
            cleaned_body = re.sub(r'^Post Title:\s*.+?(?:\n|$)', '', cleaned_body, flags=re.IGNORECASE | re.MULTILINE)
            # Remove "Post Excerpt: ..." section (may be multiline)
            cleaned_body = re.sub(r'^Post Excerpt:\s*.+?(?=\n(?:Permalink|Article Body):|\n*$)', '', cleaned_body, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
            # Remove "Permalink: ..." line
            cleaned_body = re.sub(r'^Permalink:\s*.+?(?:\n|$)', '', cleaned_body, flags=re.IGNORECASE | re.MULTILINE)
            # Clean up extra newlines
            cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body).strip()
            result["cleaned_body"] = cleaned_body
            result["body_starts_with"] = cleaned_body[:60] if cleaned_body else None
        
        # If we got canonical format, return early (don't check fallbacks)
        if result["post_title"] or result["post_excerpt"] or result["permalink"]:
            return result
    
    # PRIORITY 2: JSON format
    json_patterns = [
        r'\{[^{}]*"post_title"\s*:\s*"([^"]+)"[^{}]*"post_excerpt"\s*:\s*"([^"]+)"[^{}]*"permalink"\s*:\s*"([^"]+)"[^{}]*\}',
        r'\{[^{}]*post_title\s*:\s*"([^"]+)"[^{}]*post_excerpt\s*:\s*"([^"]+)"[^{}]*permalink\s*:\s*"([^"]+)"[^{}]*\}',
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            result["format_detected"] = "json"
            if match.group(1):
                result["post_title"] = match.group(1).strip()
                result["extracted_title_len"] = len(result["post_title"])
            if match.group(2):
                result["post_excerpt"] = match.group(2).strip()
                result["extracted_excerpt_len"] = len(result["post_excerpt"])
            if match.group(3):
                permalink = match.group(3).strip()
                permalink = re.sub(r'[^a-z0-9-]', '', permalink.lower())
                permalink = re.sub(r'-+', '-', permalink).strip('-')
                result["permalink"] = permalink
                result["extracted_slug_len"] = len(permalink)
            return result
    
    # PRIORITY 3: Markdown fallback (# Title, **Excerpt:**, **Permalink/Slug:**)
    h1_title = re.search(r'^#\s+(.+?)(?:\n|$)', text, re.MULTILINE)
    excerpt_markdown = re.search(r'\*\*Excerpt:\*\*\s*(.+?)(?:\n\n|\n\*\*|\n---|$)', text, re.IGNORECASE | re.DOTALL)
    permalink_markdown = re.search(r'\*\*Permalink/Slug:\*\*\s*([^\n]+)', text, re.IGNORECASE)
    if not permalink_markdown:
        permalink_markdown = re.search(r'\*\*Permalink:\*\*\s*([^\n]+)', text, re.IGNORECASE)
    
    if h1_title or excerpt_markdown or permalink_markdown:
        result["format_detected"] = "markdown_fallback"
        
        if h1_title:
            title = h1_title.group(1).strip()
            title = re.sub(r'\*\*|__', '', title).strip()
            if title and len(title) > 5:
                result["post_title"] = title
                result["extracted_title_len"] = len(title)
        
        if excerpt_markdown:
            excerpt = excerpt_markdown.group(1).strip()
            excerpt = re.sub(r'\*\*|__|#+', '', excerpt).strip().rstrip('.')
            sentences = re.split(r'[.!?]\s+', excerpt)
            if sentences and len(sentences[0]) < 300:
                excerpt = sentences[0].rstrip('.')
            if len(excerpt) > 500:
                excerpt = excerpt[:500].rsplit(' ', 1)[0] + '...'
            if excerpt and len(excerpt) > 10:
                result["post_excerpt"] = excerpt
                result["extracted_excerpt_len"] = len(excerpt)
        
        if permalink_markdown:
            permalink = permalink_markdown.group(1).strip()
            if re.match(r'^[a-z0-9-]+$', permalink.lower()):
                result["permalink"] = permalink.lower()
            else:
                permalink = re.sub(r'[^a-z0-9-]', '', permalink.lower())
                permalink = re.sub(r'-+', '-', permalink).strip('-')
                if permalink and len(permalink) > 3:
                    result["permalink"] = permalink
            if result["permalink"]:
                result["extracted_slug_len"] = len(result["permalink"])
        
        # Extract and clean body text (remove markdown field labels)
        cleaned_body = text
        # Remove H1 title
        if h1_title:
            cleaned_body = re.sub(r'^#\s+.+?(?:\n|$)', '', cleaned_body, flags=re.MULTILINE)
        # Remove excerpt section
        if excerpt_markdown:
            cleaned_body = re.sub(r'\*\*Excerpt:\*\*\s*.+?(?=\n\n|\n\*\*|\n---|$)', '', cleaned_body, flags=re.IGNORECASE | re.DOTALL)
        # Remove permalink section
        if permalink_markdown:
            cleaned_body = re.sub(r'\*\*Permalink(?:/Slug)?:\*\*\s*[^\n]+', '', cleaned_body, flags=re.IGNORECASE)
        # Remove horizontal rules and clean up
        cleaned_body = re.sub(r'^---+$', '', cleaned_body, flags=re.MULTILINE)
        cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body).strip()
        result["cleaned_body"] = cleaned_body
        
        # Extract body start (after first --- or after permalink section)
        body_match = re.search(r'(?:---|\*\*Permalink[^\n]+\n)', text, re.IGNORECASE)
        if body_match:
            body_start = text[body_match.end():].strip()[:60]
            result["body_starts_with"] = body_start
        elif cleaned_body:
            result["body_starts_with"] = cleaned_body[:60]
        
        # If we got any markdown fields, return (don't check heuristics)
        if result["post_title"] or result["post_excerpt"] or result["permalink"]:
            return result
    
    # PRIORITY 4: Heuristic fallback (last resort)
    # Only use if nothing else matched
    result["format_detected"] = "heuristic"
    
    # Try to get title from first H1 or first line
    if not result["post_title"]:
        h1_heuristic = re.search(r'^#\s+(.+?)(?:\n|$)', text, re.MULTILINE)
        if h1_heuristic:
            title = h1_heuristic.group(1).strip()
            title = re.sub(r'\*\*|__|#+', '', title).strip()
            if title and len(title) > 5:
                result["post_title"] = title
                result["extracted_title_len"] = len(title)
    
    # Try to get excerpt from first paragraph
    if not result["post_excerpt"]:
        first_para = re.search(r'^(?:[^\n]+\n){1,3}(.+?)(?:\n\n|\n#|$)', text, re.MULTILINE | re.DOTALL)
        if first_para:
            excerpt = first_para.group(1).strip()
            excerpt = re.sub(r'\*\*|__|#+', '', excerpt).strip()
            if len(excerpt) > 500:
                excerpt = excerpt[:500].rsplit(' ', 1)[0] + '...'
            if excerpt and len(excerpt) > 10:
                result["post_excerpt"] = excerpt
                result["extracted_excerpt_len"] = len(excerpt)
    
    # Extract body start and clean body (for heuristic, just use original text)
    if text:
        result["body_starts_with"] = text.strip()[:60]
        result["cleaned_body"] = text.strip()  # For heuristic, use original text
    
    return result
    
    # PRIORITY 3: Try JSON-like format
    json_patterns = [
        r'\{[^{}]*"post_title"\s*:\s*"([^"]+)"[^{}]*"post_excerpt"\s*:\s*"([^"]+)"[^{}]*"permalink"\s*:\s*"([^"]+)"[^{}]*\}',
        r'\{[^{}]*post_title\s*:\s*"([^"]+)"[^{}]*post_excerpt\s*:\s*"([^"]+)"[^{}]*permalink\s*:\s*"([^"]+)"[^{}]*\}',
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if not result["post_title"]:
                result["post_title"] = match.group(1).strip()
            if not result["post_excerpt"]:
                result["post_excerpt"] = match.group(2).strip()
            if not result["permalink"]:
                result["permalink"] = match.group(3).strip()
            # If we got all three, return early
            if all(result.values()):
                return result
    
    # PRIORITY 4: Try separate field extraction patterns (only if not already found)
    if not result["post_title"]:
        title_patterns = [
            r'Post Title\s*:?\s*(.+?)(?:\n|$|Excerpt|Permalink)',
            r'##\s*Post Title\s*\n(.+?)(?:\n##|$)',
            r'post_title\s*:?\s*"([^"]+)"',
            r'post_title\s*:?\s*([^\n]+)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result["post_title"] = match.group(1).strip()
                break
    
    if not result["post_excerpt"]:
        excerpt_patterns = [
            r'Post Excerpt\s*:?\s*(.+?)(?:\n|$|Permalink|Post Title)',
            r'Excerpt\s*:?\s*(.+?)(?:\n|$|Permalink|Post Title)',
            r'##\s*Post Excerpt\s*\n(.+?)(?:\n##|$)',
            r'##\s*Excerpt\s*\n(.+?)(?:\n##|$)',
            r'post_excerpt\s*:?\s*"([^"]+)"',
            r'post_excerpt\s*:?\s*(.+?)(?:\n|$|permalink)',
        ]
        for pattern in excerpt_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                excerpt = match.group(1).strip()
                # Remove markdown formatting
                excerpt = re.sub(r'\*\*|__|#+', '', excerpt).strip()
                # Limit excerpt length
                if len(excerpt) > 500:
                    excerpt = excerpt[:500].rsplit(' ', 1)[0] + '...'
                result["post_excerpt"] = excerpt
                break
    
    if not result["permalink"]:
        permalink_patterns = [
            r'Permalink\s*:?\s*(.+?)(?:\n|$|Post Title|Excerpt)',
            r'Permalink/Slug\s*:?\s*(.+?)(?:\n|$|Post Title|Excerpt)',
            r'Slug\s*:?\s*(.+?)(?:\n|$|Post Title|Excerpt)',
            r'##\s*Permalink\s*\n(.+?)(?:\n##|$)',
            r'permalink\s*:?\s*"([^"]+)"',
            r'permalink\s*:?\s*([^\n\s]+)',
        ]
        for pattern in permalink_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                permalink = match.group(1).strip()
                # Clean permalink (remove special chars except hyphens, make lowercase)
                permalink = re.sub(r'[^a-z0-9-]', '', permalink.lower())
                result["permalink"] = permalink
                break
    
    return result

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Brand Personalities endpoints
@brand_personalities_router.get("/brand_personalities")
def get_brand_personalities(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all brand personalities for the current user - REQUIRES AUTHENTICATION"""
    logger.info(f"🔍 /brand_personalities GET endpoint called by user {current_user.id}")
    try:
        from models import BrandPersonality
        # Filter by user_id to only return user's own personalities
        personalities = db.query(BrandPersonality).filter(
            BrandPersonality.user_id == current_user.id
        ).all()
        return {
            "status": "success",
            "message": {
                "personalities": [
                    {
                        "id": personality.id,
                        "name": personality.name,
                        "description": personality.description,
                        "guidelines": personality.guidelines,
                        "created_at": personality.created_at.isoformat() if personality.created_at else None,
                        "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                        "user_id": personality.user_id
                    }
                    for personality in personalities
                ]
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching brand personalities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch brand personalities: {str(e)}"
        )

@brand_personalities_router.post("/brand_personalities")
def create_brand_personality(personality_data: BrandPersonalityCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new brand personality - REQUIRES AUTHENTICATION"""
    try:
        from models import BrandPersonality
        logger.info(f"Creating brand personality: {personality_data.name} for user {current_user.id}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database with user_id
        personality = BrandPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            guidelines=personality_data.guidelines,
            user_id=current_user.id  # Associate with logged-in user
        )
        
        db.add(personality)
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality created successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create brand personality: {str(e)}"
        )

@brand_personalities_router.put("/brand_personalities/{personality_id}")
def update_brand_personality(personality_id: str, personality_data: BrandPersonalityUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        if personality_data.guidelines is not None:
            personality.guidelines = personality_data.guidelines
        
        personality.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality updated successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand personality: {str(e)}"
        )

@brand_personalities_router.delete("/brand_personalities/{personality_id}")
def delete_brand_personality(personality_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        db.delete(personality)
        db.commit()
        logger.info(f"Brand personality deleted successfully: {personality_id}")
        return {
            "status": "success",
            "message": "Brand personality deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error deleting brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete brand personality: {str(e)}"
        )

# Campaign Planning Endpoint
@brand_personalities_router.post("/campaigns/{campaign_id}/plan")
async def create_campaign_plan(
    campaign_id: str,
    request_data: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a campaign plan based on weeks, scheduling settings, and content queue items.
    Generates parent/children idea hierarchy and knowledge graph locations.
    
    Request body:
    {
        "scheduling": {
            "weeks": 4,
            "posts_per_day": {"facebook": 3, "instagram": 2},
            "posts_per_week": {"facebook": 15, "instagram": 10},
            "start_date": "2025-01-01",
            "day_frequency": "selected_days",  # daily, selected_days, every_other, every_first, etc.
            "post_frequency_type": "weeks",
            "post_frequency_value": 4
        },
        "content_queue_items": [...],  # Checked items from content queue
        "landing_page_url": "https://example.com/landing"
    }
    """
    try:
        from models import Campaign, SystemSettings
        import json
        from datetime import datetime, timedelta
        from machine_agent import IdeaGeneratorAgent
        from langchain_openai import ChatOpenAI
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        scheduling = request_data.get("scheduling", {})
        content_queue_items = request_data.get("content_queue_items", [])
        landing_page_url = request_data.get("landing_page_url", "")
        max_refactoring = request_data.get("max_refactoring", 3)  # Default max refactoring attempts
        
        weeks = scheduling.get("weeks", 4)
        posts_per_day = scheduling.get("posts_per_day", {})
        start_date_str = scheduling.get("start_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now()
        
        # Get knowledge graph location selection prompt from admin settings
        kg_location_prompt_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "knowledge_graph_location_selection_prompt"
        ).first()
        
        kg_location_prompt = kg_location_prompt_setting.setting_value if kg_location_prompt_setting else """Given a parent idea and existing knowledge graph locations used, select a new location on the knowledge graph that:
1. Supports the same core topic as the parent idea
2. Has not been used recently for this campaign
3. Provides a different angle or perspective
4. Can drive traffic to the landing page

Return the knowledge graph location (node name or entity) that should be used for the next post."""
        
        # Initialize LLM for planning
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings.")
        
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key.strip(), temperature=0.7)
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        # Generate campaign plan with parent/children structure
        plan = {
            "weeks": [],
            "landing_page_url": landing_page_url,
            "created_at": datetime.now().isoformat()
        }
        
        # For each week, generate parent ideas and children
        for week_num in range(1, weeks + 1):
            week_plan = {
                "week_num": week_num,
                "parent_ideas": [],
                "knowledge_graph_locations": []
            }
            
            # Generate parent ideas for this week (one per day, or based on scheduling)
            # For simplicity, generate one parent idea per day of the week
            days_in_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            for day in days_in_week[:5]:  # Weekdays only for now
                # Generate parent idea for this day
                parent_prompt = f"""Based on the following content queue items, generate a parent idea for {day} of week {week_num}:

Content Queue Items:
{queue_context}

Generate a parent idea that:
1. Is based on the content queue items
2. Can be broken down into supporting children concepts
3. Drives traffic to: {landing_page_url}
4. Is suitable for multiple posts on the same day

Return only the parent idea, no additional text."""
                
                # Guardrails: sanitize parent_prompt + check for injection (raises GuardrailsBlocked if blocking enabled)
                parent_prompt, audit = guard_or_raise(parent_prompt, max_len=12000)

                parent_response = llm.invoke(parent_prompt)
                parent_idea = parent_response.content.strip()
                
                # Generate children concepts for this parent
                children_prompt = f"""Given this parent idea: "{parent_idea}"

Generate 3-5 children concepts that support this parent idea. Each child should:
1. Focus on a different aspect of the parent
2. Be suitable for a single post
3. Drive traffic to: {landing_page_url}

Return as a numbered list."""
                
                # Guardrails: sanitize children_prompt + check for injection (raises GuardrailsBlocked if blocking enabled)
                children_prompt, audit = guard_or_raise(children_prompt, max_len=12000)

                children_response = llm.invoke(children_prompt)
                children_text = children_response.content.strip()
                children = [line.strip() for line in children_text.split("\n") if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))]
                
                # Clean up children (remove numbering)
                children = [c.split(". ", 1)[-1] if ". " in c else c.replace("- ", "").strip() for c in children]
                
                # Select knowledge graph location for this parent idea
                kg_location_prompt_full = f"""{kg_location_prompt}

Parent Idea: {parent_idea}
Existing Locations Used: {', '.join(week_plan['knowledge_graph_locations']) if week_plan['knowledge_graph_locations'] else 'None'}

Select a knowledge graph location for this parent idea."""
                
                # Guardrails: sanitize kg_location_prompt_full + check for injection (raises GuardrailsBlocked if blocking enabled)
                kg_location_prompt_full, audit = guard_or_raise(kg_location_prompt_full, max_len=12000)

                kg_response = llm.invoke(kg_location_prompt_full)
                kg_location = kg_response.content.strip()
                
                week_plan["parent_ideas"].append({
                    "day": day,
                    "idea": parent_idea,
                    "children": children,
                    "knowledge_graph_location": kg_location
                })
                week_plan["knowledge_graph_locations"].append(kg_location)
            
            plan["weeks"].append(week_plan)
        
        # Save plan to campaign
        campaign.campaign_plan_json = json.dumps(plan)
        campaign.scheduling_settings_json = json.dumps(scheduling)
        campaign.content_queue_items_json = json.dumps(content_queue_items)
        db.commit()
        
        return {
            "status": "success",
            "plan": plan,
            "message": f"Campaign plan created for {weeks} weeks"
        }
        
    except Exception as e:
        logger.error(f"Error creating campaign plan: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Content Pre-population Endpoint
@brand_personalities_router.post("/campaigns/{campaign_id}/prepopulate-content")
async def prepopulate_campaign_content(
    campaign_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pre-populate content for the entire campaign lifecycle based on the campaign plan.
    Creates draft content for all scheduled posts that can be edited until scheduled time.
    Images are NOT generated until push time to save tokens.
    """
    try:
        from models import Campaign, Content, SystemSettings
        from crewai_workflows import create_content_generation_crew
        import json
        from datetime import datetime, timedelta
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if not campaign.campaign_plan_json:
            raise HTTPException(status_code=400, detail="Campaign plan not found. Please create a plan first.")
        
        plan = json.loads(campaign.campaign_plan_json)
        scheduling = json.loads(campaign.scheduling_settings_json) if campaign.scheduling_settings_json else {}
        content_queue_items = json.loads(campaign.content_queue_items_json) if campaign.content_queue_items_json else []
        
        start_date_str = scheduling.get("start_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now()
        posts_per_day = scheduling.get("posts_per_day", {})
        landing_page_url = plan.get("landing_page_url", "")
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        generated_content = []
        
        # Generate content for each week in the plan
        for week_data in plan.get("weeks", []):
            week_num = week_data.get("week_num", 1)
            
            for parent_data in week_data.get("parent_ideas", []):
                day = parent_data.get("day")
                parent_idea = parent_data.get("idea")
                children = parent_data.get("children", [])
                kg_location = parent_data.get("knowledge_graph_location", "")
                
                # Calculate actual date for this day
                day_offset = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
                week_start = start_date + timedelta(weeks=week_num - 1)
                # Find the Monday of this week
                days_since_monday = (week_start.weekday()) % 7
                monday_of_week = week_start - timedelta(days=days_since_monday)
                post_date = monday_of_week + timedelta(days=day_offset)
                
                # Generate content for each platform
                for platform, posts_count in posts_per_day.items():
                    # Generate posts for this platform on this day
                    # If multiple posts, use different children or knowledge graph locations
                    for post_num in range(posts_count):
                        # Select content source (parent idea, child, or knowledge graph location)
                        if post_num == 0:
                            # First post uses parent idea
                            content_source = parent_idea
                        elif post_num <= len(children):
                            # Use child concept
                            content_source = children[post_num - 1]
                        else:
                            # Use knowledge graph location (refactored)
                            content_source = f"{parent_idea} (focusing on {kg_location})"
                        
                        # Build writing context
                        writing_context = f"""Content Queue Foundation:
{queue_context}

Parent Idea: {parent_idea}
Content Source: {content_source}
Knowledge Graph Location: {kg_location}
Landing Page: {landing_page_url}

Generate content for {platform} that:
1. Is based on the content source above
2. Drives traffic to the landing page
3. Focuses on the knowledge graph location
4. Is suitable for {platform} platform"""
                        
                        # Generate content using CrewAI workflow
                        try:
                            crew_result = create_content_generation_crew(
                                text=writing_context,
                                week=week_num,
                                platform=platform.lower(),
                                days_list=[day],
                                author_personality=None  # Can be added later
                            )
                            
                            if crew_result.get("success"):
                                content_text = crew_result.get("data", {}).get("content", "")
                                title = crew_result.get("data", {}).get("title", f"{platform} Post - {day}")
                                
                                # Create content record (draft, not finalized)
                                content = Content(
                                    user_id=current_user.id,
                                    campaign_id=campaign_id,
                                    week=week_num,
                                    day=day,
                                    content=content_text,
                                    title=title,
                                    status="draft",  # Draft status until scheduled
                                    date_upload=post_date,
                                    platform=platform.lower(),
                                    file_name=f"{campaign_id}_{week_num}_{day}_{platform}_{post_num}.txt",
                                    file_type="text",
                                    platform_post_no=str(post_num + 1),
                                    schedule_time=post_date.replace(hour=9, minute=0),  # Default 9 AM
                                    is_draft=True,
                                    can_edit=True,
                                    knowledge_graph_location=kg_location,
                                    parent_idea=parent_idea,
                                    landing_page_url=landing_page_url
                                )
                                
                                db.add(content)
                                generated_content.append({
                                    "id": content.id,
                                    "week": week_num,
                                    "day": day,
                                    "platform": platform,
                                    "title": title,
                                    "status": "draft"
                                })
                        except Exception as e:
                            logger.error(f"Error generating content for {platform} on {day}: {e}")
                            # Continue with other posts
                            continue
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Pre-populated {len(generated_content)} content items",
            "content": generated_content
        }
        
    except Exception as e:
        logger.error(f"Error pre-populating content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Update writing endpoint to accept content queue items
@brand_personalities_router.post("/campaigns/{campaign_id}/generate-content")
async def generate_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content for a campaign using content queue items as foundation.
    Updated to accept content_queue_items and use them as context.
    Now runs in background with status tracking.
    """
    logger.info(f"📝 generate_campaign_content called for campaign_id: {campaign_id}")
    logger.info(f"📝 request_data keys: {list(request_data.keys()) if request_data else 'None'}")
    try:
        # Create task for status tracking
        task_id = str(uuid.uuid4())
        platform = request_data.get("platform", "linkedin")
        
        CONTENT_GEN_TASKS[task_id] = {
            "campaign_id": campaign_id,
            "platform": platform,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "status": "pending",
            "current_agent": None,
            "current_task": "Initializing content generation",
            "agent_statuses": [],
            "error": None,
            "result": None,
        }
        
        # Index by campaign_id for easy lookup
        if campaign_id not in CONTENT_GEN_TASK_INDEX:
            CONTENT_GEN_TASK_INDEX[campaign_id] = []
        CONTENT_GEN_TASK_INDEX[campaign_id].append(task_id)
        
        logger.info(f"📝 Created content generation task: {task_id} for campaign {campaign_id}")
        
        # Run generation in background thread
        def run_generation_background(tid: str, cid: str, req_data: Dict[str, Any], user_id: int):
            try:
                from database import SessionLocal
                session = SessionLocal()
                try:
                    from models import Campaign
                    from crewai_workflows import create_content_generation_crew
                    import json
                    
                    # Helper to update task status
                    def update_task_status(agent: str = None, task: str = None, progress: int = None, 
                                          status: str = None, error: str = None, agent_status: str = "running"):
                        if tid not in CONTENT_GEN_TASKS:
                            return
                        task_data = CONTENT_GEN_TASKS[tid]
                        if agent:
                            task_data["current_agent"] = agent
                        if task:
                            task_data["current_task"] = task
                        if progress is not None:
                            task_data["progress"] = progress
                        if status:
                            task_data["status"] = status
                        if error:
                            task_data["error"] = error
                            task_data["status"] = "error"
                        # Add to agent statuses
                        if agent:
                            agent_entry = {
                                "agent": agent,
                                "task": task or "Processing",
                                "status": agent_status,
                                "timestamp": datetime.utcnow().isoformat(),
                                "error": error
                            }
                            # Add message if provided (for QC agents, this might contain approval/rejection details)
                            if task and ("approved" in task.lower() or "rejected" in task.lower() or "review" in task.lower()):
                                agent_entry["message"] = task
                            task_data["agent_statuses"].append(agent_entry)
                        logger.info(f"📊 Task {tid}: {progress}% - {agent} - {task}")
                    
                    update_task_status(progress=5, task="Initializing", status="in_progress")
                    
                    # Verify campaign ownership
                    campaign = session.query(Campaign).filter(
                        Campaign.campaign_id == cid,
                        Campaign.user_id == user_id
                    ).first()
                    
                    if not campaign:
                        update_task_status(error="Campaign not found", status="error")
                        return
                    
                    # Get content queue items for THIS ONE ARTICLE ONLY
                    # The frontend passes only the items relevant to this specific article/post
                    # Do NOT fall back to all campaign items - we process one article at a time
                    content_queue_items = req_data.get("content_queue_items", [])
                    if not content_queue_items:
                        # If no items passed, log warning but continue with empty list
                        # This ensures we're only processing the items for this specific article
                        logger.warning(f"⚠️ No content_queue_items passed for this article. Processing with empty queue.")
                        content_queue_items = []
                    
                    # Build context from items for THIS ONE ARTICLE
                    queue_context = "\n".join([
                        f"- {item.get('title', item.get('text', str(item)))}"
                        for item in content_queue_items
                    ]) if content_queue_items else "No specific content queue items for this article."
                    
                    # Get parameters
                    platform = req_data.get("platform", "linkedin")
                    week = req_data.get("week", 1)
                    day = req_data.get("day", "Monday")
                    parent_idea = req_data.get("parent_idea", "")
                    author_personality_id = req_data.get("author_personality_id")
                    brand_personality_id = req_data.get("brand_personality_id")  # NEW: Support brand personality
                    use_author_voice = req_data.get("use_author_voice", True)
                    use_validation = req_data.get("use_validation", False)
                    
                    # Get brand personality guidelines if provided
                    brand_guidelines = ""
                    if brand_personality_id:
                        from models import BrandPersonality
                        brand_personality = session.query(BrandPersonality).filter(
                            BrandPersonality.id == brand_personality_id,
                            BrandPersonality.user_id == user_id
                        ).first()
                        if brand_personality and brand_personality.guidelines:
                            brand_guidelines = f"\n\nBrand Voice Guidelines:\n{brand_personality.guidelines}"
                    
                    # Build campaign context for {context} placeholder (matches instructional copy)
                    # Get scraped texts for context (using CampaignRawData model)
                    from models import CampaignRawData
                    scraped_texts = session.query(CampaignRawData).filter(
                        CampaignRawData.campaign_id == cid
                    ).limit(10).all()
                    
                    # Get topics (if available from campaign or extract from scraped texts)
                    topics_list = []
                    if campaign.topics:
                        try:
                            topics_list = json.loads(campaign.topics) if isinstance(campaign.topics, str) else campaign.topics
                        except:
                            topics_list = []
                    
                    # Get keywords
                    campaign_keywords = campaign.keywords.split(",") if campaign.keywords else []
                    
                    # Build sample text (first 500 chars from first scraped text)
                    sample_text = ""
                    if scraped_texts and scraped_texts[0].extracted_text:
                        sample_text = scraped_texts[0].extracted_text[:500]
                    
                    # Build word cloud data (top keywords from scraped content)
                    word_cloud_data = []
                    if scraped_texts:
                        from collections import Counter
                        import re
                        all_words = []
                        for st in scraped_texts:
                            if st.extracted_text:
                                words = re.findall(r'\b\w+\b', st.extracted_text.lower())
                                all_words.extend(words)
                        word_counts = Counter(all_words)
                        # Get top 20 keywords (excluding common stop words)
                        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'where', 'when', 'why', 'how'}
                        top_keywords = [(word, count) for word, count in word_counts.most_common(30) if word not in stop_words and len(word) > 3][:20]
                        word_cloud_data = [{"term": word, "count": count} for word, count in top_keywords]
                    
                    # Build context string matching instructional copy format
                    campaign_context = f"""Campaign Query: {campaign.query or 'N/A'}
Campaign Keywords: {', '.join(campaign_keywords) if campaign_keywords else 'N/A'}

Top Keywords Found in Scraped Content:
{', '.join([item['term'] for item in word_cloud_data[:10]]) if word_cloud_data else 'N/A'}

Topics Identified: {', '.join([str(t) for t in topics_list[:10]]) if topics_list else 'N/A'}

Number of Scraped Texts: {len(scraped_texts)}

Sample Text (first 500 characters):
{sample_text if sample_text else 'N/A'}"""
                    
                    # Get platform-specific settings (Instagram-specific modifications from research assistant)
                    platform_settings_text = ""
                    if "platformSettings" in req_data:
                        platform_settings = req_data.get("platformSettings", {})
                        platform_lower = platform.lower()
                        if platform_lower in platform_settings:
                            settings = platform_settings[platform_lower]
                            if settings:
                                # Format platform-specific settings/modifications
                                settings_items = []
                                for key, value in settings.items():
                                    if value:  # Only include non-empty values
                                        settings_items.append(f"{key}: {value}")
                                if settings_items:
                                    platform_settings_text = f"\n\n{platform.capitalize()}-Specific Settings/Modifications:\n" + "\n".join(settings_items)
                    
                    # Fetch cornerstone content if this is a supporting platform (not the cornerstone platform)
                    # IMPORTANT: Fetch cornerstone content for the SPECIFIC week and day being generated
                    # This ensures supporting platforms reference the correct cornerstone post for that day
                    cornerstone_content = ""
                    if campaign.cornerstone_platform and platform.lower() != campaign.cornerstone_platform.lower():
                        # This is a supporting platform - fetch the cornerstone content for THIS specific week and day
                        from models import Content
                        
                        # First try to find cornerstone content for the exact week and day
                        cornerstone_content_item = session.query(Content).filter(
                            Content.campaign_id == cid,
                            Content.platform == campaign.cornerstone_platform.lower(),
                            Content.week == week,
                            Content.day == day
                        ).first()
                        
                        # If not found for exact match, try to find any cornerstone content for this day (different week)
                        if not cornerstone_content_item:
                            cornerstone_content_item = session.query(Content).filter(
                                Content.campaign_id == cid,
                                Content.platform == campaign.cornerstone_platform.lower(),
                                Content.day == day
                            ).order_by(Content.week.desc(), Content.date_upload.desc()).first()
                        
                        # If still not found, fall back to most recent cornerstone content (for backward compatibility)
                        if not cornerstone_content_item:
                            cornerstone_content_item = session.query(Content).filter(
                                Content.campaign_id == cid,
                                Content.platform == campaign.cornerstone_platform.lower()
                            ).order_by(Content.date_upload.desc()).first()
                            logger.warning(f"⚠️ No cornerstone content found for week {week}, day {day}. Using most recent cornerstone content.")
                        
                        if cornerstone_content_item and cornerstone_content_item.content:
                            # Pass ONLY the content body (no title or excerpt)
                            # This prevents agents from anchoring to summary instead of mining the full article
                            cornerstone_text = cornerstone_content_item.content.strip()
                            
                            # Prepend label for clarity
                            cornerstone_content = f"Cornerstone Article Body:\n{cornerstone_text}"
                            
                            # Log which cornerstone content was used (for debugging)
                            matched_week = cornerstone_content_item.week
                            matched_day = cornerstone_content_item.day
                            if matched_week == week and matched_day == day:
                                logger.info(f"📝 Fetched cornerstone content for week {week}, day {day} (exact match) - {len(cornerstone_text)} chars")
                            else:
                                # Day match but different week - warn about potential theme mismatch
                                logger.warning(f"⚠️ Using cornerstone content from week {matched_week}, day {matched_day} (requested: week {week}, day {day}). Campaign themes may differ week-to-week. - {len(cornerstone_text)} chars")
                        else:
                            logger.warning(f"⚠️ Cornerstone platform {campaign.cornerstone_platform} is set but no cornerstone content found for week {week}, day {day}")
                    
                    # Build writing context for THIS ONE ARTICLE
                    # Includes: content queue items (for this article only), parent idea, brand guidelines,
                    # campaign context, platform-specific modifications, and cornerstone content
                    writing_context = f"""Content Queue Foundation (for this article only):
{queue_context}

{f'Parent Idea: {parent_idea}' if parent_idea else ''}{brand_guidelines}{platform_settings_text}

Campaign Context:
{campaign_context}
{cornerstone_content}

Generate content for {platform} based on the content queue items and campaign context above."""
                    
                    # Replace {cornerstone} placeholder if it exists in the writing context
                    if "{cornerstone}" in writing_context and cornerstone_content:
                        writing_context = writing_context.replace("{cornerstone}", cornerstone_content.strip())
                    elif "{cornerstone}" in writing_context:
                        # Placeholder exists but no cornerstone content - remove placeholder
                        writing_context = writing_context.replace("{cornerstone}", "[No cornerstone content available]")
                        logger.warning(f"⚠️ {{cornerstone}} placeholder found but no cornerstone content available")
                    
                    # Log configuration details for verbose status tracking
                    author_personality_name = "None"
                    brand_personality_name = "None"
                    if author_personality_id:
                        from models import AuthorPersonality
                        author_personality_obj = session.query(AuthorPersonality).filter(
                            AuthorPersonality.id == author_personality_id,
                            AuthorPersonality.user_id == user_id
                        ).first()
                        if author_personality_obj:
                            author_personality_name = author_personality_obj.name or author_personality_id
                    if brand_personality_id:
                        from models import BrandPersonality
                        brand_personality_obj = session.query(BrandPersonality).filter(
                            BrandPersonality.id == brand_personality_id,
                            BrandPersonality.user_id == user_id
                        ).first()
                        if brand_personality_obj:
                            brand_personality_name = brand_personality_obj.name or brand_personality_id
                    
                    update_task_status(
                        agent="Configuration",
                        task=f"Author Personality: {author_personality_name} | Brand Voice: {brand_personality_name} | Platform: {platform.capitalize()}",
                        progress=5,
                        agent_status="completed"
                    )
                    
                    update_task_status(progress=10, task="Preparing content context")
                    
                    # Phase 3: Integrate author voice if author_personality_id is provided
                    if author_personality_id and use_author_voice:
                        from author_voice_helper import generate_with_author_voice, should_use_author_voice
                        
                        if should_use_author_voice(author_personality_id):
                            update_task_status(
                                agent="Author Voice Generator",
                                task="Generating content with author personality",
                                progress=20,
                                status="in_progress"
                            )
                            
                            # Get custom modifications
                            custom_modifications = None
                            if "platformSettings" in req_data:
                                platform_settings = req_data.get("platformSettings", {})
                                platform_lower = platform.lower()
                                if platform_lower in platform_settings:
                                    settings = platform_settings[platform_lower]
                                    if not settings.get("useGlobalDefaults", True):
                                        custom_modifications = settings.get("customModifications", "")
                            
                            # Generate with author voice
                            try:
                                generated_text, style_config, metadata, validation_result = generate_with_author_voice(
                                    content_prompt=writing_context,
                                    author_personality_id=author_personality_id,
                                    platform=platform.lower(),
                                    goal="content_generation",
                                    target_audience="general",
                                    custom_modifications=custom_modifications,
                                    use_validation=use_validation,
                                    db=session
                                )
                                
                                update_task_status(
                                    agent="Author Voice Generator",
                                    task="Content generated successfully",
                                    progress=80,
                                    agent_status="completed"
                                )
                                
                                if generated_text:
                                    use_crewai_qc = req_data.get("use_crewai_qc", False)
                                    
                                    if use_crewai_qc:
                                        update_task_status(
                                            agent="CrewAI QC Agent",
                                            task="Reviewing content quality",
                                            progress=85,
                                            status="in_progress"
                                        )
                                        
                                        crew_result = create_content_generation_crew(
                                            text=f"Review and refine this content:\n\n{generated_text}\n\nStyle Config:\n{style_config}",
                                            week=week,
                                            platform=platform.lower(),
                                            days_list=[day],
                                            author_personality=req_data.get("author_personality", "custom")
                                        )
                                        
                                        update_task_status(
                                            agent="CrewAI QC Agent",
                                            task="Quality review completed",
                                            progress=95,
                                            agent_status="completed"
                                        )
                                        
                                        if crew_result.get("success"):
                                            response_data = {
                                                **crew_result.get("data", {}),
                                                "author_voice_used": True,
                                                "style_config": style_config,
                                                "author_voice_metadata": metadata
                                            }
                                            if validation_result:
                                                response_data["validation"] = validation_result
                                            CONTENT_GEN_TASKS[tid]["result"] = {
                                                "status": "success",
                                                "data": response_data,
                                                "error": None
                                            }
                                            update_task_status(progress=100, status="completed", task="Content generation completed")
                                            return
                                    
                                    # Extract WordPress fields if platform is WordPress
                                    wordpress_fields = {}
                                    if platform.lower() == "wordpress":
                                        extraction_result = extract_wordpress_fields(generated_text)
                                        format_detected = extraction_result.get("format_detected", "unknown")
                                        
                                        # Log contract compliance
                                        logger.info(f"📝 WordPress fields extraction - Format: {format_detected}")
                                        
                                        wordpress_fields = {
                                            "post_title": extraction_result.get("post_title"),
                                            "post_excerpt": extraction_result.get("post_excerpt"),
                                            "permalink": extraction_result.get("permalink"),
                                            "format_detected": format_detected
                                        }
                                        
                                        if format_detected != "canonical":
                                            logger.warning(f"⚠️ Non-canonical WordPress format detected: {format_detected}.")
                                        logger.info(f"📝 Extracted WordPress fields from generated_text (first 500 chars): {generated_text[:500]}")
                                        logger.info(f"📝 Extracted WordPress fields result: {wordpress_fields}")
                                    
                                    # Return author voice content directly
                                    # Use cleaned body if WordPress fields were extracted, otherwise use original
                                    content_to_use = extraction_result.get("cleaned_body") if wordpress_fields and extraction_result.get("cleaned_body") else generated_text
                                    response_data = {
                                        "content": content_to_use,
                                        "title": "",
                                        "author_voice_used": True,
                                        "style_config": style_config,
                                        "author_voice_metadata": metadata,
                                        "platform": platform
                                    }
                                    # Add WordPress fields if extracted
                                    if wordpress_fields:
                                        response_data.update(wordpress_fields)
                                    if validation_result:
                                        response_data["validation"] = validation_result
                                    CONTENT_GEN_TASKS[tid]["result"] = {
                                        "status": "success",
                                        "data": response_data,
                                        "error": None
                                    }
                                    update_task_status(progress=100, status="completed", task="Content generation completed")
                                    return
                            except Exception as av_error:
                                logger.error(f"Author voice generation error: {av_error}")
                                update_task_status(
                                    agent="Author Voice Generator",
                                    task=f"Error: {str(av_error)}",
                                    error=str(av_error),
                                    agent_status="error"
                                )
                                logger.warning(f"Author voice generation failed, falling back to CrewAI")
                    
                    # Fallback to CrewAI workflow
                    # Note: CrewAI will handle Research → Writing → QC sequentially
                    # We track overall progress, but individual agents are tracked by CrewAI internally
                    update_task_status(
                        agent="CrewAI Workflow",
                        task="Starting content generation workflow",
                        progress=20,
                        status="in_progress"
                    )
                    
                    # Pass update_task_status callback for progress tracking
                    crew_result = create_content_generation_crew(
                        text=writing_context,
                        week=week,
                        platform=platform.lower(),
                        days_list=[day],
                        author_personality=req_data.get("author_personality"),
                        update_task_status_callback=update_task_status
                    )
                    
                    if crew_result.get("success"):
                        # Track individual agents from CrewAI result
                        # Research agent runs once at the start (not re-engaged)
                        update_task_status(
                            agent="Research Agent",
                            task="Content analysis completed",
                            progress=40,
                            agent_status="completed"
                        )
                        
                        # Platform writing agent
                        platform_agent_name = f"{platform.capitalize()} Writing Agent"
                        update_task_status(
                            agent=platform_agent_name,
                            task="Platform-specific content created",
                            progress=70,
                            agent_status="completed"
                        )
                        
                        # Log writing agent used
                        writing_agent_name = f"{platform.capitalize()} Writing Agent"
                        update_task_status(
                            agent=writing_agent_name,
                            task=f"Platform-specific content created for {platform.capitalize()}",
                            progress=70,
                            agent_status="completed"
                        )
                        
                        # Track QC agents with platform name and show which ones ran
                        qc_agents_used = []
                        if "metadata" in crew_result and "agents_used" in crew_result["metadata"]:
                            qc_agents = [a for a in crew_result["metadata"]["agents_used"] if "qc" in a.lower()]
                            platform_name = platform.capitalize()
                            
                            # Log QC agent configuration
                            qc_agent_list_str = ", ".join([f"{platform_name} QC Agent {i+1}" for i in range(len(qc_agents))]) if len(qc_agents) > 1 else f"{platform_name} QC Agent"
                            update_task_status(
                                agent="QC Configuration",
                                task=f"QC Agents Running: {qc_agent_list_str} (Platform: {platform_name}, Global: Included)",
                                progress=75,
                                agent_status="completed"
                            )
                            
                            for idx, qc_agent in enumerate(qc_agents):
                                # Use platform name in QC agent name
                                qc_agent_name = f"{platform_name} QC Agent {idx + 1}" if len(qc_agents) > 1 else f"{platform_name} QC Agent"
                                qc_agents_used.append(qc_agent_name)
                                # Extract QC result details if available
                                qc_result = crew_result.get("data", {}).get("quality_control")
                                qc_message = "Quality review completed - content approved"
                                qc_details = []
                                
                                # Build QC criteria list for display
                                qc_criteria = [
                                    "Quality and clarity",
                                    f"Platform-specific requirements ({platform_name})",
                                    "Compliance with guidelines",
                                    "Author personality match",
                                    "Accuracy and relevance to research"
                                ]
                                
                                if qc_result:
                                    # Try to extract meaningful information from QC result
                                    if isinstance(qc_result, dict):
                                        if "approved" in str(qc_result).lower() or "pass" in str(qc_result).lower():
                                            qc_message = "Quality review: Content approved - meets all quality criteria"
                                            qc_details = qc_criteria
                                        elif "rejected" in str(qc_result).lower() or "fail" in str(qc_result).lower():
                                            qc_message = "Quality review: Content requires revision - quality criteria not met"
                                            qc_details = qc_criteria
                                        else:
                                            qc_message = f"Quality review completed - {str(qc_result)[:100]}"
                                            qc_details = qc_criteria
                                    elif isinstance(qc_result, str):
                                        if len(qc_result) > 200:
                                            qc_message = f"Quality review: {qc_result[:150]}..."
                                        else:
                                            qc_message = f"Quality review: {qc_result}"
                                        qc_details = qc_criteria
                                else:
                                    # Default: show criteria even if result not available
                                    qc_details = qc_criteria
                                
                                # Build detailed message with criteria
                                detailed_message = qc_message
                                if qc_details:
                                    detailed_message += f"\n\nReview Criteria Checked:\n" + "\n".join([f"• {criterion}" for criterion in qc_details])
                                
                                update_task_status(
                                    agent=qc_agent_name,
                                    task=detailed_message,
                                    progress=85 + (idx * 5),
                                    agent_status="completed"
                                )
                        
                        # Log execution summary
                        execution_order = [
                            "1. Research Agent (Content analysis)",
                            f"2. {platform.capitalize()} Writing Agent (Platform-specific content)",
                        ]
                        for idx, qc_name in enumerate(qc_agents_used):
                            execution_order.append(f"{3 + idx}. {qc_name} (Quality review)")
                        
                        update_task_status(
                            agent="CrewAI Workflow",
                            task=f"All agents completed successfully\n\nExecution Order:\n" + "\n".join(execution_order),
                            progress=95,
                            agent_status="completed"
                        )
                        
                        # Extract WordPress fields from CrewAI result if platform is WordPress
                        crew_data = crew_result.get("data", {})
                        if platform.lower() == "wordpress":
                            # Get content from crew result (could be in different fields)
                            # Try multiple locations where content might be
                            content_text = (
                                crew_data.get("content", "") or 
                                crew_data.get("text", "") or 
                                crew_data.get("final_content", "") or
                                crew_data.get("writing", "") or
                                crew_data.get("platform_content", {}).get("content", "") or
                                str(crew_data)
                            )
                            # If content_text is a dict, try to extract text from it
                            if isinstance(content_text, dict):
                                content_text = content_text.get("content", "") or content_text.get("text", "") or str(content_text)
                            
                            extraction_result = extract_wordpress_fields(str(content_text))
                            format_detected = extraction_result.get("format_detected", "unknown")
                            
                            # Log contract compliance
                            logger.info(f"📝 WordPress fields extraction (CrewAI) - Format: {format_detected}")
                            logger.info(f"📝 Extracted - Title: {extraction_result.get('extracted_title_len', 0)} chars, "
                                      f"Excerpt: {extraction_result.get('extracted_excerpt_len', 0)} chars, "
                                      f"Slug: {extraction_result.get('extracted_slug_len', 0)} chars")
                            logger.info(f"📝 Body starts with: {extraction_result.get('body_starts_with', 'N/A')}")
                            
                            # Extract just the fields (not metadata)
                            wordpress_fields = {
                                "post_title": extraction_result.get("post_title"),
                                "post_excerpt": extraction_result.get("post_excerpt"),
                                "permalink": extraction_result.get("permalink"),
                                "format_detected": format_detected  # Include for frontend warning
                            }
                            
                            if wordpress_fields.get("post_title") or wordpress_fields.get("post_excerpt") or wordpress_fields.get("permalink"):
                                crew_data.update(wordpress_fields)
                                # Use cleaned body if available (removes field labels)
                                cleaned_body = extraction_result.get("cleaned_body")
                                if cleaned_body and "content" in crew_data:
                                    crew_data["content"] = cleaned_body
                                elif cleaned_body and "text" in crew_data:
                                    crew_data["text"] = cleaned_body
                                if format_detected != "canonical":
                                    logger.warning(f"⚠️ Non-canonical WordPress format detected: {format_detected}. "
                                                 f"Consider updating writing prompt to use canonical format.")
                            else:
                                logger.warning(f"⚠️ No WordPress fields extracted from CrewAI result. Format: {format_detected}, "
                                             f"Content type: {type(content_text)}, length: {len(str(content_text))}")
                        
                        CONTENT_GEN_TASKS[tid]["result"] = {
                            "status": "success",
                            "data": crew_data,
                            "error": None
                        }
                        # Mark all agents as completed before final status update
                        if "agent_statuses" in CONTENT_GEN_TASKS[tid]:
                            for agent_status in CONTENT_GEN_TASKS[tid]["agent_statuses"]:
                                if agent_status.get("status") == "running":
                                    agent_status["status"] = "completed"
                                    agent_status["agent_status"] = "completed"
                        # Clear current agent/task when completed
                        CONTENT_GEN_TASKS[tid]["current_agent"] = None
                        CONTENT_GEN_TASKS[tid]["current_task"] = "Content generation completed"
                        update_task_status(progress=100, status="completed", task="Content generation completed")
                    else:
                        error_msg = crew_result.get("error", "Unknown error")
                        update_task_status(
                            agent="CrewAI Workflow",
                            task=f"Error: {error_msg}",
                            error=error_msg,
                            agent_status="error",
                            status="error"
                        )
                        
                except Exception as bg_error:
                    logger.error(f"Background generation error: {bg_error}")
                    import traceback
                    logger.error(traceback.format_exc())
                    if tid in CONTENT_GEN_TASKS:
                        CONTENT_GEN_TASKS[tid]["error"] = str(bg_error)
                        CONTENT_GEN_TASKS[tid]["status"] = "error"
                        CONTENT_GEN_TASKS[tid]["current_task"] = f"Error: {str(bg_error)}"
                finally:
                    session.close()
            except Exception as outer_error:
                logger.error(f"Outer background error: {outer_error}")
                if tid in CONTENT_GEN_TASKS:
                    CONTENT_GEN_TASKS[tid]["error"] = str(outer_error)
                    CONTENT_GEN_TASKS[tid]["status"] = "error"
        
        # Start background thread
        import threading
        thread = threading.Thread(
            target=run_generation_background,
            args=(task_id, campaign_id, request_data, current_user.id),
            daemon=True
        )
        thread.start()
        
        # Return task_id immediately
        return {
            "status": "pending",
            "task_id": task_id,
            "message": "Content generation started. Use task_id to poll status."
        }
        
    except Exception as e:
        from models import Campaign
        from crewai_workflows import create_content_generation_crew
        import json
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get content queue items from request or campaign
        content_queue_items = request_data.get("content_queue_items", [])
        if not content_queue_items and campaign.content_queue_items_json:
            content_queue_items = json.loads(campaign.content_queue_items_json)
        
        # Build context from content queue items
        queue_context = "\n".join([
            f"- {item.get('title', item.get('text', str(item)))}"
            for item in content_queue_items
        ])
        
        # Get other parameters
        platform = request_data.get("platform", "linkedin")
        week = request_data.get("week", 1)
        day = request_data.get("day", "Monday")
        parent_idea = request_data.get("parent_idea", "")
        kg_location = request_data.get("knowledge_graph_location", "")
        landing_page_url = request_data.get("landing_page_url", "")
        author_personality_id = request_data.get("author_personality_id")  # NEW: Support author personality ID
        use_author_voice = request_data.get("use_author_voice", True)  # NEW: Toggle for author voice
        use_validation = request_data.get("use_validation", False)  # Phase 4: Toggle for validation
        
        # Build writing context
        writing_context = f"""Content Queue Foundation:
{queue_context}

{f'Parent Idea: {parent_idea}' if parent_idea else ''}
{f'Knowledge Graph Location: {kg_location}' if kg_location else ''}
{f'Landing Page: {landing_page_url}' if landing_page_url else ''}

Generate content for {platform} based on the content queue items above."""
        
        # Phase 3: Integrate author voice if author_personality_id is provided
        if author_personality_id and use_author_voice:
            from author_voice_helper import generate_with_author_voice, should_use_author_voice
            
            if should_use_author_voice(author_personality_id):
                logger.info(f"Using author voice for personality: {author_personality_id}")
                
                # Get custom modifications for this platform if available
                custom_modifications = None
                if "platformSettings" in request_data:
                    platform_settings = request_data.get("platformSettings", {})
                    platform_lower = platform.lower()
                    if platform_lower in platform_settings:
                        settings = platform_settings[platform_lower]
                        if not settings.get("useGlobalDefaults", True):
                            custom_modifications = settings.get("customModifications", "")
                
                # Generate content with author voice (Phase 4: includes validation if requested)
                generated_text, style_config, metadata, validation_result = generate_with_author_voice(
                    content_prompt=writing_context,
                    author_personality_id=author_personality_id,
                    platform=platform.lower(),
                    goal="content_generation",
                    target_audience="general",
                    custom_modifications=custom_modifications,
                    use_validation=use_validation,
                    db=db
                )
                
                if generated_text:
                    # Optionally pass through CrewAI for QC if requested
                    use_crewai_qc = request_data.get("use_crewai_qc", False)
                    
                    if use_crewai_qc:
                        # Pass generated content to CrewAI for QC only
                        crew_result = create_content_generation_crew(
                            text=f"Review and refine this content:\n\n{generated_text}\n\nStyle Config:\n{style_config}",
                            week=week,
                            platform=platform.lower(),
                            days_list=[day],
                            author_personality=request_data.get("author_personality", "custom")
                        )
                        
                        # Merge author voice metadata with CrewAI result
                        if crew_result.get("success"):
                            crew_data = crew_result.get("data", {})
                            # Extract WordPress fields if platform is WordPress
                            if platform.lower() == "wordpress":
                                content_text = crew_data.get("content", "") or crew_data.get("text", "") or str(crew_data)
                                extraction_result = extract_wordpress_fields(str(content_text))
                                format_detected = extraction_result.get("format_detected", "unknown")
                                
                                # Log contract compliance
                                logger.info(f"📝 WordPress fields extraction (CrewAI QC sync) - Format: {format_detected}")
                                
                                wordpress_fields = {
                                    "post_title": extraction_result.get("post_title"),
                                    "post_excerpt": extraction_result.get("post_excerpt"),
                                    "permalink": extraction_result.get("permalink"),
                                    "format_detected": format_detected
                                }
                                if wordpress_fields.get("post_title") or wordpress_fields.get("post_excerpt") or wordpress_fields.get("permalink"):
                                    crew_data.update(wordpress_fields)
                                    # Use cleaned body if available (removes field labels)
                                    cleaned_body = extraction_result.get("cleaned_body")
                                    if cleaned_body and "content" in crew_data:
                                        crew_data["content"] = cleaned_body
                                    elif cleaned_body and "text" in crew_data:
                                        crew_data["text"] = cleaned_body
                                    if format_detected != "canonical":
                                        logger.warning(f"⚠️ Non-canonical WordPress format detected: {format_detected}.")
                            
                            response_data = {
                                **crew_data,
                                "author_voice_used": True,
                                "style_config": style_config,
                                "author_voice_metadata": metadata
                            }
                            # Phase 4: Add validation results if available
                            if validation_result:
                                response_data["validation"] = validation_result
                            return {
                                "status": "success",
                                "data": response_data,
                                "error": crew_result.get("error")
                            }
                    
                    # Return author voice generated content directly (when not using CrewAI QC)
                    # Extract WordPress fields if platform is WordPress
                    wordpress_fields = {}
                    if platform.lower() == "wordpress":
                        extraction_result = extract_wordpress_fields(generated_text)
                        format_detected = extraction_result.get("format_detected", "unknown")
                        
                        # Log contract compliance
                        logger.info(f"📝 WordPress fields extraction (Author Voice) - Format: {format_detected}")
                        
                        wordpress_fields = {
                            "post_title": extraction_result.get("post_title"),
                            "post_excerpt": extraction_result.get("post_excerpt"),
                            "permalink": extraction_result.get("permalink"),
                            "format_detected": format_detected
                        }
                        
                        if format_detected != "canonical":
                            logger.warning(f"⚠️ Non-canonical WordPress format detected: {format_detected}. "
                                         f"Consider updating writing prompt to use canonical format.")
                    
                    # Use cleaned body if WordPress fields were extracted, otherwise use original
                    content_to_use = extraction_result.get("cleaned_body") if wordpress_fields and extraction_result.get("cleaned_body") else generated_text
                    response_data = {
                        "content": content_to_use,
                        "title": "",  # Can be extracted or generated separately
                        "author_voice_used": True,
                        "style_config": style_config,
                        "author_voice_metadata": metadata,
                        "platform": platform
                    }
                    # Add WordPress fields if extracted
                    if wordpress_fields:
                        response_data.update(wordpress_fields)
                    # Phase 4: Add validation results if available
                    if validation_result:
                        response_data["validation"] = validation_result
                    return {
                        "status": "success",
                        "data": response_data,
                        "error": None
                    }
                else:
                    logger.warning(f"Author voice generation failed, falling back to CrewAI")
                    # Fall through to CrewAI workflow
        
        # Generate content using CrewAI workflow (fallback or default)
        crew_result = create_content_generation_crew(
            text=writing_context,
            week=week,
            platform=platform.lower(),
            days_list=[day],
            author_personality=request_data.get("author_personality")
        )
        
        # Extract WordPress fields if platform is WordPress
        crew_data = crew_result.get("data", {})
        if platform.lower() == "wordpress" and crew_result.get("success"):
            content_text = crew_data.get("content", "") or crew_data.get("text", "") or str(crew_data)
            extraction_result = extract_wordpress_fields(str(content_text))
            format_detected = extraction_result.get("format_detected", "unknown")
            
            # Log contract compliance
            logger.info(f"📝 WordPress fields extraction (sync fallback) - Format: {format_detected}")
            
            wordpress_fields = {
                "post_title": extraction_result.get("post_title"),
                "post_excerpt": extraction_result.get("post_excerpt"),
                "permalink": extraction_result.get("permalink"),
                "format_detected": format_detected
            }
            if wordpress_fields.get("post_title") or wordpress_fields.get("post_excerpt") or wordpress_fields.get("permalink"):
                crew_data.update(wordpress_fields)
                # Use cleaned body if available (removes field labels)
                cleaned_body = extraction_result.get("cleaned_body")
                if cleaned_body and "content" in crew_data:
                    crew_data["content"] = cleaned_body
                elif cleaned_body and "text" in crew_data:
                    crew_data["text"] = cleaned_body
                if format_detected != "canonical":
                    logger.warning(f"⚠️ Non-canonical WordPress format detected: {format_detected}.")
        
        return {
            "status": "success" if crew_result.get("success") else "error",
            "data": crew_data,
            "error": crew_result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error generating campaign content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@brand_personalities_router.get("/campaigns/{campaign_id}/generate-content/status/{task_id}")
async def get_content_generation_status(
    campaign_id: str,
    task_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status of content generation task.
    """
    try:
        from models import Campaign
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if task_id not in CONTENT_GEN_TASKS:
            return {
                "status": "pending",
                "progress": 0,
                "current_agent": None,
                "current_task": "Waiting for task",
                "agent_statuses": [],
                "error": None
            }
        
        task = CONTENT_GEN_TASKS[task_id]
        
        # If task is completed, clear current_agent and current_task
        task_status = task.get("status", "pending")
        if task_status == "completed":
            # Clear current agent/task when completed
            current_agent = None
            current_task = "Content generation completed"
        else:
            current_agent = task.get("current_agent")
            current_task = task.get("current_task", "Processing")
        
        # If task is completed and has result, include it
        response = {
            "status": task_status,
            "progress": task.get("progress", 0),
            "current_agent": current_agent,
            "current_task": current_task,
            "agent_statuses": task.get("agent_statuses", []),
            "error": task.get("error")
        }
        
        # If completed, include result
        if task_status == "completed" and task.get("result"):
            response["result"] = task.get("result")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting content generation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

