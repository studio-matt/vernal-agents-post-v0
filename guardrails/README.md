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
