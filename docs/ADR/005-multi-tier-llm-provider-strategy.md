# ADR-005: Multi-Tier LLM Provider Strategy with AgentRouter

**Title:** Selection of AgentRouter as Multi-Model LLM Provider for Memory Lifecycle Engines  
**Status:** Proposed  
**Date:** November 2, 2025  
**Author:** Development Team  
**Affects:** Phase 2B-2D (Weeks 4-11), Phase 3 (Agent Integration)  
**Related ADRs:** 
- [ADR-003: Four-Tier Cognitive Memory Architecture](003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](004-ciar-scoring-formula.md)

---

## 1. Context

### 1.1 Problem Statement

Phase 2 implementation of the ADR-003 four-tier memory architecture requires Large Language Model (LLM) integration at multiple critical points in the information lifecycle:

| Component | Week | LLM Requirement | Expected Volume |
|-----------|------|----------------|-----------------|
| **CIAR Certainty Assessment** | Week 4 | Extract confidence scores from facts | ~10M tokens/month |
| **Fact Extraction** | Week 5 | Extract structured facts from conversational turns | ~30M tokens/month |
| **Episode Summarization** | Week 7 | Generate narrative summaries from fact clusters | ~20M tokens/month |
| **Knowledge Synthesis** | Week 10 | Generalize patterns across multiple episodes | ~15M tokens/month |
| **Relationship Inference** | Week 7 | Extract entity relationships for graph storage | ~10M tokens/month |

**Total Projected Volume:** 85M tokens/month

### 1.2 Key Requirements

**Functional Requirements:**
1. **OpenAI API Compatibility:** Seamless integration with LangChain/LangGraph framework
2. **Multiple Model Access:** Different tasks require different capability/cost trade-offs
3. **Explicit Model Selection:** No automatic routing (conflicts with circuit breaker pattern)
4. **Structured Output:** JSON schema support for fact extraction
5. **Batch Processing:** Efficient handling of 5-10 turns at once

**Non-Functional Requirements:**
1. **Cost Efficiency:** Research budget constraints (~$60-80/month target)
2. **Reliability:** Must support circuit breaker pattern with fallback
3. **Performance:** <2s average latency for fact extraction
4. **Scalability:** Handle Phase 3 agent integration (3+ concurrent agents)
5. **Maintainability:** Minimal API surface, single credential management

### 1.3 Constraints

- **Budget:** Limited research funding (student/academic project)
- **Timeline:** 14 weeks remaining in Phase 2-4 implementation
- **Architecture:** Already committed to circuit breaker pattern (Week 5)
- **Evaluation:** Cost metrics required for AIMS 2025 paper submission
- **CIAR Filter:** Already reduces unnecessary LLM calls by ~60% (promotion threshold)

---

## 2. Decision

We will adopt **AgentRouter.org** as the unified LLM provider with a **three-tier model selection strategy** aligned to task complexity and cost requirements.

### 2.1 Selected Provider: AgentRouter.org

**Provider Characteristics:**
- **API Compatibility:** 100% OpenAI-compatible (drop-in replacement)
- **Model Portfolio:** 7 models across 4 providers (OpenAI, Anthropic, Google, DeepSeek)
- **Pricing:** Usage-based, no subscription fees
- **Trial Credits:** $100-200 available for proof-of-concept
- **Routing Model:** Explicit model selection (no automatic routing)
- **Framework Support:** Native LangChain/LangGraph compatibility

### 2.2 Three-Tier Model Selection Strategy

#### **Tier 1: Budget-Optimized** ($0.26-0.50/1M tokens blended)

**Use Cases:** High-frequency, low-complexity operations

| Model | Provider | Input $/1M | Output $/1M | Context | Primary Use Cases |
|-------|----------|-----------|-------------|---------|-------------------|
| **GPT-5 Mini** | OpenAI | $0.25 | $2.00 | 128K | CIAR scoring, fact classification |
| **Claude 3.5 Haiku** | Anthropic | $0.80 | $4.00 | 200K | Entity extraction, code generation |
| **Gemini 2.5 Flash** | Google | $0.15 | $0.60 | 1M | Batch processing, massive context windows |

**Allocation:** ~23M tokens/month (~$13)

**Specific Assignments:**
- **CIAR Certainty Scoring:** GPT-5 Mini (simple classification: 0.0-1.0 scale)
- **Entity Recognition:** Claude 3.5 Haiku (fast, accurate NER)
- **Batch Turn Processing:** Gemini 2.5 Flash (when processing 10+ turns)

#### **Tier 2: Balanced** ($0.38-0.48/1M tokens blended)

**Use Cases:** Primary workload - fact extraction and episode consolidation

