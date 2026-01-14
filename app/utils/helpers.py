"""
Utility helper functions extracted from main.py
Moved from main.py to preserve behavior
"""


def _safe_getattr(obj, attr_name, default=None):
    """Safely get attribute from SQLAlchemy model, returning default if column doesn't exist"""
    try:
        return getattr(obj, attr_name, default)
    except AttributeError:
        return default


def _safe_get_json(obj, attr_name, default=None):
    """Safely get and parse JSON attribute from SQLAlchemy model"""
    try:
        import json
        value = getattr(obj, attr_name, None)
        if value:
            return json.loads(value)
        return default
    except (AttributeError, json.JSONDecodeError, TypeError):
        return default



