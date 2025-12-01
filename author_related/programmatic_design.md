# Content Machine Programmatic Design

## Table of Contents
- [Purpose](#purpose)
- [Module Boundaries](#module-boundaries)
- [Shared Assets](#shared-assets)
- [Data Contracts](#data-contracts)
  - [Author Profile Schema](#author-profile-schema)
  - [Style Config Header Contract](#style-config-header-contract)
  - [Context Legend Contract](#context-legend-contract)
- [Processing Pipelines](#processing-pipelines)
  - [Profile Extraction Pipeline](#profile-extraction-pipeline)
  - [Prompt Planning Pipeline](#prompt-planning-pipeline)
  - [Generation Orchestration](#generation-orchestration)
  - [Deterministic Enforcement](#deterministic-enforcement)
  - [Validation and Reporting](#validation-and-reporting)
- [Adapters](#adapters)
- [Portability and Versioning](#portability-and-versioning)

## Purpose
Programmatic design for an external content system that uses only the assets contained in `content_machine/`. The design converts the architectural intent in `content_generation.md` into concrete interfaces, state machines, and validator behaviors that can be transplanted into another project without additional dependencies.

## Module Boundaries
1. **Asset Loader**: Typed readers for JSON/CSV/MD assets in this folder. Enforces UTF-8 and validates required columns/keys.
2. **Profile Store**: CRUD layer for author profiles serialized as JSON; uses the schema in `author_profile.schema.json`.
3. **Planner**: Builds `[STYLE_CONFIG]` headers and lexicon hints using profile data plus adapters.
4. **Generator Harness**: Wraps the target LLM call; accepts planner outputs and returns raw text.
5. **Deterministic Filters**: Pure functions for typography normalization, cadence enforcement, pronoun checks, empathy coverage, and metaphor coherence.
6. **Validator**: Re-runs LIWC against generated text, checks z-score tolerances, and assembles reports with human-readable messaging.
7. **Reporter**: Emits JSON and Markdown reports using only folder assets for wording and category definitions.

## Shared Assets
- `context_domains.json` and `HighLow_TextAnalysis.md` drive `(mode, audience)` labeling and adapter selection.
- `LIWC_Mean_Table.csv`, `LIWC_StdDev_Mean_Table.csv`, and `LWC_TextAnalysis.json` provide baseline means/stddevs for z-score math.
- `HighLow_Vectorization.json` and `Trait_Mapping.json` map LIWC categories to personality sliders (MBTI/OCEAN/HEXACO proxies).
- `LIWC_AUDIT_SLIM__v3.json`, `LIWC_Legend_Quickref.md`, and `LIWC Legend.txt` supply human-readable category and pronoun guidance.
- `content_generation.md` remains the high-level reference; this document supplies the executable contracts.

## Data Contracts
### Author Profile Schema
- JSON schema lives in `author_profile.schema.json`.
- Required top-level keys: `author_id`, `sources`, `liwc_profile`, `lexicon`, `default_controls`, `tolerance`.
- Sliders (`mbti`, `ocean`, `hexaco`) are normalized to `[0,1]`.
- `liwc_profile.categories` accepts arbitrary LIWC categories keyed to `{"mean": number, "stdev": number, "z": number}` plus `domain_mode` to bind to `LWCxx` codes.
- `lexicon` buckets accept string arrays; `avoid` denotes stop words.
- `default_controls` define cadence, pronoun policy, evidence density, empathy, and CTA style defaults.
- `tolerance` governs validator thresholds (z-score tolerance and maximum long sentence run).

### Style Config Header Contract
- `[STYLE_CONFIG]` headers must include `mode`, `audience`, `goal`, `cadence_pattern`, and `pronoun_distance`.
- Optional keys: `evidence_density`, `metaphor_sets`, `cta_style`, `empathy_target`, `liwc_targets`, `lexicon_*` groups.
- Validators reject unknown keys; planner must clamp values to the options described in `content_generation.md`.

### Context Legend Contract
- Context definitions come from `context_domains.json` and must include `code`, `label`, `description`, and optional `tags`.
- Planner and validator modules consume the legend to align buckets and adapters; no external taxonomy is permitted.

## Processing Pipelines
### Profile Extraction Pipeline
1. **Normalize Input**: Enforce UTF-8, normalize dashes/quotes, remove zero-width characters.
2. **Bucket Samples**: Map each text to `(mode, audience)` using `context_domains.json` heuristics; record provenance in `sources`.
3. **LIWC Pass**: Run LIWC and compute per-category means and z-scores using `LIWC_Mean_Table.csv` and `LIWC_StdDev_Mean_Table.csv`.
4. **Domain Context**: Use `LWC_TextAnalysis.json` to anchor category distributions to `LWCxx` domain modes.
5. **Trait Projection**: Translate LIWC summary metrics into MBTI/OCEAN/HEXACO sliders via `HighLow_Vectorization.json` and `Trait_Mapping.json`; clamp to `[0,1]`.
6. **Lexicon Mining**: Extract top n-grams aligned to dominant LIWC categories, filtered to tokens present in the author's corpus; populate `lexicon` buckets.
7. **Persist Profile**: Serialize to `author_profile` using the schema; log profiling metadata alongside tolerance defaults.

### Prompt Planning Pipeline
1. **Load Profile**: Fetch author profile and relevant `(mode, audience)` bucket.
2. **Apply Adapter Overlay**: Merge base controls with target format overlays (see [Adapters](#adapters)).
3. **Assemble Header**: Build `[STYLE_CONFIG]` with required and optional keys; generate `liwc_targets` using bucket z-scores and tolerance windows.
4. **Lexicon Hints**: Create `lexicon_*` hints from profile banks and dominant LIWC categories; include `avoid` list.
5. **Scaffold Selection**: Choose scaffold and empathy targets based on `goal` and audience.
6. **Planner Output**: `{style_config_block, lexicon_hints, scaffold, planner_metadata}`.

### Generation Orchestration
1. **Prepare Prompt**: Combine `style_config_block`, scaffold, cadence guidance, lexicon hints, and exemplar phrases.
2. **LLM Call**: Send prompt to the external LLM; return raw text plus metadata (prompt ID, token counts) for reporting.
3. **Traceability**: Store planner metadata and adapter identifiers so validators can reconstruct decisions.

### Deterministic Enforcement
1. **Typography Normalization**: Replace smart quotes/dashes, collapse whitespace, enforce UTF-8.
2. **Cadence Enforcement**: Ensure sentence-length runs respect `cadence_pattern`; truncate or split long runs according to `tolerance.sentence_length_max_run`.
3. **Pronoun Policy**: Validate pronoun distance matches `pronoun_distance`; rewrite outliers when deterministic replacements exist.
4. **Empathy Coverage**: Enforce minimum frequency of second-person or empathy cues per `empathy_target`.
5. **Metaphor Coherence**: Ensure metaphors come from the configured `metaphor_sets`; remove strays.

### Validation and Reporting
1. **Re-run LIWC**: Compute LIWC on post-processed text and compare z-scores against profile targets.
2. **Category Translation**: Use `LIWC_AUDIT_SLIM__v3.json` and `LIWC_Legend_Quickref.md` to explain category deviations and pronoun drift.
3. **Findings**: Emit structured JSON with `liwc_deviation`, `cadence_errors`, `pronoun_errors`, `metaphor_errors`, and `empathy_gaps`.
4. **Reports**: Produce Markdown/JSON reports using only folder assets; include offsets and suggested fixes from deterministic filters.

## Adapters
- Adapters are overlay dictionaries that adjust `cadence_pattern`, `empathy_target`, `cta_style`, `evidence_density`, and `metaphor_sets` based on channel.
- **LinkedIn Overlay**: tighter cadence, higher direct address, boosted `affiliation`, explicit CTA.
- **Blog Overlay**: higher `evidence_density`, longer cadence allowance, moderated affect.
- **Memo/Email Overlay**: reduced metaphors, increased clarity (articles/determiners), audience-specific pronoun distance.
- Store adapter definitions adjacent to this design (see `adapters.json`) and merge them with base profile controls before planning.

## Portability and Versioning
- Treat all assets in `content_machine/` as the canonical, transferable package; external systems may mount this folder intact.
- Record `schema_version` on exported profiles and report payloads; bump when adding new required fields.
- Keep validators strict: reject unknown `[STYLE_CONFIG]` keys and unrecognized adapters to avoid silent drift.
