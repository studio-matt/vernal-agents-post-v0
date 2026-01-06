"""
Guardrails package

Responsibilities:
- redact secrets/PII from logs
- sanitize inbound user text before sending to LLM/tools
- validate filenames/paths for SFTP uploads
- lightweight prompt-injection heuristics
"""

from .redaction import redact_headers, redact_text, redact_jsonish
from .sanitize import sanitize_user_text, detect_prompt_injection
from .sftp_rules import validate_remote_path, safe_filename
