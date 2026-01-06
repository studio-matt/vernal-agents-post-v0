import re
from typing import Tuple

# Very lightweight heuristic flags. This is not "perfect security" but it catches common prompt injection patterns.
_INJECTION_SIGNALS = [
    r"(?i)\bignore (all|any|previous) instructions\b",
    r"(?i)\bsystem prompt\b",
    r"(?i)\bdeveloper message\b",
    r"(?i)\byou are chatgpt\b",
    r"(?i)\breveal\b.*\bsecret\b",
    r"(?i)\bexfiltrate\b",
    r"(?i)\bdo anything now\b|\bDAN\b",
    r"(?i)\bBEGIN\s+SYSTEM\b|\bEND\s+SYSTEM\b",
    r"(?i)\btool\b.*\boverride\b",
]

_INJECTION_RE = [re.compile(p) for p in _INJECTION_SIGNALS]

def detect_prompt_injection(text: str) -> Tuple[bool, str]:
    if not text:
        return (False, "")
    for rx in _INJECTION_RE:
        if rx.search(text):
            return (True, rx.pattern)
    return (False, "")

def sanitize_user_text(text: str, max_len: int = 12000) -> str:
    """
    Basic normalization:
    - trim
    - cap length
    - remove null bytes
    """
    if text is None:
        return ""
    text = str(text).replace("\x00", "").strip()
    if len(text) > max_len:
        text = text[:max_len] + "\n...[TRUNCATED]..."
    return text
