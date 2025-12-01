# Content Machine Asset Guide

This guide lists the reusable assets in `content_machine/` and how to consume them from an external project that implements the design in `content_generation.md`.

## Context and Domain Legend
- **`context_domains.json`** — Canonical map of `LWCxx` codes to labels, descriptions, and tags. Use this as the single source of truth when labeling samples or selecting adapters.
- **`HighLow_TextAnalysis.md`** — Plain-language table of the `LWCxx` domains for humans and reports. Mirrors `context_domains.json` without symbolic notation.

## LIWC Reference Tables
- **`LIWC_Mean_Table.csv`** and **`LIWC_StdDev_Mean_Table.csv`** — Baseline means and standard deviations for LIWC categories. Combine them to compute z-scores for author buckets and generated outputs.
- **`LIWC Legend.txt`** — Excerpt from the LIWC-22 manual for category definitions; use when interpreting scores or building lexicon hints.

## Style and Trait Mapping
- **`HighLow_Vectorization.json`** — Detailed descriptions of LIWC summary dimensions (analytic, clout, authenticity, tone, WPS, etc.) with high/low interpretations and psychometric anchors. Use to translate raw LIWC outputs into human-readable knob settings.
- **`Trait_Mapping.json`** — Crosswalk from LIWC summary metrics to HEXACO, Big Five, and Enneagram indicators. Useful for enriching author profiles with broader trait metadata.
- **`LIWC_AUDIT_SLIM__v3.json`** — Plain-language interpretations of pronoun and reference behaviors. Pair this with validator output to surface actionable feedback.

## Usage Notes
- All files are UTF-8 encoded.
- Treat JSON and CSV assets as read-only inputs to the external pipeline; do not embed repository-specific paths in consuming code.
- Prefer the canonical assets (`context_domains.json`, LIWC mean/stddev tables) over legacy text tables when building automated flows.
