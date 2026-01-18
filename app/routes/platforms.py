"""
Platform authentication and posting endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import os
import secrets
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth1Session

logger = logging.getLogger(__name__)

platforms_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import get_openai_api_key from utils (moved from main to avoid circular import)
from app.utils.openai_helpers import get_openai_api_key

@platforms_router.get("/platforms/{platform}/credentials")
async def check_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has stored OAuth credentials for a platform"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        platform_enum = None
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        has_credentials = bool(connection and connection.platform_user_id and connection.refresh_token)
        
        return {"has_credentials": has_credentials, "platform": platform}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")

# ============================================================================
# PLATFORM CREDENTIALS CHECK
# ============================================================================

@platforms_router.get("/platforms/{platform}/credentials")
async def check_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has stored OAuth credentials for a platform"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        platform_enum = None
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        # Check if credentials are stored (platform_user_id and refresh_token indicate stored OAuth creds)
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        has_credentials = bool(connection and connection.platform_user_id and connection.refresh_token)
        
        return {
            "has_credentials": has_credentials,
            "platform": platform
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")

# ============================================================================
# PLATFORM CONNECTION ENDPOINTS
# ============================================================================

@platforms_router.get("/linkedin/auth-v2")
async def linkedin_auth_v2(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Initiate LinkedIn OAuth connection - returns auth URL for redirect"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        load_dotenv()
        cid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_id").first()
        cs_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_redirect_uri").first()
        cid = cid_s.setting_value if cid_s and cid_s.setting_value else os.getenv("LINKEDIN_CLIENT_ID")
        cs = cs_s.setting_value if cs_s and cs_s.setting_value else os.getenv("LINKEDIN_CLIENT_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("LINKEDIN_REDIRECT_URI", "https://themachine.vernalcontentum.com/linkedin/callback")
        if not cid or not cs:
            raise HTTPException(status_code=500, detail="LinkedIn OAuth credentials not configured. Please configure them in Admin Settings > System > Platform Keys > LinkedIn.")
        import secrets
        state = secrets.token_urlsafe(32)
        existing_state = db.query(StateToken).filter(StateToken.user_id == current_user.id, StateToken.platform == PlatformEnum.LINKEDIN, StateToken.state == state).first()
        if not existing_state:
            new_state = StateToken(user_id=current_user.id, platform=PlatformEnum.LINKEDIN, state=state, created_at=datetime.now())
            db.add(new_state)
        db.commit()
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={cid}&redirect_uri={ru}&state={state}&scope=openid%20profile%20email%20w_member_social"
        logger.info(f"✅ LinkedIn auth URL generated for user {current_user.id}")
        return {"status": "success", "auth_url": auth_url}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"❌ Error generating LinkedIn auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate LinkedIn auth URL: {str(e)}")


@platforms_router.post("/linkedin/auth-v2")
async def linkedin_auth_v2(
    request_data: Dict[str, Any] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate LinkedIn OAuth - uses stored credentials or accepts new ones"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        from typing import Dict, Any
        from datetime import datetime
        
        redirect_uri = "https://machine.vernalcontentum.com/linkedin/callback"
        
        client_id = None
        client_secret = None
        
        # If POST with credentials, store them
        if request_data and request_data.get("client_id") and request_data.get("client_secret"):
            client_id = request_data.get("client_id", "").strip()
            client_secret = request_data.get("client_secret", "").strip()
            
            if not client_id or not client_secret:
                raise HTTPException(status_code=400, detail="LinkedIn Client ID and Client Secret are required")
            
            # Store credentials in database
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if connection:
                connection.platform_user_id = client_id
                connection.refresh_token = client_secret
            else:
                connection = PlatformConnection(
                    user_id=current_user.id,
                    platform=PlatformEnum.LINKEDIN,
                    platform_user_id=client_id,
                    refresh_token=client_secret
                )
                db.add(connection)
            db.commit()
        else:
            # GET request - check for stored credentials
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == current_user.id,
                PlatformConnection.platform == PlatformEnum.LINKEDIN
            ).first()
            
            if not connection or not connection.platform_user_id or not connection.refresh_token:
                raise HTTPException(
                    status_code=400, 
                    detail="LinkedIn credentials not found. Please provide Client ID and Client Secret."
                )
            
            client_id = connection.platform_user_id
            client_secret = connection.refresh_token
        
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state in database
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.LINKEDIN,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.LINKEDIN,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        # Build LinkedIn OAuth URL
        auth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"response_type=code&"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=r_liteprofile%20r_emailaddress%20w_member_social"
        )
        
        logger.info(f"✅ LinkedIn auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error generating LinkedIn auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LinkedIn auth URL: {str(e)}"
        )

@platforms_router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle LinkedIn OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        load_dotenv()
        cid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_id").first()
        cs_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_client_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "linkedin_redirect_uri").first()
        cid = cid_s.setting_value if cid_s and cid_s.setting_value else os.getenv("LINKEDIN_CLIENT_ID")
        cs = cs_s.setting_value if cs_s and cs_s.setting_value else os.getenv("LINKEDIN_CLIENT_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("LINKEDIN_REDIRECT_URI", "https://themachine.vernalcontentum.com/linkedin/callback")
        if not cid or not cs:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=linkedin_not_configured")
        st = db.query(StateToken).filter(StateToken.platform == PlatformEnum.LINKEDIN, StateToken.state == state).first()
        if not st:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=invalid_state")
        uid = st.user_id
        db.delete(st)
        r = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={"grant_type": "authorization_code", "code": code, "redirect_uri": ru, "client_id": cid, "client_secret": cs})
        if r.status_code != 200:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        at = r.json().get("access_token")
        if not at:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # Fetch user profile information from LinkedIn
        user_email = None
        user_name = None
        try:
            # Use OpenID Connect userinfo endpoint to get email
            profile_url = "https://api.linkedin.com/v2/userinfo"
            headers = {"Authorization": f"Bearer {at}"}
            profile_response = requests.get(profile_url, headers=headers)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_email = profile_data.get("email")
                user_name = profile_data.get("name")
                logger.info(f"✅ Fetched LinkedIn profile: email={user_email}, name={user_name}")
            else:
                # Fallback to basic profile endpoint
                profile_url = "https://api.linkedin.com/v2/me"
                profile_response = requests.get(profile_url, headers=headers)
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
                    logger.info(f"✅ Fetched LinkedIn basic profile: name={user_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch LinkedIn profile: {e}")
            # Continue without profile info - connection still works
        
        # Use email if available, otherwise use name, otherwise use a generic identifier
        platform_user_identifier = user_email or user_name or "LinkedIn User"
        
        conn = db.query(PlatformConnection).filter(PlatformConnection.user_id == uid, PlatformConnection.platform == PlatformEnum.LINKEDIN).first()
        if conn:
            conn.access_token = at
            conn.connected_at = datetime.now()
            if platform_user_identifier:
                conn.platform_user_id = platform_user_identifier
        else:
            conn = PlatformConnection(user_id=uid, platform=PlatformEnum.LINKEDIN, access_token=at, platform_user_id=platform_user_identifier, connected_at=datetime.now())
            db.add(conn)
        db.commit()
        logger.info(f"✅ LinkedIn connection successful for user {uid}")
        return RedirectResponse(url="https://machine.vernalcontentum.com/account-settings?linkedin=connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in LinkedIn callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=callback_failed&message={str(e)}")


@platforms_router.get("/twitter/auth-v2")
async def twitter_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Twitter OAuth connection - returns redirect URL"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        import os
        from dotenv import load_dotenv
        from requests_oauthlib import OAuth1Session
        
        load_dotenv()
        
        consumer_key = os.getenv("TWITTER_API_KEY")
        consumer_secret = os.getenv("TWITTER_API_SECRET")
        callback_url = os.getenv("TWITTER_CALLBACK_URL", "https://machine.vernalcontentum.com/twitter/callback")
        
        if not consumer_key or not consumer_secret:
            raise HTTPException(status_code=500, detail="Twitter OAuth credentials not configured")
        
        oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri=callback_url)
        request_token_url = "https://api.twitter.com/oauth/request_token"
        
        try:
            fetch_response = oauth.fetch_request_token(request_token_url)
        except Exception as e:
            logger.error(f"Error fetching Twitter request token: {e}")
            raise HTTPException(status_code=500, detail="Failed to get Twitter request token")
        
        oauth_token = fetch_response.get('oauth_token')
        oauth_token_secret = fetch_response.get('oauth_token_secret')
        
        if not oauth_token:
            raise HTTPException(status_code=500, detail="No oauth_token in response")
        
        new_state = StateToken(
            user_id=current_user.id,
            platform=PlatformEnum.TWITTER,
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
            state=oauth_token,
            created_at=datetime.now()
        )
        db.add(new_state)
        db.commit()
        
        authorization_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"
        
        logger.info(f"✅ Twitter auth URL generated for user {current_user.id}")
        return {"status": "success", "redirect_url": authorization_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Twitter auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Twitter auth URL: {str(e)}")

@platforms_router.get("/twitter/callback")
async def twitter_callback(
    oauth_token: str,
    oauth_verifier: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle Twitter OAuth callback and exchange verifier for access token"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken
        import os
        from dotenv import load_dotenv
        from requests_oauthlib import OAuth1Session
        
        load_dotenv()
        
        consumer_key = os.getenv("TWITTER_API_KEY")
        consumer_secret = os.getenv("TWITTER_API_SECRET")
        
        state_token = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.TWITTER,
            StateToken.oauth_token == oauth_token
        ).first()
        
        if not state_token:
            raise HTTPException(status_code=400, detail="Invalid oauth_token")
        
        oauth_token_secret = state_token.oauth_token_secret
        db.delete(state_token)
        
        oauth = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier
        )
        
        access_token_url = "https://api.twitter.com/oauth/access_token"
        oauth_tokens = oauth.fetch_access_token(access_token_url)
        
        access_token = oauth_tokens.get('oauth_token')
        access_token_secret = oauth_tokens.get('oauth_token_secret')
        
        if not access_token or not access_token_secret:
            raise HTTPException(status_code=400, detail="Failed to get access tokens")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.TWITTER
        ).first()
        
        if connection:
            connection.access_token = access_token
            connection.refresh_token = access_token_secret
            connection.connected_at = datetime.now()
        else:
            connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.TWITTER,
                access_token=access_token,
                refresh_token=access_token_secret,
                connected_at=datetime.now()
            )
            db.add(connection)
        
        db.commit()
        
        logger.info(f"✅ Twitter connection successful for user {current_user.id}")
        return JSONResponse(content={"status": "success", "message": "Twitter connected successfully"}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in Twitter callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to complete Twitter connection: {str(e)}")

@platforms_router.post("/wordpress/auth-v2")
async def wordpress_auth_v2(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect WordPress site using application password"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        from requests.auth import HTTPBasicAuth
        
        form_data = await request.form()
        site_url = form_data.get("site_url", "").strip()
        username = form_data.get("username", "").strip()
        password = form_data.get("password", "").strip()
        
        if not site_url or not username or not password:
            raise HTTPException(status_code=400, detail="Missing required fields: site_url, username, password")
        
        if not site_url.startswith(("http://", "https://")):
            site_url = f"https://{site_url}"
        
        wp_api_url = f"{site_url}/wp-json/wp/v2/users/me"
        
        try:
            # Try with HTTPBasicAuth first (for application passwords)
            response = requests.get(wp_api_url, auth=HTTPBasicAuth(username, password), timeout=10)
            
            # If that fails with 401, try with X-API-Key header (for plugin API key)
            if response.status_code == 401:
                logger.info(f"⚠️ HTTPBasicAuth failed, trying API key authentication for user {current_user.id}")
                # Try plugin API endpoint with API key
                plugin_api_url = f"{site_url}/wp-json/vernal-contentum/v1/categories"
                api_response = requests.get(plugin_api_url, headers={"X-API-Key": password}, timeout=10)
                if api_response.status_code == 200:
                    logger.info(f"✅ WordPress connection verified via API key for user {current_user.id}")
                    response = api_response  # Use successful response
                else:
                    raise HTTPException(status_code=400, detail=f"WordPress authentication failed: Both HTTPBasicAuth and API key authentication returned {api_response.status_code}. Please verify your credentials.")
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"WordPress authentication failed: {response.status_code}")
            logger.info(f"✅ WordPress connection verified for user {current_user.id}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to connect to WordPress: {str(e)}")
        
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        # Auto-generate a backend API key for this user (for WP → Backend calls)
        from models import PluginAPIKey
        import secrets
        
        # Check if user already has an active API key
        existing_api_key = db.query(PluginAPIKey).filter(
            PluginAPIKey.user_id == current_user.id,
            PluginAPIKey.is_active == True
        ).first()
        
        backend_api_key = None
        if not existing_api_key:
            # Generate new API key for this user
            backend_api_key = f"vcb_{secrets.token_hex(32)}"
            plugin_key = PluginAPIKey(
                user_id=current_user.id,
                api_key=backend_api_key,
                name=f"WordPress Plugin - {site_url}",
                is_active=True,
                created_at=datetime.now()
            )
            db.add(plugin_key)
            logger.info(f"✅ Generated backend API key for user {current_user.id}")
        else:
            backend_api_key = existing_api_key.api_key
            logger.info(f"✅ Using existing backend API key for user {current_user.id}")
        
        if existing_connection:
            existing_connection.platform_user_id = site_url
            existing_connection.refresh_token = username
            existing_connection.access_token = password
            existing_connection.connected_at = datetime.now()
        else:
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.WORDPRESS,
                platform_user_id=site_url,
                refresh_token=username,
                access_token=password,
                connected_at=datetime.now()
            )
            db.add(new_connection)
        
        db.commit()
        
        # Get backend URL from environment or use default
        backend_url = os.getenv("BACKEND_URL") or os.getenv("API_BASE_URL") or "https://themachine.vernalcontentum.com"
        # Ensure no trailing slash for consistency
        backend_url = backend_url.rstrip('/')
        
        return {
            "status": "success", 
            "message": "WordPress connected successfully",
            "backend_api_key": backend_api_key,  # Return API key for WP to store
            "backend_url": backend_url
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error connecting WordPress: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to connect WordPress: {str(e)}")

@platforms_router.post("/instagram/connect")
async def instagram_connect(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect Instagram account using App ID, App Secret, and Access Token"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        
        app_id = request_data.get("app_id", "").strip()
        app_secret = request_data.get("app_secret", "").strip()
        access_token = request_data.get("access_token", "").strip()
        
        if not app_id or not app_secret or not access_token:
            raise HTTPException(status_code=400, detail="Missing required fields: app_id, app_secret, access_token")
        
        verify_url = f"https://graph.instagram.com/me?fields=id,username&access_token={access_token}"
        
        try:
            response = requests.get(verify_url, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Instagram access token invalid: {response.status_code}")
            logger.info(f"✅ Instagram connection verified for user {current_user.id}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to verify Instagram token: {str(e)}")
        
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if existing_connection:
            existing_connection.platform_user_id = app_id
            existing_connection.access_token = access_token
            existing_connection.connected_at = datetime.now()
        else:
            new_connection = PlatformConnection(
                user_id=current_user.id,
                platform=PlatformEnum.INSTAGRAM,
                platform_user_id=app_id,
                access_token=access_token,
                connected_at=datetime.now()
            )
            db.add(new_connection)
        
        db.commit()
        
        return {"status": "success", "message": "Instagram connected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error connecting Instagram: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to connect Instagram: {str(e)}")


# PLATFORM POSTING ENDPOINTS (for scheduled content)
# ============================================================================

@platforms_router.post("/platforms/linkedin/post")
async def post_to_linkedin(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to LinkedIn using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.LINKEDIN
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=400, detail="LinkedIn not connected. Please connect your LinkedIn account first.")
        
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
            raise HTTPException(status_code=400, detail=f"LinkedIn API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to LinkedIn for user {current_user.id}")
        return {"status": "success", "message": "Content posted to LinkedIn successfully", "post_id": response.json().get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to LinkedIn: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to LinkedIn: {str(e)}")

@platforms_router.post("/platforms/twitter/post")
async def post_to_twitter(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to Twitter/X using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        from requests_oauthlib import OAuth1Session
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.TWITTER
        ).first()
        
        if not connection or not connection.access_token or not connection.refresh_token:
            raise HTTPException(status_code=400, detail="Twitter not connected. Please connect your Twitter account first.")
        
        api_url = "https://api.twitter.com/2/tweets"
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        oauth = OAuth1Session(
            os.getenv("TWITTER_API_KEY"),
            client_secret=os.getenv("TWITTER_API_SECRET"),
            resource_owner_key=connection.access_token,
            resource_owner_secret=connection.refresh_token
        )
        
        tweet_data = {"text": content_text[:280]}
        
        if image_url:
            media_url = "https://upload.twitter.com/1.1/media/upload.json"
            media_response = oauth.post(media_url, files={"media": requests.get(image_url).content})
            if media_response.status_code == 200:
                media_id = media_response.json().get("media_id_string")
                tweet_data["media"] = {"media_ids": [media_id]}
        
        response = oauth.post(api_url, json=tweet_data, timeout=30)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Twitter API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to Twitter for user {current_user.id}")
        return {"status": "success", "message": "Content posted to Twitter successfully", "tweet_id": response.json().get("data", {}).get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to Twitter: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to Twitter: {str(e)}")

@platforms_router.post("/platforms/wordpress/post")
async def post_to_wordpress(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to WordPress using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        from requests.auth import HTTPBasicAuth
        
        content_id = request_data.get("content_id")
        title = request_data.get("title", "")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not content_text:
            raise HTTPException(status_code=400, detail="Content text is required")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if not connection or not connection.platform_user_id or not connection.access_token:
            raise HTTPException(status_code=400, detail="WordPress not connected. Please connect your WordPress site first.")
        
        site_url = connection.platform_user_id
        username = connection.refresh_token
        app_password = connection.access_token
        
        api_url = f"{site_url}/wp-json/wp/v2/posts"
        post_data = {"title": title or "New Post", "content": content_text, "status": "publish"}
        
        if image_url:
            media_url = f"{site_url}/wp-json/wp/v2/media"
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code == 200:
                files = {"file": ("image.jpg", image_response.content, "image/jpeg")}
                media_response = requests.post(media_url, files=files, auth=HTTPBasicAuth(username, app_password), timeout=30)
                if media_response.status_code == 201:
                    post_data["featured_media"] = media_response.json().get("id")
        
        response = requests.post(api_url, json=post_data, auth=HTTPBasicAuth(username, app_password), timeout=30)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"WordPress API error: {response.status_code} - {response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to WordPress for user {current_user.id}")
        return {"status": "success", "message": "Content posted to WordPress successfully", "post_id": response.json().get("id"), "post_url": response.json().get("link")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to WordPress: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to WordPress: {str(e)}")

@platforms_router.get("/platforms/wordpress/categories")
async def get_wordpress_categories(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch WordPress categories from connected site"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        from requests.auth import HTTPBasicAuth
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if not connection or not connection.platform_user_id or not connection.access_token:
            raise HTTPException(status_code=400, detail="WordPress not connected. Please connect your WordPress site first.")
        
        site_url = connection.platform_user_id
        username = connection.refresh_token
        app_password = connection.access_token
        
        # Try plugin endpoint first (using WP REST API auth as fallback)
        plugin_url = f"{site_url}/wp-json/vernal-contentum/v1/categories"
        # Try with app password first (if plugin accepts it)
        response = requests.get(plugin_url, auth=HTTPBasicAuth(username, app_password), timeout=10)
        if response.status_code == 200:
            categories_data = response.json()
            # Handle both plugin format and WP REST API format
            if isinstance(categories_data, list):
                formatted_categories = [{"id": cat.get("id"), "name": cat.get("name"), "slug": cat.get("slug")} for cat in categories_data]
            else:
                formatted_categories = categories_data.get("categories", [])
            logger.info(f"✅ Fetched {len(formatted_categories)} categories via plugin API for user {current_user.id}")
            return {"status": "success", "categories": formatted_categories}
        
        # Fallback to WordPress REST API
        wp_api_url = f"{site_url}/wp-json/wp/v2/categories"
        response = requests.get(wp_api_url, auth=HTTPBasicAuth(username, app_password), timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch categories: {response.status_code}")
        
        categories = response.json()
        # Format categories for frontend
        formatted_categories = [{"id": cat.get("id"), "name": cat.get("name"), "slug": cat.get("slug")} for cat in categories]
        
        logger.info(f"✅ Fetched {len(formatted_categories)} categories for user {current_user.id}")
        return {"status": "success", "categories": formatted_categories}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching WordPress categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@platforms_router.get("/platforms/wordpress/sitemap")
async def get_wordpress_sitemap(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch WordPress sitemap data from connected site"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        from requests.auth import HTTPBasicAuth
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.WORDPRESS
        ).first()
        
        if not connection or not connection.platform_user_id or not connection.access_token:
            raise HTTPException(status_code=400, detail="WordPress not connected. Please connect your WordPress site first.")
        
        site_url = connection.platform_user_id
        username = connection.refresh_token
        app_password = connection.access_token
        
        # Try plugin endpoint first (using WP REST API auth as fallback)
        plugin_url = f"{site_url}/wp-json/vernal-contentum/v1/sitemap"
        response = requests.get(plugin_url, auth=HTTPBasicAuth(username, app_password), timeout=10)
        if response.status_code == 200:
            sitemap_data = response.json()
            logger.info(f"✅ Fetched sitemap via plugin API for user {current_user.id}")
            return {
                "status": "success",
                "sitemap": sitemap_data,
                "site_url": site_url
            }
        
        # Fallback: return site URL for Site Builder (even if sitemap endpoint not available)
        logger.info(f"✅ Returning site URL for Site Builder: {site_url}")
        return {
            "status": "success",
            "sitemap": {"urls": []},
            "site_url": site_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching WordPress sitemap: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sitemap: {str(e)}")

@platforms_router.post("/platforms/instagram/post")
async def post_to_instagram(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post content to Instagram using stored connection"""
    try:
        from models import PlatformConnection, PlatformEnum, Content
        import requests
        
        content_id = request_data.get("content_id")
        content_text = request_data.get("content", "")
        image_url = request_data.get("image_url")
        
        if not image_url:
            raise HTTPException(status_code=400, detail="Image URL is required for Instagram posts")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=400, detail="Instagram not connected. Please connect your Instagram account first.")
        
        access_token = connection.access_token
        app_id = connection.platform_user_id
        
        create_url = f"https://graph.instagram.com/v18.0/{app_id}/media"
        image_response = requests.get(image_url, timeout=30)
        if image_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        create_data = {"image_url": image_url, "caption": content_text[:2200], "access_token": access_token}
        create_response = requests.post(create_url, data=create_data, timeout=30)
        
        if create_response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Instagram API error creating media: {create_response.status_code} - {create_response.text}")
        
        creation_id = create_response.json().get("id")
        publish_url = f"https://graph.instagram.com/v18.0/{app_id}/media_publish"
        publish_data = {"creation_id": creation_id, "access_token": access_token}
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        
        if publish_response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Instagram API error publishing: {publish_response.status_code} - {publish_response.text}")
        
        if content_id:
            content = db.query(Content).filter(Content.id == content_id, Content.user_id == current_user.id).first()
            if content:
                content.status = "posted"
                content.date_upload = datetime.now().replace(tzinfo=None)
                db.commit()
        
        logger.info(f"✅ Posted to Instagram for user {current_user.id}")
        return {"status": "success", "message": "Content posted to Instagram successfully", "media_id": publish_response.json().get("id")}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error posting to Instagram: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to post to Instagram: {str(e)}")


