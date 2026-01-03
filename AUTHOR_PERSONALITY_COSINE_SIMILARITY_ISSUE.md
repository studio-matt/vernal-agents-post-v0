# Author Personality Cosine Similarity Inversion Issue

## Problem Summary

The author personality system is showing cosine similarity values of exactly **-1.0** for:
- BH-LVT weighted cosine similarity
- Punctuation cosine similarity

This indicates a **pairwise z-scoring artifact** where vectors are being forced to be exact opposites, causing cosine similarity to always return -1.0 regardless of actual stylistic relationship.

## Root Cause Analysis

Based on the diagnostic information provided:

1. **Pairwise Z-Scoring Problem**: When z-scoring is applied using only the two texts being compared (pairwise), with only two samples, per-feature z-scores become +1 vs -1 (or 0 if identical), making the resulting vectors antipodes → cosine becomes -1 deterministically.

2. **Incorrect Normalization**: The transformation should use **normalized baselines across multiple texts** instead of pairwise standardization.

3. **Possible Inversion**: The similarity metric might be:
   - Actually computing cosine distance (1 - cosine similarity) but being treated as similarity
   - Or the delta direction is reversed in the rebalancing step

## Files to Investigate

Based on codebase search, the cosine similarity calculation is likely in one of these locations:

1. **Profile Comparison Function** (not yet found)
   - May be in a comparison endpoint or analysis function
   - Could be comparing two profiles or profile vs generated text

2. **Similarity Calculation Module** (not yet found)
   - May be a separate module for computing stylometric similarities
   - Could be using scipy/numpy for cosine calculations

3. **Validation/Comparison Endpoints** in `main.py`:
   - `/author_personalities/{id}/test-full-chain` - Full chain test
   - `/author_personalities/{id}/preview-adjustments` - Preview adjustments
   - Any comparison or analysis endpoints

## Current Code Locations Reviewed

✅ **Reviewed but no cosine similarity found:**
- `backend-repo/author_related/validator.py` - Only z-score calculations, no cosine
- `backend-repo/author_related/profile_extraction.py` - Profile extraction, no cosine
- `backend-repo/author_related/reporter.py` - Reporting only, no calculations
- `backend-repo/author_validation_helper.py` - Validation wrapper, no cosine

## Search Strategy

To locate the cosine similarity calculation:

1. **Search for cosine similarity imports:**
   ```bash
   grep -r "cosine\|cosine_similarity\|from scipy\|from sklearn" backend-repo/
   ```

2. **Search for BH-LVT or punctuation metrics:**
   ```bash
   grep -r "BH\|LVT\|punctuation.*cosine\|weighted.*cosine" backend-repo/
   ```

3. **Search for vector comparisons:**
   ```bash
   grep -r "vector\|dot\|norm\|similarity" backend-repo/author_related/
   ```

4. **Check API responses** for where these metrics are returned

## Fix Strategy (Once Located)

### 1. Fix Pairwise Z-Scoring

**Current (WRONG):**
```python
# Pairwise z-scoring - causes -1.0 cosine similarity
def pairwise_zscore(text1_features, text2_features):
    # Standardize using only these two texts
    mean = (text1_features + text2_features) / 2
    std = np.std([text1_features, text2_features], axis=0)
    z1 = (text1_features - mean) / std
    z2 = (text2_features - mean) / std
    # z1 and z2 are now opposites → cosine = -1.0
    return cosine_similarity(z1, z2)
```

**Fixed (CORRECT):**
```python
# Use baseline normalization across multiple texts
def baseline_zscore(text_features, baseline_mean, baseline_std):
    # Standardize using global baseline, not pairwise
    z = (text_features - baseline_mean) / baseline_std
    return z

def compute_similarity(text1_features, text2_features, baseline_mean, baseline_std):
    z1 = baseline_zscore(text1_features, baseline_mean, baseline_std)
    z2 = baseline_zscore(text2_features, baseline_mean, baseline_std)
    # Now cosine similarity reflects actual relationship
    return cosine_similarity(z1, z2)
```

### 2. Verify Similarity vs Distance

Check if the metric is inverted:
- **Similarity**: Higher = more similar (range: -1 to 1, where 1 = identical)
- **Distance**: Lower = more similar (range: 0 to 2, where 0 = identical)

If using `1 - cosine_similarity`, that's distance, not similarity.

### 3. Fix Delta Direction

Check rebalancing step:
- **Correct**: `delta = target - generated` → apply as `generated += delta`
- **Wrong**: `delta = generated - target` → apply as `generated += delta` (pushes away)

### 4. Add Validation Tests

```python
def test_cosine_similarity():
    # Test 1: Identical texts should return 1.0
    text1 = "This is a test."
    text2 = "This is a test."
    similarity = compute_similarity(text1, text2, baseline_mean, baseline_std)
    assert abs(similarity - 1.0) < 0.01, f"Identical texts should have similarity ≈ 1.0, got {similarity}"
    
    # Test 2: Different texts should not be exactly -1.0
    text3 = "This is completely different content with different words."
    similarity = compute_similarity(text1, text3, baseline_mean, baseline_std)
    assert similarity > -1.0, f"Different texts should not have similarity = -1.0, got {similarity}"
    
    # Test 3: Similar texts should have positive similarity
    text4 = "This is a similar test."
    similarity = compute_similarity(text1, text4, baseline_mean, baseline_std)
    assert similarity > 0, f"Similar texts should have positive similarity, got {similarity}"
```

## Next Steps

1. **Locate the cosine similarity calculation code**
2. **Identify where pairwise z-scoring is applied**
3. **Replace with baseline normalization**
4. **Verify similarity metric is not inverted**
5. **Add validation tests**
6. **Test with (A, A) case to verify fix**

## References

- User's diagnostic: "BH-LVT weighted cosine = −1.0 (exact)" and "punctuation cosine = −1.0 (exact)"
- Function-word similarity (JSD→similarity) ≈ 0.784 (this one works correctly)
- Issue: Pairwise z-scoring with only two samples creates exact opposites