| Model | Provider | Input $/1M | Output $/1M | Context | Primary Use Cases |
|-------|----------|-----------|-------------|---------|-------------------|
| **DeepSeek-V3** | DeepSeek | $0.27 | $1.10 | 128K | Fact extraction, relationship inference |
| **GLM-4.6** | Zhipu AI | $0.25 | $0.75 | 200K | Episode summarization, accuracy-critical tasks |

**Allocation:** ~35M tokens/month (~$17)

**Specific Assignments:**
- **Primary Fact Extraction:** DeepSeek-V3 (structured output, good accuracy)
- **Episode Summarization:** GLM-4.6 (narrative generation, coherence)
- **Relationship Extraction:** DeepSeek-V3 (entity-relationship tuples)

#### **Tier 3: Premium** ($3.44-6.00/1M tokens blended)

**Use Cases:** Complex reasoning, knowledge synthesis, critical accuracy

| Model | Provider | Input $/1M | Output $/1M | Context | Primary Use Cases |
|-------|----------|-----------|-------------|---------|-------------------|
| **GPT-5** | OpenAI | $1.25 | $10.00 | 400K | Knowledge pattern extraction, complex reasoning |
| **Claude 3.5 Sonnet** | Anthropic | $3.00 | $15.00 | 200K | Episode narrative generation, instruction following |

**Allocation:** ~27M tokens/month (~$26)

**Specific Assignments:**
- **Knowledge Synthesis (L3→L4):** GPT-5 (pattern generalization across episodes)
- **Complex Episode Narratives:** Claude 3.5 Sonnet (coherent storytelling)
- **Critical Fact Extraction:** Claude 3.5 Sonnet (when precision >95% required)

### 2.3 Model Selection Logic

**Implementation in `src/utils/llm_client.py`:**

```python
class ModelSelector:
    """Select appropriate model tier based on task type."""
    
    TIER_1_MODELS = {
        'ciar_scoring': 'gpt-5-mini',
        'entity_extraction': 'claude-3-5-haiku',
        'batch_processing': 'gemini-2.5-flash'
    }
    
    TIER_2_MODELS = {
        'fact_extraction': 'deepseek-v3',
        'episode_summary': 'glm-4.6',
        'relationship_extraction': 'deepseek-v3'
    }
    
    TIER_3_MODELS = {
        'knowledge_synthesis': 'gpt-5',
        'complex_narrative': 'claude-3.5-sonnet',
        'critical_extraction': 'claude-3.5-sonnet'
    }
    
    @staticmethod
    def select_model(task_type: str) -> str:
        """Select model based on task type."""
        # Try each tier in order
        for tier in [TIER_1_MODELS, TIER_2_MODELS, TIER_3_MODELS]:
            if task_type in tier:
                return tier[task_type]
        
        # Default to balanced tier
        return 'deepseek-v3'
```

### 2.4 Cost Projection

**Monthly Breakdown (85M tokens projected):**

| Component | Volume | Tier | Model | Blended Cost |
|-----------|--------|------|-------|--------------|
| CIAR Scoring | 10M | Tier 1 | GPT-5 Mini | $3.50 |
| Entity Extraction | 8M | Tier 1 | Claude 3.5 Haiku | $5.60 |
| Batch Processing | 5M | Tier 1 | Gemini 2.5 Flash | $1.05 |
| Fact Extraction | 25M | Tier 2 | DeepSeek-V3 | $12.75 |
| Episode Summary | 10M | Tier 2 | GLM-4.6 | $4.00 |
| Knowledge Synthesis | 15M | Tier 3 | GPT-5 | $21.75 |
| Complex Narratives | 12M | Tier 3 | Claude 3.5 Sonnet | $10.80 |
| **TOTAL** | **85M** | | | **$59.05** |

**With Buffer:** $70-80/month (includes retries, testing, optimization, overhead)

**Comparison to Alternatives:**
- Using GPT-4 Turbo exclusively: ~$350/month (6x more expensive)
- Using Claude 3.5 Sonnet exclusively: ~$280/month (4.7x more expensive)
- **Savings: 85%** vs. premium-only approach

---

## 3. Alternatives Considered

### Alternative 1: Direct OpenAI API Only

**Pros:**
- ✅ Simplest integration
- ✅ Most familiar API
- ✅ Excellent documentation
- ✅ Best-in-class models (GPT-4, GPT-5)

**Cons:**
- ❌ **Cost:** ~$350/month using GPT-4 Turbo for all operations
- ❌ Single point of failure (no redundancy)
- ❌ No cost optimization across model tiers
- ❌ Limited to OpenAI model family

**Why Rejected:** Cost prohibitive for research budget. Single-provider risk conflicts with reliability requirements.

---

### Alternative 2: Direct Anthropic API Only

