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


def _looks_like_openai_secret(value: Optional[str]) -> bool:
    if not value:
        return False
    s = value.strip()
    # OpenAI issued secrets are sk-… and are much longer than placeholders.
    return s.startswith("sk-") and len(s) >= 20


def get_openai_api_key(current_user=None, db: Session = None) -> Optional[str]:
    """
    Resolve the OpenAI API key for LLM calls.

    Default: admin/system key from ``system_settings`` (``openai_api_key``).

    Override: only when the authenticated user has stored a personal key on
    their account (``User.openai_key``) that looks like a real OpenAI secret.

    Fallback: ``OPENAI_API_KEY`` environment variable.

    Args:
        current_user: User ORM instance (optional). Non-user values (e.g. raw
            ids) are ignored for BYOK so the system key remains the default.
        db: Database session (optional, required to load the system key).

    Returns:
        API key string or None if not found.
    """
    system_key: Optional[str] = None
    if db:
        try:
            from models import SystemSettings

            global_setting = (
                db.query(SystemSettings)
                .filter(SystemSettings.setting_key == "openai_api_key")
                .first()
            )
            if global_setting and global_setting.setting_value:
                candidate = global_setting.setting_value.strip()
                if _looks_like_openai_secret(candidate):
                    system_key = candidate
        except Exception as e:
            logger.warning("Could not retrieve global API key from database: %s", e)

    user_key: Optional[str] = None
    if current_user is not None and hasattr(current_user, "openai_key"):
        raw = getattr(current_user, "openai_key", None)
        if raw:
            candidate = str(raw).strip()
            if _looks_like_openai_secret(candidate):
                user_key = candidate

    env_raw = os.getenv("OPENAI_API_KEY")
    env_key = env_raw.strip() if env_raw and _looks_like_openai_secret(env_raw) else None

    if user_key:
        uid = getattr(current_user, "id", None)
        logger.info("Using user-provided OpenAI API key (BYOK override, user_id=%s)", uid)
        return user_key
    if system_key:
        logger.info("Using system OpenAI API key from admin settings")
        return system_key
    if env_key:
        logger.info("Using OpenAI API key from environment variable")
        return env_key

    logger.warning("No OpenAI API key found (system admin key, user BYOK, or env)")
    return None



