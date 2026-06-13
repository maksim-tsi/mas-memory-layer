# Phase 3 Research Questions

**Document Version**: 1.0  
**Date**: December 27, 2025  
**Status**: Active Research  
**Related**: [Phase 3 Specification](spec-phase3-agent-integration.md)  
**Target Completion**: Before Phase 3 Implementation Start

---

## 1. Executive Summary

This document outlines critical research questions that must be answered before finalizing Phase 3 design. These questions validate our novel architectural decisions and ensure implementation feasibility.

### Research Objectives

1. **Validate Tool Calling Patterns**: Ensure LangChain/LangGraph compatibility with our tool design
2. **Confirm Structured Output Strategies**: Verify LLM capabilities for memory updates
3. **Test Multi-Agent Coordination**: Validate namespace and concurrency patterns
4. **Measure Context Injection Impact**: Assess hybrid approach performance
5. **Evaluate CIAR Reasoning**: Determine if exposing CIAR improves agent decisions

### Research Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Literature Review | Week -2 | Documented findings from production systems |
| Prototype Testing | Week -1 | Working prototypes for each research topic |
| Decision Making | Week 0 | Updated Phase 3 spec with validated decisions |

---

## 2. Research Topics

### RT-01: LangChain/LangGraph Tool Calling Patterns

#### Research Question
Can our proposed tool architecture (unified + granular + feature-specific) integrate seamlessly with LangGraph's tool calling mechanism?

#### Hypothesis
LangGraph's `@tool` decorator with Pydantic schemas will support our multi-layered tool interface across all target LLM providers (Gemini, OpenAI, Anthropic).

#### Key Sub-Questions

1. **Q1.1**: Does LangGraph support async tool execution?
   - **Why Critical**: All our memory operations are async
   - **Validation Method**: Create async tool prototype, test with LangGraph agent

2. **Q1.2**: Can tools access graph state (session_id, user_id, agent_id)?
   - **Why Critical**: Namespace management requires runtime context
   - **Validation Method**: Test LangChain's `runtime` parameter injection

3. **Q1.3**: How does LangGraph handle tool errors?
   - **Why Critical**: Memory system can have partial failures
   - **Validation Method**: Test circuit breaker pattern with tool wrapper

4. **Q1.4**: What's the latency overhead of tool calling?
   - **Why Critical**: Multiple tool calls per turn could impact performance
   - **Validation Method**: Benchmark tool call latency vs direct function calls

#### Research Sources

