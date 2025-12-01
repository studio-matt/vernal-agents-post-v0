# Adapter Keys & System Integration Guide

## What is an Adapter Key?

An **adapter key** is a style overlay template from the `author_related` tools that adjusts an author's base writing style for different output formats.

### Adapter Keys Available:
- `linkedin`: Professional, shorter cadence, higher affiliation, coalition CTAs
- `blog`: Longer form, higher evidence density, synthesis CTAs
- `memo_email`: Short cadence, decision CTAs, direct pronoun usage

### What Adapters Adjust:
- **Cadence pattern**: Sentence rhythm (e.g., "2_long_1_short" vs "4_long_1_short")
- **CTA style**: Call-to-action type (coalition, synthesis, decision)
- **Evidence density**: How much supporting evidence (0.5 to 0.8)
- **Empathy targets**: How often to address reader directly
- **LIWC biases**: Adjust LIWC category targets (affiliation, clout, analytic)
- **Metaphor sets**: Which metaphors to use (coalition, ecology, clarity, etc.)

## Integration Hierarchy

Your system has **4 layers** that work together:

```
1. Author Profile (Base Style)
   ↓
2. Adapter Overlay (Platform Style Adjustments)
   ↓
3. Platform Agent (Admin Panel Assignment)
   ↓
4. Custom Modifications (Content Planner User Input)
   ↓
Final Prompt → LLM
```

### Layer 1: Author Profile
- Extracted from writing samples
- Contains: LIWC scores, lexicon, default controls, trait scores
- **Stored in**: `author_personalities.profile_json`

### Layer 2: Adapter Overlay
- Platform-specific style adjustments
- **Adapter keys**: `linkedin`, `blog`, `memo_email`
- **Merges with**: Author profile default_controls
- **Result**: STYLE_CONFIG block

### Layer 3: Platform Agent
- Assigned in admin panel per platform
- **Examples**: `linkedin_agent`, `twitter_agent`, `facebook_agent`
- **Stored in**: `SystemSettings` (e.g., `writing_agent_{agent_id}_name`)
- **Used by**: CrewAI workflow for actual writing

### Layer 4: Custom Modifications
- User-defined per platform in Content Planner
- **Stored in**: Frontend `localStorage` → `contentGenPayload.platformSettings[platform].customModifications`
- **Format**: Free-form text instructions
- **Example**: "Always include 3 hashtags", "Use emojis sparingly", "Keep under 280 chars"

## How They Work Together

### Current Flow (Without Author Voice):
```
Content Prompt
  → Platform Agent (from admin panel)
  → Custom Modifications (from content planner)
  → LLM
```

### New Flow (With Author Voice):
```
Content Prompt
  → Author Profile (base style)
  → Adapter Overlay (platform style adjustments)
  → STYLE_CONFIG block
  → Platform Agent (from admin panel) + STYLE_CONFIG
  → Custom Modifications (from content planner)
  → LLM
```

## Implementation Strategy

### Option A: Author Voice + CrewAI (Recommended)
Use author voice to generate STYLE_CONFIG, then pass it to CrewAI workflow:

```python
# 1. Generate STYLE_CONFIG with author voice
style_config = generate_style_config(author_personality_id, platform)

# 2. Pass STYLE_CONFIG to CrewAI writing agent
crew_result = create_content_generation_crew(
    text=content_prompt,
    platform=platform,
    style_config=style_config,  # NEW
    custom_modifications=custom_modifications  # NEW
)
```

### Option B: Author Voice Direct (Current Implementation)
Use author voice directly, bypassing CrewAI:

```python
# Generate content directly with author voice
generated_text, style_config, metadata = generate_with_author_voice(
    content_prompt=content_prompt,
    author_personality_id=author_personality_id,
    platform=platform
)
```

## Custom Modifications Integration

Custom modifications should be appended to the STYLE_CONFIG or included in the agent instructions:

```python
# Merge custom modifications with STYLE_CONFIG
final_prompt = f"""{style_config_block}

Additional Platform-Specific Instructions:
{custom_modifications}

Content Prompt:
{content_prompt}
"""
```

## Platform-to-Adapter Mapping

Current mapping (can be extended):
- `linkedin` → `linkedin` adapter
- `twitter` → `blog` adapter (fallback, can add twitter adapter)
- `facebook` → `blog` adapter (fallback, can add facebook adapter)
- `instagram` → `blog` adapter (fallback, can add instagram adapter)
- `blog` → `blog` adapter
- `email` → `memo_email` adapter

## Next Steps

1. **Update `generate_with_author_voice()`** to accept `custom_modifications` parameter
2. **Update CrewAI workflow** to accept `style_config` and merge with agent instructions
3. **Update content generation endpoint** to pass custom modifications from request
4. **Test integration** with all 4 layers working together

