# Content Generation Programmatic Design

## Table of Contents
- [Purpose and Scope](#purpose-and-scope)
- [Goals](#goals)
- [Source Assets](#source-assets)
- [Architectural Overview](#architectural-overview)
  - [Ingestion and Profiling](#ingestion-and-profiling)
  - [Profile Store and Defaults](#profile-store-and-defaults)
  - [Planning and Prompt Construction](#planning-and-prompt-construction)
  - [Generation](#generation)
  - [Deterministic Enforcement](#deterministic-enforcement)
  - [Validation and Reporting](#validation-and-reporting)
  - [Channel and Format Adapters](#channel-and-format-adapters)
- [Data Model](#data-model)
  - [Author Profile (JSON)](#author-profile-json)
  - [STYLE_CONFIG Header](#style_config-header)
  - [Context Definitions](#context-definitions)
- [Processing Pipelines](#processing-pipelines)
  - [Profile Extraction](#profile-extraction)
  - [Prompt Planning and Generation](#prompt-planning-and-generation)
  - [Deterministic Enforcement and Validation](#deterministic-enforcement-and-validation)
- [Interfaces for External Projects](#interfaces-for-external-projects)
- [Post-processing and Safety](#post-processing-and-safety)
- [Portability and Versioning](#portability-and-versioning)

## Purpose and Scope
This document merges the two prior content generation designs into a single, programmatic plan for using the assets in `content_machine/` to capture an author's voice and generate new material. It is intended for consumption by an external project and should not be integrated into this repository's runtime.

## Goals
1. **Style capture:** Scan an author's corpus, score stylistic traits, and persist a reusable author profile.
2. **Voice-preserving generation:** Use the persisted profile and supporting assets to guide LLM prompts so new content matches the captured voice.
3. **Format-aware adaptation:** Modify author settings per output type (LinkedIn post, blog, email, etc.) while preserving core identity.

## Source Assets
| Asset | Role in the design |
| --- | --- |
| `HighLow_Vectorization.json` | Trait interpretations for mapping LIWC outputs to personality sliders (MBTI/OCEAN/HEXACO proxies); used during profile extraction. |
| `Trait_Mapping.json` | Bridges LIWC summary metrics to HEXACO, Big Five, and Enneagram signals when enriching profiles. |
| `LIWC_AUDIT_SLIM__v3.json` | Plain-language LIWC descriptions for validator messaging and adaptation rules. |
| `LIWC_Mean_Table.csv`, `LIWC_StdDev_Mean_Table.csv` | Reference distributions for LIWC categories used to compute z-scores during profiling and audit steps. |
| `LWC_TextAnalysis.json` | Domain baseline means/stddevs per `LWCxx` context with plain-language descriptions for labeling and z-score calculations. |
| `context_domains.json`, `HighLow_TextAnalysis.md` | Canonical domain legend for pairing human-readable domains with `LWCxx` codes and reporting text without legacy symbolic notation. |
| `LIWC_Legend_Quickref.md`, `LIWC Legend.txt` | Condensed LIWC category descriptions to align planner labels with validator outputs. |

## Architectural Overview
Each stage is separable so the consuming project can replace or augment components as needed.

### Ingestion and Profiling
- Inputs: raw text samples plus optional metadata (mode, audience, publication type).
- Segment the author's samples by **mode** (memoir, reform, epistemic, live) and **audience** (general, practitioner, scholar, live) using `context_domains.json` and the domain summaries in `LWC_TextAnalysis.json`.
- Normalize inputs (UTF-8, stable sentence segmentation) and strip non-text artifacts before analysis.
- Run LIWC on each `(mode, audience)` bucket and compute per-category means and z-scores using the CSV baselines.
- Identify discriminative categories (signature highs/lows) for each bucket and map LIWC metrics to personality knobs via `HighLow_Vectorization.json` and `Trait_Mapping.json`.

### Profile Store and Defaults
- Persist bucket-level LIWC distributions, derived personality sliders, lexicon hints, and control knobs (cadence, pronoun distance, evidence density, empathy targets, metaphor sets).
- Maintain global defaults when bucket-specific data is missing; store profiles as JSON alongside summary CSV/JSON assets for transparency.
- Treat the assets in this folder as the read-only source of truth; the external system holds serialized author profiles and audit logs.

### Planning and Prompt Construction
- Build a compact `[STYLE_CONFIG]` header plus lexical hints for the LLM, merging base profile values with target output adjustments.
- Planner responsibilities:
  - Choose `mode`, `audience`, `goal`, scaffold, governing metaphors, pronoun policy, cadence, CTA type, and empathy targets.
  - Emit lexicon bias blocks keyed to LIWC categories (e.g., `core_cognitive_verbs`, `core_sensory_nouns`).
  - Record planner metadata so validators can re-read the decisions.

### Generation
- Provide the LLM with the `[STYLE_CONFIG]` block, scaffold, cadence guidance, lexicon biases, and any exemplar phrases.
- Soft constraints include rhythm pressure, pronoun distance, lexicon bias, metaphor sets, and CTA type; downstream validators enforce hard rules.

### Deterministic Enforcement
- Pure text functions (no additional model calls) handle typography normalization, sentence-length gating, pronoun drift checks, empathy coverage, metaphor set coherence, and evidence pairing.
- Avoid hallucinated config: validators should only accept `[STYLE_CONFIG]` keys defined in this document.

### Validation and Reporting
- Re-run LIWC on generated text and compare against targets from the author profile within tolerance windows.
- Use `LIWC_AUDIT_SLIM__v3.json` to translate pronoun/reference drift into human-readable guidance.
- Emit structured findings (per-category z-scores, pronoun policy violations, cadence exceptions) for downstream tooling.
- Optional critic LLM pass comments on coherence, empathy routing, and reframing quality, suggesting minimal edits.

### Channel and Format Adapters
- Define adapter templates per target format (LinkedIn, blog, email, technical memo, etc.).
- Adjust cadence, CTA type, evidence density, pronoun distance, and empathy frequency while retaining core lexicon, metaphor sets, and LIWC targets.
- Store adapters as overlay configs that merge with the base `[STYLE_CONFIG]` before generation.

## Data Model
### Author Profile (JSON)
```json
{
  "author_id": "<uuid or slug>",
  "sources": [{"path": "...", "mode": "memoir|reform|epistemic|live", "audience": "general|practitioner|scholar|live"}],
  "mbti": {"e_i": 0.62, "s_n": 0.31, "t_f": 0.73, "j_p": 0.28},
  "ocean": {"o": 0.71, "c": 0.64, "e": 0.32, "a": 0.55, "n": 0.41},
  "hexaco": {"h": 0.58, "e": 0.44, "x": 0.31, "a": 0.57, "c": 0.63, "o": 0.76},
  "liwc_profile": {
    "categories": {"analytic": {"mean": 18.2, "stdev": 5.4, "z": 0.7}, "affiliation": {"mean": 2.3, "stdev": 1.1, "z": -0.3}},
    "domain_mode": "LWC09"
  },
  "lexicon": {
    "core_verbs": ["infer", "structure", "surface"],
    "core_nouns": ["bridge", "system", "pattern"],
    "evaluatives": ["durable", "fragile", "pragmatic"],
    "metaphor_stems": ["bridge", "ecology", "mycelium"],
    "avoid": ["awesome", "epic"]
  },
  "default_controls": {
    "pronoun_distance": "we",
    "cadence_pattern": "3_long_1_short",
    "evidence_density": 0.7,
    "empathy_target": "1_second_person_per_3_paragraphs",
    "cta_style": "coalition"
  },
  "tolerance": {"liwc_z": 0.6, "sentence_length_max_run": 2}
}
```
- Profiles include empirical distributions, interpreted sliders, and control knobs. Keep repository-specific paths out of stored profiles.

### STYLE_CONFIG Header
```
[STYLE_CONFIG]
mode=reform
audience=practitioner
goal=mobilization
evidence_density=0.7
metaphor_sets=collapse_reconstruction,ecology_mycelium
pronoun_distance=we
cadence_pattern=3_long_1_short
empathy_target=1_second_person_per_3_paragraphs
cta_style=coalition
lexicon_core_verbs=infer,structure,stitch
lexicon_evaluatives=durable,fragile,pragmatic
liwc_targets=analytic:high,social:medium,affiliation:medium_low
[/STYLE_CONFIG]
```
- The header is machine-readable and powers both the generator and validators.
- Required keys: `mode`, `audience`, `goal`, `cadence_pattern`, `pronoun_distance`.
- Optional keys: `evidence_density`, `metaphor_sets`, `cta_style`, `empathy_target`, `liwc_targets`, `lexicon_*` biases.

### Context Definitions
- Source: `context_domains.json` plus the plain-language legend in `HighLow_TextAnalysis.md`.
- Purpose: Normalize how samples are labeled and how adapters are selected.
- Contract: Each entry exposes `code` (`LWCxx`), `label` (e.g., Applications, Blogs), `description`, and optional `tags` to align with target formats.

## Processing Pipelines
### Profile Extraction
1. Normalize text (ASCII-safe punctuation, dash/quote normalization, zero-width removal) and enforce UTF-8.
2. Segment by `(mode, audience)` using provided metadata or heuristics tied to `context_domains.json`.
3. Run LIWC using category definitions from the quick-reference assets and baseline tables.
4. Compute z-scores per domain context using `LWC_TextAnalysis.json` means/stddevs and the CSV baselines.
5. Map LIWC categories to MBTI/OCEAN/HEXACO proxies via `HighLow_Vectorization.json` and `Trait_Mapping.json` and clamp to `[0,1]`.
6. Derive lexical banks by extracting top n-grams per dominant LIWC category and filtering to author-used tokens only.
7. Persist `author_profile` plus a lightweight audit log describing source texts and derived scores.

### Prompt Planning and Generation
1. Load the base profile for the requested author.
2. Apply target format deltas:
   - LinkedIn: tighten `cadence_pattern`, raise direct address, boost `affiliation`, and encourage CTA.
   - Blog: increase `evidence_density`, allow longer `cadence_pattern`, moderate `affect`.
   - Memo/email: reduce `metaphor_sets`, raise clarity via determiners/articles, enforce audience-appropriate `pronoun_distance`.
3. Compose `[STYLE_CONFIG]` and lexicon hints; include exemplar phrases if available.
4. Call the LLM with the meta-prompt that explains desired scaffold, rhythm goals, pronoun policy, lexicon bias, and metaphor caps.

### Deterministic Enforcement and Validation
1. Post-process text: typography normalization, sentence-length guardrails, pronoun drift checks, empathy coverage, metaphor coherence, and evidence pairing.
2. Run LIWC again to compare generated output against target z-score ranges defined in `author_profile.tolerance` and bucket-specific targets.
3. Emit a report containing category deviations with suggested fixes, cadence violations, and pronoun mismatches with offsets.
4. Optional critic pass asks a secondary LLM to audit soft qualities (coherence, empathy routing) and recommend minimal edits.

## Interfaces for External Projects
- **Profile Loader:** Reads `author_profile` JSON and delivers normalized objects to planners.
- **Planner API:** Given `author_profile` + `target_format`, returns `{style_config_block, lexicon_hints, scaffolds}`.
- **Validator CLI:** Accepts generated text and `style_config_block`, emits JSON diagnostics (category z-scores, cadence errors, pronoun drifts).
- **Asset Versioning:** Maintain semantic versions for JSON/MD assets; include `schema_version` and `generated_from` metadata on profile exports.

## Post-processing and Safety
- All post-processing functions must be deterministic and side-effect free.
- Enforce UTF-8 encoding for all saved assets and outputs.
- Restrict validators to known `[STYLE_CONFIG]` keys and fail closed on unknown fields.

## Portability and Versioning
- Treat `content_machine/` as a read-only asset pack; external orchestration owns profiling, planning, and validation.
- Profiles should use relative names or opaque IDs so downstream systems can mount assets in any environment.
- Extend LIWC-like dimensions by updating `HighLow_Vectorization.json` and `LIWC_Legend_Quickref.md` together and bumping the asset version.
