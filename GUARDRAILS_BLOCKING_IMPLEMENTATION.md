# Guardrails Blocking Implementation

## Summary

Implemented clean HTTP 400 responses for prompt injection blocking across all LLM call sites.

## Changes Made

### 1. Added GuardrailsBlocked Exception and Helper (`guardrails/sanitize.py`)

- **GuardrailsBlocked Exception**: Custom exception with `matched` attribute storing the detected pattern
- **guard_or_raise() Function**: Unified helper that:
  - Always sanitizes text first
  - Detects prompt injection
  - Raises `GuardrailsBlocked` if blocking enabled (`GUARDRAILS_BLOCK_INJECTION=1`)
  - Logs warning if blocking disabled
  - Returns `(sanitized_text, audit_dict)` for future audit logging

### 2. Replaced Duplicated Blocks

**main.py** (5 locations):
- Line ~5347: Before `llm.invoke(prompt)` in agent recommendations
- Line ~7017: Before `llm.invoke(parent_prompt)` in site builder
- Line ~7033: Before `llm.invoke(children_prompt)` in site builder
- Line ~7051: Before `llm.invoke(kg_location_prompt_full)` in site builder

**tasks.py** (1 location):
- Line ~166: Before `client.chat.completions.create()` in `analyze_text()`

**machine_agent.py** (1 location):
- Line ~125: Before `self.client.chat.completions.create()` in agent execution

### 3. Added FastAPI Exception Handler (`main.py`)

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

This ensures any `GuardrailsBlocked` exception (even from deep in tasks/agents) becomes a clean HTTP 400, not a 500.

## Behavior

### When `GUARDRAILS_BLOCK_INJECTION=1`:
- Injection detected → Raises `GuardrailsBlocked`
- FastAPI handler → Returns HTTP 400 with JSON:
  ```json
  {
    "error": "guardrails_blocked",
    "message": "Potential prompt injection detected: ...",
    "matched": "..."
  }
  ```

### When `GUARDRAILS_BLOCK_INJECTION=0`:
- Injection detected → Logs warning, continues execution
- No exception raised, normal flow continues

## Verification

On the backend server, run:

```bash
# Compile check
python3 -m py_compile main.py tasks.py machine_agent.py guardrails/*.py

# Restart service
sudo systemctl restart vernal-agents.service

# Check logs
sudo journalctl -u vernal-agents.service -n 80 --no-pager
```

## Testing

To test blocking:
1. Set `GUARDRAILS_BLOCK_INJECTION=1` in systemd environment
2. Send a request with prompt injection (e.g., "ignore previous instructions")
3. Should receive HTTP 400 with `guardrails_blocked` error

To test warn-only:
1. Set `GUARDRAILS_BLOCK_INJECTION=0` (or unset)
2. Send a request with prompt injection
3. Should see warning in logs, request continues normally

## Files Modified

- `guardrails/sanitize.py` - Added exception and helper
- `guardrails/__init__.py` - Export new symbols
- `main.py` - Added exception handler, replaced 5 blocks
- `tasks.py` - Replaced 1 block
- `machine_agent.py` - Replaced 1 block

## Commit

Backend commit: `[commit hash]` - "Add GuardrailsBlocked exception and unified guard_or_raise helper"