**Pros:**
- ✅ Excellent instruction following (Claude family)
- ✅ Strong at structured output generation
- ✅ Good context window (200K tokens)
- ✅ Reputation for safety and accuracy

**Cons:**
- ❌ **Cost:** ~$280/month using Claude 3.5 Sonnet for all operations
- ❌ Single point of failure
- ❌ Different API format (not OpenAI-compatible)
- ❌ Limited model diversity

**Why Rejected:** Still too expensive. API incompatibility with LangChain examples would require code rewrites.

---

### Alternative 3: Multi-Provider Direct Integration

**Approach:** Integrate OpenAI, Anthropic, and Google APIs directly

**Pros:**
- ✅ Maximum control over provider selection
- ✅ No intermediary dependencies
- ✅ Access to all models
- ✅ No vendor lock-in to aggregator

**Cons:**
- ❌ **Complex credential management:** 3+ API keys to manage
- ❌ **Different API interfaces:** OpenAI vs. Anthropic vs. Google formats
- ❌ **No unified error handling:** Each provider has different error codes
- ❌ **No automatic failover:** Manual implementation required
- ❌ **Development overhead:** 2-3x implementation time

**Why Rejected:** Complexity outweighs benefits. Would delay Phase 2 implementation by 1-2 weeks for marginal gains.

---

### Alternative 4: LiteLLM (Open Source Router)

**Approach:** Self-hosted open-source LLM routing layer

**Pros:**
- ✅ Free (no usage fees)
- ✅ Open source (full control)
- ✅ Supports 100+ models
- ✅ Unified API interface

**Cons:**
- ❌ **Self-hosted overhead:** Requires infrastructure (Docker, monitoring)
- ❌ **No built-in failover:** Must implement circuit breaker ourselves
- ❌ **Maintenance burden:** Updates, security patches, etc.
- ❌ **No trial credits:** Must bring own API keys from start

**Why Rejected:** Infrastructure overhead conflicts with rapid Phase 2 development timeline. Research project doesn't have DevOps resources for self-hosting.

---

### Alternative 5: Local Models (Ollama/LLaMA)

**Approach:** Run models locally using Ollama

**Pros:**
- ✅ Zero API costs
- ✅ Complete privacy (no data leaves server)
- ✅ No rate limits
- ✅ Offline capability

**Cons:**
- ❌ **Requires GPU infrastructure:** Not available on current dev/staging nodes
- ❌ **Quality gap:** Local models significantly worse than GPT-4/Claude
- ❌ **Fact extraction precision:** Unlikely to meet ≥80% target
- ❌ **Context window limitations:** Most local models <32K context

**Why Rejected:** Quality requirements cannot be met with current local model capabilities. Would invalidate AIMS 2025 evaluation results.

---

## 4. Rationale

### 4.1 Why AgentRouter Selected

1. **Cost Efficiency: 85% Savings**
   - Multi-tier strategy reduces costs from $350 to $60/month
   - Sustainable for multi-month research project timeline
   - Allows budget allocation to compute infrastructure instead

2. **100% OpenAI API Compatibility**
   - Zero code changes from LangChain documentation examples
   - Single-line configuration change: `base_url="https://agentrouter.org/v1"`
   - No learning curve for team familiar with OpenAI API

3. **Multi-Provider Risk Mitigation**
   - Access to 4 providers (OpenAI, Anthropic, Google, DeepSeek)
   - If one provider has outage, can switch models in config
   - Aligns with circuit breaker pattern (already planned Week 5)

4. **Explicit Model Selection**
   - No automatic routing complexity
   - Developer specifies exact model per task
   - Predictable costs and behavior
   - Easier to debug and optimize

5. **Trial Credits for POC**
   - $100-200 trial credits available
   - Test all 7 models before committing
   - Validate cost projections before Phase 2 investment

6. **Research Budget Friendly**
   - $60-80/month sustainable for academic project
   - Cost metrics suitable for publication (AIMS 2025)
   - Demonstrates cost-awareness (CIAR filter + tiered selection)

### 4.2 Alignment with ADR-003 Architecture

**Conceptual Mapping:**

| Memory Tier | Characteristics | LLM Tier Analogy |
|-------------|----------------|------------------|
| **L1: Active Context** | High-speed, volatile, recent | **Tier 1 Models** (fast, cheap, frequent) |
| **L2: Working Memory** | Filtered by significance | **Tier 2 Models** (balanced, primary) |
| **L3: Episodic Memory** | Consolidated, structured | **Tier 2-3 Models** (summarization) |
| **L4: Semantic Memory** | Distilled, generalized | **Tier 3 Models** (synthesis, patterns) |

The three-tier LLM strategy mirrors the memory hierarchy: frequent operations use budget models, consolidated operations use balanced models, knowledge synthesis uses premium models.

### 4.3 Risk Mitigation