# ============================================================================
# PLATFORM CREDENTIALS MANAGEMENT ENDPOINTS
# ============================================================================

@platforms_router.get("/platforms/credentials/all")
async def get_all_platform_credentials(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all platform credentials for the current user"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        connections = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id
        ).all()
        
        credentials = {}
        for conn in connections:
            platform_name = conn.platform.value.lower()
            
            if conn.platform == PlatformEnum.LINKEDIN:
                # LinkedIn uses platform's app - return connection status and account info
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "connected": bool(conn.access_token),
                    "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                    "platform_user_id": conn.platform_user_id or "",
                }
            elif conn.platform == PlatformEnum.TWITTER:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.platform_user_id and conn.refresh_token),
                    "api_key": conn.platform_user_id or "",
                    "api_secret": conn.refresh_token or "",
                    "access_token": conn.access_token or "",
                }
            elif conn.platform == PlatformEnum.WORDPRESS:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.platform_user_id and conn.refresh_token and conn.access_token),
                    "site_url": conn.platform_user_id or "",
                    "username": conn.refresh_token or "",
                    "app_password": conn.access_token or "",
                }
            elif conn.platform == PlatformEnum.INSTAGRAM:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token and conn.platform_user_id),
                    "app_id": conn.platform_user_id or "",
                    "app_secret": conn.refresh_token or "",
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
            elif conn.platform == PlatformEnum.FACEBOOK:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
            else:
                credentials[platform_name] = {
                    "has_credentials": bool(conn.access_token),
                    "access_token": conn.access_token or "",
                    "platform_user_id": conn.platform_user_id or "",
                }
        
        return {"success": True, "credentials": credentials}
    except Exception as e:
        logger.error(f"❌ Error fetching platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch credentials: {str(e)}")

