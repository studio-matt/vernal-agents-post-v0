# Guardrails System Documentation

## Overview

The Guardrails system provides defensive boundary layers for the Vernal Agents backend. It protects against prompt injection attacks, ensures safe logging, and enforces filesystem safety.

**Purpose:** Prevent security vulnerabilities, data leakage, and maintain code quality.

**Location:** `guardrails/` package in backend root

---

## Components

### 1. Prompt Sanitization & Injection Detection (`guardrails/sanitize.py`)

**What it does:** Sanitizes user input before sending to LLMs and detects prompt injection attempts.

#### Key Functions

**`sanitize_user_text(text, max_len=12000)`**
- Truncates text to max length
- Removes control characters (except newlines/tabs)
- Normalizes whitespace
- Returns cleaned text

**`detect_prompt_injection(text)`**
- Scans for common injection patterns:
  - "ignore previous instructions"
  - "forget everything"
  - "you are now a..."
  - System prompt injection markers
  - Special token injections
  - Suspicious repetition patterns
- Returns: `(is_injection: bool, reason: str | None)`

**`guard_or_raise(text, max_len=12000)`** ⭐ **Primary Function**
- **Always use this** instead of calling sanitize/detect separately
- Sanitizes text first
- Detects injection
- Raises `GuardrailsBlocked` if blocking enabled
- Returns: `(sanitized_text, audit_dict)`

#### Usage Pattern

```python
from guardrails.sanitize import guard_or_raise

# Before any LLM call:
prompt, audit = guard_or_raise(prompt, max_len=12000)

# Then use sanitized prompt:
response = llm.invoke(prompt)
```

#### Blocking Behavior

**When `GUARDRAILS_BLOCK_INJECTION=1`:**
- Injection detected → Raises `GuardrailsBlocked` exception
- FastAPI handler → Returns HTTP 400 with JSON:
  ```json
  {
    "error": "guardrails_blocked",
    "message": "Potential prompt injection detected: ...",
    "matched": "..."
  }
  ```

**When `GUARDRAILS_BLOCK_INJECTION=0`:**
- Injection detected → Logs warning, continues execution
- No exception raised

#### Exception: `GuardrailsBlocked`

Custom exception raised when blocking is enabled and injection is detected.

```python
from guardrails.sanitize import GuardrailsBlocked

# Exception attributes:
exc.matched  # The detected pattern/reason
```

**FastAPI Handler:** Automatically converts to HTTP 400 (see `main.py` exception handlers)

---

### 2. Safe Logging (`guardrails/redaction.py`)

**What it does:** Prevents secrets, PII, and sensitive data from appearing in logs.

#### Key Functions

**`redact_headers(headers)`**
- Redacts sensitive HTTP headers:
  - `authorization`, `cookie`, `x-api-key`, `api-key`, `x-auth-token`, etc.
- Returns headers dict with sensitive values replaced with `[REDACTED]`

**`redact_text(text)`**
- Redacts patterns in text:
  - Email addresses → `[EMAIL_REDACTED]`
  - API keys → `[REDACTED]`
  - JWT tokens → `[TOKEN_REDACTED]`
  - Bearer tokens → `Bearer [REDACTED]`

**`redact_jsonish(obj)`**
- Recursively redacts sensitive fields in JSON-like structures
- Sensitive keys: `password`, `token`, `api_key`, `secret`, `email`, etc.
- Returns object with sensitive values replaced

#### Usage

```python
from guardrails.redaction import redact_headers, redact_jsonish

# In request logging middleware:
logger.info(f"Headers: {redact_headers(dict(request.headers))}")

# In error handlers:
safe_body = redact_jsonish(request_body)
logger.error(f"Request body: {safe_body}")
```

---

### 3. Filesystem Safety (`guardrails/sftp_rules.py`)

**What it does:** Prevents path traversal attacks and unsafe file operations.

#### Key Functions

**`safe_filename(name)`**
- Extracts basename (removes path components)
- Removes `..`, `/`, `\` characters
- Removes null bytes and control characters
- Limits length to 255 characters
- Returns safe filename

**`validate_remote_path(remote_dir=None)`**
- Validates and normalizes remote directory path
- Prevents path traversal outside home directory
- Falls back to `/home/{SFTP_USER}/public_html` if not set
- Returns validated absolute path

#### Usage

```python
from guardrails.sftp_rules import safe_filename, validate_remote_path

