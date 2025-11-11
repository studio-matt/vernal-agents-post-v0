# Architecture Tracking: MCP & CrewAI Usage

## Overview
This document tracks two critical architectural patterns:
1. **MCP Functionality Maximization** - Ensuring all LLM operations go through MCP tools to avoid code duplication
2. **CrewAI vs Direct LLM** - Maximizing agent-to-agent collaboration vs direct LLM calls

---

## [1] MCP Functionality Tracking

### Current MCP Tools (Registered)
✅ **Available MCP Tools:**
- `script_research` - Text analysis and theme extraction
- `quality_control` - Content review and validation
- `regenerate_content` - Content regeneration
- `{platform}_generation` - Platform-specific content (linkedin, twitter, facebook, etc.)
- `crewai_content_generation` - Full CrewAI workflow

### MCP Usage Patterns

**✅ GOOD: Using MCP Tools**
```python
# simple_mcp_api.py - Content generation endpoint
research_tool = simple_mcp_server.get_tool("script_research")
qc_tool = simple_mcp_server.get_tool("quality_control")
platform_tool = simple_mcp_server.get_tool(f"{platform}_generation")
```

**❌ BAD: Direct LLM Calls (Bypassing MCP)**
Found in these files:

1. **`main.py:1914-1915`** - Research Agent Recommendations
   ```python
   from langchain_openai import ChatOpenAI
   llm = ChatOpenAI(model="gpt-4o-mini", ...)
   response = llm.invoke(prompt)
   ```
   **Should use:** MCP tool for research agent recommendations

2. **`text_processing.py:813`** - Topic Extraction
   ```python
   llm = ChatOpenAI(model="gpt-4o-mini", ...)
   response = llm.invoke(prompt)
   ```
   **Should use:** MCP tool for topic extraction (or create new MCP tool)

3. **`keyword_expansions.py:132`** - Abbreviation Expansion
   ```python
   llm = ChatOpenAI(model="gpt-4o-mini", ...)
   response = llm.invoke(prompt)
   ```
   **Should use:** MCP tool for keyword expansion (or create new MCP tool)

4. **`tasks.py:106, 161`** - Text Analysis
   ```python
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   response = client.chat.completions.create(...)
   ```
   **Should use:** `script_research` MCP tool

5. **`tools.py:38`** - General OpenAI Client
   ```python
   client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
   ```
   **Should use:** MCP tools instead of direct client

6. **`machine_agent.py:13, 123`** - Content Generation
   ```python
   self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
   response = self.client.chat.completions.create(...)
   ```
   **Should use:** Platform generation MCP tools

### MCP Migration Checklist

- [ ] **Research Agent Recommendations** (`main.py:1857`)
  - Current: Direct `ChatOpenAI` call
  - Target: Create/use MCP tool `research_agent_recommendations`
  
- [ ] **Topic Extraction** (`text_processing.py:795`)
  - Current: Direct `ChatOpenAI` call in `llm_model()`
  - Target: Create MCP tool `topic_extraction` or use existing research tool
  
- [ ] **Keyword Expansion** (`keyword_expansions.py:106`)
  - Current: Direct `ChatOpenAI` call in `_expand_with_llm()`
  - Target: Create MCP tool `keyword_expansion`
  
- [ ] **Text Analysis** (`tasks.py:158`)
  - Current: Direct `OpenAI` client call
  - Target: Use existing `script_research` MCP tool
  
- [ ] **Content Generation** (`machine_agent.py`)
  - Current: Direct `OpenAI` client call
  - Target: Use platform-specific MCP tools (`{platform}_generation`)

### Benefits of MCP Migration
- ✅ **Code Reusability:** Same tools used across endpoints
- ✅ **Consistency:** Uniform error handling and logging
- ✅ **Testability:** Tools can be tested independently
- ✅ **Maintainability:** Single source of truth for each operation
- ✅ **Extensibility:** Easy to add new tools without duplicating code

---

## [2] CrewAI vs Direct LLM Tracking

### Current CrewAI Usage

**✅ GOOD: CrewAI Orchestration**
- **`crewai_workflows.py`** - Full agent workflows:
  - `create_content_generation_crew()` - Research → Writing → QC
  - `create_research_to_writing_crew()` - Research → Writing
- **`simple_mcp_api.py:104`** - Uses CrewAI when `use_crewai=True`
- **`mcp_server.py:131`** - Registers `crewai_content_generation` as MCP tool