**Risk 1: AgentRouter Service Reliability**
- **Likelihood:** Low-Medium (depends on provider uptime)
- **Impact:** High (blocks fact extraction pipeline)
- **Mitigation:** 
  - Circuit breaker pattern (already planned Week 5)
  - Rule-based fallback extraction (already planned)
  - Monitor circuit breaker state in metrics
- **Contingency:** Can switch to Alternative 3 (direct APIs) if needed

**Risk 2: Cost Overruns**
- **Likelihood:** Medium (actual usage may exceed projections)
- **Impact:** Medium (budget constraints)
- **Mitigation:**
  - Daily cost monitoring (export from AgentRouter dashboard)
  - CIAR threshold already filters 60% of potential extractions
  - Can shift allocation: reduce Tier 3, increase Tier 1
- **Contingency:** Add stricter CIAR threshold (0.6 → 0.7) if needed

**Risk 3: Model Quality Below Requirements**
- **Likelihood:** Low-Medium (especially Tier 1 models)
- **Impact:** High (breaks fact extraction precision target ≥80%)
- **Mitigation:**
  - POC testing (Week 4) validates quality before commitment
  - Can upgrade tasks to higher tier if quality insufficient
  - Evaluation dataset tracks precision/recall per model
- **Contingency:** Shift budget allocation to higher tiers

**Risk 4: Model Deprecation/Changes**
- **Likelihood:** Medium (providers deprecate models over time)
- **Impact:** Low (can substitute equivalent model)
- **Mitigation:**
  - Abstract model selection in config file
  - Map task types to models, not hardcode model names
  - AgentRouter provides multiple alternatives per tier
- **Contingency:** Update model mappings in config

**Risk 5: Vendor Lock-In to AgentRouter**
- **Likelihood:** Low (OpenAI API is standard)
- **Impact:** Low (easy to migrate)
- **Mitigation:**
  - Use standard OpenAI API interface (LangChain)
  - Only configuration-level dependency (base_url)
  - Can switch to direct APIs with single config change
- **Contingency:** Migration requires only environment variable changes

---

## 5. Implementation Plan

### Phase 1: Proof of Concept (Week 4 - Days 1-2)

**Objective:** Validate AgentRouter functionality and cost projections

**Tasks:**
1. Register AgentRouter account → receive API key + trial credits
2. Test all 7 models with sample prompts:
   ```python
   # scripts/poc_agentrouter_test.py
   from langchain_openai import ChatOpenAI
   
   models_to_test = [
       'gpt-5-mini', 'claude-3-5-haiku', 'gemini-2.5-flash',
       'deepseek-v3', 'glm-4.6',
       'gpt-5', 'claude-3.5-sonnet'
   ]
   
   for model in models_to_test:
       llm = ChatOpenAI(
           model=model,
           api_key=os.getenv("AGENTROUTER_API_KEY"),
           base_url="https://agentrouter.org/v1"
       )
       response = llm.invoke("Extract facts: User prefers Hamburg port")
       print(f"{model}: {response.content}")
   ```

3. Run fact extraction quality test:
   - 20 sample conversational turns
   - Extract facts with each Tier 2 model
   - Manually score precision/recall
   - Select best performer

4. Validate pricing:
   - Track token usage from trial
   - Compare to AgentRouter billing dashboard
   - Confirm projections ±10%

**Success Criteria:**
- ✅ All 7 models respond successfully
- ✅ At least 1 Tier 2 model achieves ≥75% precision on test set
- ✅ Actual costs match projections within ±20%
- ✅ Average latency <2s for fact extraction

**Timeline:** 2 days (8 hours)

---

### Phase 2: Integration Development (Week 5 - Days 1-3)

**Objective:** Integrate AgentRouter into fact extraction pipeline

**Tasks:**

**Day 1: LLM Client Wrapper** (4 hours)

Create `src/utils/llm_client.py`:

