# MCP Integration for Author-Related Tools

## ✅ MCP Tools Registered

Three new MCP tools have been added to `mcp_server.py`:

### 1. `extract_author_profile`
**Purpose:** Extract author profile from writing samples using LIWC analysis

**Input:**
- `author_personality_id` (string, required)
- `writing_samples` (array of strings, required)
- `sample_metadata` (array of objects, optional) - `{mode, audience, path}` for each sample

**Output:**
- Profile extraction summary with LIWC categories, traits, lexicon size

**Usage in MCP workflows:**
```python
result = mcp_server.get_tool("extract_author_profile").execute({
    "author_personality_id": "uuid-here",
    "writing_samples": ["Sample 1", "Sample 2"],
    "sample_metadata": [{"mode": "reform", "audience": "general"}]
})
```

### 2. `generate_with_author_voice`
**Purpose:** Generate content using author personality profile to match author's writing style

**Input:**
- `author_personality_id` (string, required)
- `content_prompt` (string, required) - The topic/prompt to write about
- `platform` (string, default: "blog") - Target platform (linkedin, blog, memo_email, etc.)
- `goal` (string, default: "content_generation")
- `target_audience` (string, default: "general")

**Output:**
- Generated text with author voice
- Style config block used
- Token count and prompt ID

**Usage in MCP workflows:**
```python
result = mcp_server.get_tool("generate_with_author_voice").execute({
    "author_personality_id": "uuid-here",
    "content_prompt": "Write about AI in healthcare",
    "platform": "linkedin",
    "goal": "mobilization",
    "target_audience": "practitioner"
})
```

### 3. `validate_author_voice`
**Purpose:** Validate generated content against author personality profile

**Input:**
- `author_personality_id` (string, required)
- `generated_text` (string, required)
- `style_config` (string, optional) - STYLE_CONFIG block used

**Output:**
- Validation findings
- LIWC deltas
- Cadence/pronoun errors

**Usage in MCP workflows:**
```python
result = mcp_server.get_tool("validate_author_voice").execute({
    "author_personality_id": "uuid-here",
    "generated_text": "Generated content here...",
    "style_config": "[STYLE_CONFIG]..."
})
```

## Integration with Existing MCP Tools

These tools can be used alongside existing MCP tools:

**Example: Generate content with author voice, then validate:**
```python
# Step 1: Generate with author voice
generate_result = mcp_server.get_tool("generate_with_author_voice").execute({
    "author_personality_id": "uuid",
    "content_prompt": "Topic here",
    "platform": "linkedin"
})

# Step 2: Validate the generated content
validation_result = mcp_server.get_tool("validate_author_voice").execute({
    "author_personality_id": "uuid",
    "generated_text": generate_result.data["generated_text"],
    "style_config": generate_result.data["style_config"]
})
```

## Frontend Integration

The `AuthorMimicry` component now:
- ✅ Calls `extractAuthorProfile` API when "Analyze Features" is clicked
- ✅ Creates personality first if needed (from add page)
- ✅ Displays real LIWC scores and traits
- ✅ Connects writing samples to profile extraction

**Flow:**
1. User enters writing samples on `/dashboard/author-personality/add`
2. Clicks "Analyze Features"
3. Component creates personality (if new) → calls extract-profile API
4. Displays real analysis results
5. User can save profile

## Next Steps

- [ ] Update existing content generation workflows to use `generate_with_author_voice`
- [ ] Add validation step to content generation pipelines
- [ ] Integrate with platform-specific generators (LinkedIn, Twitter, etc.)
- [ ] Add personality guardrails to all content generation

