"""
Author Personality endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal
from app.schemas.models import AuthorPersonalityCreate, AuthorPersonalityUpdate, ExtractProfileRequest

logger = logging.getLogger(__name__)

author_personalities_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import shared utilities from main
# TODO: Move these to app/core/config.py or app/utils/helpers.py in future refactor
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from main import ALLOWED_ORIGINS, get_openai_api_key

# Author Personalities endpoints
@author_personalities_router.get("/author_personalities")
def get_author_personalities(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all author personalities for the current user - REQUIRES AUTHENTICATION"""
    logger.info(f"🔍 /author_personalities GET endpoint called by user {current_user.id}")
    try:
        from models import AuthorPersonality
        # Filter by user_id to only return user's own personalities
        personalities = db.query(AuthorPersonality).filter(
            AuthorPersonality.user_id == current_user.id
        ).all()
        return {
            "status": "success",
            "message": {
                "personalities": [
                    {
                        "id": personality.id,
                        "name": personality.name,
                        "description": personality.description,
                        "created_at": personality.created_at.isoformat() if personality.created_at else None,
                        "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                        "user_id": personality.user_id,
                "model_config_json": personality.model_config_json,
                "baseline_adjustments_json": personality.baseline_adjustments_json,
                "selected_features_json": personality.selected_features_json,
                "configuration_preset": personality.configuration_preset,
                "writing_samples_json": personality.writing_samples_json,
                "samples_count": len(json.loads(personality.writing_samples_json)) if personality.writing_samples_json else 0,
                "has_profile": bool(personality.profile_json),
                    }
                    for personality in personalities
                ]
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching author personalities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch author personalities: {str(e)}"
        )

@author_personalities_router.post("/author_personalities")
def create_author_personality(personality_data: AuthorPersonalityCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new author personality - REQUIRES AUTHENTICATION"""
    try:
        from models import AuthorPersonality
        logger.info(f"Creating author personality: {personality_data.name} for user {current_user.id}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database with user_id
        personality = AuthorPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            user_id=current_user.id  # Associate with logged-in user
        )
        
        db.add(personality)
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Author personality created successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create author personality: {str(e)}"
        )

@author_personalities_router.put("/author_personalities/{personality_id}")
def update_author_personality(personality_id: str, personality_data: AuthorPersonalityUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update an author personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import AuthorPersonality
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        if personality_data.model_config_json is not None:
            personality.model_config_json = personality_data.model_config_json
        if personality_data.baseline_adjustments_json is not None:
            personality.baseline_adjustments_json = personality_data.baseline_adjustments_json
        if personality_data.selected_features_json is not None:
            personality.selected_features_json = personality_data.selected_features_json
        if personality_data.configuration_preset is not None:
            personality.configuration_preset = personality_data.configuration_preset
        if personality_data.writing_samples_json is not None:
            personality.writing_samples_json = personality_data.writing_samples_json
        
        personality.updated_at = datetime.now()
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Author personality updated successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update author personality: {str(e)}"
        )

@author_personalities_router.delete("/author_personalities/{personality_id}")
def delete_author_personality(personality_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete an author personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import AuthorPersonality
        
        # Check if personality exists at all (for better error messages)
        personality_any = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id
        ).first()
        
        if not personality_any:
            logger.warning(f"Delete attempt: Personality {personality_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Author personality '{personality_id}' not found"
            )
        
        # Check ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        
        if not personality:
            logger.warning(
                f"Delete attempt: Personality {personality_id} exists but user_id mismatch. "
                f"Profile user_id: {personality_any.user_id}, Current user_id: {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        db.delete(personality)
        db.commit()
        logger.info(f"Author personality deleted successfully: {personality_id} by user {current_user.id}")
        return {
            "status": "success",
            "message": "Author personality deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error deleting author personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete author personality: {str(e)}"
        )

# Author Profile endpoints (Phase 2)
@author_personalities_router.post("/author_personalities/{personality_id}/extract-profile")
async def extract_author_profile(
    personality_id: str,
    request_data: ExtractProfileRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract author profile from writing samples - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    # Get origin for CORS header
    origin = request.headers.get("Origin", "")
    cors_headers = {}
    if origin in ALLOWED_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        logger.info(f"Extracting profile for author personality: {personality_id}")
        
        # Extract profile using service
        service = AuthorProfileService()
        profile = service.extract_and_save_profile(
            author_personality_id=personality_id,
            writing_samples=request_data.writing_samples,
            sample_metadata=request_data.sample_metadata,
            db=db
        )
        
        # Compute similarity metrics by comparing profile to aggregated sample LIWC scores
        from author_related import compute_bh_lvt_weighted_similarity, compute_punctuation_similarity
        from liwc_analyzer import analyze_text
        import statistics
        
        similarity_metrics = {}
        try:
            # Aggregate LIWC scores from all writing samples
            # Get API key for analyze_text
            api_key = get_openai_api_key(current_user=current_user, db=db)
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or configure in Admin Settings > System > Platform Keys."
                )
            
            all_liwc_scores = []
            for sample_text in request_data.writing_samples:
                if sample_text and sample_text.strip():
                    sample_liwc = analyze_text(sample_text, api_key=api_key)
                    all_liwc_scores.append(sample_liwc)
            
            if all_liwc_scores:
                # Aggregate by averaging across all samples
                aggregated_sample_liwc = {}
                all_categories = set()
                for liwc in all_liwc_scores:
                    all_categories.update(liwc.keys())
                
                for category in all_categories:
                    values = [liwc.get(category, 0.0) for liwc in all_liwc_scores if category in liwc]
                    if values:
                        aggregated_sample_liwc[category] = statistics.fmean(values)
                
                # Extract profile features
                profile_features = {
                    cat: score.mean 
                    for cat, score in profile.liwc_profile.categories.items()
                }
                
                # Compute BH-LVT weighted cosine similarity
                try:
                    bh_lvt_similarity = compute_bh_lvt_weighted_similarity(profile_features, aggregated_sample_liwc)
                    similarity_metrics["bh_lvt_weighted_cosine"] = float(bh_lvt_similarity)
                except Exception as e:
                    logger.warning(f"Error computing BH-LVT similarity during extraction: {e}")
                    similarity_metrics["bh_lvt_weighted_cosine"] = None
                
                # Compute punctuation cosine similarity
                try:
                    punctuation_similarity = compute_punctuation_similarity(profile_features, aggregated_sample_liwc)
                    similarity_metrics["punctuation_cosine"] = float(punctuation_similarity)
                except Exception as e:
                    logger.warning(f"Error computing punctuation similarity during extraction: {e}")
                    similarity_metrics["punctuation_cosine"] = None
            else:
                similarity_metrics["bh_lvt_weighted_cosine"] = None
                similarity_metrics["punctuation_cosine"] = None
        except Exception as e:
            logger.warning(f"Error computing similarity metrics during profile extraction: {e}")
            similarity_metrics["bh_lvt_weighted_cosine"] = None
            similarity_metrics["punctuation_cosine"] = None
        
        # Return summary (not full profile to avoid large response) with CORS headers
        response_data = {
            "status": "success",
            "message": {
                "personality_id": personality_id,
                "profile_extracted": True,
                "samples_analyzed": len(request_data.writing_samples),
                "liwc_categories": len(profile.liwc_profile.categories),
                "has_traits": profile.mbti is not None or profile.ocean is not None or profile.hexaco is not None,
                "lexicon_size": {
                    "core_verbs": len(profile.lexicon.core_verbs),
                    "core_nouns": len(profile.lexicon.core_nouns),
                    "evaluatives": len(profile.lexicon.evaluatives),
                    "metaphor_stems": len(profile.lexicon.metaphor_stems)
                },
                "similarity_metrics": similarity_metrics  # BH-LVT and punctuation cosine
            }
        }
        return JSONResponse(content=response_data, headers=cors_headers)
        
    except HTTPException as e:
        # Re-raise with CORS headers
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers={**cors_headers, **(e.headers or {})}
        )
    except ValueError as e:
        logger.error(f"Validation error extracting profile: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
            headers=cors_headers
        )
    except Exception as e:
        import traceback
        logger.error(f"Error extracting author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to extract author profile: {str(e)}"},
            headers=cors_headers
        )

@author_personalities_router.post("/author_personalities/{personality_id}/re-extract-profile")
def re_extract_author_profile(
    personality_id: str,
    request_data: ExtractProfileRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Re-extract author profile with updated writing samples.
    
    This endpoint allows users to update an existing profile by providing new writing samples.
    It merges the new samples with existing samples from the database and re-extracts the profile.
    
    - REQUIRES AUTHENTICATION AND OWNERSHIP
    - Merges new samples with existing samples from writing_samples_json
    - Re-extracts profile with all samples (existing + new)
    """
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        import json
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        logger.info(f"Re-extracting profile for author personality: {personality_id}")
        
        # Load existing samples from database
        existing_samples = []
        if personality.writing_samples_json:
            try:
                existing_samples = json.loads(personality.writing_samples_json)
                logger.info(f"Loaded {len(existing_samples)} existing samples from database")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse existing writing_samples_json: {e}, using only new samples")
        
        # Merge new samples with existing samples
        # Note: This is a simple append - users can provide duplicates if they want
        # For a more sophisticated approach, could deduplicate or merge metadata
        all_samples = existing_samples + request_data.writing_samples
        logger.info(f"Merged samples: {len(existing_samples)} existing + {len(request_data.writing_samples)} new = {len(all_samples)} total")
        
        # Merge sample metadata if provided
        all_metadata = None
        if request_data.sample_metadata:
            # Existing samples don't have metadata stored separately, so we'll use defaults for them
            # New samples use provided metadata
            existing_metadata = [{}] * len(existing_samples)  # Default metadata for existing samples
            all_metadata = existing_metadata + request_data.sample_metadata
        
        # Re-extract profile using service with all samples
        service = AuthorProfileService()
        profile = service.extract_and_save_profile(
            author_personality_id=personality_id,
            writing_samples=all_samples,
            sample_metadata=all_metadata,
            db=db
        )
        
        # Return summary
        return {
            "status": "success",
            "message": {
                "personality_id": personality_id,
                "profile_re_extracted": True,
                "samples_analyzed": len(all_samples),
                "existing_samples_count": len(existing_samples),
                "new_samples_count": len(request_data.writing_samples),
                "liwc_categories": len(profile.liwc_profile.categories),
                "has_traits": profile.mbti is not None or profile.ocean is not None or profile.hexaco is not None,
                "lexicon_size": {
                    "core_verbs": len(profile.lexicon.core_verbs),
                    "core_nouns": len(profile.lexicon.core_nouns),
                    "evaluatives": len(profile.lexicon.evaluatives),
                    "metaphor_stems": len(profile.lexicon.metaphor_stems)
                }
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error re-extracting profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        logger.error(f"Error re-extracting author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-extract author profile: {str(e)}"
        )

@author_personalities_router.get("/author_personalities/test-assets")
def test_asset_loading(current_user = Depends(get_current_user)):
    """Test endpoint to verify asset files can be loaded - REQUIRES AUTHENTICATION"""
    try:
        from author_related import ProfileExtractor
        from author_related.asset_loader import AssetLoader
        import traceback
        
        results = {
            "asset_root": None,
            "assets_found": [],
            "assets_missing": [],
            "extractor_init": False,
            "error": None
        }
        
        # Test AssetLoader
        try:
            loader = AssetLoader()
            results["asset_root"] = str(loader.root)
            
            # Check for required files
            required_files = [
                "LIWC_Mean_Table.csv",
                "LIWC_StdDev_Mean_Table.csv",
                "context_domains.json",
                "HighLow_Vectorization.json",
                "Trait_Mapping.json",
                "adapters.json"
            ]
            
            for filename in required_files:
                try:
                    path = loader._resolve(filename)
                    if path.exists():
                        results["assets_found"].append(filename)
                    else:
                        results["assets_missing"].append(filename)
                except Exception as e:
                    results["assets_missing"].append(f"{filename}: {str(e)}")
            
            # Test ProfileExtractor initialization
            try:
                extractor = ProfileExtractor()
                results["extractor_init"] = True
            except Exception as e:
                results["extractor_init"] = False
                results["error"] = f"ProfileExtractor init failed: {str(e)}\n{traceback.format_exc()}"
                
        except Exception as e:
            results["error"] = f"AssetLoader failed: {str(e)}\n{traceback.format_exc()}"
        
        return {
            "status": "success" if results["extractor_init"] else "error",
            "results": results
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": f"Test failed: {str(e)}\n{traceback.format_exc()}"
        }

@author_personalities_router.get("/author_personalities/{personality_id}/profile")
def get_author_profile(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full author profile - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Load profile
        service = AuthorProfileService()
        profile = service.load_profile(personality_id, db)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Extract profile from writing samples first."
            )
        
        # Return full profile with error handling
        try:
            profile_dict = profile.to_dict()
            return {
                "status": "success",
                "profile": profile_dict
            }
        except Exception as e:
            logger.error(f"Error serializing profile to dict: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to serialize profile: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading author profile: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load author profile: {str(e)}"
        )

@author_personalities_router.get("/author_personalities/{personality_id}/liwc-scores")
def get_liwc_scores(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick access to LIWC scores - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        service = AuthorProfileService()
        liwc_scores = service.get_liwc_scores(personality_id, db)
        
        if not liwc_scores:
            # Check if profile exists but LIWC scores are missing
            if personality.profile_json:
                logger.warning(f"Profile exists but LIWC scores missing for {personality_id}, attempting to extract from profile")
                try:
                    profile = service.load_profile(personality_id, db)
                    if profile and profile.liwc_profile:
                        # Extract LIWC scores from profile
                        liwc_scores = {
                            category: {"mean": score.mean, "stdev": score.stdev, "z": score.z}
                            for category, score in profile.liwc_profile.categories.items()
                        }
                        # Save for future quick access
                        personality.liwc_scores = json.dumps(liwc_scores, ensure_ascii=False)
                        db.commit()
                        logger.info(f"Extracted and saved LIWC scores from profile for {personality_id}")
                except Exception as e:
                    logger.error(f"Failed to extract LIWC scores from profile: {e}")
            
            if not liwc_scores:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="LIWC scores not found. Extract profile from writing samples first."
                )
        
        return {
            "status": "success",
            "liwc_scores": liwc_scores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading LIWC scores: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load LIWC scores: {str(e)}"
        )

@author_personalities_router.get("/author_personalities/{personality_id}/trait-scores")
def get_trait_scores(
    personality_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick access to trait scores (MBTI/OCEAN/HEXACO) - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_profile_service import AuthorProfileService
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        service = AuthorProfileService()
        trait_scores = service.get_trait_scores(personality_id, db)
        
        if not trait_scores:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trait scores not found. Extract profile from writing samples first."
            )
        
        return {
            "status": "success",
            "trait_scores": trait_scores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error loading trait scores: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trait scores: {str(e)}"
        )

@author_personalities_router.post("/author_personalities/{personality_id}/validate-content")
def validate_content(
    personality_id: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate content against author profile - REQUIRES AUTHENTICATION AND OWNERSHIP"""
    try:
        from models import AuthorPersonality
        from author_validation_helper import validate_content_against_profile
        
        # Verify ownership
        personality = db.query(AuthorPersonality).filter(
            AuthorPersonality.id == personality_id,
            AuthorPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Author personality not found or access denied"
            )
        
        # Get content and style config from request
        content = request_data.get("content", "")
        style_config_block = request_data.get("style_config", "")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required"
            )
        
        # Validate content
        validation_result = validate_content_against_profile(
            generated_text=content,
            style_config_block=style_config_block,
            author_personality_id=personality_id,
            db=db
        )
        
        return {
            "status": "success",
            "validation": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error validating content: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate content: {str(e)}"
        )

# Brand Personality Endpoints
@author_personalities_router.get("/brand_personalities")
def get_brand_personalities(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all brand personalities for the current user - REQUIRES AUTHENTICATION"""
    logger.info(f"🔍 /brand_personalities GET endpoint called by user {current_user.id}")
    try:
        from models import BrandPersonality
        # Filter by user_id to only return user's own personalities
        personalities = db.query(BrandPersonality).filter(
            BrandPersonality.user_id == current_user.id
        ).all()
        return {
            "status": "success",
            "message": {
                "personalities": [
                    {
                        "id": personality.id,
                        "name": personality.name,
                        "description": personality.description,
                        "guidelines": personality.guidelines,
                        "created_at": personality.created_at.isoformat() if personality.created_at else None,
                        "updated_at": personality.updated_at.isoformat() if personality.updated_at else None,
                        "user_id": personality.user_id
                    }
                    for personality in personalities
                ]
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching brand personalities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch brand personalities: {str(e)}"
        )

@author_personalities_router.post("/brand_personalities")
def create_brand_personality(personality_data: BrandPersonalityCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new brand personality - REQUIRES AUTHENTICATION"""
    try:
        from models import BrandPersonality
        logger.info(f"Creating brand personality: {personality_data.name} for user {current_user.id}")
        
        # Generate unique ID
        personality_id = str(uuid.uuid4())
        
        # Create personality in database with user_id
        personality = BrandPersonality(
            id=personality_id,
            name=personality_data.name,
            description=personality_data.description,
            guidelines=personality_data.guidelines,
            user_id=current_user.id  # Associate with logged-in user
        )
        
        db.add(personality)
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality created successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create brand personality: {str(e)}"
        )

@author_personalities_router.put("/brand_personalities/{personality_id}")
def update_brand_personality(personality_id: str, personality_data: BrandPersonalityUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        
        # Update fields if provided
        if personality_data.name is not None:
            personality.name = personality_data.name
        if personality_data.description is not None:
            personality.description = personality_data.description
        if personality_data.guidelines is not None:
            personality.guidelines = personality_data.guidelines
        
        personality.updated_at = datetime.now()
        db.commit()
        db.refresh(personality)
        
        logger.info(f"Brand personality updated successfully: {personality_id}")
        
        return {
            "status": "success",
            "message": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "guidelines": personality.guidelines,
                "created_at": personality.created_at.isoformat() if personality.created_at else None,
                "updated_at": personality.updated_at.isoformat() if personality.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand personality: {str(e)}"
        )

@author_personalities_router.delete("/brand_personalities/{personality_id}")
def delete_brand_personality(personality_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a brand personality - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    try:
        from models import BrandPersonality
        personality = db.query(BrandPersonality).filter(
            BrandPersonality.id == personality_id,
            BrandPersonality.user_id == current_user.id
        ).first()
        if not personality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand personality not found or access denied"
            )
        db.delete(personality)
        db.commit()
        logger.info(f"Brand personality deleted successfully: {personality_id}")
        return {
            "status": "success",
            "message": "Brand personality deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error deleting brand personality: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete brand personality: {str(e)}"
        )
