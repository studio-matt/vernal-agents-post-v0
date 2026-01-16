"""
OpenAI API key helper functions
Moved from main.py to avoid circular imports
"""
import os
import logging
from typing import Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_openai_api_key(current_user=None, db: Session = None) -> Optional[str]:
    """
    Get OpenAI API key with priority:
    1. User's personal API key (if provided and available)
    2. Global API key from system_settings table (openai_api_key)
    3. Environment variable (OPENAI_API_KEY)
    
    Args:
        current_user: Current user object (optional, for user-specific key)
        db: Database session (optional, for global key lookup)
    
    Returns:
        API key string or None if not found
    """
    # Priority 1: User's personal API key
    if current_user and hasattr(current_user, 'openai_key') and current_user.openai_key:
        user_key = current_user.openai_key.strip()
        if user_key and len(user_key) > 50:
            logger.info(f"✅ Using user's personal OpenAI API key (user_id: {current_user.id})")
            return user_key
    
    # Priority 2: Global API key from system_settings
    if db:
        try:
            from models import SystemSettings
            global_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "openai_api_key"
            ).first()
            if global_setting and global_setting.setting_value:
                global_key = global_setting.setting_value.strip()
                if global_key and len(global_key) > 50:
                    logger.info("✅ Using global OpenAI API key from system_settings")
                    return global_key
        except Exception as e:
            logger.warning(f"Could not retrieve global API key from database: {e}")
    
    # Priority 3: Environment variable
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key and len(env_key.strip()) > 50:
        logger.info("✅ Using OpenAI API key from environment variable")
        return env_key.strip()
    
    logger.warning("⚠️  No OpenAI API key found (user, global, or env)")
    return None


