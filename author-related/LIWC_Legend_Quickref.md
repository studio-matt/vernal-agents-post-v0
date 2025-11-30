# LIWC Legend Quick Reference

This quick reference distills the LIWC-22 categories represented across the accompanying assets. Use these short descriptions when mapping LIWC outputs to planner and validator labels.

## Summary Variables
- **Analytic** — logical, formal, hierarchical thinking.
- **Clout** — perceived authority or status in language.
- **Authentic** — sincerity, self-revelation, genuineness.
- **Tone** — positive vs. negative emotional valence.
- **WPS** — average words per sentence (syntactic complexity).
- **BigWords** — share of words ≥7 letters (lexical sophistication).
- **Dic** — percentage of tokens matched to LIWC dictionary (normative usage).

## Core Linguistic Dimensions
- **function** — function words overall; grammatical scaffolding.
- **pronoun / ppron / i / we / you / shehe / they / ipron** — personal vs. impersonal reference and perspective.
- **det / article / prep / auxverb / verb / adj / adverb / conj / negate / quantity** — grammatical structuring, specificity, and polarity.
- **number** — numeric language and quantification.

## Psychological Processes
- **affiliation / achieve / power** — motivational drives.
- **cogproc / insight / cause / discrep / tentat / certitude / differ / memory** — reasoning modes and epistemic stance.
- **tone_pos / tone_neg / emo_pos / emo_neg / emo_anx / emo_anger / emo_sad** — emotional polarity and granularity.
- **swear** — profanity frequency.
- **social** — overall social process language.

## Perception, Time, and Conversation
- **attention / motion / space / visual / auditory / feeling** — sensory/perceptual grounding.
- **focuspast / focuspresent / focusfuture** — temporal orientation.
- **conversation / netspeak / assent / nonflu / filler** — conversationality and fluency markers.

## Usage Notes
- For validator messaging or UI labels, prefer the abbreviations above; map them to full definitions in `LIWC_AUDIT_SLIM__v3.json` when you need explanatory text.
- When computing z-scores, pair category abbreviations with the means/stddevs in `LIWC_StdDev_Mean_Table.csv` and the per-domain values in `LWC_TextAnalysis.json`.
- Extend this quick reference alongside `HighLow_Vectorization.json` whenever new LIWC categories are added to the planning pipeline.
