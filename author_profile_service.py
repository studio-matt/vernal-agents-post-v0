"""Database-backed author profile service integrating author-related tools."""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from sqlalchemy.orm import Session

# Import should work now that main.py sets up the import shim
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
            logger.info("Initializing ProfileExtractor...")
            self.extractor = ProfileExtractor()
            logger.info("ProfileExtractor initialized successfully")
        except FileNotFoundError as e:
            logger.error(f"Asset file not found: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Required asset file missing. Check that all asset files are present in author-related folder: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize ProfileExtractor: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to initialize profile extractor: {str(e)}")

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
            # Extract domain/platform from metadata (linkedin, twitter, facebook, instagram, blog, general)
            domain = metadata.get("domain") or metadata.get("platform", "general")

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

            # Use domain as mode if provided, otherwise use mode from metadata
            # Domain-aware mode helps with platform-specific LIWC analysis
            final_mode = domain if domain and domain != "general" else mode
            
            sample = Sample(
                text=normalized_text,
                path=path,
                mode=final_mode,  # Use domain-aware mode for platform-specific analysis
                audience=audience,
                liwc_counts=liwc_counts,
            )
            samples.append(sample)

        if not samples:
            raise ValueError("No valid writing samples provided")

        # Validate that at least one sample has LIWC counts
        samples_with_liwc = [s for s in samples if s.liwc_counts]
        if not samples_with_liwc:
            logger.warning("No samples have LIWC counts, this may cause issues")
            # Add minimal LIWC data to first sample if needed
            if samples:
                samples[0].liwc_counts = samples[0].liwc_counts or {"WC": float(len(samples[0].text.split()))}

        logger.info(f"Prepared {len(samples)} samples ({len(samples_with_liwc)} with LIWC data), building profile...")

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
        if not hasattr(self, 'extractor') or self.extractor is None:
            raise ValueError("ProfileExtractor not initialized. Cannot build profile.")
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

        # Save to database (including writing samples)
        try:
            self._save_profile_to_db(personality, profile, db, writing_samples)
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
            logger.debug(f"Profile JSON loaded, keys: {list(profile_dict.keys())}")
            profile = AuthorProfile.from_dict(profile_dict)
            logger.info(f"Profile loaded for: {author_personality_id}")
            return profile
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading profile for {author_personality_id}: {e}")
            logger.error(f"Profile JSON (first 500 chars): {personality.profile_json[:500] if personality.profile_json else 'None'}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to load profile for {author_personality_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Profile dict keys: {list(profile_dict.keys()) if 'profile_dict' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading profile for {author_personality_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _save_profile_to_db(self, personality: AuthorPersonality, profile: AuthorProfile, db: Session, writing_samples: Optional[List[str]] = None) -> None:
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

        # Save writing samples for display when editing
        if writing_samples:
            # Sanitize writing samples to remove invalid UTF-8 characters that MySQL can't store
            sanitized_samples = [self._sanitize_text_for_db(sample) for sample in writing_samples]
            personality.writing_samples_json = json.dumps(sanitized_samples, ensure_ascii=False)
            logger.info(f"Saved {len(writing_samples)} writing samples for: {personality.id}")

        db.commit()
        logger.info(f"Profile data saved to database for: {personality.id}")

    def _sanitize_text_for_db(self, text: str) -> str:
        """
        Sanitize text to remove invalid UTF-8 characters that MySQL can't store.
        
        Removes:
        - Invalid UTF-8 byte sequences
        - Control characters (except newlines, tabs, carriage returns)
        - Binary data artifacts from Word documents
        
        Args:
            text: Raw text that may contain invalid characters
            
        Returns:
            Cleaned text safe for MySQL storage
        """
        if not text:
            return ""
        
        try:
            # First, try to decode as UTF-8 and replace invalid sequences
            # This handles most cases of invalid UTF-8
            text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            
            # Remove null bytes and other problematic control characters
            # Keep: \n (newline), \r (carriage return), \t (tab)
            # Remove: \x00 (null), \x01-\x08, \x0B-\x0C, \x0E-\x1F (other control chars)
            text = re.sub(r'[\x00\x01-\x08\x0B\x0C\x0E-\x1F]', '', text)
            
            # Remove common Word document artifacts (binary data that sometimes leaks through)
            # These are often from embedded objects, images, or formatting
            text = re.sub(r'[\xF0-\xF7][\x80-\xBF]{3}', '', text)  # 4-byte UTF-8 sequences that are invalid
            text = re.sub(r'[\xE0-\xEF][\x80-\xBF]{2}', lambda m: m.group(0) if len(m.group(0).encode('utf-8', errors='replace')) == 3 else '', text)  # 3-byte sequences
            text = re.sub(r'[\xC0-\xDF][\x80-\xBF]', lambda m: m.group(0) if len(m.group(0).encode('utf-8', errors='replace')) == 2 else '', text)  # 2-byte sequences
            
            # Remove any remaining invalid UTF-8 sequences
            # This is a catch-all for any remaining problematic bytes
            try:
                text.encode('utf-8').decode('utf-8')
            except UnicodeDecodeError:
                # If still invalid, do a more aggressive cleanup
                text = ''.join(char for char in text if ord(char) < 0x110000)  # Valid Unicode range
                text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            
            # Clean up excessive whitespace that might result from removals
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 consecutive newlines
            text = text.strip()
            
            return text
        except Exception as e:
            logger.warning(f"Error sanitizing text, using fallback: {e}")
            # Fallback: very aggressive cleanup
            try:
                return text.encode('ascii', errors='ignore').decode('ascii')
            except:
                return ""  # Last resort: return empty string
    
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

