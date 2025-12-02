"""
ProfileModifier: Applies baseline adjustments to AuthorProfile LIWC scores.

This module provides functionality to modify author profiles based on user-defined
baseline adjustments, allowing dynamic style tuning without re-extraction.
"""

from typing import Dict, Optional
import copy
import logging
from author_related import AuthorProfile, LIWCScore, LIWCProfile
import math

logger = logging.getLogger(__name__)


def percentile_to_z_score(percentile: float) -> float:
    """
    Convert percentile (0-100) to z-score using inverse normal CDF.
    
    Uses scipy.stats.norm.ppf if available, otherwise falls back to approximation.
    
    Args:
        percentile: Percentile value (0-100)
        
    Returns:
        Z-score corresponding to the percentile
    """
    # Normalize percentile to 0-1 range
    p = percentile / 100.0
    
    # Clamp to avoid edge cases
    p = max(0.001, min(0.999, p))
    
    # Try to use scipy for accurate conversion
    try:
        from scipy.stats import norm
        z = norm.ppf(p)
        return float(z)
    except ImportError:
        # Fallback to approximation if scipy not available
        # Beasley-Springer-Moro algorithm approximation
        # This is more accurate than simple log approximation
        if p < 0.5:
            t = math.sqrt(-2.0 * math.log(p))
            z = -t + ((0.010328 * t + 0.802853) * t + 2.515517) / (((0.001308 * t + 0.189269) * t + 1.432788) * t + 1.0)
        else:
            t = math.sqrt(-2.0 * math.log(1.0 - p))
            z = t - ((0.010328 * t + 0.802853) * t + 2.515517) / (((0.001308 * t + 0.189269) * t + 1.432788) * t + 1.0)
        return float(z)


class ProfileModifier:
    """
    Modifies AuthorProfile instances by applying baseline adjustments.
    
    Baseline adjustments are stored as percentile values (0-100) in the frontend,
    which are converted to z-scores and applied to the profile's LIWC categories.
    """
    
    @staticmethod
    def apply_adjustments(
        profile: AuthorProfile,
        adjustments: Dict[str, float],
        adjustment_type: str = "percentile"
    ) -> AuthorProfile:
        """
        Apply baseline adjustments to an author profile.
        
        Creates a deep copy of the profile and modifies LIWC category z-scores
        based on the provided adjustments.
        
        Args:
            profile: Original AuthorProfile to modify
            adjustments: Dictionary mapping category names to adjustment values
                         Keys should match LIWC category names (e.g., "BigWords", "I", "We")
                         Values are percentiles (0-100) if adjustment_type="percentile"
            adjustment_type: Type of adjustment values ("percentile" or "z_score")
                            Default is "percentile" to match frontend format
            
        Returns:
            Modified AuthorProfile (deep copy, original unchanged)
        """
        if not adjustments:
            logger.debug("No adjustments provided, returning original profile")
            return profile
        
        # Create a deep copy to avoid mutating the original
        profile_dict = profile.to_dict()
        modified_profile = AuthorProfile.from_dict(profile_dict)
        
        # Get LIWC categories
        categories = modified_profile.liwc_profile.categories
        
        # Apply adjustments
        applied_count = 0
        for category_key, adjustment_value in adjustments.items():
            # Frontend sends keys with "liwc_" prefix (e.g., "liwc_BigWords")
            # Strip prefix to match backend category names (e.g., "BigWords")
            category = category_key
            if category_key.startswith("liwc_"):
                category = category_key[5:]  # Remove "liwc_" prefix
            
            if category not in categories:
                logger.warning(f"Adjustment category '{category}' (from key '{category_key}') not found in profile, skipping")
                continue
            
            # Get original score
            original_score = categories[category]
            
            # Convert adjustment to z-score if needed
            if adjustment_type == "percentile":
                # Frontend sends percentiles (0-100), convert to z-score
                target_z = percentile_to_z_score(adjustment_value)
            elif adjustment_type == "z_score":
                # Direct z-score adjustment (additive)
                target_z = original_score.z + adjustment_value
            else:
                logger.warning(f"Unknown adjustment_type '{adjustment_type}', skipping {category}")
                continue
            
            # Clamp z-score to reasonable range (-3.5 to +3.5)
            # This prevents extreme values that could cause validation issues
            clamped_z = max(-3.5, min(3.5, target_z))
            if clamped_z != target_z:
                logger.debug(f"Clamped z-score for {category}: {target_z:.3f} -> {clamped_z:.3f}")
            
            # Update the z-score
            # Note: We keep mean and stdev unchanged, only modify z-score
            # This is intentional - we're adjusting the target, not the distribution
            modified_score = LIWCScore(
                mean=original_score.mean,
                stdev=original_score.stdev,
                z=clamped_z
            )
            categories[category] = modified_score
            applied_count += 1
            
            logger.debug(
                f"Applied adjustment to {category}: "
                f"z-score {original_score.z:.3f} -> {target_z:.3f} "
                f"(percentile: {adjustment_value:.1f}%)"
            )
        
        logger.info(f"Applied {applied_count} adjustments to profile")
        return modified_profile
    
    @staticmethod
    def validate_adjustments(
        adjustments: Dict[str, float],
        profile: Optional[AuthorProfile] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate baseline adjustments.
        
        Args:
            adjustments: Dictionary of adjustments to validate
            profile: Optional profile to check category names against
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not adjustments:
            return True, None
        
        # Check for invalid values
        for category, value in adjustments.items():
            if not isinstance(value, (int, float)):
                return False, f"Adjustment value for '{category}' must be numeric"
            
            if value < 0 or value > 100:
                return False, f"Adjustment value for '{category}' must be between 0 and 100 (percentile)"
        
        # Check category names if profile provided
        if profile:
            valid_categories = set(profile.liwc_profile.categories.keys())
            invalid_categories = set(adjustments.keys()) - valid_categories
            if invalid_categories:
                return False, f"Invalid categories: {', '.join(invalid_categories)}"
        
        return True, None

