"""
LLM prompt sanitization and injection detection.

Protects against prompt injection attacks and ensures safe prompt execution.
"""

import os
import re
from typing import Tuple, Optional


def sanitize_user_text(text: str, max_len: int = 12000) -> str:
    """
    Sanitize user text before sending to LLM.
    
    - Enforces max length
    - Removes control characters
    - Normalizes whitespace
    
    Args:
        text: User-provided text
        max_len: Maximum allowed length (default 12000)
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_len:
        text = text[:max_len]
    
    # Remove control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize whitespace (preserve intentional newlines)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double
    
    return text.strip()


def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect common prompt injection patterns.
    
    Args:
        text: Text to check
        
    Returns:
        Tuple of (is_injection: bool, reason: str | None)
    """
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    # Common injection patterns
    injection_patterns = [
        (r'ignore\s+(previous|above|all|prior)\s+(instructions?|prompts?|rules?)', 'Ignore previous instructions'),
        (r'forget\s+(everything|all|previous)', 'Forget command'),
        (r'you\s+are\s+now\s+(a|an)\s+', 'Role hijacking'),
        (r'system\s*:\s*', 'System prompt injection'),
        (r'<\|(system|user|assistant)\|>', 'Special token injection'),
        (r'\[INST\]|\[/INST\]', 'Llama format injection'),
        (r'###\s*(system|user|assistant)\s*:', 'Format injection'),
        (r'override|bypass|hack', 'Override keywords'),
        (r'new\s+instructions?\s*:', 'New instructions'),
        (r'disregard|disobey', 'Disregard commands'),
    ]
    
    for pattern, reason in injection_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, f"Potential prompt injection detected: {reason}"
    
    # Check for suspicious repetition (possible obfuscation)
    if len(set(text_lower.split())) < len(text_lower.split()) * 0.3:
        # More than 70% of words are repeated
        return True, "Suspicious repetition pattern (possible obfuscation)"
    
    return False, None


def should_block_injection() -> bool:
    """
    Check if prompt injection should block execution (vs warn only).
    
    Returns:
        True if blocking is enabled, False for warn-only mode
    """
    return os.getenv("GUARDRAILS_BLOCK_INJECTION", "0") == "1"


class GuardrailsBlocked(Exception):
    """
    Exception raised when prompt injection is detected and blocking is enabled.
    
    Attributes:
        matched: The matched pattern/reason for the block
    """
    def __init__(self, message: str, matched: Optional[str] = None):
        super().__init__(message)
        self.matched = matched


def guard_or_raise(text: str, max_len: int = 12000) -> Tuple[str, dict]:
    """
    Sanitize text and check for prompt injection. Raise GuardrailsBlocked if blocking is enabled.
    
    This is the unified helper that replaces repeated sanitize/detect blocks across the codebase.
    
    Args:
        text: User-provided text to sanitize and check
        max_len: Maximum allowed length (default 12000)
        
    Returns:
        Tuple of (sanitized_text, audit_dict) where audit_dict includes:
        - sanitized: bool
        - prompt_injection_detected: bool
        - matched: str | None (the matched pattern/reason)
        - blocked: bool (whether blocking was enabled and triggered)
        
    Raises:
        GuardrailsBlocked: If injection is detected and blocking is enabled
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Always sanitize first
    sanitized = sanitize_user_text(text, max_len=max_len)
    
    # Run detection
    is_inj, matched = detect_prompt_injection(sanitized)
    
    # Read blocking flag
    block = os.getenv("GUARDRAILS_BLOCK_INJECTION", "0").strip() == "1"
    
    # Build audit dict
    audit_dict = {
        "sanitized": True,
        "prompt_injection_detected": is_inj,
        "matched": matched,
        "blocked": False,
    }
    
    if is_inj:
        msg = f"Potential prompt injection detected: {matched}"
        if block:
            audit_dict["blocked"] = True
            raise GuardrailsBlocked(msg, matched=matched)
        else:
            # Warn-only mode: log and continue
            logger.warning(msg)
    
    return sanitized, audit_dict

