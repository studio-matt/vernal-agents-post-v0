"""Database-backed author profile service integrating author-related tools."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from author_related import (
    AuthorProfile,
    ControlDefaults,
    ProfileExtractor,
    ToleranceConfig,
)
from author_related.profile_extraction import Sample
from models import AuthorPersonality

logger = logging.getLogger(__name__)


class AuthorProfileService:
    """Service for managing author profiles with database persistence."""

    def __init__(self):
        try:
            self.extractor = ProfileExtractor()
        except Exception as e:
            logger.error(f"Failed to initialize ProfileExtractor: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to initialize profile extractor. Check that all asset files are present in author-related folder: {str(e)}")

    def extract_and_save_profile(
        self,
        author_personality_id: str,
        writing_samples: List[str],
        sample_metadata: Optional[List[dict]] = None,
        db: Session = None,
    ) -> AuthorProfile:
        """
        Extract author profile from writing samples and save to database.

        Args:
            author_personality_id: ID of the author personality record
            writing_samples: List of text samples to analyze
            sample_metadata: Optional list of dicts with 'mode' and 'audience' for each sample
            db: Database session

        Returns:
            AuthorProfile object
        """
        if not db:
            raise ValueError("Database session required")

        # Load author personality record
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == author_personality_id).first()
        if not personality:
            raise ValueError(f"Author personality not found: {author_personality_id}")

        logger.info(f"Extracting profile for author personality: {author_personality_id}")
        logger.info(f"Processing {len(writing_samples)} writing samples")

        # Prepare samples with metadata
        samples = []
        for idx, text in enumerate(writing_samples):
            if not text or not text.strip():
                logger.debug(f"Skipping empty sample {idx + 1}")
                continue  # Skip empty samples

            logger.info(f"Processing sample {idx + 1}/{len(writing_samples)} (length: {len(text)} chars)")

            # Get metadata for this sample (default to 'reform' mode, 'general' audience)
            metadata = sample_metadata[idx] if sample_metadata and idx < len(sample_metadata) else {}
            mode = metadata.get("mode", "reform")
            audience = metadata.get("audience", "general")
            path = metadata.get("path", f"sample_{idx + 1}")

            # Normalize text
            logger.debug(f"Normalizing text for sample {idx + 1}")
            normalized_text = ProfileExtractor.normalize_text(text)

            # Run LIWC analysis on the text
            logger.info(f"Running LIWC analysis on sample {idx + 1}...")
            try:
                liwc_counts = self._placeholder_liwc_analysis(normalized_text)
                if not liwc_counts:
                    logger.warning(f"LIWC analysis returned empty results for sample {idx + 1}, using minimal defaults")
                    liwc_counts = {"WC": float(len(normalized_text.split()))}  # At least provide word count
                logger.info(f"LIWC analysis complete for sample {idx + 1} ({len(liwc_counts)} categories)")
            except Exception as e:
                logger.error(f"Error during LIWC analysis for sample {idx + 1}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Use minimal defaults if analysis fails
                liwc_counts = {"WC": float(len(normalized_text.split()))}

            sample = Sample(
                text=normalized_text,
                path=path,
                mode=mode,
                audience=audience,
                liwc_counts=liwc_counts,
            )
            samples.append(sample)

        if not samples:
            raise ValueError("No valid writing samples provided")

        logger.info(f"Prepared {len(samples)} samples, building profile...")

        # Extract profile using ProfileExtractor
        default_controls = ControlDefaults(
            pronoun_distance="we",
            cadence_pattern="3_long_1_short",
            evidence_density=0.7,
            empathy_target="1_second_person_per_3_paragraphs",
            cta_style="coalition",
        )

        tolerance = ToleranceConfig(liwc_z=0.6, sentence_length_max_run=2)

        logger.info("Calling extractor.build_profile...")
        try:
            profile = self.extractor.build_profile(
                author_id=author_personality_id,
                samples=samples,
                default_controls=default_controls,
                tolerance=tolerance,
            )
            logger.info("Profile extraction complete, saving to database...")
        except Exception as e:
            logger.error(f"Error during build_profile: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        # Save to database
        try:
            self._save_profile_to_db(personality, profile, db)
            logger.info("Profile saved to database successfully")
        except Exception as e:
            logger.error(f"Error saving profile to database: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        logger.info(f"Profile extracted and saved for: {author_personality_id}")
        return profile

    def load_profile(self, author_personality_id: str, db: Session) -> Optional[AuthorProfile]:
        """
        Load author profile from database.

        Args:
            author_personality_id: ID of the author personality record
            db: Database session

        Returns:
            AuthorProfile object or None if not found
        """
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == author_personality_id).first()
        if not personality or not personality.profile_json:
            return None

        try:
            profile_dict = json.loads(personality.profile_json)
            profile = AuthorProfile.from_dict(profile_dict)
            logger.info(f"Profile loaded for: {author_personality_id}")
            return profile
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load profile for {author_personality_id}: {e}")
            return None

    def _save_profile_to_db(self, personality: AuthorPersonality, profile: AuthorProfile, db: Session) -> None:
        """Save profile data to database columns."""
        # Save full profile as JSON
        personality.profile_json = json.dumps(profile.to_dict(), ensure_ascii=False)

        # Extract and save LIWC scores for quick access
        liwc_scores = {
            category: {"mean": score.mean, "stdev": score.stdev, "z": score.z}
            for category, score in profile.liwc_profile.categories.items()
        }
        personality.liwc_scores = json.dumps(liwc_scores, ensure_ascii=False)

        # Extract and save trait scores
        trait_scores = {}
        if profile.mbti:
            trait_scores["mbti"] = profile.mbti
        if profile.ocean:
            trait_scores["ocean"] = profile.ocean
        if profile.hexaco:
            trait_scores["hexaco"] = profile.hexaco
        personality.trait_scores = json.dumps(trait_scores, ensure_ascii=False) if trait_scores else None

        db.commit()
        logger.info(f"Profile data saved to database for: {personality.id}")

    def _placeholder_liwc_analysis(self, text: str) -> dict[str, float]:
        """
        Lightweight LIWC analysis using pattern matching.
        
        Uses regex patterns and word lists to detect common LIWC categories
        without requiring the proprietary LIWC dictionary.
        """
        try:
            from liwc_analyzer import analyze_text
            return analyze_text(text)
        except ImportError:
            logger.warning("liwc_analyzer not found - using empty analysis")
            return {}

    def get_liwc_scores(self, author_personality_id: str, db: Session) -> Optional[dict]:
        """Get quick access to LIWC scores without loading full profile."""
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == author_personality_id).first()
        if not personality or not personality.liwc_scores:
            return None

        try:
            return json.loads(personality.liwc_scores)
        except json.JSONDecodeError:
            return None

    def get_trait_scores(self, author_personality_id: str, db: Session) -> Optional[dict]:
        """Get quick access to trait scores without loading full profile."""
        personality = db.query(AuthorPersonality).filter(AuthorPersonality.id == author_personality_id).first()
        if not personality or not personality.trait_scores:
            return None

        try:
            return json.loads(personality.trait_scores)
        except json.JSONDecodeError:
            return None