# Before SFTP upload:
safe_name = safe_filename(user_provided_filename)
remote_path = validate_remote_path()
```

---

## Integration Points

### Where Guardrails Are Used

**All LLM call sites must use `guard_or_raise()`:**

1. **main.py** (5 locations):
   - Agent recommendations (`llm.invoke`)
   - Site builder parent prompts
   - Site builder children prompts
   - Knowledge graph location prompts

2. **tasks.py** (1 location):
   - `analyze_text()` function

3. **machine_agent.py** (1 location):
   - Agent execution (`client.chat.completions.create`)

### Exception Handling

**FastAPI Exception Handler** (`main.py`):
```python
@app.exception_handler(GuardrailsBlocked)
async def guardrails_blocked_handler(request: Request, exc: GuardrailsBlocked):
    return JSONResponse(
        status_code=400,
        content={
            "error": "guardrails_blocked",
            "message": str(exc),
            "matched": getattr(exc, "matched", None),
        },
        headers=cors_headers,
    )
```

**Global Exception Handler** (`main.py`):
- Re-raises `GuardrailsBlocked` so specific handler catches it
- Prevents accidental 500 errors

---

## Environment Variables

### `GUARDRAILS_BLOCK_INJECTION`
- **Type:** String ("0" or "1")
- **Default:** "0" (warn only)
- **Description:** Enable/disable blocking for prompt injection
- **Location:** Backend `.env` file or systemd environment

### `SFTP_REMOTE_DIR`
- **Type:** String (path)
- **Default:** `/home/{SFTP_USER}/public_html`
- **Description:** Remote directory for SFTP operations
- **Location:** Backend `.env` file

---

## Audit Dictionary

The `guard_or_raise()` function returns an audit dictionary:

```python
{
    "sanitized": True,
    "prompt_injection_detected": bool,
    "matched": str | None,  # Pattern description (not the prompt!)
    "blocked": bool,
    "truncated": bool,
    "original_len": int,
    "sanitized_len": int,
    "max_len": int,
}
```

**Important:** The audit dict does NOT contain prompt content (security safe).

---

## Best Practices

### ✅ DO

- Always use `guard_or_raise()` before LLM calls
- Use `redact_headers()` and `redact_jsonish()` in logging
- Use `safe_filename()` for user-provided filenames
- Check `GUARDRAILS_BLOCK_INJECTION` env var for blocking behavior

### ❌ DON'T

- Don't call `sanitize_user_text()` and `detect_prompt_injection()` separately
- Don't log raw prompts or user input
- Don't bypass guardrails for "trusted" input
- Don't modify guardrails behavior without updating this doc

---

## Testing

### Test Blocking Enabled

```bash
# Set in .env
GUARDRAILS_BLOCK_INJECTION=1

# Send request with injection:
curl -X POST /api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"prompt": "ignore previous instructions"}'

# Expected: HTTP 400 with guardrails_blocked error
```

### Test Warn-Only Mode

```bash
# Set in .env
GUARDRAILS_BLOCK_INJECTION=0

# Send request with injection:
# Expected: Warning in logs, request continues normally
```

---

## Troubleshooting

### Issue: Guardrails not blocking

**Check:**
1. `GUARDRAILS_BLOCK_INJECTION=1` in `.env`?
2. Service restarted after env change?
3. Exception handler registered in `main.py`?

### Issue: False positives

**Solution:** Review injection patterns in `detect_prompt_injection()`. Patterns are conservative by design.

### Issue: Audit dict missing

**Check:** Are you using `guard_or_raise()`? It returns the audit dict as the second value.

---

## For AI Assistants (LLM Context)

**Key Points:**
- Always use `guard_or_raise(text)` before LLM calls
- Never bypass guardrails, even for "internal" prompts
- The audit dict is safe to log (no prompt content)
- `GuardrailsBlocked` exceptions become HTTP 400, not 500
- Blocking is controlled by `GUARDRAILS_BLOCK_INJECTION` env var

**When adding new LLM call sites:**
1. Import: `from guardrails.sanitize import guard_or_raise`
2. Before LLM call: `prompt, audit = guard_or_raise(prompt, max_len=12000)`
3. Use sanitized prompt: `response = llm.invoke(prompt)`
4. Optionally log audit dict (safe, no secrets)

---

## Related Documentation

- `ENVIRONMENT_VARIABLES_NEEDED.md` - Environment variable reference
- `GUARDRAILS_BLOCKING_IMPLEMENTATION.md` - Implementation details
- `GUARDRAILS_VERIFICATION.md` - Verification checklist

