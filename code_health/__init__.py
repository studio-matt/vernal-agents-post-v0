"""
Code Health Scanner for Vernal Agents backend.

Scans codebase for files exceeding LOC threshold and optionally runs pylint.
"""

from code_health.scanner import scan_codebase, generate_reports

__all__ = ["scan_codebase", "generate_reports"]

