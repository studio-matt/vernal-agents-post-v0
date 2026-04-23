"""
Safe assembly of admin-edited prompt templates.

str.format() treats every `{...}` as a replacement field, so JSON examples,
schema snippets, or prose like "use {curly} braces" break at runtime. Research
(and similar) prompts only need a bounded set of injected values — use
explicit placeholder rules + doubled-brace escapes instead.
"""

from __future__ import annotations

import re
from typing import Iterable, Set

# Sentinels must not appear in real campaign/scrape text.
_DBL_L = "\ufdd0FMT_ESC_L\ufdd1"
_DBL_R = "\ufdd0FMT_ESC_R\ufdd1"

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _mask_double_braces(s: str) -> str:
    return s.replace("{{", _DBL_L).replace("}}", _DBL_R)


def _unmask_double_braces(s: str) -> str:
    return s.replace(_DBL_L, "{{").replace(_DBL_R, "}}")


def list_unescaped_placeholders(template: str) -> Set[str]:
    """Names inside `{name}` that are not part of escaped `{{` / `}}` pairs."""
    masked = _mask_double_braces(template)
    return set(_PLACEHOLDER_RE.findall(masked))


def assert_allowed_placeholders(template: str, allowed: Iterable[str]) -> None:
    found = list_unescaped_placeholders(template)
    extra = found - set(allowed)
    if not extra:
        return
    bad = ", ".join("{" + x + "}" for x in sorted(extra))
    allowed_txt = ", ".join("{" + a + "}" for a in sorted(allowed))
    raise ValueError(
        f"Prompt contains unsupported placeholder(s): {bad}. "
        f"Allowed: {allowed_txt}. "
        "For literal curly braces in examples or JSON, double them: use {{ and }}."
    )


def truncate_prompt_injection(text: str, max_chars: int, label: str = "context") -> str:
    if len(text) <= max_chars:
        return text
    overhead = 120
    cap = max(0, max_chars - overhead)
    return (
        text[:cap]
        + f"\n\n[Truncated {label}: original {len(text)} chars, limit {max_chars}.]\n"
    )


def apply_safe_prompt_template(
    template: str,
    replacements: dict[str, str],
    *,
    max_field_chars: dict[str, int] | None = None,
) -> str:
    """
    Substitute `{key}` values without str.format (safe for JSON / prose with braces).

    Every `{name}` in the template (after `{{`/`}}` masking) must be listed in
    `replacements`. Each required `{key}` substring must appear at least once.
    """
    assert_allowed_placeholders(template, replacements.keys())
    maxc = max_field_chars or {}
    masked = _mask_double_braces(template)
    out = masked
    for key, raw in replacements.items():
        cap = maxc.get(key, 1_000_000)
        val = truncate_prompt_injection(raw, cap, key)
        tag = "{" + key + "}"
        if tag not in out:
            raise ValueError(f"Prompt template is missing required placeholder {tag}.")
        out = out.replace(tag, val)
    return _unmask_double_braces(out)


def build_research_agent_prompt(
    template: str,
    context: str,
    *,
    max_context_chars: int = 80_000,
) -> str:
    """
    Inject scraped `context` into the research-agent system prompt.

    - Only `{context}` is substituted (after `{{` / `}}` literal masking).
    - Any other `{name}` raises ValueError (map to HTTP 400).
    - If `{context}` is missing, context is appended (backward compatible).
    """
    assert_allowed_placeholders(template, {"context"})
    ctx = truncate_prompt_injection(context, max_context_chars, "campaign context")
    masked = _mask_double_braces(template)
    if "{context}" not in masked:
        return _unmask_double_braces(masked).rstrip() + "\n\n--- Campaign context ---\n\n" + ctx
    merged = masked.replace("{context}", ctx)
    return _unmask_double_braces(merged)