```python
"""
LLM client with AgentRouter integration and model selection.
"""

from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os


class LLMClient:
    """
    Unified LLM client with multi-tier model selection.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AGENTROUTER_API_KEY")
        self.base_url = "https://agentrouter.org/v1"
        self._clients = {}  # Cache clients per model
    
    def get_client(self, model: str, **kwargs) -> ChatOpenAI:
        """Get or create LangChain client for model."""
        if model not in self._clients:
            self._clients[model] = ChatOpenAI(
                model=model,
                api_key=self.api_key,
                base_url=self.base_url,
                **kwargs
            )
        return self._clients[model]
    
    async def extract_facts(
        self, 
        turns: List[str],
        model: str = "deepseek-v3"
    ) -> Dict[str, Any]:
        """
        Extract facts from conversation turns.
        Uses Tier 2 model by default (balanced cost/quality).
        """
        client = self.get_client(model, temperature=0.3)
        
        # Build prompt
        turns_text = "\n".join([f"Turn {i+1}: {t}" for i, t in enumerate(turns)])
        prompt = f"""Extract structured facts from these conversation turns.

{turns_text}

Return JSON array with format:
[
  {{
    "fact_type": "preference|constraint|entity|goal|metric",
    "content": "fact statement",
    "certainty": 0.0-1.0,
    "entities": ["entity1", "entity2"]
  }}
]"""
        
        response = await client.ainvoke([
            SystemMessage(content="You are a fact extraction assistant."),
            HumanMessage(content=prompt)
        ])
        
        return self._parse_response(response.content)
    
    async def score_certainty(
        self,
        fact: str,
        model: str = "gpt-5-mini"
    ) -> float:
        """
        Score certainty of a fact (CIAR component).
        Uses Tier 1 model (fast, cheap).
        """
        client = self.get_client(model, temperature=0.0)
        
        prompt = f"""Rate the certainty of this fact on a scale of 0.0-1.0:

Fact: "{fact}"

Return only a number between 0.0 and 1.0."""
        
        response = await client.ainvoke([HumanMessage(content=prompt)])
        
        try:
            return float(response.content.strip())
        except ValueError:
            return 0.6  # Default fallback
    
    async def synthesize_knowledge(
        self,
        episodes: List[Dict[str, Any]],
        model: str = "gpt-5"
    ) -> str:
        """
        Synthesize knowledge patterns from episodes.
        Uses Tier 3 model (complex reasoning).
        """
        client = self.get_client(model, temperature=0.5)
        
        episodes_text = "\n\n".join([
            f"Episode {i+1}: {ep['summary']}" 
            for i, ep in enumerate(episodes)
        ])
        
        prompt = f"""Identify common patterns across these episodes and synthesize general knowledge:

{episodes_text}

Generate a concise knowledge statement that captures recurring themes."""
        
        response = await client.ainvoke([
            SystemMessage(content="You are a knowledge synthesis assistant."),
            HumanMessage(content=prompt)
        ])
        
        return response.content
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM JSON response with error handling."""
        # Implementation details...
        pass
```

**Day 2: Model Selection Configuration** (2 hours)

Create `config/llm_config.yaml`:

```yaml
# LLM Provider Configuration
llm:
  provider: "agentrouter"
  api_key_env: "AGENTROUTER_API_KEY"
  base_url: "https://agentrouter.org/v1"
  
  # Timeout and retry settings
  timeout_seconds: 30
  max_retries: 3
  retry_delay_seconds: 2

# Model tier mappings
model_tiers:
  tier_1:  # Budget ($0.26-0.50/1M tokens)
    ciar_scoring: "gpt-5-mini"
    entity_extraction: "claude-3-5-haiku"
    batch_processing: "gemini-2.5-flash"
    default: "gpt-5-mini"
  
  tier_2:  # Balanced ($0.38-0.48/1M tokens)
    fact_extraction: "deepseek-v3"
    episode_summary: "glm-4.6"
    relationship_extraction: "deepseek-v3"
    default: "deepseek-v3"
  
  tier_3:  # Premium ($3.44-6.00/1M tokens)
    knowledge_synthesis: "gpt-5"
    complex_narrative: "claude-3.5-sonnet"
    critical_extraction: "claude-3.5-sonnet"
    default: "gpt-5"

# Cost monitoring
cost_monitoring:
  enabled: true
  daily_budget_usd: 3.00
  alert_threshold_percent: 80
  log_file: "logs/llm_costs.json"
```

**Day 3: Integration with Fact Extractor** (4 hours)

Update `src/memory/fact_extractor.py`:

```python
from src.utils.llm_client import LLMClient
from src.memory.circuit_breaker import CircuitBreaker

class FactExtractor:
    def __init__(self, llm_client: LLMClient, circuit_breaker: CircuitBreaker):
        self.llm = llm_client
        self.circuit_breaker = circuit_breaker
    
    async def extract_facts(self, turns: List[Dict]) -> List[Dict]:
        """Extract facts with circuit breaker protection."""
        
        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            logger.warning("Circuit breaker open, using rule-based extraction")
            return await self._rule_based_extraction(turns)
        
        try:
            # Try LLM extraction (Tier 2 model)
            turn_contents = [t['content'] for t in turns]
            facts = await self.llm.extract_facts(
                turn_contents,
                model="deepseek-v3"  # From config: tier_2.fact_extraction
            )
            
            self.circuit_breaker.record_success()
            return facts
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            self.circuit_breaker.record_failure()
            
            # Fallback to rule-based
            return await self._rule_based_extraction(turns)
```

