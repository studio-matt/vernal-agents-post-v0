import json
import re
from typing import Any, Dict

# Patterns: API keys, bearer tokens, common secret env names, emails, long tokens
_SECRET_KEYWORDS = [
    "authorization", "x-api-key", "api-key", "apikey",
    "openai", "anthropic", "claude",
    "cookie", "set-cookie",
    "secret", "token", "password", "passwd", "key",
]

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
# Rough token detector (base64-ish / JWT-ish / long alnum)
_LONG_TOKEN_RE = re.compile(r"([A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|[A-Za-z0-9_\-]{40,})")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.=]+\b")

def _looks_sensitive_key(k: str) -> bool:
    lk = k.lower()
    return any(word in lk for word in _SECRET_KEYWORDS)

def redact_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in headers.items():
        if _looks_sensitive_key(k):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out

def redact_text(s: str) -> str:
    if not s:
        return s
    s = _BEARER_RE.sub("Bearer ***REDACTED***", s)
    s = _LONG_TOKEN_RE.sub("***REDACTED_TOKEN***", s)
    s = _EMAIL_RE.sub("***REDACTED_EMAIL***", s)
    return s

def redact_jsonish(obj: Any) -> Any:
    """
    Redact secrets recursively in dict/list structures.
    """
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if _looks_sensitive_key(str(k)):
                new[k] = "***REDACTED***"
            else:
                new[k] = redact_jsonish(v)
        return new
    if isinstance(obj, list):
        return [redact_jsonish(x) for x in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj

def try_parse_json(body_str: str):
    try:
        return json.loads(body_str)
    except Exception:
        return None
