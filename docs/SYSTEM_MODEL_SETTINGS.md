# System Model Topic Extraction - Configurable Settings

All parameters for the system model (non-LLM topic extraction) are configurable via the `system_settings` table. Settings are prefixed with `system_model_`.

## Required Settings

All settings should be added to the `system_settings` table with the prefix `system_model_`:

### 1. `system_model_phrases_min_count` (Integer)
- **Default:** `5`
- **Description:** Minimum count for phrases to be considered in Gensim Phrases model
- **Range:** 1-100
- **Impact:** Higher = fewer phrases, more selective

### 2. `system_model_phrases_threshold` (Float)
- **Default:** `15.0`
- **Description:** Threshold score for phrase detection in Gensim Phrases
- **Range:** 1.0-100.0
- **Impact:** Higher = stricter phrase detection

### 3. `system_model_tfidf_min_df` (Integer)
- **Default:** `3`
- **Description:** Minimum document frequency for TF-IDF (terms must appear in at least N documents)
- **Range:** 1-100
- **Impact:** Higher = filters out rare terms, reduces noise

### 4. `system_model_tfidf_max_df` (Float)
- **Default:** `0.7`
- **Description:** Maximum document frequency for TF-IDF (terms appearing in more than X% of documents are ignored)
- **Range:** 0.1-1.0
- **Impact:** Lower = filters out common stopwords, higher = keeps more terms

### 5. `system_model_k_grid` (JSON Array)
- **Default:** `[10, 15, 20, 25]`
- **Description:** List of K values (number of topics) to test. Best K is selected by coherence score.
- **Format:** JSON array of integers, e.g., `[10, 15, 20, 25, 30]`
- **Impact:** More values = better optimization but slower

### 6. `system_model_top_words` (Integer)
- **Default:** `12`
- **Description:** Number of top words to use for topic labeling and coherence calculation
- **Range:** 5-50
- **Impact:** Higher = more words per topic, richer labels

### 7. `system_model_min_doc_len_chars` (Integer)
- **Default:** `400`
- **Description:** Minimum document length in characters. Documents shorter than this are filtered out.
- **Range:** 0-10000
- **Impact:** Higher = filters out more noise, but may remove valid short documents

### 8. `system_model_max_per_domain` (Integer or "none")
- **Default:** `none` (disabled)
- **Description:** Maximum number of documents per domain. Set to "none" to disable domain diversity filtering.
- **Range:** 1-1000 or "none"
- **Impact:** Prevents single domains from dominating topics. Only works if URLs are provided.

### 9. `system_model_nmf_max_iter` (Integer)
- **Default:** `500`
- **Description:** Maximum iterations for NMF algorithm
- **Range:** 100-2000
- **Impact:** Higher = more accurate but slower

### 10. `system_model_nmf_random_state` (Integer)
- **Default:** `42`
- **Description:** Random seed for NMF (ensures reproducible results)
- **Range:** Any integer
- **Impact:** Same seed = same results (good for testing)

### 11. `system_model_use_spacy` (String: "true" or "false")
- **Default:** `true`
- **Description:** Whether to use spaCy for enhanced tokenization (lemmatization + POS filtering)
- **Values:** "true" or "false"
- **Impact:** spaCy = better quality, simple = faster (fallback if spaCy unavailable)

## Setting Up in Database

You can add these settings via SQL or through the admin panel API:

```sql
-- Example: Add all default settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('system_model_phrases_min_count', '5', 'Minimum count for phrases in Gensim Phrases model'),
('system_model_phrases_threshold', '15.0', 'Threshold score for phrase detection'),
('system_model_tfidf_min_df', '3', 'Minimum document frequency for TF-IDF'),
('system_model_tfidf_max_df', '0.7', 'Maximum document frequency for TF-IDF'),
('system_model_k_grid', '[10, 15, 20, 25]', 'List of K values to test (JSON array)'),
('system_model_top_words', '12', 'Number of top words for topic labeling'),
('system_model_min_doc_len_chars', '400', 'Minimum document length in characters'),
('system_model_max_per_domain', 'none', 'Maximum documents per domain (or "none" to disable)'),
('system_model_nmf_max_iter', '500', 'Maximum iterations for NMF algorithm'),
('system_model_nmf_random_state', '42', 'Random seed for NMF'),
('system_model_use_spacy', 'true', 'Use spaCy for enhanced tokenization');
```

## Admin Panel Integration

These settings should be added to the admin panel under a "System Model" or "Topic Extraction" section, allowing users to:
- Adjust phrase detection sensitivity
- Control TF-IDF filtering
- Test different K values
- Enable/disable spaCy tokenization
- Set document length and domain diversity filters

## Notes

- All settings are loaded dynamically from the database on each topic extraction call
- If a setting is missing, sensible defaults are used
- Settings prefixed with `system_model_` are automatically loaded
- JSON arrays (like `k_grid`) must be valid JSON
- Boolean settings use "true"/"false" strings (case-insensitive)