**Success Criteria:**
- ✅ `LLMClient` class created with 3 tier methods
- ✅ Configuration file with model mappings
- ✅ Fact extractor integrated with circuit breaker
- ✅ Unit tests for LLM client (mocked responses)

**Timeline:** 3 days (10 hours)

---

### Phase 3: Production Deployment (Week 6+)

**Objective:** Monitor, optimize, and scale LLM integration

**Ongoing Tasks:**

1. **Daily Cost Monitoring** (10 min/day)
   - Check AgentRouter dashboard
   - Log to `logs/llm_costs.json`
   - Alert if >$3/day (>$90/month pace)

2. **Quality Monitoring** (Weekly)
   - Sample 20 fact extractions
   - Manually score precision/recall
   - Adjust model selection if quality drops

3. **Optimization** (Bi-weekly)
   - Analyze which tasks use most tokens
   - Experiment with Tier 1 models for high-volume tasks
   - Update config with optimizations

4. **Documentation** (Week 6)
   - Add to `examples/metrics_demo.py`
   - Document in Phase 2 completion report
   - Include cost metrics for AIMS 2025 paper

**Success Criteria:**
- ✅ Monthly costs stay within $60-80 range
- ✅ Fact extraction precision ≥80% maintained
- ✅ Circuit breaker trips <5% of requests
- ✅ Zero manual interventions required

**Timeline:** Ongoing through Phase 2-4

---

## 6. Success Metrics

### 6.1 Functional Metrics (from Week 5 Plan)

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Fact Extraction Precision** | ≥80% | Manual review of 100 sample extractions |
| **Fact Extraction Recall** | ≥70% | Manual review against expected facts |
| **CIAR Certainty Accuracy** | ±0.1 vs. manual scoring | Compare LLM scores to expert judgment |
| **Episode Summary Coherence** | ≥4.0/5.0 rating | Manual quality review |
| **Knowledge Synthesis Relevance** | ≥4.0/5.0 rating | Manual quality review |

### 6.2 Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Average Latency** | <2s | Metrics collector (P50, P95, P99) |
| **Circuit Breaker Trip Rate** | <5% | Count failures / total requests |
| **LLM Availability** | ≥99% | Track successful vs. failed calls |
| **Timeout Rate** | <2% | Count timeouts / total requests |

### 6.3 Cost Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Monthly Cost** | $60-80 | AgentRouter dashboard |
| **Cost per Fact Extracted** | <$0.002 | Total cost / fact count |
| **Cost per Episode Consolidated** | <$0.01 | Total cost / episode count |
| **Cost per Knowledge Synthesized** | <$0.05 | Total cost / knowledge doc count |

### 6.4 Reliability Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Fallback Accuracy** | ≥60% | Precision of rule-based extraction |
| **Recovery Time** | <60s | Time from failure to circuit breaker recovery |
| **Multi-Provider Usage** | ≥2 providers | Track which providers used |

---

## 7. Monitoring and Observability

### 7.1 Metrics Collection

**Integration with Existing Metrics System:**

```python
# src/utils/llm_client.py
from src.storage.metrics import MetricsCollector

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        # ... existing code ...
        self.metrics = MetricsCollector(component="llm_client")
    
    async def extract_facts(self, turns, model):
        with self.metrics.timer('llm.extract_facts'):
            try:
                result = await self._call_llm(turns, model)
                self.metrics.increment('llm.extract_facts.success')
                self.metrics.record('llm.extract_facts.tokens', result.usage.total_tokens)
                self.metrics.record('llm.extract_facts.cost', self._calculate_cost(result))
                return result
            except Exception as e:
                self.metrics.increment('llm.extract_facts.failure')
                self.metrics.record('llm.extract_facts.error_type', type(e).__name__)
                raise
```

**Metrics Exported:**
- `llm.extract_facts.duration_ms` - Latency histogram
- `llm.extract_facts.success` - Success counter
- `llm.extract_facts.failure` - Failure counter
- `llm.extract_facts.tokens` - Token usage histogram
- `llm.extract_facts.cost` - Cost histogram
- `llm.circuit_breaker.state` - Current state (0=closed, 1=half-open, 2=open)
- `llm.model_usage.{model_name}` - Usage counter per model

### 7.2 Cost Tracking

**Daily Cost Log:**

```json
// logs/llm_costs.json
{
  "date": "2025-11-15",
  "total_cost_usd": 2.45,
  "total_tokens": 1250000,
  "by_tier": {
    "tier_1": {"cost": 0.35, "tokens": 150000},
    "tier_2": {"cost": 1.10, "tokens": 800000},
    "tier_3": {"cost": 1.00, "tokens": 300000}
  },
  "by_task": {
    "fact_extraction": {"cost": 1.20, "count": 350},
    "ciar_scoring": {"cost": 0.25, "count": 800},
    "episode_summary": {"cost": 0.60, "count": 45},
    "knowledge_synthesis": {"cost": 0.40, "count": 12}
  },
  "budget_status": {
    "daily_budget": 3.00,
    "used_percent": 81.7,
    "remaining": 0.55
  }
}
```

