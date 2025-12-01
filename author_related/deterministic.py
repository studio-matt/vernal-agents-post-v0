"""Deterministic enforcement utilities for generated text."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .models import ValidationFinding


def normalize_typography(text: str) -> str:
    """Replace smart punctuation and collapse whitespace deterministically."""
    replacements = {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "…": "...",
    }
    normalized = text
    for src, dest in replacements.items():
        normalized = normalized.replace(src, dest)
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]


def enforce_cadence(text: str, pattern: str, max_run: int) -> tuple[str, int]:
    """Ensure sentence-length cadence stays within the configured run.

    Returns the potentially adjusted text and the number of sentences that
    exceeded the allowed run.
    """
    sentences = _sentences(text)
    long_sentences = [s for s in sentences if len(s.split()) > 28]
    errors = 0
    if len(long_sentences) > max_run:
        errors = len(long_sentences) - max_run
        sentences = [" ".join(s.split()[:28]) + "..." if len(s.split()) > 28 else s for s in sentences]
    adjusted = " ".join(sentences)
    return adjusted, errors


def enforce_pronoun_distance(text: str, pronoun_distance: str) -> tuple[str, int]:
    """Count pronoun drift relative to the configured distance."""
    pronouns = {
        "we": {"we", "our", "ours"},
        "you": {"you", "your", "yours"},
        "i": {"i", "me", "my", "mine"},
    }
    target = pronouns.get(pronoun_distance, set())
    tokens = re.findall(r"\b\w+\b", text.lower())
    drift = sum(
        1
        for token in tokens
        if token in {"i", "me", "my", "mine", "you", "your", "yours", "we", "our", "ours"} and token not in target
    )
    return text, drift


def enforce_empathy(text: str, empathy_target: str) -> tuple[str, int]:
    desired_frequency = 1 if "per_" in empathy_target else 0
    hits = len(re.findall(r"\byou\b", text.lower()))
    return text, max(desired_frequency - hits, 0)


def enforce_metaphors(text: str, allowed_stems: Iterable[str]) -> tuple[str, int]:
    errors = 0
    for metaphor in re.findall(r"\b([a-zA-Z]{4,})\b", text):
        if metaphor.lower() not in {stem.lower() for stem in allowed_stems}:
            errors += 1
    return text, errors


def enforce_all(
    text: str,
    cadence_pattern: str,
    pronoun_distance: str,
    empathy_target: str,
    metaphor_stems: Iterable[str],
    max_run: int,
) -> tuple[str, dict[str, int], list[ValidationFinding]]:
    normalized = normalize_typography(text)
    adjusted, cadence_errors = enforce_cadence(normalized, cadence_pattern, max_run)
    adjusted, pronoun_errors = enforce_pronoun_distance(adjusted, pronoun_distance)
    adjusted, empathy_gaps = enforce_empathy(adjusted, empathy_target)
    adjusted, metaphor_errors = enforce_metaphors(adjusted, metaphor_stems)
    findings: list[ValidationFinding] = []
    if cadence_errors:
        findings.append(ValidationFinding("cadence", "Cadence exceeded configured run", "warning"))
    if pronoun_errors:
        findings.append(ValidationFinding("pronoun", "Pronoun drift detected", "warning"))
    if empathy_gaps:
        findings.append(ValidationFinding("empathy", "Empathy coverage below target", "warning"))
    if metaphor_errors:
        findings.append(ValidationFinding("metaphor", "Metaphor outside configured set", "warning"))
    counts = {
        "cadence_errors": cadence_errors,
        "pronoun_errors": pronoun_errors,
        "metaphor_errors": metaphor_errors,
        "empathy_gaps": empathy_gaps,
    }
    return adjusted, counts, findings
