"""
Similarity computation utilities for author personality system.

Fixes the pairwise z-scoring issue that causes cosine similarity to always return -1.0.
Uses baseline normalization instead of pairwise standardization.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .asset_loader import AssetLoader


def cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector (must be same length as vec1)
        
    Returns:
        Cosine similarity value in range [-1, 1], where 1 = identical, -1 = opposite
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vectors must be same length: {len(vec1)} != {len(vec2)}")
    
    if len(vec1) == 0:
        return 1.0  # Empty vectors are considered identical
    
    # Compute dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Compute magnitudes
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    
    # Avoid division by zero
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def compute_feature_similarity(
    features1: Mapping[str, float],
    features2: Mapping[str, float],
    category_names: Sequence[str],
    loader: AssetLoader | None = None,
) -> float:
    """
    Compute cosine similarity between two feature vectors using baseline normalization.
    
    This fixes the pairwise z-scoring issue by using global LIWC baselines instead
    of standardizing using only the two texts being compared.
    
    Args:
        features1: First feature vector (category -> value mapping)
        features2: Second feature vector (category -> value mapping)
        category_names: List of category names to include in comparison
        loader: Optional AssetLoader instance (creates new one if not provided)
        
    Returns:
        Cosine similarity value in range [-1, 1]
    """
    if loader is None:
        loader = AssetLoader()
    
    baselines = loader.load_liwc_baselines()
    
    # Build z-scored vectors using global baselines (not pairwise)
    z1 = []
    z2 = []
    
    for category in category_names:
        # Get baseline for this category
        baseline = baselines.get(category, {"mean": 0.0, "stdev": 1.0})
        mean = baseline.get("mean", 0.0)
        stdev = baseline.get("stdev", 1.0) or 1.0
        
        # Get feature values (default to 0 if missing)
        val1 = features1.get(category, 0.0)
        val2 = features2.get(category, 0.0)
        
        # Z-score each feature independently using global baseline
        z1_val = (val1 - mean) / stdev if stdev > 0 else 0.0
        z2_val = (val2 - mean) / stdev if stdev > 0 else 0.0
        
        z1.append(z1_val)
        z2.append(z2_val)
    
    # Compute cosine similarity on z-scored vectors
    return cosine_similarity(z1, z2)


def compute_bh_lvt_weighted_similarity(
    profile1_features: Mapping[str, float],
    profile2_features: Mapping[str, float],
    loader: AssetLoader | None = None,
) -> float:
    """
    Compute BH-LVT (BigWords-HighLow Vectorization) weighted cosine similarity.
    
    This compares lexical features including BigWords, Dictionary Match Rate,
    and other vocabulary-related LIWC categories.
    
    Args:
        profile1_features: First profile's LIWC features
        profile2_features: Second profile's LIWC features
        loader: Optional AssetLoader instance
        
    Returns:
        Weighted cosine similarity value
    """
    # BH-LVT categories: BigWords, Dictionary Match Rate, and related lexical features
    bh_lvt_categories = [
        "BigWords",  # Complex vocabulary
        "Dic",  # Dictionary match rate
        "Linguistic",  # Overall linguistic content
        "function",  # Function words
        "pronoun",  # Pronoun usage
        "ppron",  # Personal pronouns
    ]
    
    return compute_feature_similarity(
        profile1_features,
        profile2_features,
        bh_lvt_categories,
        loader
    )


def compute_punctuation_similarity(
    profile1_features: Mapping[str, float],
    profile2_features: Mapping[str, float],
    loader: AssetLoader | None = None,
) -> float:
    """
    Compute punctuation cosine similarity.
    
    This compares punctuation-related features between two profiles.
    
    Args:
        profile1_features: First profile's LIWC features
        profile2_features: Second profile's LIWC features
        loader: Optional AssetLoader instance
        
    Returns:
        Cosine similarity value for punctuation features
    """
    # Punctuation-related categories
    # Note: LIWC doesn't have direct punctuation categories, but we can use
    # related structural features. If specific punctuation categories exist,
    # they should be added here.
    punctuation_categories = [
        "AllPunc",  # All punctuation (if available)
        "Period",  # Periods (if available)
        "Comma",  # Commas (if available)
        "OtherPunc",  # Other punctuation (if available)
        # Fallback to structural features that correlate with punctuation patterns
        "wps",  # Words per sentence (correlates with punctuation density)
        "function",  # Function words (correlates with punctuation usage)
    ]
    
    # Filter to only include categories that exist in the features
    available_categories = [
        cat for cat in punctuation_categories
        if cat in profile1_features or cat in profile2_features
    ]
    
    if not available_categories:
        # If no punctuation categories found, return 0 (no similarity data)
        return 0.0
    
    return compute_feature_similarity(
        profile1_features,
        profile2_features,
        available_categories,
        loader
    )


def compute_profile_similarity(
    profile1: Any,  # AuthorProfile
    profile2: Any,  # AuthorProfile
    similarity_type: str = "overall",
    loader: AssetLoader | None = None,
) -> float:
    """
    Compute similarity between two AuthorProfile objects.
    
    Args:
        profile1: First AuthorProfile
        profile2: Second AuthorProfile
        similarity_type: Type of similarity to compute:
            - "overall": All LIWC categories
            - "bh_lvt": BH-LVT weighted cosine
            - "punctuation": Punctuation cosine
        loader: Optional AssetLoader instance
        
    Returns:
        Cosine similarity value
    """
    # Extract feature vectors from profiles
    features1 = {cat: score.mean for cat, score in profile1.liwc_profile.categories.items()}
    features2 = {cat: score.mean for cat, score in profile2.liwc_profile.categories.items()}
    
    if similarity_type == "bh_lvt":
        return compute_bh_lvt_weighted_similarity(features1, features2, loader)
    elif similarity_type == "punctuation":
        return compute_punctuation_similarity(features1, features2, loader)
    else:  # overall
        # Use all categories
        all_categories = list(set(features1.keys()) | set(features2.keys()))
        return compute_feature_similarity(features1, features2, all_categories, loader)