### 7.3 Alerting Rules

**Cost Alerts:**
- Daily cost exceeds $3.00 (>$90/month pace)
- Weekly cost exceeds $15.00 (>$60/month pace)
- Single request costs >$0.10 (anomaly detection)

**Quality Alerts:**
- Fact extraction precision drops below 75%
- Circuit breaker open >10% of time
- Timeout rate exceeds 5%

**Implementation:** Add to existing monitoring infrastructure (Prometheus/Grafana if available)

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test LLM Client in Isolation:**

```python
# tests/utils/test_llm_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.utils.llm_client import LLMClient

@pytest.fixture
def mock_llm_client():
    client = LLMClient(api_key="test-key")
    # Mock the underlying ChatOpenAI clients
    return client

@pytest.mark.asyncio
async def test_extract_facts_success(mock_llm_client):
    """Test successful fact extraction."""
    mock_response = MagicMock()
    mock_response.content = '[{"fact_type": "preference", "content": "User prefers Hamburg"}]'
    
    # Mock the client
    mock_llm_client._clients['deepseek-v3'] = AsyncMock()
    mock_llm_client._clients['deepseek-v3'].ainvoke.return_value = mock_response
    
    result = await mock_llm_client.extract_facts(
        ["User: I prefer Hamburg port"],
        model="deepseek-v3"
    )
    
    assert len(result) == 1
    assert result[0]['fact_type'] == 'preference'

@pytest.mark.asyncio
async def test_extract_facts_timeout(mock_llm_client):
    """Test timeout handling."""
    mock_llm_client._clients['deepseek-v3'] = AsyncMock()
    mock_llm_client._clients['deepseek-v3'].ainvoke.side_effect = TimeoutError()
    
    with pytest.raises(TimeoutError):
        await mock_llm_client.extract_facts(["test"], model="deepseek-v3")
```

### 8.2 Integration Tests

**Test with Real API (using VCR.py for recording):**

```python
# tests/integration/test_llm_integration.py
import pytest
import vcr

@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_fact_extraction_with_real_api(llm_client):
    """Test fact extraction with real API (recorded response)."""
    # First run: makes real API call and records to cassette
    # Subsequent runs: replays from cassette (no API call)
    
    turns = [
        "User: I need to ship containers to Hamburg",
        "Agent: Hamburg Port has capacity available"
    ]
    
    result = await llm_client.extract_facts(turns, model="deepseek-v3")
    
    assert len(result) >= 1
    assert any(f['fact_type'] == 'entity' and 'Hamburg' in f['content'] for f in result)
```

### 8.3 End-to-End Tests

**Test Full Promotion Pipeline:**

```python
# tests/integration/test_promotion_e2e.py
@pytest.mark.asyncio
async def test_promotion_pipeline_with_llm(
    l1_tier,
    l2_tier,
    llm_client,
    fact_extractor,
    ciar_scorer,
    promotion_engine
):
    """Test complete L1→L2 promotion with LLM."""
    
    # Store turns in L1
    session_id = "test-session"
    await l1_tier.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'User prefers Hamburg port'
    })
    
    # Run promotion engine
    await promotion_engine.process_session(session_id)
    
    # Verify facts in L2
    facts = await l2_tier.retrieve(session_id)
    
    assert len(facts) >= 1
    assert any(f['fact_type'] == 'preference' for f in facts)
    assert all(f['ciar_score'] >= 0.6 for f in facts)  # Threshold check
```

### 8.4 Cost Testing

**Monitor Token Usage:**

```python
# tests/performance/test_llm_costs.py
@pytest.mark.cost_test
@pytest.mark.asyncio
async def test_fact_extraction_cost(llm_client):
    """Ensure fact extraction stays within cost targets."""
    
    turns = ["Sample turn " * 10 for _ in range(10)]  # 10 turns
    
    # Track token usage
    with track_tokens() as tracker:
        result = await llm_client.extract_facts(turns, model="deepseek-v3")
    
    # Assert cost per fact is reasonable
    tokens_per_fact = tracker.total_tokens / len(result)
    cost_per_fact = (tokens_per_fact / 1_000_000) * 0.38  # Tier 2 blended
    
    assert cost_per_fact < 0.002, f"Cost per fact ${cost_per_fact} exceeds target $0.002"
```

---

## 9. Migration and Rollback Plan

### 9.1 Migration from No LLM (Current State)

**Current State:** No LLM integration, using placeholder/mock implementations

**Migration Steps:**

