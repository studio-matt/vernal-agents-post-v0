# Author Personality Domain Delta System - Analysis & Implementation Gap

## 📋 Intended Design (Per User Requirements)

### Flow:
1. **Evaluate writing samples** - Analyze with LIWC
2. **Consider source domain** - Use pulldown/domain detection (linkedin, twitter, facebook, instagram, blog)
3. **Adjust results based on delta chart** - Use `LIWC_StdDev_Mean_Table.csv` to normalize domain-specific scores
4. **Assign baseline to WordPress** - WordPress (LWC02 "Blogs") is the neutral baseline with least constraints
5. **Calculate platform deltas** - For each platform, calculate difference between WordPress baseline and that platform's baseline
6. **Feed deltas to writing agents** - BEFORE agents run, apply platform deltas to influence output

---

## 🔍 Current Implementation Analysis

### ✅ What's Working:

1. **Domain Detection** (`components/AuthorMimicry.tsx:2287`)
   - Domain is detected from filename/URL
   - Stored in `sampleMetadata.domain`
   - Passed to backend in `extractAuthorProfile()`

2. **Domain-Aware Z-Score Calculation** (`profile_extraction.py:51-71`)
   - `_z_score()` function SUPPORTS domain-specific baselines
   - Can use `load_domain_baselines()` to get LWC-specific means/stdevs
   - Falls back to global baseline if domain not found

3. **Platform Adapters** (`planner.py:21-27`)
   - Adapters exist for platform-specific style overlays
   - Applied via `_apply_adapter()` during content generation

### ❌ What's Missing/Broken:

1. **Domain NOT Used in Profile Extraction** (`profile_extraction.py:344`)
   ```python
   # CURRENT: Always uses global baseline
   liwc_scores = self._aggregate_liwc(normalized_samples, domain=None)
   
   # SHOULD BE: Use domain for z-score calculation
   liwc_scores = self._aggregate_liwc(normalized_samples, domain=detected_domain)
   ```

2. **No WordPress Baseline Normalization**
   - WordPress (LWC02) should be the reference baseline
   - Current: Uses global "Total" baseline from CSV
   - Missing: Normalize all scores to WordPress/LWC02 baseline

3. **Platform Deltas Not Calculated from LIWC Tables**
   - Current adapters are style overlays (cadence, pronoun_distance, etc.)
   - Missing: LIWC category deltas calculated from `LIWC_StdDev_Mean_Table.csv`
   - Should calculate: `delta = WordPress_mean - Platform_mean` for each LIWC category

4. **Deltas Not Fed to Writing Agents**
   - Current: Writing agents get style config with LIWC targets
   - Missing: Platform-specific LIWC deltas applied BEFORE agent runs
   - Should modify: LIWC targets based on platform deltas

---

## 📊 Data Available

### LIWC_StdDev_Mean_Table.csv Structure:
- Columns: `Category`, `LWC01_StdDev`, `LWC01_Mean`, `LWC02_StdDev`, `LWC02_Mean`, ..., `Total_StdDev`, `Total_Mean`
- LWC02 = Blogs = WordPress baseline
- Each platform should map to an LWC code:
  - WordPress/Blog → LWC02
  - LinkedIn → ? (needs mapping)
  - Twitter → LWC14 (Tweets)
  - Facebook → LWC05
  - Instagram → ? (needs mapping)
  - etc.

### Domain Mapping Needed:
```python
PLATFORM_TO_LWC = {
    "wordpress": "LWC02",  # Blogs - BASELINE
    "blog": "LWC02",
    "linkedin": "LWC08",   # NYT (professional/journalistic) - NEEDS CONFIRMATION
    "twitter": "LWC14",    # Tweets
    "facebook": "LWC05",   # Facebook
    "instagram": "LWC09",  # Reddit (social commentary) - NEEDS CONFIRMATION
    "general": None        # Use global baseline
}
```

---

## 🔧 Required Changes

### 1. Use Domain in Profile Extraction

**File**: `backend-repo-git/author_related/profile_extraction.py`

**Current (line 344):**
```python
liwc_scores = self._aggregate_liwc(normalized_samples, domain=None)  # Always use global baseline
```

**Should Be:**
```python
# Extract domain from samples (use first sample's domain, or most common)
detected_domain = self._extract_domain_from_samples(normalized_samples)
# Map platform name to LWC code
lwc_code = self._platform_to_lwc(detected_domain)
liwc_scores = self._aggregate_liwc(normalized_samples, domain=lwc_code)
```

### 2. Normalize to WordPress Baseline

**New Function Needed:**
```python
def _normalize_to_wordpress_baseline(
    self, 
    liwc_scores: dict[str, LIWCScore], 
    sample_domain: str | None
) -> dict[str, LIWCScore]:
    """Normalize LIWC scores to WordPress (LWC02) baseline.
    
    If sample came from Twitter (LWC14), adjust z-scores to reflect
    what they would be if measured against WordPress baseline instead.
    """
    if not sample_domain or sample_domain == "LWC02":
        return liwc_scores  # Already WordPress baseline
    
    wordpress_baselines = self.loader.load_domain_baselines()["LWC02"]
    sample_baselines = self.loader.load_domain_baselines()[sample_domain]
    
    normalized = {}
    for category, score in liwc_scores.items():
        # Get WordPress mean/stdev for this category
        wp_mean = wordpress_baselines.get(category, {}).get("mean", 0)
        wp_stdev = wordpress_baselines.get(category, {}).get("stdev", 1.0)
        
        # Get sample domain mean/stdev
        sample_mean = sample_baselines.get(category, {}).get("mean", 0)
        sample_stdev = sample_baselines.get(category, {}).get("stdev", 1.0)
        
        # Convert sample z-score back to raw value, then recalculate against WordPress
        raw_value = (score.z * sample_stdev) + sample_mean
        normalized_z = (raw_value - wp_mean) / wp_stdev if wp_stdev > 0 else 0
        
        normalized[category] = LIWCScore(
            mean=score.mean,
            stdev=score.stdev,
            z=normalized_z
        )
    
    return normalized
```

