"""
Environment variable overrides from Admin > Environment Variables (SystemSettings env_*).
All editable vars on the Admin Environment Variables page are read from here first, then os.getenv.
This makes changing those items in the UI take effect without server restart.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache of env_* values from SystemSettings (key without "env_" prefix -> value)
_env_override_cache: dict = {}
_loaded = False


def _load_env_overrides_from_db() -> None:
    """Load env_* keys from SystemSettings into cache. Safe to call; logs and no-op on error."""
    global _env_override_cache, _loaded
    try:
        from database import SessionLocal
        from models import SystemSettings
        db = SessionLocal()
        try:
            rows = db.query(SystemSettings).filter(SystemSettings.setting_key.like("env_%")).all()
            _env_override_cache = {}
            for s in rows:
                if s.setting_key and s.setting_key.startswith("env_") and s.setting_value is not None:
                    key = s.setting_key[4:]  # strip "env_"
                    _env_override_cache[key] = str(s.setting_value).strip()
            _loaded = True
            if _env_override_cache:
                logger.debug("Loaded %d env overrides from Admin Settings", len(_env_override_cache))
        finally:
            db.close()
    except Exception as e:
        logger.warning("Could not load env overrides from Admin Settings: %s", e)
        _env_override_cache = {}
        _loaded = True  # don't retry every time


def get_effective_env(key: str, default: Optional[str] = None) -> str:
    """
    Get effective value for an environment variable: Admin Settings (env_*) first, then os.getenv.
    Used so Admin > Environment Variables page controls behavior without server restart.
    """
    global _loaded
    if not _loaded:
        _load_env_overrides_from_db()
    value = _env_override_cache.get(key)
    if value is not None:
        return value
    return os.getenv(key, default) if default is not None else os.getenv(key, "")


def refresh_env_overrides() -> None:
    """Clear cache so next get_effective_env() reloads from DB. Call after Admin updates an env var."""
    global _env_override_cache, _loaded
    _env_override_cache = {}
    _loaded = False
    logger.info("Env overrides cache cleared; will reload from Admin Settings on next use")
