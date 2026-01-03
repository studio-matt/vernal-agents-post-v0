# Cosine Similarity Fix - Integration Guide

## Problem Fixed

The cosine similarity metrics (BH-LVT weighted cosine and punctuation cosine) were returning exactly **-1.0** due to pairwise z-scoring. This has been fixed by using baseline normalization instead.

## Solution

Created `author_related/similarity.py` with corrected similarity computation functions that:
- Use global LIWC baselines (from `AssetLoader`) instead of pairwise standardization
- Properly compute cosine similarity between feature vectors
- Provide specific functions for BH-LVT and punctuation similarity

## Usage

### 1. Compare Two Profiles

```python
from author_related import compute_profile_similarity, AuthorProfile

# Load two profiles
profile1 = load_profile(...)
profile2 = load_profile(...)

# Compute BH-LVT weighted cosine similarity
bh_lvt_sim = compute_profile_similarity(profile1, profile2, similarity_type="bh_lvt")

# Compute punctuation cosine similarity
punct_sim = compute_profile_similarity(profile1, profile2, similarity_type="punctuation")

# Compute overall similarity (all categories)
overall_sim = compute_profile_similarity(profile1, profile2, similarity_type="overall")
```

### 2. Compare Profile to Generated Content

```python
from author_related import compute_feature_similarity, compute_bh_lvt_weighted_similarity
from liwc_analyzer import analyze_text

# Get profile features
profile_features = {cat: score.mean for cat, score in profile.liwc_profile.categories.items()}

# Analyze generated content
generated_liwc = analyze_text(generated_text)

# Compute BH-LVT similarity
bh_lvt_sim = compute_bh_lvt_weighted_similarity(profile_features, generated_liwc)

# Compute punctuation similarity
from author_related import compute_punctuation_similarity
punct_sim = compute_punctuation_similarity(profile_features, generated_liwc)
```

### 3. Integration Points

#### During Profile Extraction (AuthorMimicry)
Add similarity metrics when extracting profile to validate it matches the samples:

```python
from author_related import compute_profile_similarity
from author_profile_service import AuthorProfileService

# After extracting profile
service = AuthorProfileService()
profile = service.extract_and_save_profile(...)

# Compare profile to original samples (if you have sample profiles)
# This validates the extraction worked correctly
similarity_metrics = {
    "bh_lvt": compute_profile_similarity(profile, sample_profile, "bh_lvt"),
    "punctuation": compute_profile_similarity(profile, sample_profile, "punctuation"),
}
```

#### During Content Validation
Add similarity metrics when validating generated content:

```python
from author_related import compute_bh_lvt_weighted_similarity, compute_punctuation_similarity
from author_validation_helper import validate_content_against_profile
from liwc_analyzer import analyze_text

# Validate content
validation_result = validate_content_against_profile(
    generated_text=text,
    style_config_block=style_config,
    author_personality_id=personality_id,
    db=db
)

# Add similarity metrics
profile_features = {cat: score.mean for cat, score in profile.liwc_profile.categories.items()}
generated_liwc = analyze_text(generated_text)

similarity_metrics = {
    "bh_lvt_weighted_cosine": compute_bh_lvt_weighted_similarity(profile_features, generated_liwc),
    "punctuation_cosine": compute_punctuation_similarity(profile_features, generated_liwc),
}

# Add to validation result
validation_result["similarity_metrics"] = similarity_metrics
```

## API Endpoint Integration

### Add Similarity Metrics to Test Full Chain Endpoint

In `main.py`, update the `/author_personalities/{id}/test-full-chain` endpoint:

```python
from author_related import compute_bh_lvt_weighted_similarity, compute_punctuation_similarity

# After computing measured_liwc
profile_features = {
    cat: score.mean 
    for cat, score in modified_profile.liwc_profile.categories.items()
}

similarity_metrics = {
    "bh_lvt_weighted_cosine": compute_bh_lvt_weighted_similarity(
        profile_features, measured_liwc
    ),
    "punctuation_cosine": compute_punctuation_similarity(
        profile_features, measured_liwc
    ),
}

# Add to response
return {
    ...
    "similarity_metrics": similarity_metrics,
    ...
}
```

## Expected Results

After the fix:
- **Identical texts**: Cosine similarity ≈ 1.0 (not -1.0)
- **Similar texts**: Cosine similarity > 0 (positive, not exactly -1.0)
- **Different texts**: Cosine similarity can be negative but not always exactly -1.0

## Validation Test

```python
def test_similarity_fix():
    from author_related import compute_feature_similarity
    
    # Test 1: Identical features should return ~1.0
    features1 = {"BigWords": 10.5, "Dic": 85.0}
    features2 = {"BigWords": 10.5, "Dic": 85.0}
    sim = compute_feature_similarity(features1, features2, ["BigWords", "Dic"])
    assert abs(sim - 1.0) < 0.1, f"Expected ~1.0, got {sim}"
    
    # Test 2: Different features should not be exactly -1.0
    features3 = {"BigWords": 5.0, "Dic": 70.0}
    sim = compute_feature_similarity(features1, features3, ["BigWords", "Dic"])
    assert sim > -1.0, f"Expected > -1.0, got {sim}"
```

## Files Modified

1. **Created**: `backend-repo/author_related/similarity.py` - Fixed similarity computation
2. **Updated**: `backend-repo/author_related/__init__.py` - Exported similarity functions

## Next Steps

1. Integrate similarity metrics into profile extraction endpoint
2. Add similarity metrics to content validation endpoint
3. Update frontend (AuthorMimicry) to display these metrics
4. Test with real profiles to verify fix works correctly