@platforms_router.post("/platforms/{platform}/refresh-profile")
async def refresh_platform_profile(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh user profile information for an existing OAuth connection"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        if not connection or not connection.access_token:
            raise HTTPException(status_code=404, detail=f"No {platform} connection found")
        
        access_token = connection.access_token
        user_email = None
        user_name = None
        platform_user_identifier = None
        
        if platform_enum == PlatformEnum.LINKEDIN:
            try:
                # Try OpenID Connect userinfo endpoint first
                profile_url = "https://api.linkedin.com/v2/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_email = profile_data.get("email")
                    user_name = profile_data.get("name")
                    logger.info(f"✅ Refreshed LinkedIn profile: email={user_email}, name={user_name}")
                else:
                    # Fallback to basic profile endpoint
                    profile_url = "https://api.linkedin.com/v2/me"
                    profile_response = requests.get(profile_url, headers=headers)
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        user_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
                        logger.info(f"✅ Refreshed LinkedIn basic profile: name={user_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not refresh LinkedIn profile: {e}")
            
            platform_user_identifier = user_email or user_name or "LinkedIn User"
            
        elif platform_enum == PlatformEnum.FACEBOOK or platform_enum == PlatformEnum.INSTAGRAM:
            try:
                profile_url = "https://graph.facebook.com/v18.0/me"
                params = {
                    "access_token": access_token,
                    "fields": "email,name"
                }
                profile_response = requests.get(profile_url, params=params)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    user_email = profile_data.get("email")
                    user_name = profile_data.get("name")
                    logger.info(f"✅ Refreshed {platform} profile: email={user_email}, name={user_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not refresh {platform} profile: {e}")
            
            platform_user_identifier = user_email or user_name or f"{platform} User"
        
        if platform_user_identifier:
            connection.platform_user_id = platform_user_identifier
            db.commit()
            return {"success": True, "message": f"{platform} profile refreshed", "platform_user_id": platform_user_identifier}
        else:
            return {"success": False, "message": f"Could not fetch {platform} profile information"}
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error refreshing {platform} profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh profile: {str(e)}")

@platforms_router.post("/platforms/{platform}/credentials/save")
async def save_platform_credentials(
    platform: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update platform credentials"""
    try:
        from models import PlatformConnection, PlatformEnum
        from datetime import datetime
        
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).first()
        
        if platform_enum == PlatformEnum.LINKEDIN:
            # LinkedIn uses OAuth - users cannot provide Client ID/Secret
            raise HTTPException(
                status_code=400,
                detail="LinkedIn uses OAuth flow. Use /linkedin/auth-v2 to connect your account."
            )
        elif platform_enum == PlatformEnum.TWITTER:
            api_key = request_data.get("api_key", "").strip()
            api_secret = request_data.get("api_secret", "").strip()
            if not api_key or not api_secret:
                raise HTTPException(status_code=400, detail="Twitter API Key and API Secret are required")
            if connection:
                connection.platform_user_id = api_key
                connection.refresh_token = api_secret
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=api_key, refresh_token=api_secret,
                    access_token="", connected_at=datetime.now()
                )
                db.add(connection)
        elif platform_enum == PlatformEnum.WORDPRESS:
            site_url = request_data.get("site_url", "").strip()
            username = request_data.get("username", "").strip()
            app_password = request_data.get("app_password", "").strip()
            if not site_url or not username or not app_password:
                raise HTTPException(status_code=400, detail="WordPress Site URL, Username, and App Password are required")
            if connection:
                connection.platform_user_id = site_url
                connection.refresh_token = username
                connection.access_token = app_password
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=site_url, refresh_token=username,
                    access_token=app_password, connected_at=datetime.now()
                )
                db.add(connection)
        elif platform_enum == PlatformEnum.INSTAGRAM:
            app_id = request_data.get("app_id", "").strip()
            app_secret = request_data.get("app_secret", "").strip()
            access_token = request_data.get("access_token", "").strip()
            if not app_id or not app_secret or not access_token:
                raise HTTPException(status_code=400, detail="Instagram App ID, App Secret, and Access Token are required")
            if connection:
                connection.platform_user_id = app_id
                connection.refresh_token = app_secret
                connection.access_token = access_token
                connection.connected_at = datetime.now()
            else:
                connection = PlatformConnection(
                    user_id=current_user.id, platform=platform_enum,
                    platform_user_id=app_id, refresh_token=app_secret,
                    access_token=access_token, connected_at=datetime.now()
                )
                db.add(connection)
        else:
            raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
        
        db.commit()
        return {"success": True, "message": f"{platform} credentials saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")

@platforms_router.delete("/platforms/{platform}/credentials")
async def remove_platform_credentials(
    platform: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove platform credentials - DELETE all connections for this platform (permanent removal)"""
    try:
        from models import PlatformConnection, PlatformEnum
        
        # Convert platform name to enum
        try:
            platform_enum = PlatformEnum[platform.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
        
        # Find ALL connections for this platform and user
        connections = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum
        ).all()
        
        if connections:
            # DELETE all connection records (permanent removal)
            for connection in connections:
                db.delete(connection)
            db.commit()
            
            return {
                "success": True,
                "message": f"{platform} disconnected successfully - all connections removed"
            }
        else:
            return {
                "success": True,
                "message": f"No {platform} connections found to remove"
            }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error removing platform credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove credentials: {str(e)}")


# [Paste endpoint code here]


@platforms_router.get("/facebook/auth-v2")
async def facebook_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Facebook OAuth connection - returns auth URL for redirect"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Try system settings first, fall back to env vars
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("FACEBOOK_REDIRECT_URI", "https://machine.vernalcontentum.com/facebook/callback")
        
        if not app_id or not app_secret:
            raise HTTPException(
                status_code=500,
                detail="Facebook OAuth credentials not configured. Please configure them in Admin Settings > System > Platform Keys > Facebook."
            )
        
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state in database for verification
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.FACEBOOK,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.FACEBOOK,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        # Build Facebook OAuth URL
        auth_url = (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=pages_manage_posts,pages_read_engagement,pages_show_list"
        )
        
        logger.info(f"✅ Facebook auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Facebook auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Facebook auth URL: {str(e)}"
        )

@platforms_router.get("/facebook/callback")
async def facebook_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Facebook OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        load_dotenv()
        aid_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        as_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        ru_s = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_redirect_uri").first()
        aid = aid_s.setting_value if aid_s and aid_s.setting_value else os.getenv("FACEBOOK_APP_ID")
        asec = as_s.setting_value if as_s and as_s.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        ru = ru_s.setting_value if ru_s and ru_s.setting_value else os.getenv("FACEBOOK_REDIRECT_URI", "https://themachine.vernalcontentum.com/facebook/callback")
        if not aid or not asec:
            logger.error("❌ Facebook OAuth credentials not configured")
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=facebook_not_configured")
        
        # Log state for debugging
        logger.info(f"🔍 Facebook callback - Looking for state token: {state[:20]}...")
        
        # Check for state token - also check if it was recently created (within last 10 minutes)
        from datetime import timedelta
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        
        st = db.query(StateToken).filter(
            StateToken.platform == PlatformEnum.FACEBOOK,
            StateToken.state == state,
            StateToken.created_at >= ten_minutes_ago
        ).first()
        
        if not st:
            # Log all recent state tokens for debugging
            all_states = db.query(StateToken).filter(
                StateToken.platform == PlatformEnum.FACEBOOK,
                StateToken.created_at >= ten_minutes_ago
            ).all()
            logger.warning(f"⚠️ State token not found. Received state: {state[:20]}... Found {len(all_states)} recent state tokens")
            if all_states:
                logger.warning(f"⚠️ Recent state tokens: {[s.state[:20] + '...' for s in all_states[:3]]}")
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=invalid_state&message=State token expired or not found. Please try connecting again.")
        uid = st.user_id
        db.delete(st)
        r = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={"client_id": aid, "client_secret": asec, "redirect_uri": ru, "code": code})
        if r.status_code != 200:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        at = r.json().get("access_token")
        if not at:
            return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # Fetch user profile information from Facebook
        user_email = None
        user_name = None
        try:
            profile_url = "https://graph.facebook.com/v18.0/me"
            params = {
                "access_token": at,
                "fields": "email,name"
            }
            profile_response = requests.get(profile_url, params=params)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_email = profile_data.get("email")
                user_name = profile_data.get("name")
                logger.info(f"✅ Fetched Facebook profile: email={user_email}, name={user_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch Facebook profile: {e}")
            # Continue without profile info - connection still works
        
        # Use email if available, otherwise use name, otherwise use a generic identifier
        platform_user_identifier = user_email or user_name or "Facebook User"
        
        conn = db.query(PlatformConnection).filter(PlatformConnection.user_id == uid, PlatformConnection.platform == PlatformEnum.FACEBOOK).first()
        if conn:
            conn.access_token = at
            conn.connected_at = datetime.now()
            if platform_user_identifier:
                conn.platform_user_id = platform_user_identifier
        else:
            conn = PlatformConnection(user_id=uid, platform=PlatformEnum.FACEBOOK, access_token=at, platform_user_id=platform_user_identifier, connected_at=datetime.now())
            db.add(conn)
        db.commit()
        logger.info(f"✅ Facebook connection successful for user {uid}")
        return RedirectResponse(url="https://machine.vernalcontentum.com/account-settings?facebook=connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in Facebook callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"https://machine.vernalcontentum.com/account-settings?error=callback_failed&message={str(e)}")


@platforms_router.get("/instagram/auth-v2")
async def instagram_auth_v2(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate Instagram OAuth connection - uses Facebook OAuth (Instagram is part of Facebook)
    
    Architecture:
    - Uses APPLICATION credentials from Admin Settings (SystemSettings) for OAuth
    - Stores USER's Instagram Business Account ID in PlatformConnection (user account settings)
    - Each user connects their personal Instagram account via /account-settings
    """
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Get APPLICATION credentials from admin settings (SystemSettings)
        # These are the app-level credentials used for OAuth, stored in /admin
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "instagram_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("INSTAGRAM_REDIRECT_URI", "https://machine.vernalcontentum.com/instagram/callback")
        
        if not app_id or not app_secret:
            logger.error("❌ Instagram OAuth: Application credentials not configured in Admin Settings")
            raise HTTPException(
                status_code=500,
                detail="Instagram OAuth credentials not configured. Please configure Facebook App credentials in Admin Settings > System > Platform Keys > Facebook (Instagram uses Facebook OAuth)."
            )
        
        logger.info(f"🔑 Using APPLICATION credentials (App ID: {app_id[:10]}...) from Admin Settings for user {current_user.id}'s OAuth flow")
        
        import secrets
        state = secrets.token_urlsafe(32)
        
        existing_state = db.query(StateToken).filter(
            StateToken.user_id == current_user.id,
            StateToken.platform == PlatformEnum.INSTAGRAM,
            StateToken.state == state
        ).first()
        
        if not existing_state:
            new_state = StateToken(
                user_id=current_user.id,
                platform=PlatformEnum.INSTAGRAM,
                state=state,
                created_at=datetime.now()
            )
            db.add(new_state)
        
        db.commit()
        
        # Build Facebook OAuth URL (Instagram uses Facebook OAuth)
        # Scopes: instagram_basic, instagram_content_publish for Instagram posting
        # Also need pages_manage_posts, pages_read_engagement, pages_show_list for Facebook Pages (Instagram Business Accounts are linked to Pages)
        auth_url = (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope=pages_manage_posts,pages_read_engagement,pages_show_list,instagram_basic,instagram_content_publish"
        )
        
        logger.info(f"✅ Instagram auth URL generated for user {current_user.id}")
        return {
            "status": "success",
            "auth_url": auth_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating Instagram auth URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Instagram auth URL: {str(e)}"
        )

@platforms_router.get("/instagram/callback")
async def instagram_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Instagram OAuth callback - NO AUTH REQUIRED"""
    try:
        from models import PlatformConnection, PlatformEnum, StateToken, SystemSettings
        import os
        from dotenv import load_dotenv
        import requests
        from fastapi.responses import RedirectResponse
        from datetime import datetime
        
        load_dotenv()
        
        # Instagram uses Facebook OAuth credentials
        app_id_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_id").first()
        app_secret_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "facebook_app_secret").first()
        redirect_uri_setting = db.query(SystemSettings).filter(SystemSettings.setting_key == "instagram_redirect_uri").first()
        
        app_id = app_id_setting.setting_value if app_id_setting and app_id_setting.setting_value else os.getenv("FACEBOOK_APP_ID")
        app_secret = app_secret_setting.setting_value if app_secret_setting and app_secret_setting.setting_value else os.getenv("FACEBOOK_APP_SECRET")
        redirect_uri = redirect_uri_setting.setting_value if redirect_uri_setting and redirect_uri_setting.setting_value else os.getenv("INSTAGRAM_REDIRECT_URI", "https://themachine.vernalcontentum.com/instagram/callback")
        
        if not app_id or not app_secret:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=instagram_not_configured")
        
        # Verify state and get user_id from StateToken
        state_token = db.query(StateToken).filter(
            StateToken.platform == PlatformEnum.INSTAGRAM,
            StateToken.state == state
        ).first()
        
        if not state_token:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=invalid_state")
        
        user_id = state_token.user_id
        
        # Clean up state token
        db.delete(state_token)
        db.commit()
        
        # Exchange code for access token
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        token_params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        
        response = requests.get(token_url, params=token_params)
        if response.status_code != 200:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=token_exchange_failed")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=no_access_token")
        
        # First, check what permissions the token has
        logger.info(f"🔍 Checking access token permissions for user {user_id}...")
        debug_token_url = "https://graph.facebook.com/v18.0/debug_token"
        debug_params = {
            "input_token": access_token,
            "access_token": access_token
        }
        debug_response = requests.get(debug_token_url, params=debug_params, timeout=30)
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            token_info = debug_data.get("data", {})
            scopes = token_info.get("scopes", [])
            logger.info(f"📋 Token scopes: {scopes}")
            logger.info(f"📋 Token info: {json.dumps(token_info, indent=2)}")
            
            # Check if we have the required scopes
            required_scopes = ["pages_show_list", "pages_read_engagement"]
            missing_scopes = [s for s in required_scopes if s not in scopes]
            if missing_scopes:
                logger.warning(f"⚠️ Missing required scopes: {missing_scopes}")
        
        # Get user's Facebook Pages (Instagram Business Accounts are linked to Pages)
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params, timeout=30)
        
        instagram_business_account_id = None
        page_access_token = None
        
        # Log pages API response for debugging
        if pages_response.status_code != 200:
            error_data = pages_response.json() if pages_response.text else {}
            logger.error(f"❌ Failed to fetch Facebook Pages for user {user_id}: {pages_response.status_code}")
            logger.error(f"❌ Pages API error: {json.dumps(error_data, indent=2)}")
            logger.error(f"❌ Response text: {pages_response.text[:500]}")
            
            error_message = error_data.get("error", {}).get("message", "") if isinstance(error_data, dict) else str(error_data)
            if "permission" in error_message.lower() or "access" in error_message.lower():
                return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=pages_permission&message=Permission denied. Please ensure you grant 'pages_show_list' permission when authorizing the app. Try disconnecting and reconnecting Instagram.")
            else:
                return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=pages_api_failed&message=Failed to fetch Facebook Pages: {error_message}")
        
        pages_data = pages_response.json()
        pages = pages_data.get("data", [])
        
        logger.info(f"🔍 Found {len(pages)} Facebook Pages for user {user_id}")
        logger.info(f"📋 Pages API response: {json.dumps(pages_data, indent=2)}")
        
        if len(pages) == 0:
            logger.warning(f"⚠️ User {user_id} has no Facebook Pages returned by API")
            logger.warning(f"⚠️ This could mean:")
            logger.warning(f"   1. User doesn't have any Facebook Pages")
            logger.warning(f"   2. Token doesn't have 'pages_show_list' permission")
            logger.warning(f"   3. User needs to grant page access permissions")
            logger.warning(f"   4. App is in Development mode and user is not an admin/tester")
            
            # Try alternative: check if user has pages via /me/permissions
            granted_permissions = []
            try:
                permissions_url = "https://graph.facebook.com/v18.0/me/permissions"
                permissions_params = {"access_token": access_token}
                permissions_response = requests.get(permissions_url, params=permissions_params, timeout=30)
                if permissions_response.status_code == 200:
                    permissions_data = permissions_response.json()
                    logger.info(f"📋 User permissions: {json.dumps(permissions_data, indent=2)}")
                    granted_permissions = [p.get("permission") for p in permissions_data.get("data", []) if p.get("status") == "granted"]
                    logger.info(f"📋 Granted permissions: {granted_permissions}")
            except Exception as perm_error:
                logger.warning(f"⚠️ Could not check permissions: {perm_error}")
            
            # Try alternative method: /me/accounts with different parameters
            try:
                logger.info(f"🔄 Trying alternative method: /me/accounts?fields=id,name,access_token")
                alt_pages_url = "https://graph.facebook.com/v18.0/me/accounts"
                alt_pages_params = {
                    "access_token": access_token,
                    "fields": "id,name,access_token,instagram_business_account"
                }
                alt_pages_response = requests.get(alt_pages_url, params=alt_pages_params, timeout=30)
                if alt_pages_response.status_code == 200:
                    alt_pages_data = alt_pages_response.json()
                    alt_pages = alt_pages_data.get("data", [])
                    logger.info(f"🔄 Alternative method returned {len(alt_pages)} pages")
                    if len(alt_pages) > 0:
                        pages = alt_pages
                        logger.info(f"✅ Using alternative method results")
            except Exception as alt_error:
                logger.warning(f"⚠️ Alternative method failed: {alt_error}")
            
            # If still no pages, return error
            if len(pages) == 0:
                missing_perms = []
                if "pages_show_list" not in granted_permissions:
                    missing_perms.append("pages_show_list")
                if "pages_read_engagement" not in granted_permissions:
                    missing_perms.append("pages_read_engagement")
                
                error_msg = "No Facebook Pages found. "
                if missing_perms:
                    error_msg += f"Missing permissions: {', '.join(missing_perms)}. "
                error_msg += "Please: 1) Create a Facebook Page at facebook.com/pages/create, 2) Link your Instagram Business Account to that Page in Instagram Settings > Account > Linked Accounts, 3) Disconnect and reconnect Instagram here, ensuring you grant ALL requested permissions."
                
                return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=no_pages&message={error_msg.replace(' ', '%20')}")
        
        # If we got here, we have pages - reset the pages variable if we used alternative method
        if len(pages) > 0:
            logger.info(f"✅ Successfully found {len(pages)} Facebook Pages")
        
        # Find the first page with an Instagram Business Account
        for page in pages:
            page_id = page.get("id")
            page_name = page.get("name", "Unknown")
            page_access_token = page.get("access_token")
            
            if not page_id or not page_access_token:
                logger.warning(f"⚠️ Page {page_id} missing ID or access token, skipping")
                continue
            
            logger.info(f"🔍 Checking page '{page_name}' (ID: {page_id}) for Instagram Business Account...")
            
            # First, try to get the page with instagram_business_account field
            # Try multiple field combinations in case one works
            instagram_url = f"https://graph.facebook.com/v18.0/{page_id}"
            
            # Try method 1: Just instagram_business_account field
            instagram_params = {
                "fields": "instagram_business_account",
                "access_token": page_access_token
            }
            instagram_response = requests.get(instagram_url, params=instagram_params, timeout=30)
            
            # If that fails, try with more fields
            if instagram_response.status_code != 200:
                logger.warning(f"⚠️ First attempt failed ({instagram_response.status_code}), trying with more fields...")
                instagram_params = {
                    "fields": "id,name,instagram_business_account,connected_instagram_account",
                    "access_token": page_access_token
                }
                instagram_response = requests.get(instagram_url, params=instagram_params, timeout=30)
            
            # If still fails, try without fields (get all page data)
            if instagram_response.status_code != 200:
                logger.warning(f"⚠️ Second attempt failed ({instagram_response.status_code}), trying to get all page data...")
                instagram_params = {
                    "access_token": page_access_token
                }
                instagram_response = requests.get(instagram_url, params=instagram_params, timeout=30)
            
            if instagram_response.status_code == 200:
                instagram_data = instagram_response.json()
                logger.info(f"📄 Page data for '{page_name}': {json.dumps(instagram_data, indent=2)}")
                
                # Check for instagram_business_account field
                if instagram_data.get("instagram_business_account"):
                    instagram_account = instagram_data["instagram_business_account"]
                    logger.info(f"📋 Found instagram_business_account field: {json.dumps(instagram_account, indent=2) if isinstance(instagram_account, dict) else instagram_account}")
                    
                    if isinstance(instagram_account, dict):
                        instagram_business_account_id = instagram_account.get("id")
                    else:
                        instagram_business_account_id = instagram_account
                    
                    if instagram_business_account_id:
                        logger.info(f"✅ Found Instagram Business Account ID: {instagram_business_account_id} for page '{page_name}' (ID: {page_id})")
                        # Use the page access token for Instagram API calls (not the user access token)
                        access_token = page_access_token
                        break
                    else:
                        logger.warning(f"⚠️ Page '{page_name}' has instagram_business_account field but no ID: {instagram_account}")
                
                # Also check for connected_instagram_account (alternative field name)
                elif instagram_data.get("connected_instagram_account"):
                    connected_account = instagram_data["connected_instagram_account"]
                    logger.info(f"📋 Found connected_instagram_account field: {json.dumps(connected_account, indent=2) if isinstance(connected_account, dict) else connected_account}")
                    
                    if isinstance(connected_account, dict):
                        instagram_business_account_id = connected_account.get("id")
                    else:
                        instagram_business_account_id = connected_account
                    
                    if instagram_business_account_id:
                        logger.info(f"✅ Found Instagram Account ID via connected_instagram_account: {instagram_business_account_id}")
                        access_token = page_access_token
                        break
                else:
                    logger.info(f"ℹ️ Page '{page_name}' (ID: {page_id}) does not have an Instagram Business Account linked")
                    logger.info(f"💡 Available fields in page data: {list(instagram_data.keys())}")
                    logger.info(f"💡 To link Instagram: Go to Facebook Page Settings > Instagram > Connect Account")
            else:
                error_data = instagram_response.json() if instagram_response.text else {}
                error_message = error_data.get("error", {}).get("message", "") if isinstance(error_data, dict) else str(error_data)
                logger.warning(f"⚠️ Failed to check Instagram Business Account for page '{page_name}' (ID: {page_id}): {instagram_response.status_code}")
                logger.warning(f"⚠️ Error: {error_message}")
                logger.warning(f"⚠️ Full error data: {error_data}")
                
                # Check if it's a permissions issue
                if "permission" in error_message.lower() or "access" in error_message.lower():
                    logger.error(f"❌ Permission issue accessing page '{page_name}'. User may need to grant 'pages_show_list' and 'pages_read_engagement' permissions.")
        
        if not instagram_business_account_id:
            logger.warning(f"⚠️ No Instagram Business Account found for user {user_id} across {len(pages)} Facebook Pages")
            logger.warning(f"⚠️ Troubleshooting steps:")
            logger.warning(f"   1. Ensure Instagram account is linked to Facebook Page")
            logger.warning(f"   2. Ensure Instagram account is set up as a Business Account (not Personal)")
            logger.warning(f"   3. Go to Facebook Page Settings > Instagram > Connect Account")
            logger.warning(f"   4. Verify the Instagram account appears in Page Settings")
            
            # Try one more thing: check if we can get Instagram account directly from user token
            # (This might work if user has direct Instagram permissions)
            try:
                logger.info(f"🔍 Attempting alternative: checking for Instagram account via user token...")
                user_instagram_url = "https://graph.facebook.com/v18.0/me"
                user_instagram_params = {
                    "fields": "instagram_business_account",
                    "access_token": access_token
                }
                user_instagram_response = requests.get(user_instagram_url, params=user_instagram_params, timeout=30)
                if user_instagram_response.status_code == 200:
                    user_data = user_instagram_response.json()
                    logger.info(f"📄 User data: {user_data}")
                    if user_data.get("instagram_business_account"):
                        logger.info(f"✅ Found Instagram Business Account via user token!")
                        instagram_account = user_data["instagram_business_account"]
                        if isinstance(instagram_account, dict):
                            instagram_business_account_id = instagram_account.get("id")
                        else:
                            instagram_business_account_id = instagram_account
            except Exception as alt_error:
                logger.warning(f"⚠️ Alternative method also failed: {alt_error}")
            
            if not instagram_business_account_id:
                error_msg = (
                    "No Instagram Business Account found. "
                    "Please ensure: 1) Your Instagram account is linked to your Facebook Page, "
                    "2) Your Instagram account is set up as a Business Account (not Personal), "
                    "3) Go to Facebook Page Settings > Instagram to verify the connection."
                )
                return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=no_instagram_account&message={error_msg.replace(' ', '%20')}")
        
        # Store or update connection with the Instagram Business Account ID
        conn = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if conn:
            conn.access_token = access_token
            conn.platform_user_id = instagram_business_account_id  # Store numeric Instagram Business Account ID
            conn.connected_at = datetime.now()
        else:
            conn = PlatformConnection(
                user_id=user_id,
                platform=PlatformEnum.INSTAGRAM,
                access_token=access_token,
                platform_user_id=instagram_business_account_id,  # Store numeric Instagram Business Account ID
                connected_at=datetime.now()
            )
            db.add(conn)
        
        db.commit()
        logger.info(f"✅ Instagram connection successful for user {user_id}")
        logger.info(f"📝 Stored user's Instagram Business Account ID: {instagram_business_account_id} (numeric ID for posting)")
        logger.info(f"📝 Note: This is the USER's Instagram Business Account ID, not the application's App ID")
        return RedirectResponse(url="https://themachine.vernalcontentum.com/account-settings?instagram=connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Instagram callback error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        db.rollback()
        return RedirectResponse(url=f"https://themachine.vernalcontentum.com/account-settings?error=callback_failed&message={str(e)}")

@platforms_router.get("/instagram/debug")
async def instagram_debug(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check Instagram connection status and token permissions"""
    try:
        from models import PlatformConnection, PlatformEnum
        import requests
        
        connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == PlatformEnum.INSTAGRAM
        ).first()
        
        if not connection:
            return JSONResponse(content={
                "status": "error",
                "message": "No Instagram connection found",
                "has_connection": False
            })
        
        access_token = connection.access_token
        platform_user_id = connection.platform_user_id
        
        debug_info = {
            "has_connection": True,
            "platform_user_id": platform_user_id,
            "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
            "token_preview": access_token[:20] + "..." if access_token else None
        }
        
        # Check token permissions
        if access_token:
            try:
                debug_token_url = "https://graph.facebook.com/v18.0/debug_token"
                debug_params = {
                    "input_token": access_token,
                    "access_token": access_token
                }
                debug_response = requests.get(debug_token_url, params=debug_params, timeout=30)
                if debug_response.status_code == 200:
                    debug_data = debug_response.json()
                    token_info = debug_data.get("data", {})
                    debug_info["token_scopes"] = token_info.get("scopes", [])
                    debug_info["token_expires_at"] = token_info.get("expires_at")
                    debug_info["token_is_valid"] = token_info.get("is_valid", False)
            except Exception as e:
                debug_info["token_debug_error"] = str(e)
            
            # Try to get pages
            try:
                pages_url = "https://graph.facebook.com/v18.0/me/accounts"
                pages_params = {"access_token": access_token}
                pages_response = requests.get(pages_url, params=pages_params, timeout=30)
                if pages_response.status_code == 200:
                    pages_data = pages_response.json()
                    pages = pages_data.get("data", [])
                    debug_info["pages_count"] = len(pages)
                    debug_info["pages"] = [{"id": p.get("id"), "name": p.get("name")} for p in pages[:5]]  # Limit to 5
                else:
                    debug_info["pages_error"] = pages_response.text[:500]
            except Exception as e:
                debug_info["pages_error"] = str(e)
            
            # Check permissions
            try:
                permissions_url = "https://graph.facebook.com/v18.0/me/permissions"
                permissions_params = {"access_token": access_token}
                permissions_response = requests.get(permissions_url, params=permissions_params, timeout=30)
                if permissions_response.status_code == 200:
                    permissions_data = permissions_response.json()
                    granted = [p.get("permission") for p in permissions_data.get("data", []) if p.get("status") == "granted"]
                    debug_info["granted_permissions"] = granted
            except Exception as e:
                debug_info["permissions_error"] = str(e)
        
        return JSONResponse(content={
            "status": "success",
            "debug_info": debug_info
        })
    except Exception as e:
        logger.error(f"❌ Error in Instagram debug endpoint: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)