**CrewAI Agent Flow:**
```
Research Agent → Writing Agent → QC Agent
     ↓              ↓              ↓
  Context      Context        Final
  Passing      Passing        Output
```

### Direct LLM Usage (Should Consider CrewAI)

**❌ Direct LLM Calls That Could Benefit from CrewAI:**

1. **Research Agent Recommendations** (`main.py:1857`)
   - Current: Single LLM call
   - **CrewAI Opportunity:** Research Agent → Recommendation Agent
   - **Benefit:** Better context awareness, agent specialization

2. **Topic Extraction** (`text_processing.py:795`)
   - Current: Single LLM call
   - **CrewAI Opportunity:** Research Agent → Topic Analysis Agent
   - **Benefit:** More nuanced topic identification

3. **Keyword Expansion** (`keyword_expansions.py:106`)
   - Current: Single LLM call
   - **CrewAI Opportunity:** Research Agent → Expansion Agent → Validation Agent
   - **Benefit:** More accurate expansions with validation

4. **Content Generation** (`simple_mcp_api.py:130-175`)
   - Current: Manual orchestration (Research → QC → Platform)
   - **CrewAI Opportunity:** Already available via `use_crewai=True`
   - **Status:** ✅ Implemented but optional

### When to Use CrewAI vs Direct LLM

**Use CrewAI When:**
- ✅ Multiple steps with context passing needed
- ✅ Agent specialization improves quality
- ✅ Error recovery and retry logic needed
- ✅ Complex workflows with dependencies
- ✅ Agent-to-agent collaboration adds value

**Use Direct LLM When:**
- ✅ Simple, single-step operations
- ✅ Speed is critical (CrewAI adds overhead)
- ✅ No context passing needed
- ✅ Stateless operations

### CrewAI Migration Opportunities

**High Priority:**
1. **Research Agent Recommendations** - Multi-agent analysis would improve quality
2. **Topic Extraction** - Research → Topic Analysis → Validation flow
3. **Content Generation** - Already available, but should be default for complex content

**Medium Priority:**
1. **Keyword Expansion** - Research → Expansion → Validation
2. **Content Regeneration** - Research → Regeneration → QC

**Low Priority:**
1. Simple one-off LLM calls (abbreviation expansion, etc.)

---

## Tracking Metrics

### MCP Coverage
```
Total LLM Operations: [COUNT]
MCP Tool Operations: [COUNT]
Direct LLM Calls: [COUNT]
MCP Coverage: [PERCENTAGE]
```

### CrewAI Usage
```
Total Workflows: [COUNT]
CrewAI Workflows: [COUNT]
Direct LLM Workflows: [COUNT]
CrewAI Adoption: [PERCENTAGE]
```

### Code Duplication
```
Duplicate LLM Patterns: [COUNT]
Unique MCP Tools: [COUNT]
Reusability Score: [PERCENTAGE]
```

---

## Action Items for Content Creation

### Before Starting Content Creation Work:

1. **Audit All LLM Calls**
   - Identify all `ChatOpenAI`, `OpenAI()`, `client.chat.completions` calls
   - Map to existing MCP tools or create new ones

2. **Define CrewAI Workflows**
   - Identify multi-step processes
   - Design agent collaboration flows
   - Determine where CrewAI adds value vs overhead

3. **Create Missing MCP Tools**
   - Research agent recommendations tool
   - Topic extraction tool
   - Keyword expansion tool

4. **Refactor Direct Calls**
   - Replace direct LLM calls with MCP tools
   - Update endpoints to use MCP
   - Remove duplicate code

---

## Quick Reference

### MCP Tool Registration Pattern
```python
self.register_tool(SimpleTool(
    name="tool_name",
    description="Tool description",
    input_schema={...},
    handler=self._handle_tool
))
```

### CrewAI Workflow Pattern
```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    tasks=[task1, task2, task3],
    process=Process.sequential,
    verbose=True,
    memory=True
)
result = crew.kickoff(inputs={...})
```

### Direct LLM Pattern (To Avoid)
```python
# ❌ Don't do this
llm = ChatOpenAI(...)
response = llm.invoke(prompt)

# ✅ Do this instead
tool = simple_mcp_server.get_tool("tool_name")
result = await tool.execute(input_data)
```

---

## Next Steps

1. **Create MCP tools** for all direct LLM calls
2. **Design CrewAI workflows** for multi-step processes
3. **Refactor existing code** to use MCP/CrewAI
4. **Update content creation** to maximize both patterns
5. **Monitor usage** and track metrics

