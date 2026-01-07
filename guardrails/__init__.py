"""
Guardrails package for Vernal Agents backend.

This package provides defensive boundary layers for:
- Safe logging (redaction)
- LLM prompt protection (sanitization)
- SFTP file operations (path safety)
"""

from guardrails.redaction import redact_headers, redact_text, redact_jsonish
from guardrails.sanitize import sanitize_user_text, detect_prompt_injection, guard_or_raise, GuardrailsBlocked
from guardrails.sftp_rules import safe_filename, validate_remote_path

__all__ = [
    "redact_headers",
    "redact_text",
    "redact_jsonish",
    "sanitize_user_text",
    "detect_prompt_injection",
    "guard_or_raise",
    "GuardrailsBlocked",
    "safe_filename",
    "validate_remote_path",
]

