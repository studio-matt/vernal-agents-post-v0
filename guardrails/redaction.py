"""
Safe logging redaction utilities.

Prevents leaking secrets, PII, and sensitive data in logs.
"""

import json
import re
from typing import Any, Dict, Optional


def redact_headers(headers: dict) -> dict:
    """
    Redact sensitive headers from request logging.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Dictionary with sensitive headers redacted
    """
    sensitive_keys = [
        "authorization",
        "cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-access-token",
    ]
    
    redacted = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    
    return redacted


def redact_text(text: str) -> str:
    """
    Redact sensitive patterns from text.
    
    Args:
        text: Raw text to redact
        
    Returns:
        Text with sensitive patterns redacted
    """
    if not text:
        return text
    
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # API keys (common patterns)
    text = re.sub(r'(?i)(api[_-]?key|apikey)[\s:=]+([A-Za-z0-9_-]{20,})', r'\1=[REDACTED]', text)
    
    # Tokens (JWT-like patterns)
    text = re.sub(r'\b(eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b', '[TOKEN_REDACTED]', text)
    
    # Bearer tokens
    text = re.sub(r'(?i)bearer\s+[A-Za-z0-9_-]{20,}', 'Bearer [REDACTED]', text)
    
    return text


def try_parse_json(text: str) -> Optional[Any]:
    """
    Attempt to parse text as JSON.
    
    Args:
        text: Text to parse
        
    Returns:
        Parsed JSON object or None if not valid JSON
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def redact_jsonish(obj: Any) -> Any:
    """
    Recursively redact sensitive fields from JSON-like structures.
    
    Args:
        obj: JSON-serializable object (dict, list, etc.)
        
    Returns:
        Object with sensitive fields redacted
    """
    if isinstance(obj, dict):
        redacted = {}
        sensitive_keys = [
            "password", "passwd", "pwd",
            "token", "access_token", "refresh_token",
            "api_key", "apikey", "apiKey",
            "secret", "secret_key", "secretKey",
            "authorization", "auth",
            "email", "email_address",
            "cookie", "cookies",
        ]
        
        for key, value in obj.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                redacted[key] = redact_jsonish(value)
            elif isinstance(value, str):
                redacted[key] = redact_text(value)
            else:
                redacted[key] = value
        
        return redacted
    
    elif isinstance(obj, list):
        return [redact_jsonish(item) for item in obj]
    
    elif isinstance(obj, str):
        return redact_text(obj)
    
    else:
        return obj