### 3. Calculate Platform Deltas

**New Function Needed:**
```python
def _calculate_platform_deltas(
    self, 
    target_platform: str
) -> dict[str, float]:
    """Calculate LIWC category deltas between WordPress and target platform.
    
    Returns dict of {category: delta} where delta = WordPress_mean - Platform_mean
    """
    wordpress_baselines = self.loader.load_domain_baselines()["LWC02"]
    platform_lwc = self._platform_to_lwc(target_platform)
    
    if not platform_lwc or platform_lwc == "LWC02":
        return {}  # No delta for WordPress
    
    platform_baselines = self.loader.load_domain_baselines()[platform_lwc]
    
    deltas = {}
    for category in wordpress_baselines:
        wp_mean = wordpress_baselines[category]["mean"]
        platform_mean = platform_baselines.get(category, {}).get("mean", wp_mean)
        deltas[category] = wp_mean - platform_mean
    
    return deltas
```

### 4. Apply Deltas Before Writing Agents

**File**: `backend-repo-git/author_related/planner.py` or `author_voice_helper.py`

**Modify `build_style_config()` or content generation:**
```python
# Calculate platform deltas
platform_deltas = self._calculate_platform_deltas(target_platform)

# Adjust LIWC targets based on deltas
adjusted_liwc_targets = {}
for category, descriptor in liwc_targets.items():
    delta = platform_deltas.get(category, 0)
    # Adjust descriptor based on delta
    # e.g., if delta > 0, increase target; if delta < 0, decrease target
    adjusted_liwc_targets[category] = self._adjust_target_for_delta(descriptor, delta)
```

---

## 📝 Implementation Checklist

- [ ] **Map platforms to LWC codes** - Create `PLATFORM_TO_LWC` mapping
- [ ] **Use domain in profile extraction** - Pass domain to `_aggregate_liwc()`
- [ ] **Load domain baselines from CSV** - Ensure `load_domain_baselines()` reads `LIWC_StdDev_Mean_Table.csv` correctly
- [ ] **Normalize to WordPress baseline** - Implement `_normalize_to_wordpress_baseline()`
- [ ] **Calculate platform deltas** - Implement `_calculate_platform_deltas()`
- [ ] **Apply deltas to LIWC targets** - Modify `build_style_config()` to adjust targets
- [ ] **Feed deltas to writing agents** - Ensure deltas influence agent prompts/config
- [ ] **Test with sample data** - Verify WordPress baseline and platform deltas work correctly

---

## 🎯 Expected Behavior After Fix

### Example Flow:

1. **User uploads Twitter sample** (`twitter_post.txt`)
   - Domain detected: `twitter` → LWC14
   - LIWC scores calculated using LWC14 baselines
   - Z-scores normalized to WordPress (LWC02) baseline
   - Baseline stored: `{analytic: 65%, clout: 72%, ...}` (WordPress-normalized)

2. **User generates LinkedIn content**
   - System loads WordPress-normalized baseline
   - Calculates deltas: `LinkedIn_mean - WordPress_mean` for each category
   - Adjusts LIWC targets: `baseline + delta`
   - Feeds adjusted targets to LinkedIn writing agent
   - Agent generates content matching adjusted style

3. **User generates WordPress content**
   - System loads WordPress-normalized baseline
   - No deltas (WordPress is baseline)
   - Feeds baseline targets directly to WordPress agent

---

## ⚠️ Critical Questions

1. **Platform → LWC Mapping**: What LWC code should LinkedIn, Instagram, etc. map to?
   - LinkedIn → LWC08 (NYT/journalistic)?
   - Instagram → LWC09 (Reddit/social)?
   - Need confirmation from user

2. **Delta Application Method**: How exactly should deltas modify LIWC targets?
   - Add/subtract from z-score?
   - Modify descriptor (high/medium/low)?
   - Adjust percentile directly?

3. **Multiple Sample Domains**: What if user uploads samples from multiple domains?
   - Average the normalized scores?
   - Weight by sample count?
   - Use most common domain?

4. **CSV Parsing**: Does `load_domain_baselines()` correctly parse `LIWC_StdDev_Mean_Table.csv`?
   - Need to verify column names match
   - Need to verify data structure

---

## 📚 References

- `LIWC_StdDev_Mean_Table.csv` - Contains LWC-specific means/stdevs
- `context_domains.json` - Maps LWC codes to descriptions
- `profile_extraction.py:51-71` - Domain-aware z-score calculation (exists but not used)
- `planner.py:21-27` - Adapter system (style overlays, not LIWC deltas)
- `AUTHOR_PROFILE_CONTENT_GENERATION_CONFIRMATION.md` - Current implementation docs

