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


def _paragraphs(text: str) -> list[str]:
    """Split text into paragraphs for windowed analysis."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _bucket_sentence_length(word_count: int) -> str:
    """Bucket sentence lengths into categories for cadence patterns.
    
    Increased granularity: finer buckets to avoid tight cadence windows.
    """
    if word_count <= 8:
        return "very_short"
    elif word_count <= 15:
        return "short"
    elif word_count <= 22:
        return "medium"
    elif word_count <= 30:
        return "long"
    elif word_count <= 40:
        return "very_long"
    else:
        return "extremely_long"


def enforce_cadence(text: str, pattern: str, max_run: int) -> tuple[str, int]:
    """Ensure sentence-length cadence stays within the configured run using bucketed lengths.

    Returns the potentially adjusted text and the number of sentences that
    exceeded the allowed run.
    
    Improved: Uses bucketed sentence lengths for better cadence pattern enforcement.
    """
    sentences = _sentences(text)
    sentence_buckets = [_bucket_sentence_length(len(s.split())) for s in sentences]
    
    # Parse pattern like "3_long_1_short" to understand expected cadence
    pattern_parts = pattern.split("_")
    expected_buckets = []
    i = 0
    while i < len(pattern_parts):
        if pattern_parts[i].isdigit():
            count = int(pattern_parts[i])
            if i + 1 < len(pattern_parts):
                bucket_type = pattern_parts[i + 1]
                expected_buckets.extend([bucket_type] * count)
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    errors = 0
    adjusted_sentences = []
    run_count = 0
    last_bucket = None
    
    for i, (sentence, bucket) in enumerate(zip(sentences, sentence_buckets)):
        # Check for runs of same bucket type
        if bucket == last_bucket and bucket in ("very_long", "extremely_long"):
            run_count += 1
            if run_count > max_run:
                # Truncate extremely long sentences
                words = sentence.split()
                if len(words) > 30:
                    adjusted_sentences.append(" ".join(words[:30]) + "...")
                    errors += 1
                else:
                    adjusted_sentences.append(sentence)
            else:
                adjusted_sentences.append(sentence)
        else:
            run_count = 1 if bucket == last_bucket else 0
            adjusted_sentences.append(sentence)
        last_bucket = bucket
    
    adjusted = " ".join(adjusted_sentences)
    return adjusted, errors


def enforce_pronoun_distance(text: str, pronoun_distance: str) -> tuple[str, int]:
    """Count pronoun drift relative to the configured distance using paragraph-windowed checks.
    
    Improved: Checks pronoun drift within paragraph windows rather than globally.
    """
    pronouns = {
        "we": {"we", "our", "ours"},
        "you": {"you", "your", "yours"},
        "i": {"i", "me", "my", "mine"},
    }
    target = pronouns.get(pronoun_distance, set())
    
    # Split into paragraphs for windowed analysis
    paragraphs = _paragraphs(text)
    total_drift = 0
    
    for para in paragraphs:
        tokens = re.findall(r"\b\w+\b", para.lower())
        para_drift = sum(
            1
            for token in tokens
            if token in {"i", "me", "my", "mine", "you", "your", "yours", "we", "our", "ours"} and token not in target
        )
        total_drift += para_drift
    
    return text, total_drift


def enforce_empathy(text: str, empathy_target: str) -> tuple[str, int]:
    desired_frequency = 1 if "per_" in empathy_target else 0
    hits = len(re.findall(r"\byou\b", text.lower()))
    return text, max(desired_frequency - hits, 0)


def _get_word_stem(word: str) -> str:
    """Extract stem from word for alignment checking."""
    word_lower = word.lower()
    # Common suffixes to remove for stem alignment
    suffixes = ["ing", "ed", "er", "est", "ly", "s", "es", "tion", "sion", "ness", "ment"]
    for suffix in suffixes:
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
            return word_lower[:-len(suffix)]
    return word_lower


def _is_likely_noun_or_verb(word: str) -> tuple[bool, bool]:
    """Heuristic to identify noun/verb candidates using suffix patterns."""
    word_lower = word.lower()
    # Verb indicators
    is_verb = (
        word_lower.endswith("ing") or
        word_lower.endswith("ed") or
        word_lower.endswith("es") or
        (word_lower.endswith("s") and len(word_lower) > 3)
    )
    # Noun indicators (common noun suffixes)
    is_noun = (
        word_lower.endswith("tion") or
        word_lower.endswith("sion") or
        word_lower.endswith("ness") or
        word_lower.endswith("ment") or
        word_lower.endswith("ity") or
        word_lower.endswith("er") or
        word_lower.endswith("or")
    )
    return is_noun, is_verb


def enforce_metaphors(text: str, allowed_stems: Iterable[str]) -> tuple[str, int]:
    """Enforce metaphor usage with stem-aligned noun/verb candidate detection.
    
    Improved: Focuses on stem-aligned noun/verb candidates rather than all words.
    """
    allowed_stem_set = {_get_word_stem(stem) for stem in allowed_stems}
    errors = 0
    
    # Find potential metaphor words (longer words that could be metaphors)
    words = re.findall(r"\b([a-zA-Z]{5,})\b", text)
    for word in words:
        word_stem = _get_word_stem(word)
        is_noun, is_verb = _is_likely_noun_or_verb(word)
        
        # Only check noun/verb candidates
        if (is_noun or is_verb) and word_stem not in allowed_stem_set:
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
