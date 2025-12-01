# Author-Related Tools Integration Plan

## Vibe Check Summary

✅ **What We Have:**
- Complete, portable Python package (`author-related/`) with:
  - Profile extraction from writing samples (LIWC analysis, trait mapping)
  - Style planning and prompt construction
  - Content generation harness
  - Validation and reporting
  - Deterministic enforcement
  - Asset loading (LIWC baselines, trait mappings, adapters)

✅ **Current System:**
- Frontend: `AuthorMimicry.tsx` component (React/TypeScript)
- Backend: FastAPI with `ContentGeneratorAgent`, `machine_agent.py`, various MCP tools
- Database: SQLAlchemy models for author/brand personalities
- Existing content generation: `generate_campaign_content`, platform-specific generators

## Integration Strategy

### Phase 1: Database Integration (CRITICAL)

**Problem:** `ProfileStore` uses filesystem; we need database persistence.

**Solution:** Create database-backed profile storage that mirrors `ProfileStore` API:

```python
# backend-repo/author_profile_service.py
from author_related import AuthorProfile, ProfileExtractor, Planner, StyleValidator
from models import AuthorPersonality  # Existing model
from database import SessionLocal

class AuthorProfileService:
    """Database-backed author profile service"""
    
    def extract_and_save_profile(
        self,
        author_personality_id: str,
        writing_samples: List[str],
        db: Session
    ) -> AuthorProfile:
        # 1. Use ProfileExtractor to analyze samples
        # 2. Store profile JSON in AuthorPersonality.profile_json column
        # 3. Return AuthorProfile object
        pass
    
    def load_profile(self, author_personality_id: str, db: Session) -> AuthorProfile:
        # Load from database instead of filesystem
        pass
```

**Database Schema Extension:**
```python
# Add to models.py AuthorPersonality model:
profile_json = Column(JSON, nullable=True)  # Store AuthorProfile as JSON
liwc_scores = Column(JSON, nullable=True)  # Quick access to LIWC data
trait_scores = Column(JSON, nullable=True)  # MBTI/OCEAN/HEXACO
```

### Phase 2: API Endpoints

**Create new endpoints in `main.py`:**

```python
# POST /api/author-personalities/{id}/extract-profile
# - Accepts writing samples
# - Runs ProfileExtractor
# - Saves to database
# - Returns profile summary

# GET /api/author-personalities/{id}/profile
# - Returns full AuthorProfile JSON

# POST /api/author-personalities/{id}/generate
# - Accepts: goal, target_audience, adapter_key, scaffold
# - Uses Planner to build STYLE_CONFIG
# - Uses GeneratorHarness with existing LLM
# - Returns generated text + validation report
```

### Phase 3: Frontend Integration

**Update `AuthorMimicry.tsx` to call new endpoints:**

```typescript
// Replace mock analysis with real API call
const analyzeWritingSamples = async () => {
  const response = await Service({
    method: 'POST',
    url: `/api/author-personalities/${personalityId}/extract-profile`,
    data: { writing_samples: writingSamples.map(s => s.text) }
  });
  // Update UI with real LIWC scores, traits, lexicon
};
```

### Phase 4: Content Generation Integration

**Integrate with existing content generation workflows:**

```python
# In generate_campaign_content or platform generators:
from author_related import Planner, GeneratorHarness, StyleValidator

def generate_with_author_voice(
    content_prompt: str,
    author_personality_id: str,
    platform: str,
    db: Session
):
    # 1. Load author profile from database
    profile = author_profile_service.load_profile(author_personality_id, db)
    
    # 2. Map platform to adapter_key (linkedin -> "linkedin", etc.)
    adapter_key = platform.lower()
    
    # 3. Use Planner to build STYLE_CONFIG
    planner = Planner()
    planner_output = planner.build_style_config(
        profile=profile,
        goal="content_generation",
        target_audience="general",
        adapter_key=adapter_key,
        scaffold=content_prompt
    )
    
    # 4. Use GeneratorHarness with existing LLM
    def invoke_llm(prompt: str) -> str:
        # Use existing ChatOpenAI or agent
        return llm.invoke(prompt)
    
    harness = GeneratorHarness(invoke_llm)
    result = harness.run(planner_output)
    
    # 5. Validate output
    validator = StyleValidator()
    # Run LIWC on generated text (need LIWC library)
    validation = validator.validate_output(...)
    
    return result.text, validation
```

## Dependencies to Add

**Required Python packages:**
```bash
# LIWC analysis (choose one):
pip install liwc-python  # OR
pip install pypi-liwc    # OR
# Use existing text_processing.py if it has LIWC

# Already have (from author-related):
# - All data models
# - Asset loading
# - Planning/validation
```

## File Structure

```
backend-repo/
├── author-related/          # ✅ Already in place
│   ├── __init__.py
│   ├── models.py
│   ├── profile_extraction.py
│   ├── planner.py
│   ├── validator.py
│   └── ... (all assets)
├── author_profile_service.py  # NEW: Database wrapper
├── author_api.py              # NEW: FastAPI endpoints
└── main.py                    # Add routes
```

## Integration Checklist

- [ ] **Phase 1: Database**
  - [ ] Add `profile_json`, `liwc_scores`, `trait_scores` columns to `AuthorPersonality`
  - [ ] Create migration script
  - [ ] Create `AuthorProfileService` class
  - [ ] Test profile save/load

- [ ] **Phase 2: API Endpoints**
  - [ ] `POST /api/author-personalities/{id}/extract-profile`
  - [ ] `GET /api/author-personalities/{id}/profile`
  - [ ] `POST /api/author-personalities/{id}/generate`
  - [ ] Add authentication/authorization

- [ ] **Phase 3: Frontend**
  - [ ] Update `AuthorMimicry.tsx` to call real endpoints
  - [ ] Display real LIWC scores and traits
  - [ ] Show validation results

- [ ] **Phase 4: Content Generation**
  - [ ] Integrate Planner into `generate_campaign_content`
  - [ ] Add author voice to platform generators
  - [ ] Add validation reporting

- [ ] **Phase 5: LIWC Integration**
  - [ ] Install/configure LIWC library
  - [ ] Create LIWC analysis wrapper
  - [ ] Test with sample texts

## Key Design Decisions

1. **Database vs Filesystem:** Store profiles in database for multi-tenant support
2. **LIWC Library:** Need to choose/install LIWC analysis library (not included in package)
3. **Adapter Mapping:** Map platforms (linkedin, twitter, etc.) to adapter keys
4. **Validation:** Run validation optionally (can be expensive)
5. **Backward Compatibility:** Keep existing author personality system, extend it

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LIWC library missing | Use existing `text_processing.py` or install `liwc-python` |
| Performance (LIWC analysis) | Cache results, run async |
| Profile size (JSON) | Use JSON column, compress if needed |
| Adapter mismatch | Create platform-to-adapter mapping table |

## Next Steps

1. **Immediate:** Add database columns and create `AuthorProfileService`
2. **Short-term:** Build API endpoints and test with frontend
3. **Medium-term:** Integrate with content generation workflows
4. **Long-term:** Add validation reporting UI, optimize performance

