"""Reporting helpers for the content machine asset pack."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import ReportBundle, ValidationFinding


def _finding_lines(findings: Iterable[ValidationFinding]) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        offset_text = f" (offsets: {finding.offsets})" if finding.offsets else ""
        lines.append(f"- **{finding.severity.upper()}** `{finding.category}`: {finding.message}{offset_text}")
    return lines


def render_markdown(bundle: ReportBundle) -> str:
    lines = ["# Generation Report", "", "## STYLE_CONFIG", "```", bundle.style_config.to_header_block(), "```", ""]
    lines.extend(["## Validation Findings"])
    if bundle.validation.findings:
        lines.extend(_finding_lines(bundle.validation.findings))
    else:
        lines.append("- No validation findings. ✅")
    lines.append("")
    lines.append("## LIWC Drift")
    if bundle.validation.liwc_deltas:
        for category, delta in bundle.validation.liwc_deltas.items():
            lines.append(f"- `{category}` drift: {delta:.2f}")
    else:
        lines.append("- No LIWC drift recorded.")
    lines.append("")
    lines.append("## Generation Metadata")
    lines.append(f"- Prompt ID: `{bundle.generation.prompt_id}`")
    lines.append(f"- Token count: {bundle.generation.token_count}")
    lines.append("")
    return "\n".join(lines)


def render_json(bundle: ReportBundle) -> str:
    return json.dumps(bundle.to_json(), indent=2, ensure_ascii=False)


def save_markdown(bundle: ReportBundle, target: Path) -> Path:
    target.write_text(render_markdown(bundle), encoding="utf-8")
    return target


def save_json(bundle: ReportBundle, target: Path) -> Path:
    target.write_text(render_json(bundle), encoding="utf-8")
    return target
