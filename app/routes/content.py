"""
Content CRUD, scheduling, and publishing endpoints.
Split from original content.py which also contained generation routes (now in content_generation.py).
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.utils.wordpress_body import sanitize_wordpress_body

logger = logging.getLogger(__name__)

content_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Scheduled Posts Endpoints
@content_router.get("/scheduled-posts")
def get_scheduled_posts(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all scheduled posts for the authenticated user (only from campaigns that still exist)"""
    try:
        from models import Content, Campaign
        from datetime import datetime
        
        logger.info(f"📋 Fetching scheduled posts for user {current_user.id}")
        
        # Only return content that is scheduled (not yet published). Published posts appear on Published tab.
        existing_campaign_ids = db.query(Campaign.campaign_id).distinct().all()
        existing_campaign_ids = [r[0] for r in existing_campaign_ids]
        if not existing_campaign_ids:
            scheduled_posts = []
        else:
            scheduled_posts = db.query(Content).filter(
                Content.user_id == current_user.id,
                Content.campaign_id.in_(existing_campaign_ids),
                Content.status == "scheduled"
            ).order_by(Content.schedule_time.asc()).all()
        
        logger.info(f"📋 Found {len(scheduled_posts)} scheduled posts for user {current_user.id}")
        
        posts_data = []
        for post in scheduled_posts:
            posts_data.append({
                "id": post.id,
                "title": post.title or "",
                "content": post.content or "",
                "platform": post.platform,
                "schedule_time": post.schedule_time.isoformat() if post.schedule_time else None,
                "day": post.day,
                "week": post.week,
                "status": post.status or "draft",
                "image_url": post.image_url or "",
                "campaign_id": post.campaign_id,
                "can_edit": post.can_edit if hasattr(post, 'can_edit') else True,
                "is_draft": post.is_draft if hasattr(post, 'is_draft') else True,
            })
            logger.info(f"📋 Scheduled post: id={post.id}, campaign_id={post.campaign_id}, status={post.status}, has_image={bool(post.image_url)}")
        
        logger.info(f"✅ Returning {len(posts_data)} scheduled posts")
        
        return {
            "status": "success",
            "message": {
                "posts": posts_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching scheduled posts: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scheduled posts: {str(e)}"
        )


@content_router.get("/published-posts")
def get_published_posts(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all published posts for the user. Returns minimal data: title + link only (no stored content)."""
    try:
        from models import Content, Campaign
        
        logger.info(f"📋 Fetching published posts for user {current_user.id}")
        
        existing_campaign_ids = db.query(Campaign.campaign_id).distinct().all()
        existing_campaign_ids = [r[0] for r in existing_campaign_ids]
        if not existing_campaign_ids:
            published_posts = []
        else:
            published_posts = db.query(Content).filter(
                Content.user_id == current_user.id,
                Content.campaign_id.in_(existing_campaign_ids),
                Content.status.in_(["posted", "published"])
            ).order_by(Content.date_upload.desc()).all()
        
        posts_data = []
        for post in published_posts:
            posts_data.append({
                "id": post.id,
                "title": post.title or "",
                "post_url": getattr(post, "post_url", None) or "",
                "platform": post.platform,
                "published_at": post.date_upload.isoformat() if post.date_upload else None,
                "campaign_id": post.campaign_id,
            })
        
        logger.info(f"✅ Returning {len(posts_data)} published posts")
        
        return {
            "status": "success",
            "message": {
                "posts": posts_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching published posts: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch published posts: {str(e)}"
        )


@content_router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently delete a post. Cannot be undone. For moving back to content queue use POST /posts/{id}/return-to-editing."""
    try:
        from sqlalchemy import text
        
        logger.info(f"🗑️ Permanently deleting post {post_id} for user {current_user.id}")
        
        check_query = text("""
            SELECT id FROM content 
            WHERE id = :post_id AND user_id = :user_id
            LIMIT 1
        """)
        check_result = db.execute(check_query, {
            "post_id": post_id,
            "user_id": current_user.id
        }).first()
        
        if not check_result:
            raise HTTPException(
                status_code=404,
                detail="Post not found or access denied"
            )
        
        delete_query = text("DELETE FROM content WHERE id = :post_id AND user_id = :user_id")
        db.execute(delete_query, {
            "post_id": post_id,
            "user_id": current_user.id
        })
        db.commit()
        
        logger.info(f"✅ Post {post_id} permanently deleted")
        
        return {
            "status": "success",
            "message": "Post deleted permanently."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete post: {str(e)}"
        )


@content_router.post("/posts/{post_id}/return-to-editing")
def return_post_to_editing(
    post_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Move a scheduled post back to content queue (draft). Does not delete; post reappears in The Plan."""
    try:
        from sqlalchemy import text
        
        logger.info(f"📝 Returning post {post_id} to editing for user {current_user.id}")
        
        check_query = text("""
            SELECT id FROM content 
            WHERE id = :post_id AND user_id = :user_id
            LIMIT 1
        """)
        check_result = db.execute(check_query, {
            "post_id": post_id,
            "user_id": current_user.id
        }).first()
        
        if not check_result:
            raise HTTPException(
                status_code=404,
                detail="Post not found or access denied"
            )
        
        update_query = text("""
            UPDATE content SET status = 'draft' WHERE id = :post_id AND user_id = :user_id
        """)
        db.execute(update_query, {
            "post_id": post_id,
            "user_id": current_user.id
        })
        db.commit()
        
        logger.info(f"✅ Post {post_id} returned to content queue")
        
        return {
            "status": "success",
            "message": "Post moved back to content queue. You can edit it in The Plan."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error returning post to editing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to return post to editing: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/schedule-content")
async def schedule_campaign_content(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule content items for a campaign - saves them to database with 'scheduled' status"""
    try:
        from models import Content, Campaign
        from datetime import datetime
        import json
        
        # Verify campaign exists and belongs to user
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found"
            )
        
        # Get content items from request
        content_items = request_data.get("content_items", [])
        
        if not content_items:
            raise HTTPException(
                status_code=400,
                detail="No content items provided"
            )
        
        scheduled_count = 0
        errors = []
        for item in content_items:
            try:
                # Parse schedule time
                schedule_time_str = item.get("schedule_time")
                schedule_time = None
                if schedule_time_str:
                    try:
                        # Try ISO format first
                        if 'T' in schedule_time_str:
                            schedule_time = datetime.fromisoformat(schedule_time_str.replace('Z', '+00:00'))
                        else:
                            # Try other formats
                            try:
                                schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%dT%H:%M:%S")
                            except:
                                schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%d %H:%M:%S")
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse schedule_time '{schedule_time_str}': {parse_error}")
                        # Default to today at 9 AM if parsing fails
                        schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    # Default to today at 9 AM
                    schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                
                # MySQL doesn't support timezone-aware datetimes, so convert to naive UTC
                from datetime import timezone
                if schedule_time.tzinfo is not None:
                    schedule_time = schedule_time.astimezone(timezone.utc).replace(tzinfo=None)
                # If already naive, assume it's UTC and use as-is
                
                # Prefer matching by content id (database_id) when frontend sends it so we update the exact row
                content_id = item.get("id") or item.get("database_id")
                if content_id is not None:
                    try:
                        if isinstance(content_id, int):
                            cid = content_id
                        elif isinstance(content_id, str) and "-" in content_id:
                            # Composite id e.g. "week-1-Tuesday-wordpress-190" -> use trailing number
                            cid = int(content_id.rsplit("-", 1)[-1])
                        else:
                            cid = int(content_id)
                        existing_content = db.query(Content).filter(
                            Content.id == cid,
                            Content.campaign_id == campaign_id,
                            Content.user_id == current_user.id
                        ).first()
                    except (TypeError, ValueError, IndexError):
                        existing_content = None
                else:
                    existing_content = None
                if not existing_content:
                    # Normalize day to title case so "tuesday" and "Tuesday" both match
                    day_val = item.get("day", "Monday")
                    if isinstance(day_val, str) and day_val:
                        day_val = day_val.strip().capitalize()
                    else:
                        day_val = "Monday"
                    # Match by campaign_id, week, day, platform
                    existing_content = db.query(Content).filter(
                        Content.campaign_id == campaign_id,
                        Content.week == item.get("week", 1),
                        Content.day == day_val,
                        Content.platform == (item.get("platform", "linkedin") or "linkedin").lower(),
                        Content.user_id == current_user.id
                    ).first()
                
                if existing_content:
                    # Update existing content
                    content_text = item.get("description") or item.get("content", "")
                    title_text = item.get("title", "")
                    # WordPress: never save raw model output as body
                    if (item.get("platform", "linkedin") or "").lower() == "wordpress":
                        content_text = sanitize_wordpress_body(content_text)
                    
                    # Validate and update content - ensure we don't overwrite with empty strings
                    if content_text and content_text.strip():
                        existing_content.content = content_text
                    elif not existing_content.content or not existing_content.content.strip():
                        # Only set default if content is truly empty
                        existing_content.content = f"Content for {item.get('platform', 'linkedin').title()} - {item.get('day', 'Monday')}"
                    
                    if title_text and title_text.strip():
                        existing_content.title = title_text
                    elif not existing_content.title or not existing_content.title.strip():
                        # Only set default if title is truly empty
                        existing_content.title = f"{item.get('platform', 'linkedin').title()} Post - {item.get('day', 'Monday')}"
                    
                    existing_content.schedule_time = schedule_time
                    existing_content.status = "scheduled"  # Move from draft to scheduled
                    existing_content.is_draft = False
                    existing_content.can_edit = True  # Can still edit scheduled content
                    # Update image if provided (support both field names) - ALWAYS update even if empty to preserve existing
                    image_url = item.get("image") or item.get("image_url")
                    if image_url:
                        existing_content.image_url = image_url
                        logger.info(f"💾 Updated image_url when scheduling: {image_url[:100]}...")
                    else:
                        logger.info(f"⚠️ No image_url provided when scheduling existing content (keeping existing: {existing_content.image_url[:100] if existing_content.image_url else 'none'}...)")
                    logger.info(f"✅ Updated existing content to scheduled: week={item.get('week', 1)}, day={item.get('day', 'Monday')}, platform={item.get('platform', 'linkedin')}, has_image={bool(image_url or existing_content.image_url)}")
                    scheduled_count += 1
                else:
                    # Validate required fields
                    content_text = item.get("description") or item.get("content", "")
                    title_text = item.get("title", "")
                    
                    if not content_text or not content_text.strip():
                        logger.warning(f"Skipping item with empty content: {item.get('id', 'unknown')}")
                        continue
                    
                    # WordPress: never save raw model output as body
                    if (item.get("platform", "linkedin") or "").lower() == "wordpress":
                        content_text = sanitize_wordpress_body(content_text)
                    
                    if not title_text or not title_text.strip():
                        title_text = f"{item.get('platform', 'linkedin').title()} Post - {item.get('day', 'Monday')}"
                    
                    # Create new content
                    image_url = item.get("image") or item.get("image_url")
                    if image_url:
                        logger.info(f"💾 Saving image_url when scheduling new content: {image_url[:100]}...")
                    else:
                        logger.info(f"⚠️ No image_url provided when scheduling new content")
                    try:
                        new_content = Content(
                            user_id=current_user.id,
                            campaign_id=campaign_id,
                            week=item.get("week", 1),
                            day=item.get("day", "Monday"),
                            content=content_text,
                            title=title_text,
                            status="scheduled",  # Status: scheduled (was draft, now committed)
                            date_upload=datetime.now().replace(tzinfo=None),  # MySQL doesn't support timezone-aware datetimes
                            platform=item.get("platform", "linkedin").lower(),
                            file_name=f"{campaign_id}_{item.get('week', 1)}_{item.get('day', 'Monday')}_{item.get('platform', 'linkedin')}.txt",
                            file_type="text",
                            platform_post_no=item.get("platform_post_no", "1"),
                            schedule_time=schedule_time,
                            image_url=image_url,  # Support both field names
                            is_draft=False,  # No longer a draft
                            can_edit=True,  # Can still edit scheduled content
                            knowledge_graph_location=item.get("knowledge_graph_location"),
                            parent_idea=item.get("parent_idea"),
                            landing_page_url=item.get("landing_page_url")
                        )
                        db.add(new_content)
                        logger.info(f"✅ Created new scheduled content: week={item.get('week', 1)}, day={item.get('day', 'Monday')}, platform={item.get('platform', 'linkedin')}, has_image={bool(image_url)}")
                        scheduled_count += 1
                    except Exception as create_error:
                        logger.error(f"❌ Error creating Content object for item {item.get('id', 'unknown')}: {create_error}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        errors.append(f"Item {item.get('id', 'unknown')}: Failed to create content - {str(create_error)}")
                        continue
            except Exception as item_error:
                logger.error(f"Error processing content item {item.get('id', 'unknown')}: {item_error}")
                import traceback
                traceback.print_exc()
                errors.append(f"Item {item.get('id', 'unknown')}: {str(item_error)}")
                continue  # Continue with next item
        
        db.commit()
        
        if errors:
            logger.warning(f"Scheduled {scheduled_count} items with {len(errors)} errors")
            return {
                "status": "partial_success",
                "message": f"Successfully scheduled {scheduled_count} content item(s), {len(errors)} failed",
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"Successfully scheduled {scheduled_count} content item(s)"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error scheduling content: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule content: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/post-now")
async def post_content_now(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Post content immediately (skip scheduling) - uses same posting workflow as scheduled posts.
    This endpoint is for testing purposes to post content immediately without waiting for schedule_time.
    """
    try:
        from models import Content, Campaign, PlatformConnection, PlatformEnum
        from datetime import datetime
        import requests
        
        # Verify campaign exists and belongs to user
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found"
            )
        
        # Get content item from request
        content_id = request_data.get("content_id")
        content_item = request_data.get("content_item")
        wordpress_fields = request_data.get("wordpress_fields")  # For passing category_id/author_id when using contentId
        
        logger.info(f"📤 Post Now request received: content_id={content_id}, has_content_item={bool(content_item)}, has_wordpress_fields={bool(wordpress_fields)}")
        
        # If content_id provided, fetch from database
        if content_id:
            content = db.query(Content).filter(
                Content.id == content_id,
                Content.campaign_id == campaign_id,
                Content.user_id == current_user.id
            ).first()
            
            if not content:
                raise HTTPException(
                    status_code=404,
                    detail="Content not found"
                )
            
            content_text = content.content or ""
            title = content.title or ""
            platform = content.platform or "linkedin"
            image_url = content.image_url
        elif content_item:
            # Use provided content item (for articles not yet saved to DB)
            content_text = content_item.get("description") or content_item.get("content", "")
            title = content_item.get("title", "")
            platform = content_item.get("platform", "linkedin").lower()
            image_url = content_item.get("image") or content_item.get("image_url")
            content_id = None
        else:
            logger.error(f"❌ Post Now: Neither content_id nor content_item provided. Request data: {request_data}")
            raise HTTPException(
                status_code=400,
                detail="Either content_id or content_item is required"
            )
        
        logger.info(f"📤 Post Now: content_text length={len(content_text) if content_text else 0}, platform={platform}, has_image={bool(image_url)}")
        
        if not content_text or not content_text.strip():
            logger.error(f"❌ Post Now: Content text is empty or missing")
            raise HTTPException(
                status_code=400,
                detail="Content text is required"
            )
        
        # Route to appropriate platform posting function
        platform_lower = platform.lower()
        post_url = None  # Will be set by each platform's posting logic
        
        if platform_lower == "linkedin":
            # Call LinkedIn posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if not connection or not connection.access_token:
                raise HTTPException(
                    status_code=400,
                    detail="LinkedIn not connected. Please connect your LinkedIn account first."
                )
            
            api_url = "https://api.linkedin.com/v2/ugcPosts"
            headers = {
                "Authorization": f"Bearer {connection.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            post_data = {
                "author": f"urn:li:person:{current_user.id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content_text},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
            
            if image_url:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "media": image_url
                }]
            
            response = requests.post(api_url, json=post_data, headers=headers, timeout=30)
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"LinkedIn API error: {response.status_code} - {response.text}"
                )
            
            post_id = response.json().get("id")
            platform_name = "LinkedIn"
            # LinkedIn post URL format: https://www.linkedin.com/feed/update/{post_id}
            post_url = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None
            
        elif platform_lower == "twitter" or platform_lower == "x":
            # Call Twitter posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.TWITTER
            ).first()
            
            if not connection or not connection.access_token or not connection.refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="Twitter not connected. Please connect your Twitter account first."
                )
            
            from requests_oauthlib import OAuth1Session
            from dotenv import load_dotenv
            import os
            load_dotenv()
            
            oauth = OAuth1Session(
                os.getenv("TWITTER_API_KEY"),
                client_secret=os.getenv("TWITTER_API_SECRET"),
                resource_owner_key=connection.access_token,
                resource_owner_secret=connection.refresh_token
            )
            
            api_url = "https://api.twitter.com/2/tweets"
            tweet_data = {"text": content_text[:280]}
            
            if image_url:
                media_url = "https://upload.twitter.com/1.1/media/upload.json"
                media_response = oauth.post(media_url, files={"media": requests.get(image_url).content})
                if media_response.status_code == 200:
                    media_id = media_response.json().get("media_id_string")
                    tweet_data["media"] = {"media_ids": [media_id]}
            
            response = oauth.post(api_url, json=tweet_data, timeout=30)
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Twitter API error: {response.status_code} - {response.text}"
                )
            
            post_id = response.json().get("data", {}).get("id")
            platform_name = "Twitter"
            # Twitter post URL format: https://twitter.com/user/status/{tweet_id}
            # Note: We don't have username, so we'll use a generic format
            post_url = f"https://twitter.com/i/web/status/{post_id}" if post_id else None
            
        elif platform_lower == "instagram":
            # Call Instagram posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.INSTAGRAM
            ).first()
            
            if not connection or not connection.access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram not connected. Please connect your Instagram account first."
                )
            
            # Validate platform_user_id - must be numeric Instagram Business Account ID
            if not connection.platform_user_id:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram Business Account ID is missing. Please reconnect your Instagram account."
                )
            
            # Check if platform_user_id is numeric (Instagram Business Account IDs are numeric)
            if not connection.platform_user_id.isdigit():
                logger.warning(f"⚠️ Invalid Instagram Business Account ID detected: '{connection.platform_user_id}' (expected numeric ID, got display name). Attempting to auto-fix...")
                
                # Try to auto-fix by fetching the Instagram Business Account ID from existing access token
                try:
                    # Get user's Facebook Pages (Instagram Business Accounts are linked to Pages)
                    pages_url = "https://graph.facebook.com/v18.0/me/accounts"
                    pages_params = {"access_token": connection.access_token}
                    pages_response = requests.get(pages_url, params=pages_params, timeout=30)
                    
                    instagram_business_account_id = None
                    page_access_token = None
                    
                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        pages = pages_data.get("data", [])
                        
                        logger.info(f"🔍 Found {len(pages)} Facebook Pages, searching for Instagram Business Account...")
                        
                        # Find the first page with an Instagram Business Account
                        for page in pages:
                            page_id = page.get("id")
                            page_access_token = page.get("access_token")
                            
                            if not page_id or not page_access_token:
                                continue
                            
                            # Get Instagram Business Account for this page
                            instagram_url = f"https://graph.facebook.com/v18.0/{page_id}"
                            instagram_params = {
                                "fields": "instagram_business_account",
                                "access_token": page_access_token
                            }
                            instagram_response = requests.get(instagram_url, params=instagram_params, timeout=30)
                            
                            if instagram_response.status_code == 200:
                                instagram_data = instagram_response.json()
                                if instagram_data.get("instagram_business_account"):
                                    instagram_business_account_id = instagram_data["instagram_business_account"]["id"]
                                    logger.info(f"✅ Auto-fixed: Found Instagram Business Account ID: {instagram_business_account_id}")
                                    # Update the connection with the correct ID and page access token
                                    connection.platform_user_id = instagram_business_account_id
                                    connection.access_token = page_access_token  # Use page access token for Instagram API
                                    db.commit()
                                    logger.info(f"✅ Updated Instagram connection with correct Business Account ID")
                                    break
                    
                    if not instagram_business_account_id:
                        logger.error(f"❌ Could not auto-fix Instagram Business Account ID. No Instagram Business Account found linked to Facebook Pages.")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections. Make sure your Instagram account is linked to a Facebook Page."
                        )
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Error auto-fixing Instagram Business Account ID: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    )
                except Exception as e:
                    logger.error(f"❌ Unexpected error auto-fixing Instagram Business Account ID: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid Instagram Business Account ID. The stored ID '{connection.platform_user_id}' appears to be a display name instead of a numeric ID. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    )
            
            # Instagram requires image, so check if we have one
            if not image_url:
                raise HTTPException(
                    status_code=400,
                    detail="Instagram posts require an image. Please generate an image first."
                )
            
            logger.info(f"📸 Posting to Instagram Business Account ID: {connection.platform_user_id}")
            
            # Create media container
            container_url = f"https://graph.facebook.com/v18.0/{connection.platform_user_id}/media"
            container_params = {
                "image_url": image_url,
                "caption": content_text,
                "access_token": connection.access_token
            }
            
            container_response = requests.post(container_url, params=container_params, timeout=30)
            
            if container_response.status_code not in [200, 201]:
                error_text = container_response.text
                # Parse error for better user message
                try:
                    error_json = container_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    error_code = error_json.get("error", {}).get("code", "")
                    if "does not exist" in error_message or "missing permissions" in error_message:
                        user_friendly_error = f"Instagram Business Account ID '{connection.platform_user_id}' is invalid or you don't have permissions. Please reconnect your Instagram account in Account Settings > Platform Connections."
                    else:
                        user_friendly_error = f"Instagram API error: {error_message}"
                except:
                    user_friendly_error = f"Instagram API error: {error_text[:200]}"
                
                logger.error(f"❌ Instagram container creation failed: {error_text}")
                raise HTTPException(
                    status_code=400,
                    detail=user_friendly_error
                )
            
            creation_id = container_response.json().get("id")
            
            # Publish the media
            publish_url = f"https://graph.facebook.com/v18.0/{connection.platform_user_id}/media_publish"
            publish_params = {
                "creation_id": creation_id,
                "access_token": connection.access_token
            }
            
            publish_response = requests.post(publish_url, params=publish_params, timeout=30)
            
            if publish_response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Instagram publish error: {publish_response.status_code} - {publish_response.text}"
                )
            
            post_id = publish_response.json().get("id")
            platform_name = "Instagram"
            # Instagram post URL format: https://www.instagram.com/p/{shortcode}/
            # Note: We only have the media ID, not the shortcode, so we'll construct a generic URL
            post_url = f"https://www.instagram.com/p/{post_id}/" if post_id else None
            
        elif platform_lower == "facebook":
            # Call Facebook posting logic (posts to Facebook Page)
            logger.info(f"📘 Facebook posting requested for user {current_user.id}")
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.FACEBOOK
            ).first()
            
            logger.info(f"📘 Facebook connection found: {connection is not None}, has_token: {connection.access_token is not None if connection else False}")
            
            if not connection or not connection.access_token:
                logger.error(f"❌ Facebook not connected for user {current_user.id}")
                raise HTTPException(
                    status_code=400,
                    detail="Facebook not connected. Please connect your Facebook account first."
                )
            
            # Facebook requires a Page ID to post to
            # First, get user's pages to find the page to post to
            pages_url = "https://graph.facebook.com/v18.0/me/accounts"
            pages_params = {"access_token": connection.access_token}
            logger.info(f"📘 Fetching Facebook Pages for user {current_user.id}...")
            pages_response = requests.get(pages_url, params=pages_params, timeout=30)
            
            if pages_response.status_code != 200:
                error_text = pages_response.text
                logger.error(f"❌ Facebook Pages API failed (status {pages_response.status_code}): {error_text[:500]}")
                
                # Try to parse error for better message
                try:
                    error_json = pages_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    error_code = error_json.get("error", {}).get("code", "")
                    
                    # Check if it's a permissions issue
                    if "permission" in error_message.lower() or error_code in ["200", "10"]:
                        detail = f"Missing Facebook permissions. The error was: {error_message}. Please disconnect and reconnect your Facebook account, ensuring you grant pages_manage_posts permission."
                    else:
                        detail = f"Failed to get Facebook Pages: {error_message}"
                except:
                    detail = f"Failed to get Facebook Pages: {error_text[:200]}"
                
                raise HTTPException(status_code=400, detail=detail)
            
            pages_data = pages_response.json()
            pages = pages_data.get("data", [])
            logger.info(f"📘 Facebook Pages API returned {len(pages)} pages")
            
            if not pages:
                # Check what permissions the token actually has
                try:
                    permissions_url = "https://graph.facebook.com/v18.0/me/permissions"
                    permissions_params = {"access_token": connection.access_token}
                    permissions_response = requests.get(permissions_url, params=permissions_params, timeout=10)
                    
                    if permissions_response.status_code == 200:
                        permissions_data = permissions_response.json()
                        granted_perms = [p.get("permission") for p in permissions_data.get("data", []) if p.get("status") == "granted"]
                        logger.info(f"📘 Granted Facebook permissions: {granted_perms}")
                        
                        required_perms = ["pages_manage_posts"]
                        missing_perms = [p for p in required_perms if p not in granted_perms]
                        
                        if missing_perms:
                            detail = f"No Facebook Pages found. Missing required permissions: {', '.join(missing_perms)}. Please disconnect and reconnect your Facebook account, ensuring you grant ALL requested permissions when Facebook shows the permission screen."
                        else:
                            detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                    else:
                        detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                except Exception as perm_error:
                    logger.warning(f"⚠️ Could not check permissions: {perm_error}")
                    detail = "No Facebook Pages found. Please create a Facebook Page at facebook.com/pages/create and ensure it's connected to your account."
                
                raise HTTPException(status_code=400, detail=detail)
            
            # Use the first page (or could let user select)
            page = pages[0]
            page_id = page.get("id")
            page_access_token = page.get("access_token")
            
            if not page_id or not page_access_token:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get Facebook Page access token"
                )
            
            logger.info(f"📘 Posting to Facebook Page ID: {page_id}")
            
            # Post to Facebook Page
            post_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
            post_params = {
                "message": content_text,
                "access_token": page_access_token
            }
            
            # Add image if available
            if image_url:
                post_params["link"] = image_url
            
            post_response = requests.post(post_url, params=post_params, timeout=30)
            
            if post_response.status_code not in [200, 201]:
                error_text = post_response.text
                try:
                    error_json = post_response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                    user_friendly_error = f"Facebook API error: {error_message}"
                except:
                    user_friendly_error = f"Facebook API error: {error_text[:200]}"
                
                logger.error(f"❌ Facebook post failed: {error_text}")
                raise HTTPException(
                    status_code=400,
                    detail=user_friendly_error
                )
            
            post_id = post_response.json().get("id")
            platform_name = "Facebook"
            # Facebook post URL format: https://www.facebook.com/{page_id}/posts/{post_id}
            # Note: We have page_id from earlier, but we'll use a generic format
            post_url = f"https://www.facebook.com/{page_id}/posts/{post_id}" if post_id and page_id else None
            
        elif platform_lower == "wordpress":
            # Call WordPress posting logic
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.WORDPRESS
            ).first()
            
            if not connection or not connection.platform_user_id or not connection.access_token or not connection.refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="WordPress not connected. Please connect your WordPress site first."
                )
            
            from requests.auth import HTTPBasicAuth
            
            # For WordPress: platform_user_id = site_url, refresh_token = username, access_token = plugin_api_key
            site_url = connection.platform_user_id
            username = connection.refresh_token  # WordPress username (not used for plugin endpoint)
            plugin_api_key = connection.access_token  # WordPress plugin API key (activation_key) stored in access_token
            
            # Ensure site_url doesn't have trailing slash for API endpoint
            site_url = site_url.rstrip('/')
            # Use plugin's custom endpoint which only requires API key (no user permission checks)
            api_url = f"{site_url}/wp-json/vernal-contentum/v1/posts"
            
            logger.info(f"📤 WordPress Post Now: site_url={site_url}, api_url={api_url}, has_api_key={bool(plugin_api_key)}")
            
            # Get WordPress-specific fields from content if available
            wordpress_title = title or "Untitled Post"
            wordpress_excerpt = None
            permalink_slug = None
            
            if content_id:
                # Try to get WordPress fields from database
                content_obj = db.query(Content).filter(Content.id == content_id).first()
                if content_obj:
                    if hasattr(content_obj, 'post_title') and content_obj.post_title:
                        wordpress_title = content_obj.post_title
                    if hasattr(content_obj, 'post_excerpt') and content_obj.post_excerpt:
                        wordpress_excerpt = content_obj.post_excerpt
                    if hasattr(content_obj, 'permalink') and content_obj.permalink:
                        permalink_slug = content_obj.permalink
            elif content_item:
                # Get WordPress fields from content_item
                if content_item.get("post_title"):
                    wordpress_title = content_item.get("post_title")
                if content_item.get("post_excerpt"):
                    wordpress_excerpt = content_item.get("post_excerpt")
                if content_item.get("permalink"):
                    permalink_slug = content_item.get("permalink")
            
            # Never use raw model output as WP body: POST_TITLE→title, POST_EXCERPT→excerpt, PERMALINK→slug, CONTENT→body only
            body_only = sanitize_wordpress_body(content_text)
            if body_only != content_text:
                logger.info(f"📤 WordPress Post Now: sanitized body (removed title/excerpt/permalink), before len={len(content_text)}, after len={len(body_only)}")
            post_data = {
                "title": wordpress_title,
                "content": body_only,
                "status": "publish"
            }
            
            # Add WordPress-specific fields if available
            if wordpress_excerpt:
                post_data["excerpt"] = wordpress_excerpt
            
            # Add category and author if provided
            if content_id:
                # First check if wordpress_fields were passed (takes precedence over DB)
                if wordpress_fields:
                    if wordpress_fields.get("category_id"):
                        post_data["category_id"] = int(wordpress_fields.get("category_id"))
                    if wordpress_fields.get("author_id"):
                        post_data["author_id"] = int(wordpress_fields.get("author_id"))
                else:
                    # Fallback to database values
                    content_obj = db.query(Content).filter(Content.id == content_id).first()
                    if content_obj:
                        if hasattr(content_obj, 'category_id') and content_obj.category_id:
                            post_data["category_id"] = content_obj.category_id
                        if hasattr(content_obj, 'author_id') and content_obj.author_id:
                            post_data["author_id"] = content_obj.author_id
            elif content_item:
                if content_item.get("category_id"):
                    post_data["category_id"] = int(content_item.get("category_id"))
                if content_item.get("author_id"):
                    post_data["author_id"] = int(content_item.get("author_id"))
            
            # Plugin endpoint uses 'slug' for permalink
            if permalink_slug:
                # Note: Plugin endpoint may not support slug directly, but we'll include it
                # The plugin's create_post method doesn't explicitly handle slug, but WordPress will auto-generate from title
                pass  # Plugin endpoint doesn't support slug parameter in current implementation
            
            # Plugin endpoint supports featured_image_url (URL, not media ID)
            if image_url:
                # Plugin endpoint accepts URL and will download/attach it
                post_data["featured_image_url"] = image_url
                logger.info(f"📤 WordPress Post Now: Setting featured_image_url={image_url}")
            
            # Use plugin API key authentication (X-API-Key header)
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": plugin_api_key
            }
            
            logger.info(f"📤 WordPress Post Now: Attempting to post with plugin API key (length={len(plugin_api_key) if plugin_api_key else 0})")
            logger.info(f"📤 WordPress Post Now: Post data keys: {list(post_data.keys())}")
            
            response = requests.post(
                api_url,
                json=post_data,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"📤 WordPress API response: status={response.status_code}")
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(f"❌ WordPress API error: {response.status_code} - {error_text}")
                
                # Parse error for better user message
                try:
                    error_json = response.json()
                    error_code = error_json.get("code", "")
                    error_message = error_json.get("message", error_text)
                    
                    # Check for common WordPress plugin API errors
                    if response.status_code == 401:
                        if "invalid_api_key" in error_code or "api key" in error_message.lower():
                            detail = f"WordPress plugin API key authentication failed. Please verify:\n1. The API key (activation_key) is correct\n2. The API key hasn't been regenerated in WordPress\n3. The API key was copied correctly (no extra spaces)\n\nError: {error_message}"
                        else:
                            detail = f"WordPress plugin authentication failed. Please verify the API key is correct.\n\nError: {error_message}"
                    elif response.status_code == 400:
                        if "missing_title" in error_code:
                            detail = f"WordPress plugin error: Post title is required.\n\nError: {error_message}"
                        elif "missing_content" in error_code:
                            detail = f"WordPress plugin error: Post content is required.\n\nError: {error_message}"
                        else:
                            detail = f"WordPress plugin API error ({response.status_code}): {error_message}"
                    else:
                        detail = f"WordPress plugin API error ({response.status_code}): {error_message}"
                except:
                    detail = f"WordPress API error ({response.status_code}): {error_text[:500]}"
                
                raise HTTPException(
                    status_code=400,
                    detail=detail
                )
            
            response_data = response.json()
            post_id = response_data.get("id")
            platform_name = "WordPress"
            # WordPress plugin returns 'url' field in response
            post_url = response_data.get("url") or response_data.get("link")
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform: {platform}. Supported platforms: linkedin, twitter, instagram, facebook, wordpress"
            )
        
        # Update content status and post_url; remove stored body/image so we only keep title + link
        if content_id:
            content = db.query(Content).filter(Content.id == content_id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                if post_url:
                    content.post_url = post_url
                    logger.info(f"✅ Saved post_url for content {content_id}: {post_url}")
                # Remove content and image from our servers; published page shows title + link only
                content.content = ""
                content.image_url = None
                db.commit()
                logger.info(f"✅ Updated content {content_id} status to 'posted'; cleared body and image")
        
        logger.info(f"✅ Posted to {platform_name} immediately for user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"Content posted to {platform_name} successfully",
            "post_id": post_id,
            "platform": platform_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting content immediately: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to post content: {str(e)}"
        )

@content_router.post("/campaigns/{campaign_id}/save-content-item")
async def save_content_item(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a single content item (draft) to database - called when content/image is generated"""
    try:
        from models import Content, Campaign
        from datetime import datetime
        
        logger.info(f"💾 save-content-item called for campaign {campaign_id} by user {current_user.id}")
        logger.info(f"📦 Request data: {request_data}")
        logger.info(f"📦 WordPress fields in request: category_id={request_data.get('category_id')}, author_id={request_data.get('author_id')}")
        
        # Verify campaign exists
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        item = request_data
        week = item.get("week", 1)
        day = item.get("day", "Monday")
        platform_str = item.get("platform", "linkedin").lower()
        
        logger.info(f"🔍 Platform from request: '{platform_str}' (type: {type(platform_str)})")
        
        # Map platform string to PlatformEnum for validation, but store as string in database
        from models import PlatformEnum
        platform_map = {
            "linkedin": PlatformEnum.LINKEDIN,
            "instagram": PlatformEnum.INSTAGRAM,
            "facebook": PlatformEnum.FACEBOOK,
            "twitter": PlatformEnum.TWITTER,
            "youtube": PlatformEnum.YOUTUBE,
            "wordpress": PlatformEnum.WORDPRESS,
            "tiktok": PlatformEnum.TIKTOK,
        }
        platform_enum = platform_map.get(platform_str, PlatformEnum.LINKEDIN)
        # Convert to string for database storage (database column is String, not Enum)
        # CRITICAL: Always use lowercase for database storage to ensure consistency
        platform_db_value = (platform_enum.value if hasattr(platform_enum, 'value') else str(platform_enum)).lower()
        
        logger.info(f"🔍 Platform enum: {platform_enum}, DB value: '{platform_db_value}' (type: {type(platform_db_value)})")
        
        # Check if request includes a database ID (numeric) - if so, find that specific content item
        existing_content = None
        content_id = item.get("id")
        database_id = None  # Track if we have a numeric database ID
        
        # If id is provided and is numeric (database ID), find that specific content item and update it
        if content_id and isinstance(content_id, (int, str)):
            try:
                # Check if it's a numeric database ID
                if str(content_id).isdigit():
                    content_id_int = int(content_id)
                    database_id = content_id_int
                    # Use raw SQL to avoid ORM trying to SELECT non-existent columns
                    from sqlalchemy import text
                    id_check_query = text("""
                        SELECT id FROM content 
                        WHERE id = :id 
                        AND campaign_id = :campaign_id 
                        AND user_id = :user_id
                        LIMIT 1
                    """)
                    id_check_result = db.execute(id_check_query, {
                        "id": content_id_int,
                        "campaign_id": campaign_id,
                        "user_id": current_user.id
                    }).first()
                    
                    if id_check_result:
                        # Use raw SQL to get content data (avoid ORM column issues)
                        existing_data_query = text("SELECT * FROM content WHERE id = :id LIMIT 1")
                        existing_data = db.execute(existing_data_query, {"id": content_id_int}).first()
                        if existing_data:
                            existing_content = dict(existing_data._mapping)
                            logger.info(f"🔍 Found existing content by database ID: {content_id_int}")
                else:
                    # ID is not numeric (frontend-generated like "week-1-Monday-linkedin-0-post-1")
                    # Still check for existing content by week/day/platform to avoid duplicates
                    logger.info(f"🔍 Non-numeric ID provided ({content_id}), checking for existing content by week/day/platform")
            except (ValueError, TypeError):
                # ID format is unexpected, still check for existing content
                logger.info(f"🔍 ID format unexpected ({content_id}), checking for existing content by week/day/platform")
        
        # ALWAYS check by week/day/platform if no existing content found by database ID
        # This prevents duplicate content creation when frontend uses composite IDs
        # CRITICAL: Use raw SQL to avoid ORM trying to SELECT non-existent columns
        if not existing_content:
            from sqlalchemy import text
            # Use raw SQL to check for existing content - avoids ORM column issues
            check_query = text("""
                SELECT id FROM content 
                WHERE campaign_id = :campaign_id 
                AND week = :week 
                AND day = :day 
                AND platform = :platform 
                AND user_id = :user_id
                LIMIT 1
            """)
            check_result = db.execute(check_query, {
                "campaign_id": campaign_id,
                "week": week,
                "day": day,
                "platform": platform_db_value.lower(),  # Ensure lowercase for comparison
                "user_id": current_user.id
            }).first()
            
            if check_result:
                existing_id = dict(check_result._mapping)['id']
                # Use raw SQL to get content data (avoid ORM column issues)
                existing_data_query = text("SELECT * FROM content WHERE id = :id LIMIT 1")
                existing_data = db.execute(existing_data_query, {"id": existing_id}).first()
                if existing_data:
                    existing_content = dict(existing_data._mapping)
                    logger.info(f"🔍 Found existing content by week/day/platform: week={week}, day={day}, platform={platform_db_value}, db_id={existing_id}")
            else:
                logger.info(f"🔍 No existing content found for week={week}, day={day}, platform={platform_db_value.lower()}, will create new")
        
        # If still no existing content, we'll create a new one
        
        # Parse schedule time if provided
        schedule_time = None
        if item.get("schedule_time"):
            try:
                schedule_time_str = item.get("schedule_time")
                if 'T' in schedule_time_str:
                    schedule_time = datetime.fromisoformat(schedule_time_str.replace('Z', '+00:00'))
                else:
                    schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%dT%H:%M:%S")
            except:
                schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            schedule_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # MySQL doesn't support timezone-aware datetimes, so convert to naive UTC
        if schedule_time.tzinfo is not None:
            from datetime import timezone
            schedule_time = schedule_time.astimezone(timezone.utc).replace(tzinfo=None)
        
        if existing_content:
            # Update existing content using raw SQL (avoid ORM column issues)
            existing_id = existing_content['id']
            # Get content from either "description" or "content" field
            # Check if key exists (not just truthy) so we can save empty strings to clear content
            content_update = None
            if "description" in item:
                content_update = item.get("description", "")
            elif "content" in item:
                content_update = item.get("content", "")
            
            image_url = item.get("image") or item.get("image_url")
            
            # Get actual columns from database
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            content_columns = [col['name'] for col in inspector.get_columns('content')]
            
            # Build UPDATE statement with only existing columns
            update_fields = []
            update_values = {"id": existing_id}
            
            if item.get("title"):
                update_fields.append("title = :title")
                update_values["title"] = item.get("title")
            
            # Always update content if provided (even if empty string) - allows clearing content
            # WordPress: never save raw model output as body; sanitize so only body is stored
            if content_update is not None:
                update_fields.append("content = :content")
                body_to_save = sanitize_wordpress_body(content_update) if platform_db_value == "wordpress" else content_update
                update_values["content"] = body_to_save
                if platform_db_value == "wordpress" and body_to_save != content_update:
                    logger.info(f"💾 WordPress content sanitized before save: before len={len(content_update)}, after len={len(body_to_save)}")
                logger.info(f"💾 Updating content: length={len(body_to_save)}, empty={not body_to_save.strip()}")
            
            # Always update image_url if key present (allows clearing image on delete)
            if "image" in item or "image_url" in item:
                update_fields.append("image_url = :image_url")
                update_values["image_url"] = image_url or None
            
            update_fields.append("status = :status")
            update_values["status"] = "draft"
            
            update_fields.append("is_draft = :is_draft")
            update_values["is_draft"] = 1
            
            update_fields.append("can_edit = :can_edit")
            update_values["can_edit"] = 1
            
            update_fields.append("schedule_time = :schedule_time")
            update_values["schedule_time"] = schedule_time
            
            if item.get("week"):
                update_fields.append("week = :week")
                update_values["week"] = week
            
            if item.get("day"):
                update_fields.append("day = :day")
                update_values["day"] = day
            
            if item.get("platform"):
                update_fields.append("platform = :platform")
                update_values["platform"] = platform_db_value
            
            # WordPress-specific fields (only update if columns exist and key is present in item)
            # Check if key exists (not just truthy) so we can save empty strings to clear fields
            if "post_title" in content_columns and "post_title" in item:
                update_fields.append("post_title = :post_title")
                update_values["post_title"] = item.get("post_title") or None
                logger.info(f"💾 Updating post_title: '{item.get('post_title')}'")
            
            if "post_excerpt" in content_columns and "post_excerpt" in item:
                update_fields.append("post_excerpt = :post_excerpt")
                update_values["post_excerpt"] = item.get("post_excerpt") or None
                logger.info(f"💾 Updating post_excerpt: '{item.get('post_excerpt')}'")
            
            if "permalink" in content_columns and "permalink" in item:
                update_fields.append("permalink = :permalink")
                update_values["permalink"] = item.get("permalink") or None
                logger.info(f"💾 Updating permalink: '{item.get('permalink')}'")
            
            # WordPress category and author (only update if columns exist and key is present in item)
            # Always update if key exists (even if null) to allow clearing values
            if "category_id" in content_columns and "category_id" in item:
                category_value = item.get("category_id")
                update_fields.append("category_id = :category_id")
                # Handle null, 0, and empty string - convert to None for NULL in database
                if category_value is None or category_value == "null" or category_value == "":
                    update_values["category_id"] = None
                elif category_value:
                    try:
                        update_values["category_id"] = int(category_value)
                    except (ValueError, TypeError):
                        update_values["category_id"] = None
                else:
                    update_values["category_id"] = None
                logger.info(f"💾 Updating category_id: {update_values['category_id']} (raw value: {category_value}, type: {type(category_value).__name__})")
            
            if "author_id" in content_columns and "author_id" in item:
                author_value = item.get("author_id")
                update_fields.append("author_id = :author_id")
                # Handle null, 0, and empty string - convert to None for NULL in database
                if author_value is None or author_value == "null" or author_value == "":
                    update_values["author_id"] = None
                elif author_value:
                    try:
                        update_values["author_id"] = int(author_value)
                    except (ValueError, TypeError):
                        update_values["author_id"] = None
                else:
                    update_values["author_id"] = None
                logger.info(f"💾 Updating author_id: {update_values['author_id']} (raw value: {author_value}, type: {type(author_value).__name__})")
            
            if update_fields:
                update_stmt = text(f"UPDATE content SET {', '.join(update_fields)} WHERE id = :id")
                logger.info(f"🔧 Executing UPDATE: {update_stmt}")
                logger.info(f"🔧 UPDATE values: {update_values}")
                db.execute(update_stmt, update_values)
                db.commit()  # Explicitly commit the transaction
                logger.info(f"✅ Updated existing content (ID: {existing_id}): week={week}, day={day}, platform={platform_db_value}, image={bool(image_url)}")
                
                # Verify the update by querying back
                verify_columns = ["post_title", "post_excerpt", "permalink"]
                if "category_id" in content_columns:
                    verify_columns.append("category_id")
                if "author_id" in content_columns:
                    verify_columns.append("author_id")
                verify_query = text(f"SELECT {', '.join(verify_columns)} FROM content WHERE id = :id")
                verify_result = db.execute(verify_query, {"id": existing_id}).first()
                if verify_result:
                    verified = dict(verify_result._mapping)
                    logger.info(f"✅ Verified WordPress fields after update: post_title='{verified.get('post_title')}', post_excerpt='{verified.get('post_excerpt')}', permalink='{verified.get('permalink')}', category_id={verified.get('category_id')}, author_id={verified.get('author_id')}")
            
            # Set final_content_id for return
            final_content_id = existing_id
        else:
            # Validate required fields
            content_text = item.get("description") or item.get("content", "")
            title_text = item.get("title", "")
            
            # WordPress: never save raw model output as body; sanitize so only body is stored
            if platform_db_value == "wordpress":
                content_text = sanitize_wordpress_body(content_text)
            
            # If content is empty, use a placeholder (for image-only saves)
            if not content_text or not content_text.strip():
                platform_name = platform_db_value.title()
                content_text = f"Content for {platform_name} - {day}"
            
            # If title is empty, generate a default
            if not title_text or not title_text.strip():
                platform_name = platform_db_value.title()
                title_text = f"{platform_name} Post - {day}"
            
            # Create new content using ORM (more robust than raw SQL)
            # Support both "image" and "image_url" field names
            image_url = item.get("image") or item.get("image_url")
            if image_url:
                logger.info(f"💾 Saving image_url for new content: {image_url[:100]}...")
            else:
                logger.info(f"⚠️ No image_url provided in save request for new content")
            
            try:
                now = datetime.now().replace(tzinfo=None)
                # Ensure all required fields have defaults
                week = week or 1
                day = day or "Monday"
                
                # Use hybrid approach: ORM table definition but controlled INSERT
                # This prevents SQLAlchemy from trying to insert columns that don't exist
                from sqlalchemy import inspect
                
                # Get actual columns from database
                inspector = inspect(db.bind)
                content_columns = [col['name'] for col in inspector.get_columns('content')]
                logger.info(f"📋 Database content table has {len(content_columns)} columns")
                
                # Use platform_db_value (already converted to string)
                file_name = f"{campaign_id}_{week}_{day}_{platform_db_value}.txt"
                
                # Build values dict with only columns that exist in database
                values = {
                    "user_id": current_user.id,
                    "campaign_id": campaign_id,
                    "week": week,
                    "day": day,
                    "content": content_text,
                    "title": title_text,
                    "status": "draft",
                    "date_upload": now,
                    "platform": platform_db_value,  # Use string value, not PlatformEnum
                    "file_name": file_name,
                    "file_type": "text",
                    "platform_post_no": item.get("platform_post_no", "1"),
                    "schedule_time": schedule_time,
                    "image_url": image_url if image_url else None,
                    "is_draft": 1,
                    "can_edit": 1,
                }
                
                # Add optional columns only if they exist in database
                if "knowledge_graph_location" in content_columns and item.get("knowledge_graph_location"):
                    values["knowledge_graph_location"] = item.get("knowledge_graph_location")
                
                if "parent_idea" in content_columns and item.get("parent_idea"):
                    values["parent_idea"] = item.get("parent_idea")
                
                if "landing_page_url" in content_columns and item.get("landing_page_url"):
                    values["landing_page_url"] = item.get("landing_page_url")
                
                # WordPress-specific fields (only add if columns exist and values provided)
                if "post_title" in content_columns and item.get("post_title"):
                    values["post_title"] = item.get("post_title")
                
                if "post_excerpt" in content_columns and item.get("post_excerpt"):
                    values["post_excerpt"] = item.get("post_excerpt")
                
                if "permalink" in content_columns and item.get("permalink"):
                    values["permalink"] = item.get("permalink")
                
                # WordPress category and author (only add if columns exist and values provided)
                if "category_id" in content_columns and item.get("category_id"):
                    values["category_id"] = int(item.get("category_id"))
                    logger.info(f"💾 Adding category_id for new content: {values['category_id']}")
                
                if "author_id" in content_columns and item.get("author_id"):
                    values["author_id"] = int(item.get("author_id"))
                    logger.info(f"💾 Adding author_id for new content: {values['author_id']}")
                
                if "use_without_image" in content_columns:
                    values["use_without_image"] = 1 if item.get("use_without_image", False) else 0
                
                # Use Content.__table__ to get the table definition, but control which columns are inserted
                # This gives us ORM benefits (type safety, table definition) but full control over INSERT
                from sqlalchemy import text
                columns_str = ", ".join([col for col in values.keys() if col in content_columns])
                placeholders_str = ", ".join([f":{col}" for col in values.keys() if col in content_columns])
                
                insert_stmt = text(f"""
                    INSERT INTO content ({columns_str})
                    VALUES ({placeholders_str})
                """)
                
                # Filter values to only include columns that exist
                filtered_values = {k: v for k, v in values.items() if k in content_columns}
                
                result = db.execute(insert_stmt, filtered_values)
                content_id = result.lastrowid
                
                # CRITICAL: For raw SQL, we need to explicitly commit the statement
                # SQLAlchemy doesn't auto-track raw SQL in the session like ORM does
                db.flush()  # Flush to ensure data is sent to database
                logger.info(f"✅ Created new content (ID: {content_id}): week={week}, day={day}, platform={platform_db_value}, has_image={bool(image_url)}")
                
                # Verify the insert worked by immediately querying
                verify_content = db.execute(text("SELECT id FROM content WHERE id = :id"), {"id": content_id}).first()
                if verify_content:
                    logger.info(f"🔍 Verification: Content {content_id} is visible in database immediately after insert")
                else:
                    logger.warning(f"⚠️ Warning: Content {content_id} not visible immediately after insert (may be transaction isolation)")
            except Exception as create_error:
                logger.error(f"❌ Error creating Content object: {create_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create content item: {str(create_error)}"
                )
        
        # Commit the transaction
        db.commit()
        
        # Get the final content_id for return value
        if not existing_content:
            final_content_id = content_id if 'content_id' in locals() else None
        
        logger.info(f"✅ Committed content save for campaign {campaign_id}, user {current_user.id}, content_id={final_content_id}")
        
        # CRITICAL: Verify the commit worked by querying the database immediately after commit
        # This helps catch transaction isolation issues where data isn't visible to subsequent queries
        try:
            verify_count = db.execute(
                text("SELECT COUNT(*) as count FROM content WHERE campaign_id = :campaign_id AND user_id = :user_id"),
                {"campaign_id": campaign_id, "user_id": current_user.id}
            ).first()
            if verify_count:
                logger.info(f"🔍 Post-commit verification: Database now has {verify_count.count} content items for campaign {campaign_id}")
            else:
                logger.warning(f"⚠️ Post-commit verification: Could not verify content count")
        except Exception as verify_error:
            logger.warning(f"⚠️ Post-commit verification failed: {verify_error}")
        
        return {
            "status": "success",
            "message": "Content item saved",
            "content_id": final_content_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving content item: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save content item: {str(e)}"
        )

@content_router.get("/campaigns/{campaign_id}/content-items")
def get_campaign_content_items(
    campaign_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all content items for a campaign (draft, scheduled, pending, uploaded)"""
    try:
        from models import Content
        from sqlalchemy import or_
        
        logger.info(f"📋 Fetching content items for campaign {campaign_id}, user {current_user.id}")
        
        # CRITICAL: Use raw SQL query to ensure we see data inserted via raw SQL
        # ORM queries might not see raw SQL inserts due to session caching
        from sqlalchemy import text
        try:
            # First try with raw SQL to ensure we see all data
            raw_query = text("""
                SELECT * FROM content 
                WHERE campaign_id = :campaign_id AND user_id = :user_id
                ORDER BY week ASC, day ASC
            """)
            raw_results = db.execute(raw_query, {"campaign_id": campaign_id, "user_id": current_user.id}).fetchall()
            logger.info(f"📋 Raw SQL query found {len(raw_results)} content items for campaign {campaign_id}")
            
            # Log sample of what we found for debugging
            if raw_results:
                sample = dict(raw_results[0]._mapping)
                logger.info(f"📋 Sample content item: id={sample.get('id')}, campaign_id={sample.get('campaign_id')}, user_id={sample.get('user_id')}, platform='{sample.get('platform')}', week={sample.get('week')}, day='{sample.get('day')}'")
            else:
                logger.warning(f"⚠️ Raw SQL returned 0 results for campaign_id='{campaign_id}', user_id={current_user.id}")
                # Double-check: query all content for this user to see if campaign_id is wrong
                all_user_content = db.execute(
                    text("SELECT COUNT(*) as count, GROUP_CONCAT(DISTINCT campaign_id) as campaigns FROM content WHERE user_id = :user_id"),
                    {"user_id": current_user.id}
                ).first()
                if all_user_content:
                    logger.info(f"🔍 User {current_user.id} has {all_user_content.count} total content items across campaigns: {all_user_content.campaigns}")
            
            # Use raw SQL results directly (avoid ORM column issues)
            content_items = []
            if raw_results and len(raw_results) > 0:
                # Convert raw SQL results to dictionaries
                content_items = [dict(row._mapping) for row in raw_results]
                logger.info(f"📋 Converted {len(content_items)} raw SQL results to dictionaries")
            else:
                content_items = []
            
            # No fallback needed - raw SQL is the source of truth
        except Exception as query_error:
            logger.error(f"❌ Error with raw SQL query: {query_error}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            content_items = []  # Return empty on error
        
        logger.info(f"📋 Found {len(content_items)} content items for campaign {campaign_id}")
        
        items_data = []
        for item in content_items:
            try:
                # item is now a dict from raw SQL, not an ORM object
                item_id = item.get('id')
                image_url = item.get('image_url') or ""
                week = item.get('week') or 1
                day = item.get('day') or "Monday"
                platform = item.get('platform') or "linkedin"
                status = item.get('status') or "draft"
                title = item.get('title') or ""
                content_text = item.get('content') or ""
                schedule_time = item.get('schedule_time')
                date_upload = item.get('date_upload')
                
                # Handle datetime objects from raw SQL
                schedule_time_str = None
                if schedule_time:
                    if hasattr(schedule_time, 'isoformat'):
                        schedule_time_str = schedule_time.isoformat()
                    elif hasattr(schedule_time, 'strftime'):
                        schedule_time_str = schedule_time.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        schedule_time_str = str(schedule_time)
                
                created_at_str = None
                if date_upload:
                    if hasattr(date_upload, 'isoformat'):
                        created_at_str = date_upload.isoformat()
                    elif hasattr(date_upload, 'strftime'):
                        created_at_str = date_upload.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        created_at_str = str(date_upload)
                
                # WordPress-specific fields
                post_title = item.get('post_title') or None
                post_excerpt = item.get('post_excerpt') or None
                permalink = item.get('permalink') or None
                category_id = item.get('category_id')  # Can be None or integer
                author_id = item.get('author_id')  # Can be None or integer
                
                items_data.append({
                    "id": f"week-{week}-{day}-{platform}-{item_id}",  # Composite ID for frontend
                    "database_id": item_id,  # Include database ID separately so frontend can use it for updates
                    "title": title,
                    "description": content_text,
                    "week": week,
                    "day": day,
                    "platform": platform.lower() if platform else "linkedin",  # Ensure lowercase
                    "image": image_url,  # Ensure image_url is returned as "image" for frontend
                    "image_url": image_url,  # Also include image_url for compatibility
                    "status": status,
                    "schedule_time": schedule_time_str,
                    "created_at": created_at_str,  # Creation timestamp - IMPORTANT data point
                    "contentProcessedAt": None,  # Column doesn't exist in DB
                    "imageProcessedAt": None,  # Column doesn't exist in DB
                    "contentPublishedAt": None,  # Column doesn't exist in DB
                    "imagePublishedAt": None,  # Column doesn't exist in DB
                    "use_without_image": False,  # Column doesn't exist in DB
                    # WordPress-specific fields
                    "post_title": post_title,
                    "post_excerpt": post_excerpt,
                    "permalink": permalink,
                    "category_id": int(category_id) if category_id is not None else None,
                    "author_id": int(author_id) if author_id is not None else None,
                })
                logger.info(f"📋 Item: week={week}, day={day}, platform={platform}, status={status}, has_image={bool(image_url)}, db_id={item_id}")
            except Exception as item_error:
                logger.error(f"Error processing content item {item.get('id', 'unknown')}: {item_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue  # Skip this item but continue with others
        
        logger.info(f"✅ Returning {len(items_data)} items for campaign {campaign_id}")
        return {
            "status": "success",
            "message": {
                "items": items_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching content items: {e}")
        import traceback
        traceback.print_exc()
        # Return empty array instead of 500 error for better UX
        logger.warning(f"⚠️ Returning empty items array due to error: {e}")
        return {
            "status": "success",
            "message": {
                "items": []
            }
        }
