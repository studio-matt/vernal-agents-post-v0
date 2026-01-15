# Guardrails (Single Source of Truth)

This folder defines the workflow guardrails that prevent drift and accidental rabbit holes.

Principles:
- No git submodules.
- Front end repo is the canonical source for guardrail docs + scripts.
- Backend gets a mirrored copy of guardrail files via a controlled sync script.
- We verify before we copy, and we verify after we copy.

What this is NOT:
- This is not application code.
- This is not deployment code.
- This is process + safety rails only.

## Documentation

- **[SYNTAX_CHECKING.md](./SYNTAX_CHECKING.md)** - Comprehensive syntax error detection tools and procedures. **CRITICAL**: Always run these tools before deployment and after refactoring to catch ALL syntax errors at once.

- **[REFACTORING.md](./REFACTORING.md)** - Refactoring guardrails and best practices. **CRITICAL**: Read this before extracting routes or refactoring `main.py`. Includes checklist, validation script, and common mistakes to avoid.
