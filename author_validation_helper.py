"""
Helper functions for validating generated content against author profile.
Phase 4: Validation Integration
"""

from typing import Optional, Dict, Any
from author_related import StyleValidator, AuthorProfile, StyleConfig
from author_profile_service import AuthorProfileService
from liwc_analyzer import analyze_text
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)


def validate_content_against_profile(
    generated_text: str,
    style_config_block: str,
    author_personality_id: str,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Validate generated content against author profile.
    
    Args:
        generated_text: The generated text to validate
        style_config_block: The STYLE_CONFIG block used for generation
        author_personality_id: ID of the author personality
        db: Database session (optional)
        
    Returns:
        Dictionary with validation results including:
        - findings: List of validation findings (errors/warnings)
        - liwc_deltas: LIWC category deviations
        - cadence_errors: Number of cadence pattern violations
        - pronoun_errors: Number of pronoun distance violations
        - metaphor_errors: Number of metaphor usage errors
        - empathy_gaps: Number of empathy target gaps
        - overall_score: Overall validation score (0-100)
    """
    try:
        # Get or create database session
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            # Load author profile
            service = AuthorProfileService()
            profile = service.load_profile(author_personality_id, db)
            
            if not profile:
                logger.error(f"Profile not found for author_personality_id: {author_personality_id}")
                return {
                    "error": "Author profile not found",
                    "findings": [],
                    "overall_score": 0
                }
            
            # Parse style config from block
            from author_related.validator import parse_style_header
            try:
                style_config = parse_style_header(style_config_block)
            except Exception as e:
                logger.warning(f"Could not parse style config: {e}, using profile defaults")
                # Create minimal style config from profile
                from author_related.models import StyleConfig
                style_config = StyleConfig(
                    mode=profile.default_controls.mode,
                    audience="general",
                    goal="content_generation",
                    cadence_pattern=profile.default_controls.cadence_pattern,
                    pronoun_distance=profile.default_controls.pronoun_distance,
                )
            
            # Analyze generated text with LIWC
            liwc_scores = analyze_text(generated_text)
            
            # Validate using StyleValidator
            validator = StyleValidator()
            validation_report = validator.validate_output(
                text=generated_text,
                config=style_config,
                profile=profile,
                measured_liwc=liwc_scores
            )
            
            # Calculate overall score (0-100)
            # Lower is better (fewer errors = higher score)
            total_errors = (
                validation_report.cadence_errors +
                validation_report.pronoun_errors +
                validation_report.metaphor_errors +
                validation_report.empathy_gaps +
                len([f for f in validation_report.findings if f.severity == "error"])
            )
            total_warnings = len([f for f in validation_report.findings if f.severity == "warning"])
            
            # Score calculation: 100 - (errors * 10) - (warnings * 2)
            # Clamp between 0 and 100
            overall_score = max(0, min(100, 100 - (total_errors * 10) - (total_warnings * 2)))
            
            # Convert findings to dict for JSON serialization
            findings_list = [
                {
                    "field": f.field,
                    "message": f.message,
                    "severity": f.severity
                }
                for f in validation_report.findings
            ]
            
            result = {
                "findings": findings_list,
                "liwc_deltas": validation_report.liwc_deltas,
                "cadence_errors": validation_report.cadence_errors,
                "pronoun_errors": validation_report.pronoun_errors,
                "metaphor_errors": validation_report.metaphor_errors,
                "empathy_gaps": validation_report.empathy_gaps,
                "overall_score": overall_score,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "validation_passed": overall_score >= 70,  # Pass if score >= 70
            }
            
            logger.info(f"Validation complete: score={overall_score}, errors={total_errors}, warnings={total_warnings}")
            
            return result
            
        finally:
            if close_db:
                db.close()
                
    except Exception as e:
        logger.error(f"Error validating content: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": str(e),
            "findings": [],
            "overall_score": 0,
            "validation_passed": False
        }

