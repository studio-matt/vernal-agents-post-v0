#!/usr/bin/env python3
"""
Test suite for similarity metrics to ensure proper function and catch -1.0 cosine bug.

This test suite:
1. Tests BH-LVT weighted cosine similarity with outlier profiles
2. Tests punctuation cosine similarity with extreme cases
3. Validates that similarity values are in expected range (not -1.0)
4. Tests both identical and dissimilar profiles
5. Ensures baseline normalization works correctly (not pairwise z-scoring)
"""

import sys
import os
import unittest
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from author_related import (
    compute_bh_lvt_weighted_similarity,
    compute_punctuation_similarity,
    compute_feature_similarity,
    cosine_similarity,
)
from author_related.asset_loader import AssetLoader


class TestSimilarityMetrics(unittest.TestCase):
    """Test suite for similarity metrics with outlier profiles."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = AssetLoader()
        
        # Create baseline profile (average writer)
        self.baseline_profile = {
            "analytic": 50.0,
            "clout": 50.0,
            "authentic": 50.0,
            "tone": 50.0,
            "wps": 15.0,  # Words per sentence
            "bigwords": 10.0,  # Big words percentage
            "dic": 80.0,  # Dictionary match rate
            "function": 45.0,
            "pronoun": 15.0,
            "ppron": 10.0,
            "i": 5.0,
            "we": 2.0,
            "you": 3.0,
            "shehe": 1.0,
            "they": 2.0,
            "ipron": 8.0,
            "Period": 50.0,  # Punctuation (note: LIWC uses capitalized)
            "Comma": 30.0,
            "QMark": 2.0,
            "Exclam": 1.0,
            "Colon": 3.0,
            "SemiC": 2.0,
            "Parenth": 1.0,
            "Dash": 2.0,
            "OtherP": 1.0,
        }
        
        # Create outlier profile 1: Extremely formal, academic writer
        self.formal_profile = {
            "analytic": 95.0,  # Very high
            "clout": 20.0,  # Low confidence
            "authentic": 30.0,  # Low authenticity
            "tone": 40.0,
            "wps": 25.0,  # Long sentences
            "bigwords": 25.0,  # Many big words
            "dic": 95.0,  # High dictionary match
            "function": 50.0,
            "pronoun": 5.0,  # Very few pronouns
            "ppron": 2.0,
            "i": 0.5,  # Almost no first person
            "we": 0.5,
            "you": 0.5,
            "shehe": 0.5,
            "they": 0.5,
            "ipron": 1.0,
            "Period": 80.0,  # Heavy punctuation
            "Comma": 50.0,
            "QMark": 0.5,
            "Exclam": 0.1,
            "Colon": 10.0,
            "SemiC": 5.0,
            "Parenth": 5.0,
            "Dash": 3.0,
            "OtherP": 2.0,
        }
        
        # Create outlier profile 2: Extremely casual, conversational writer
        self.casual_profile = {
            "analytic": 10.0,  # Very low
            "clout": 80.0,  # High confidence
            "authentic": 90.0,  # Very authentic
            "tone": 70.0,
            "wps": 8.0,  # Short sentences
            "bigwords": 2.0,  # Few big words
            "dic": 60.0,  # Lower dictionary match
            "function": 40.0,
            "pronoun": 30.0,  # Many pronouns
            "ppron": 25.0,
            "i": 15.0,  # Heavy first person
            "we": 8.0,
            "you": 10.0,
            "shehe": 2.0,
            "they": 5.0,
            "ipron": 20.0,
            "Period": 20.0,  # Light punctuation
            "Comma": 15.0,
            "QMark": 5.0,
            "Exclam": 10.0,  # Many exclamations
            "Colon": 0.5,
            "SemiC": 0.5,
            "Parenth": 1.0,
            "Dash": 1.0,
            "OtherP": 0.5,
        }
        
        # Create outlier profile 3: Minimal punctuation, sparse writing
        self.minimal_profile = {
            "analytic": 30.0,
            "clout": 40.0,
            "authentic": 60.0,
            "tone": 50.0,
            "wps": 10.0,
            "bigwords": 5.0,
            "dic": 70.0,
            "function": 35.0,
            "pronoun": 20.0,
            "ppron": 15.0,
            "i": 8.0,
            "we": 3.0,
            "you": 5.0,
            "shehe": 1.0,
            "they": 2.0,
            "ipron": 10.0,
            "Period": 10.0,  # Very minimal punctuation
            "Comma": 5.0,
            "QMark": 0.1,
            "Exclam": 0.1,
            "Colon": 0.1,
            "SemiC": 0.1,
            "Parenth": 0.1,
            "Dash": 0.1,
            "OtherP": 0.1,
        }

    def test_identical_profiles(self):
        """Test that identical profiles return high similarity (not -1.0)."""
        # Same profile compared to itself
        similarity = compute_bh_lvt_weighted_similarity(
            self.baseline_profile,
            self.baseline_profile
        )
        
        # Should be close to 1.0 (identical), definitely not -1.0
        self.assertGreater(similarity, 0.8, 
            f"Identical profiles should have high similarity, got {similarity}")
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_bh_lvt_formal_vs_casual(self):
        """Test BH-LVT similarity between extremely different profiles."""
        similarity = compute_bh_lvt_weighted_similarity(
            self.formal_profile,
            self.casual_profile
        )
        
        # Should be low similarity (different styles), but not -1.0
        self.assertLess(similarity, 0.5,
            f"Formal vs casual should have low similarity, got {similarity}")
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")

    def test_bh_lvt_baseline_vs_formal(self):
        """Test BH-LVT similarity between baseline and formal profile."""
        similarity = compute_bh_lvt_weighted_similarity(
            self.baseline_profile,
            self.formal_profile
        )
        
        # Should be moderate similarity
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_bh_lvt_baseline_vs_casual(self):
        """Test BH-LVT similarity between baseline and casual profile."""
        similarity = compute_bh_lvt_weighted_similarity(
            self.baseline_profile,
            self.casual_profile
        )
        
        # Should be moderate similarity
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_punctuation_identical(self):
        """Test punctuation similarity with identical profiles."""
        similarity = compute_punctuation_similarity(
            self.baseline_profile,
            self.baseline_profile
        )
        
        # Should be close to 1.0 (identical punctuation)
        self.assertGreater(similarity, 0.8,
            f"Identical punctuation should have high similarity, got {similarity}")
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_punctuation_formal_vs_casual(self):
        """Test punctuation similarity between formal and casual profiles."""
        similarity = compute_punctuation_similarity(
            self.formal_profile,
            self.casual_profile
        )
        
        # Should be low similarity (very different punctuation patterns)
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_punctuation_minimal_vs_formal(self):
        """Test punctuation similarity between minimal and formal profiles."""
        similarity = compute_punctuation_similarity(
            self.minimal_profile,
            self.formal_profile
        )
        
        # Should be low similarity (minimal vs heavy punctuation)
        self.assertLess(similarity, 0.5,
            f"Minimal vs formal punctuation should have low similarity, got {similarity}")
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")

    def test_punctuation_minimal_vs_casual(self):
        """Test punctuation similarity between minimal and casual profiles."""
        similarity = compute_punctuation_similarity(
            self.minimal_profile,
            self.casual_profile
        )
        
        # Should be moderate to low similarity
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_extreme_outlier_case(self):
        """Test with extreme outlier to catch edge cases."""
        # Create an extreme outlier: all zeros
        zero_profile = {key: 0.0 for key in self.baseline_profile.keys()}
        
        # Compare zero profile to baseline
        bh_lvt_sim = compute_bh_lvt_weighted_similarity(
            zero_profile,
            self.baseline_profile
        )
        punct_sim = compute_punctuation_similarity(
            zero_profile,
            self.baseline_profile
        )
        
        # Should handle gracefully, not crash or return -1.0
        self.assertNotEqual(bh_lvt_sim, -1.0,
            "CRITICAL: BH-LVT similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertNotEqual(punct_sim, -1.0,
            "CRITICAL: Punctuation similarity should NOT be -1.0 (pairwise z-scoring bug)")
        self.assertGreaterEqual(bh_lvt_sim, -1.0,
            f"BH-LVT similarity should be >= -1.0, got {bh_lvt_sim}")
        self.assertGreaterEqual(punct_sim, -1.0,
            f"Punctuation similarity should be >= -1.0, got {punct_sim}")

    def test_opposite_profiles(self):
        """Test with profiles that are mathematical opposites."""
        # Create profile that's opposite of baseline (for testing)
        opposite_profile = {
            key: 100.0 - value if value > 0 else 0.0
            for key, value in self.baseline_profile.items()
        }
        
        similarity = compute_bh_lvt_weighted_similarity(
            self.baseline_profile,
            opposite_profile
        )
        
        # Should be low similarity, but NOT exactly -1.0
        # (If it's -1.0, that indicates pairwise z-scoring bug)
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL: Similarity should NOT be exactly -1.0 (indicates pairwise z-scoring bug)")
        self.assertGreaterEqual(similarity, -1.0,
            f"Similarity should be >= -1.0, got {similarity}")
        self.assertLessEqual(similarity, 1.0,
            f"Similarity should be <= 1.0, got {similarity}")

    def test_similarity_range_validation(self):
        """Validate that all similarity values are in expected range [-1, 1]."""
        test_pairs = [
            (self.baseline_profile, self.baseline_profile),
            (self.baseline_profile, self.formal_profile),
            (self.baseline_profile, self.casual_profile),
            (self.formal_profile, self.casual_profile),
            (self.minimal_profile, self.formal_profile),
            (self.minimal_profile, self.casual_profile),
        ]
        
        for profile1, profile2 in test_pairs:
            bh_lvt = compute_bh_lvt_weighted_similarity(profile1, profile2)
            punct = compute_punctuation_similarity(profile1, profile2)
            
            # Check BH-LVT
            self.assertGreaterEqual(bh_lvt, -1.0,
                f"BH-LVT similarity {bh_lvt} should be >= -1.0")
            self.assertLessEqual(bh_lvt, 1.0,
                f"BH-LVT similarity {bh_lvt} should be <= 1.0")
            self.assertNotEqual(bh_lvt, -1.0,
                f"CRITICAL: BH-LVT similarity should NOT be exactly -1.0 (got {bh_lvt})")
            
            # Check punctuation
            self.assertGreaterEqual(punct, -1.0,
                f"Punctuation similarity {punct} should be >= -1.0")
            self.assertLessEqual(punct, 1.0,
                f"Punctuation similarity {punct} should be <= 1.0")
            self.assertNotEqual(punct, -1.0,
                f"CRITICAL: Punctuation similarity should NOT be exactly -1.0 (got {punct})")

    def test_baseline_normalization_not_pairwise(self):
        """
        Critical test: Ensure we're using baseline normalization, not pairwise z-scoring.
        
        If pairwise z-scoring is used, comparing two profiles will always result in
        vectors that are negatives of each other, leading to -1.0 cosine similarity.
        """
        # Test with two very different profiles
        similarity = compute_bh_lvt_weighted_similarity(
            self.formal_profile,
            self.casual_profile
        )
        
        # The key test: should NOT be exactly -1.0
        # If it is, that means pairwise z-scoring is being used
        self.assertNotEqual(similarity, -1.0,
            "CRITICAL BUG DETECTED: Similarity is exactly -1.0, "
            "indicating pairwise z-scoring is being used instead of baseline normalization. "
            "This is the bug we're trying to prevent!")
        
        # Also test punctuation
        punct_similarity = compute_punctuation_similarity(
            self.formal_profile,
            self.casual_profile
        )
        
        self.assertNotEqual(punct_similarity, -1.0,
            "CRITICAL BUG DETECTED: Punctuation similarity is exactly -1.0, "
            "indicating pairwise z-scoring is being used instead of baseline normalization.")


def run_tests():
    """Run the test suite."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSimilarityMetrics)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.split(chr(10))[-2]}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.split(chr(10))[-2]}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Similarity metrics are working correctly.")
        print("   No -1.0 cosine similarity bug detected.")
    else:
        print("\n❌ Some tests failed. Review the output above.")
        if any("-1.0" in str(f) for f in result.failures + result.errors):
            print("\n⚠️  WARNING: -1.0 cosine similarity bug detected!")
            print("   This indicates pairwise z-scoring is being used.")
            print("   Review the similarity.py implementation.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