1. **Week 4 Day 1-2:** POC testing (no production impact)
2. **Week 5 Day 1-3:** Develop integration (feature flag disabled)
3. **Week 5 Day 4:** Enable for 10% of sessions (canary)
4. **Week 5 Day 5:** Enable for 50% of sessions (gradual rollout)
5. **Week 6 Day 1:** Enable for 100% of sessions (full deployment)

**Feature Flag Implementation:**

```python
# config/feature_flags.yaml
features:
  llm_fact_extraction:
    enabled: true
    rollout_percentage: 100  # 0-100
    fallback_to_rules: true
```

### 9.2 Rollback Plan

**Trigger Conditions for Rollback:**
- Daily cost exceeds $10 (3x budget)
- Circuit breaker open >50% of time
- Fact extraction precision drops below 60%
- Critical bugs in production

**Rollback Procedure:**

1. **Immediate:** Set feature flag `llm_fact_extraction.enabled = false`
2. **Revert:** All extractions use rule-based fallback
3. **Investigate:** Review logs, costs, quality metrics
4. **Fix:** Address root cause
5. **Re-deploy:** Gradual rollout with fixes

**Recovery Time Objective (RTO):** <5 minutes (config-only change)

**Recovery Point Objective (RPO):** Zero (all data preserved, only extraction method changes)

---

## 10. Future Considerations

### 10.1 Potential Optimizations (Phase 4+)

1. **Fine-Tuning for Domain:**
   - Collect 1000+ labeled fact extractions
   - Fine-tune Tier 1 model (GPT-5 Mini or Claude Haiku)
   - Potentially reduce to single-tier architecture

2. **Caching Layer:**
   - Cache LLM responses for identical prompts
   - Redis-based cache with 24h TTL
   - Could reduce costs by 20-30%

3. **Batch Processing:**
   - Process multiple sessions in single LLM call
   - Reduce overhead of API round-trips
   - Trade-off: increased latency, complexity

4. **Prompt Optimization:**
   - A/B test different prompt templates
   - Minimize token usage while maintaining quality
   - Target: 20% token reduction

### 10.2 Alternative Providers to Monitor

1. **Groq:** Ultra-fast inference (claimed <1s for 1000 tokens)
2. **Together AI:** Competitive pricing, open models
3. **Fireworks AI:** Function calling specialists
4. **Replicate:** Ease of custom model deployment

### 10.3 Evaluation for Journal Paper

For extended journal publication (post-AIMS 2025):

**Cost-Benefit Analysis:**
- Total cost vs. baseline (full-context agents)
- Cost per fact vs. manual extraction
- ROI of CIAR filter (avoided costs)

**Ablation Studies:**
- Impact of tier selection on quality
- Cost-quality tradeoff curves
- Comparison of providers within tiers

**Scalability Analysis:**
- Cost scaling to 1000+ sessions
- Multi-agent concurrent usage
- Production deployment costs

---

## 11. Approval and Sign-Off

**Proposed By:** Development Team  
**Date:** November 2, 2025

**Approval Status:** ⏳ Pending Review

**Reviewers:**
- [ ] Technical Lead (architecture validation)
- [ ] Budget Manager (cost approval)
- [ ] Research Advisor (evaluation strategy)

**Approval Criteria:**
- ✅ POC successfully completed (Week 4)
- ✅ Cost projections validated within ±20%
- ✅ Quality targets achievable (≥75% precision in testing)
- ✅ Circuit breaker integration validated

---

## 12. References

### 12.1 Internal Documents
- [ADR-003: Four-Tier Cognitive Memory Architecture](003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](004-ciar-scoring-formula.md)
- [Implementation Plan Week 4-5: CIAR Scoring & Promotion](../plan/implementation-plan-02112025.md#week-4-ciar-scoring-system)
- [Phase 2 Specification: Priority 6 (Promotion Logic)](../specs/spec-phase2-memory-tiers.md)

### 12.2 External Resources
- AgentRouter Integration Report (November 2, 2025)
- [AgentRouter Documentation](https://agentrouter.org/docs)
- [LangChain OpenAI Integration](https://python.langchain.com/docs/integrations/chat/openai)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

### 12.3 Pricing Sources
- OpenAI Pricing (November 2025): https://openai.com/pricing
- Anthropic Pricing (November 2025): https://anthropic.com/pricing
- Google AI Pricing (November 2025): https://ai.google.dev/pricing
- DeepSeek Pricing (November 2025): https://deepseek.com/pricing

---

## Changelog

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-02 | 1.0 | Initial draft | Development Team |

---

**Next Steps:**
1. Review this ADR with team
2. Obtain stakeholder approval
3. Register AgentRouter account (Week 4 Day 1)
4. Begin POC testing (Week 4 Day 1-2)
5. Proceed with Phase 2B implementation (Week 5)
