# Similarity Metrics Test Suite

## Purpose

This test suite validates that the similarity metrics (BH-LVT weighted cosine and punctuation cosine) work correctly and **catches the -1.0 cosine similarity bug** that occurs when pairwise z-scoring is used instead of baseline normalization.

## The Bug We're Testing For

**The Problem:** When pairwise z-scoring is used (standardizing using only the two texts being compared), cosine similarity will always return exactly -1.0 for any two different profiles. This is because with only two samples, z-scores become +1 and -1, making the vectors mathematical opposites.

**The Fix:** Use baseline normalization (z-scoring each feature independently using global LIWC baselines) instead of pairwise standardization.

## Running the Tests

### On the Server

```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate  # If using virtual environment
python3 tests/test_similarity_metrics.py
```

### Expected Output

If all tests pass, you should see:
```
✅ All tests passed! Similarity metrics are working correctly.
   No -1.0 cosine similarity bug detected.
```

If the bug is present, you'll see:
```
❌ Some tests failed. Review the output above.
⚠️  WARNING: -1.0 cosine similarity bug detected!
   This indicates pairwise z-scoring is being used.
   Review the similarity.py implementation.
```

## Test Coverage

The test suite includes:

1. **Identical Profiles Test** - Ensures identical profiles return high similarity (not -1.0)
2. **Outlier Profile Tests** - Tests with extremely different profiles:
   - Formal academic writer vs casual conversational writer
   - Baseline vs formal profile
   - Baseline vs casual profile
3. **Punctuation Tests** - Tests punctuation similarity with:
   - Identical punctuation patterns
   - Formal (heavy) vs casual (light) punctuation
   - Minimal vs formal punctuation
   - Minimal vs casual punctuation
4. **Extreme Cases** - Tests edge cases:
   - Zero profile (all zeros)
   - Opposite profiles (mathematical opposites)
5. **Range Validation** - Ensures all similarity values are in expected range [-1, 1]
6. **Critical Bug Detection** - Specifically tests that similarity is NOT exactly -1.0

## Test Profiles

The test suite uses four distinct profiles:

1. **Baseline Profile** - Average writer with moderate values
2. **Formal Profile** - Extremely formal, academic writer:
   - High analytic score (95.0)
   - High BigWords (25.0)
   - High dictionary match (95.0)
   - Heavy punctuation
3. **Casual Profile** - Extremely casual, conversational writer:
   - Low analytic score (10.0)
   - Low BigWords (2.0)
   - Many pronouns
   - Light punctuation
4. **Minimal Profile** - Sparse writing with minimal punctuation

## What the Tests Validate

- ✅ Similarity values are in expected range [-1, 1]
- ✅ Identical profiles return high similarity (> 0.8)
- ✅ Different profiles return appropriate similarity values
- ✅ **CRITICAL: Similarity is NEVER exactly -1.0** (would indicate pairwise z-scoring bug)
- ✅ Edge cases are handled gracefully (zero profiles, opposite profiles)

## Integration with CI/CD

This test should be run:
- Before deploying similarity metric changes
- After any changes to `author_related/similarity.py`
- As part of the deployment validation process

## Troubleshooting

If tests fail with -1.0 values:
1. Check `author_related/similarity.py` - ensure it uses baseline normalization
2. Verify `AssetLoader.load_liwc_baselines()` is working correctly
3. Check that `compute_feature_similarity()` uses global baselines, not pairwise standardization

If tests fail with import errors:
1. Ensure you're in the correct directory (`/home/ubuntu/vernal-agents-post-v0`)
2. Activate virtual environment if using one
3. Check that `author_related` module is accessible