- **Primary**: [LangGraph Tool Documentation](https://langchain-ai.github.io/langgraph/concepts/low_level/#tools)
- **Examples**: [memory-agent template](https://github.com/langchain-ai/memory-agent)
- **API Docs**: LangChain ToolRuntime reference

#### Expected Findings

Based on preliminary review:
- ✅ LangGraph supports async tools via `async def`
- ✅ `ToolRuntime` provides access to state and context
- ❓ Error handling requires custom middleware (`@wrap_tool_call`)
- ❓ Tool call overhead needs measurement

#### Validation Prototype

```python
# tests/research/test_langgraph_tools.py
from langchain.tools import tool, ToolRuntime
from langgraph.graph import StateGraph
import asyncio

@tool
async def test_memory_query(
    query: str,
    runtime: ToolRuntime
) -> dict:
    """Test async tool with runtime access."""
    session_id = runtime.context.get("session_id")
    # Simulate memory query
    await asyncio.sleep(0.1)
    return {"results": [], "session_id": session_id}

# Test integration
async def test_tool_in_graph():
    # Build graph, bind tool, test execution
    ...
```

#### Success Criteria

- [ ] Async tools execute without blocking
- [ ] Runtime context accessible in all tools
- [ ] Error handling strategy defined
- [ ] Latency overhead < 50ms per tool call

---

### RT-02: Structured Outputs for Memory Updates

#### Research Question
Can we reliably extract structured memory updates (facts, CIAR scores, metadata) from LLM responses?

#### Hypothesis
Gemini's native structured output mode combined with Pydantic schemas will provide >95% reliable fact extraction.

#### Key Sub-Questions

1. **Q2.1**: Does Gemini support native structured outputs?
   - **Why Critical**: Primary LLM for fact extraction
   - **Validation Method**: Test Gemini API with response_schema parameter

2. **Q2.2**: How do we handle partial/malformed responses?
   - **Why Critical**: LLMs can hallucinate fields or return incomplete data
   - **Validation Method**: Error rate testing with validation fallbacks

3. **Q2.3**: What's the performance impact of structured output mode?
   - **Why Critical**: Used in hot path (fact extraction after each turn)
   - **Validation Method**: Benchmark structured vs unstructured generation

4. **Q2.4**: Can we use tool-calling as fallback for structured outputs?
   - **Why Critical**: Some providers don't support native structured outputs
   - **Validation Method**: Compare ProviderStrategy vs ToolStrategy

#### Research Sources

- **Gemini API**: [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- **LangChain**: [Structured Output Guide](https://python.langchain.com/docs/concepts/structured_outputs/)
- **Comparison**: OpenAI structured outputs, Anthropic tool use

#### Validation Prototype

```python
# tests/research/test_structured_outputs.py
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

class FactExtraction(BaseModel):
    facts: List[str] = Field(description="Extracted facts")
    certainty: float = Field(ge=0.0, le=1.0)
    impact: float = Field(ge=0.0, le=1.0)
    fact_type: str = Field(description="Type: preference, constraint, etc.")

async def test_gemini_structured_output():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    
    # Test native structured output
    result = await llm.with_structured_output(FactExtraction).ainvoke(
        "User said: I prefer async communication on Slack"
    )
    
    assert isinstance(result, FactExtraction)
    assert 0.0 <= result.certainty <= 1.0
    # Measure: success rate, latency, token usage
```

#### Expected Findings

- ✅ Gemini supports function calling for structured outputs
- ❓ Error rate needs measurement (target: <5%)
- ❓ Latency overhead compared to unstructured

#### Success Criteria

- [ ] Structured output success rate >95%
- [ ] Fallback strategy defined for failures
- [ ] Latency increase <100ms vs unstructured
- [ ] Works across Gemini, OpenAI (Groq as fallback)

---

### RT-03: Multi-Agent State Coordination

#### Research Question
Does our namespace strategy effectively isolate agent-private state while enabling collaborative workspace sharing?

#### Hypothesis
Redis key namespacing with optimistic locking (version numbers) will handle concurrent agent writes without data corruption.

#### Key Sub-Questions

1. **Q3.1**: What's the optimal Redis key structure for namespaces?
   - **Why Critical**: Affects query performance and isolation guarantees
   - **Validation Method**: Load test with concurrent agents

2. **Q3.2**: How do production systems handle concurrent writes?
   - **Why Critical**: Learn from proven patterns (Zep, Mem0)
   - **Validation Method**: Architecture review + documentation analysis

3. **Q3.3**: Is optimistic locking sufficient or do we need distributed locks?
   - **Why Critical**: Trade-off between performance and consistency
   - **Validation Method**: Simulate race conditions, measure conflict rate

4. **Q3.4**: Should we use Redis Pub/Sub for real-time coordination?
   - **Why Critical**: Adds complexity but enables reactive agents
   - **Validation Method**: Prototype pub/sub pattern, measure latency

#### Research Sources

- **Zep**: [Multi-user architecture](https://help.getzep.com/concepts)
- **Redis**: [Concurrency patterns](https://redis.io/docs/manual/patterns/)
- **LangGraph**: [Multi-agent examples](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/)

#### Validation Prototype

```python
# tests/research/test_namespace_concurrency.py
import asyncio
import redis.asyncio as aioredis

class NamespaceTest:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def test_concurrent_writes(self):
        """Simulate two agents writing to shared workspace."""
        workspace_key = "session:test123:workspace:ws1"
        
        async def agent_write(agent_id: str, value: str):
            # Read current state
            state = await self.redis.get(workspace_key)
            version = 0 if not state else int(state.get("version", 0))
            
            # Simulate processing
            await asyncio.sleep(0.1)
            
            # Write with version check (optimistic lock)
            new_version = version + 1
            success = await self.redis.set(
                workspace_key,
                f'{{"version": {new_version}, "updated_by": "{agent_id}"}}',
                nx=False  # Allow overwrite
            )
            return success
        
        # Run concurrent writes
        results = await asyncio.gather(
            agent_write("agent1", "data1"),
            agent_write("agent2", "data2")
        )
        
        # Measure: conflict rate, data consistency
```

#### Expected Findings

- Redis key structure: `{scope}:{id}:{resource}` pattern
- Optimistic locking sufficient for low-conflict scenarios
- Pub/Sub adds ~10-50ms latency but enables real-time sync

#### Success Criteria

- [ ] Namespace isolation validated (no cross-contamination)
- [ ] Conflict resolution strategy tested
- [ ] Concurrent write performance acceptable (<5% conflict rate)
- [ ] Pub/Sub latency acceptable if implemented

---

### RT-04: Context Injection vs Tool-Based Retrieval

#### Research Question
What's the optimal balance between auto-injected context (always present) and on-demand tool-based retrieval?

#### Hypothesis
Hybrid approach (auto-inject L2 top facts + tool-based deep search) will outperform pure auto-injection or pure tool-based approaches in both latency and accuracy.

#### Key Sub-Questions

1. **Q4.1**: What's the latency impact of auto-injection vs on-demand retrieval?
   - **Why Critical**: Affects per-turn response time
   - **Validation Method**: Benchmark both approaches

2. **Q4.2**: Does context injection affect prompt caching?
   - **Why Critical**: Prompt caching can reduce latency by 50%+
   - **Validation Method**: Test with Anthropic/OpenAI caching

3. **Q4.3**: Do agents make better decisions with always-present context?
   - **Why Critical**: Affects benchmark performance
   - **Validation Method**: A/B testing in Phase 4 benchmarks

4. **Q4.4**: How should context be injected (system prompt vs tool message)?
   - **Why Critical**: Affects prompt caching and token costs
   - **Validation Method**: Test Zep pattern (tool message injection)

#### Research Sources

- **Zep Implementation**: [Context Blocks](https://help.getzep.com/concepts#context-blocks)
- **Prompt Caching**: [Anthropic](https://docs.anthropic.com/claude/docs/prompt-caching), [OpenAI](https://platform.openai.com/docs/guides/prompt-caching)
- **RAG Patterns**: Academic papers on context window optimization

#### Validation Prototype

```python
# tests/research/test_context_injection.py

async def test_auto_injection_latency():
    """Measure latency of pre-assembled context blocks."""
    start = time.time()
    
    # Assemble context block
    context = await assemble_context_block(
        session_id="test123",
        user_id="user456",
        tiers=["L2", "L3", "L4"]
    )
    
    assembly_time = time.time() - start
    
    # Generate with injected context
    response = await llm.generate(
        system="You are a helpful assistant.",
        messages=[
            ToolMessage(content=context, tool_call_id="context_injection"),
            UserMessage(content="What do you know about me?")
        ]
    )
    
    total_time = time.time() - start
    return {
        "assembly_ms": assembly_time * 1000,
        "total_ms": total_time * 1000,
        "tokens": len(context.split())
    }

async def test_tool_based_latency():
    """Measure latency of on-demand tool calls."""
    # Agent uses memory_query tool when needed
    ...
```

#### Expected Findings

- Auto-injection: 50-100ms overhead, better for frequently-needed context
- Tool-based: Variable latency (100-500ms), better for specific queries
- Hybrid: Best of both - common context always present, deep search on-demand

#### Success Criteria

- [ ] Latency profiles documented for both approaches
- [ ] Prompt caching impact measured
- [ ] Hybrid strategy defined (what to auto-inject vs tools)
- [ ] Token cost analysis completed

---

### RT-05: CIAR Exposure Impact on Agent Reasoning

#### Research Question
Does exposing CIAR scores to agents improve their ability to assess information quality and make better decisions?

#### Hypothesis
Agents with access to CIAR tools will demonstrate 10-20% better performance on information selection tasks compared to agents without CIAR visibility.

#### Key Sub-Questions

1. **Q5.1**: Do agents use CIAR scores effectively in reasoning?
   - **Why Critical**: Validates our novel contribution
   - **Validation Method**: Prompt analysis + decision tracking

2. **Q5.2**: Does CIAR transparency improve fact selection?
   - **Why Critical**: Core benefit of exposing significance scores
   - **Validation Method**: Compare retrieval precision with/without CIAR

3. **Q5.3**: How should CIAR be presented (numeric, categorical, explanation)?
   - **Why Critical**: Affects interpretability
   - **Validation Method**: A/B test different presentation formats

4. **Q5.4**: Can agents learn to calibrate CIAR thresholds for different tasks?
   - **Why Critical**: Enables adaptive memory management
   - **Validation Method**: Multi-task evaluation

#### Research Sources

- **Interpretability**: Research on explainable AI for agents
- **Confidence Scores**: Literature on LLM calibration
- **Agent Reasoning**: Papers on tool-augmented reasoning

#### Validation Prototype

```python
# tests/research/test_ciar_reasoning.py

async def test_with_ciar_tools():
    """Agent has access to ciar_explain and ciar_get_top_facts."""
    agent = MemoryAgent(
        memory_system=memory,
        llm=llm,
        tools=[memory_query, ciar_explain, ciar_get_top_facts]
    )
    
    result = await agent.process_turn(AgentInput(
        current_message="What are my most important preferences?",
        session_id="test123",
        # ...
    ))
    
    # Analyze: Did agent use CIAR tools? How did it affect decision?
    return {
        "ciar_tool_calls": count_tool_calls(result, "ciar_"),
        "facts_retrieved": result.metadata["fact_count"],
        "avg_ciar_score": result.metadata["avg_ciar"]
    }

async def test_without_ciar_tools():
    """Agent has only memory_query (no CIAR visibility)."""
    agent = MemoryAgent(
        memory_system=memory,
        llm=llm,
        tools=[memory_query]  # No CIAR tools
    )
    # Same test, compare results
    ...
```

#### Expected Findings

- Agents with CIAR tools show more selective fact retrieval
- Numeric + explanation format most effective
- Benefit most pronounced in high-noise scenarios

#### Success Criteria

- [ ] Agent CIAR tool usage patterns documented
- [ ] Fact selection quality measured (precision/recall)
- [ ] Optimal presentation format identified
- [ ] Validated for inclusion in AIMS 2025 paper

---

## 3. Research Execution Plan

### Week -2: Literature Review & Planning

**Goals**:
- Review all source documentation
- Document existing patterns from Zep, Mem0, LangGraph
- Identify gaps in current knowledge

**Deliverables**:
- Annotated bibliography
- Pattern catalog from production systems
- Research prototype specifications

### Week -1: Prototype Development & Testing

**Goals**:
- Build validation prototypes for each research topic
- Execute benchmarks and measurements
- Document findings

**Deliverables**:
- Working prototypes in `tests/research/`
- Benchmark results with analysis
- Decision matrix for each research question

### Week 0: Decision Making & Spec Update

**Goals**:
- Synthesize findings into design decisions
- Update Phase 3 specification with validated patterns
- Create implementation guidance

**Deliverables**:
- Updated [Phase 3 Specification](spec-phase3-agent-integration.md)
- Implementation patterns document
- Risk mitigation strategies

---

## 4. Decision Framework

For each research question, apply this decision framework:

### Decision Matrix

| Finding | Confidence | Impact | Action |
|---------|-----------|--------|--------|
| Strongly supported | High | High | Adopt in design |
| Weakly supported | Medium | High | Prototype further |
| Unsupported | - | High | Seek alternative |
| Inconclusive | - | Low | Defer to future phase |

### Risk Assessment

For each validated pattern:

1. **Technical Risk**: Can it be implemented reliably?
2. **Performance Risk**: Does it meet latency/throughput requirements?
3. **Maintenance Risk**: How complex is ongoing support?

### Success Thresholds

- **Critical Path** (RT-01, RT-02): Must achieve 100% of success criteria
- **Novel Contribution** (RT-05): Must achieve 75%+ for AIMS paper
- **Optimization** (RT-03, RT-04): Must achieve 60%+ or document trade-offs

---

## 5. Fallback Plans

### If RT-01 (LangGraph Tools) Fails

**Fallback A**: Use direct function calls instead of LangChain @tool decorator
**Fallback B**: Switch to LangChain agents without LangGraph
**Impact**: Loss of state graph benefits, but core functionality preserved

### If RT-02 (Structured Outputs) Fails

**Fallback A**: Use circuit breaker pattern with rule-based extraction
**Fallback B**: Increase LLM temperature and retry logic
**Impact**: Higher latency, potential accuracy reduction

### If RT-03 (Namespace Strategy) Fails

**Fallback A**: Single-agent only for Phase 3, defer multi-agent to Phase 4
**Fallback B**: Use PostgreSQL for all state (not just Redis)
**Impact**: Reduced concurrency, higher latency

### If RT-04 (Context Strategy) Unclear

**Fallback A**: Default to auto-injection (simpler implementation)
**Fallback B**: Pure tool-based (more flexible)
**Impact**: May not be optimal, but functional

### If RT-05 (CIAR Impact) Inconclusive

**Fallback A**: Include CIAR tools but make optional
**Fallback B**: Focus on L3/L4 contributions instead
**Impact**: Weaker novel contribution claim

---

## 6. Documentation Requirements

For each research topic, document:

1. **Methodology**: How was the research conducted?
2. **Data**: Raw measurements, benchmarks, test results
3. **Analysis**: Interpretation of findings
4. **Decision**: What design choice was made and why?
5. **Risks**: Known limitations or trade-offs

**Output Format**: Research memo per topic in `docs/research/phase3/`

---

## 7. Success Metrics

Phase 3 research is successful when:

- ✅ All P0 research questions answered with high confidence
- ✅ Phase 3 specification updated with validated decisions
- ✅ Prototype code demonstrates feasibility
- ✅ Risk mitigation strategies documented
- ✅ Novel contributions validated for AIMS paper

**Target Date**: Before Phase 3 implementation kickoff
**Review Process**: Team discussion on all open questions (OQ-01 to OQ-05)

---

## Appendix A: Research Tools & Resources

### Development Tools

- **Prototyping**: Jupyter notebooks in `notebooks/research/`
- **Benchmarking**: `pytest-benchmark` for performance tests
- **Monitoring**: `time`, `memory_profiler` for resource tracking

### External Resources

- LangChain Documentation: https://python.langchain.com/docs/
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Gemini API: https://ai.google.dev/
- Zep Architecture: https://help.getzep.com/
- Mem0 Concepts: https://docs.mem0.ai/

### Internal Resources

- Phase 2 engines (fact extraction, consolidation, synthesis)
- CIAR scorer implementation
- Storage adapter benchmarks

---

## Appendix B: Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-27 | 1.0 | Initial research questions document |
