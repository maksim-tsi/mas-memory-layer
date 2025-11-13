# LLM Provider Integration Implementation Plan

**Created**: November 12, 2025  
**Target**: Phase 2B - Multi-Provider LLM Client & Promotion Engine  
**Duration**: 12-18 days (2-3 weeks)  
**Status**: Ready for Implementation  
**Prerequisites**: Phase 2A at 92% (fix 6 failing tests first)

---

## Executive Summary

This plan implements the **multi-provider LLM client and Promotion Engine (L1→L2)** to enable autonomous fact extraction from conversations. Currently, LLM connectivity is verified (7 models tested) but production integration does NOT exist.

**Critical Blocker**: Without this implementation, Phase 2C-2D (Consolidation & Distillation engines) cannot proceed.

**What We Have:**
- ✅ Connectivity tests for 7 LLM models (Gemini, Groq, Mistral)
- ✅ ADR-006 multi-provider strategy (775 lines)
- ✅ SDK dependencies installed
- ✅ Memory tiers (L1-L4) implemented
- ✅ CIAR scorer implemented

**What We Need:**
- ❌ `src/utils/llm_client.py` - Multi-provider client
- ❌ `src/memory/engines/circuit_breaker.py` - Resilience pattern
- ❌ `src/memory/fact_extractor.py` - LLM-based extraction
- ❌ `src/memory/engines/promotion_engine.py` - L1→L2 pipeline

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Promotion Engine                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ L1 Active    │──▶│ Fact         │──▶│ L2 Working   │   │
│  │ Context      │   │ Extractor    │   │ Memory       │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│                            │                                │
│                            ▼                                │
│                    ┌──────────────┐                         │
│                    │ LLM Client   │                         │
│                    │ (Multi-Prov) │                         │
│                    └──────────────┘                         │
│                            │                                │
│              ┌─────────────┼─────────────┐                 │
│              ▼             ▼             ▼                 │
│         ┌────────┐   ┌────────┐   ┌────────┐              │
│         │ Gemini │   │  Groq  │   │Mistral │              │
│         │ 2.5/2.0│   │Llama8B │   │ Large  │              │
│         └────────┘   └────────┘   └────────┘              │
│              │             │             │                 │
│              └─────────────┴─────────────┘                 │
│                      Circuit Breaker                        │
│                            │                                │
│                            ▼                                │
│                   Rule-Based Fallback                       │
└─────────────────────────────────────────────────────────────┘
```

**Task-to-Provider Routing:**
- **Fact Extraction**: Gemini 2.5 Flash (quality) → Gemini 2.0 Flash → Mistral Large
- **CIAR Certainty Scoring**: Groq Llama 8B (speed) → Gemini Flash-Lite
- **Development/Testing**: Groq Llama 8B (fast, free)

---

## Implementation Roadmap

### **Phase 0: Prerequisites (1-2 days)**

**MUST FIX BEFORE STARTING Phase 2B:**

Fix 6 failing tests in Phase 2A (currently 70/76 passing):
1. Episode model Pydantic validation (3 tests) - add missing field defaults
2. Context manager cleanup (2 tests) - adjust mock expectations
3. KnowledgeDocument validation (1 test) - add required field

**Commands:**
```bash
# Run failing tests
pytest tests/memory/test_episodic_memory_tier.py::test_retrieve_parses_timestamps -v
pytest tests/memory/test_episodic_memory_tier.py::test_query_by_session -v
pytest tests/memory/test_episodic_memory_tier.py::test_delete_episode_from_both_stores -v
pytest tests/memory/test_episodic_memory_tier.py::test_context_manager_lifecycle -v
pytest tests/memory/test_semantic_memory_tier.py::test_health_check_healthy -v
pytest tests/memory/test_semantic_memory_tier.py::test_context_manager_lifecycle -v

# After fixes, verify 76/76 passing
pytest tests/memory/ -v
```

**Acceptance:** All Phase 2A tests passing (76/76)

---

### **Week 1: Core LLM Infrastructure (Days 1-5)**

#### **Day 1-2: Multi-Provider LLM Client**

**File:** `src/utils/llm_client.py`

**Tasks:**
1. Create provider abstraction layer
2. Implement Gemini provider wrapper (3 models)
3. Implement Groq provider wrapper (2 models)
4. Implement Mistral provider wrapper (2 models)
5. Add task-to-provider routing
6. Add rate limit tracking

**Key Features:**
- Automatic provider selection based on task type
- Rate limit awareness (10-60 RPM per provider)
- Token usage tracking
- Exponential backoff on failures
- Fallback chain execution

**Code Structure:**
```python
# src/utils/llm_client.py
from enum import Enum
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

class LLMTask(Enum):
    FACT_EXTRACTION = "fact_extraction"
    CERTAINTY_SCORING = "certainty_scoring"
    EPISODE_SUMMARIZATION = "episode_summarization"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"

class LLMProvider(Enum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GROQ_LLAMA_8B = "llama-3.1-8b-instant"
    GROQ_GPT_OSS_120B = "openai/gpt-oss-120b"
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_SMALL = "mistral-small-latest"

TASK_PROVIDER_PRIORITY = {
    LLMTask.FACT_EXTRACTION: [
        LLMProvider.GEMINI_2_5_FLASH,
        LLMProvider.GEMINI_2_0_FLASH,
        LLMProvider.MISTRAL_LARGE
    ],
    LLMTask.CERTAINTY_SCORING: [
        LLMProvider.GROQ_LLAMA_8B,
        LLMProvider.GEMINI_2_5_FLASH_LITE,
        LLMProvider.GEMINI_2_5_FLASH
    ],
    # ... other tasks
}

class RateLimiter:
    """Track rate limits per provider (RPM, TPM)."""
    def __init__(self, rpm: int, tpm: int):
        self.rpm = rpm
        self.tpm = tpm
        self.request_times = []
        self.token_usage = []
    
    async def wait_if_needed(self, estimated_tokens: int):
        """Wait if rate limit would be exceeded."""
        pass

class MultiProviderLLMClient:
    def __init__(self, config: Dict[str, str]):
        """
        Initialize with API keys.
        
        Args:
            config: {'google_api_key': ..., 'groq_api_key': ..., 'mistral_api_key': ...}
        """
        self.providers = self._initialize_providers(config)
        self.rate_limiters = self._initialize_rate_limiters()
    
    async def generate(
        self,
        prompt: str,
        task: LLMTask,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        response_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate text using optimal provider for task.
        
        Returns:
            {
                'text': str,
                'provider': LLMProvider,
                'usage': {'prompt_tokens': int, 'completion_tokens': int}
            }
        """
        provider_chain = TASK_PROVIDER_PRIORITY[task]
        
        for provider in provider_chain:
            try:
                # Check rate limits
                await self.rate_limiters[provider].wait_if_needed(max_tokens)
                
                # Call provider
                response = await self._call_provider(
                    provider, prompt, temperature, max_tokens, response_schema
                )
                
                return {
                    'text': response['text'],
                    'provider': provider.value,
                    'usage': response['usage']
                }
            
            except Exception as e:
                # Log and try next provider
                print(f"Provider {provider.value} failed: {e}, trying next...")
                continue
        
        raise Exception("All providers exhausted or rate limited")
    
    async def _call_provider(self, provider: LLMProvider, prompt: str, 
                           temperature: float, max_tokens: int,
                           response_schema: Optional[Dict]) -> Dict:
        """Call specific provider."""
        if provider.value.startswith('gemini'):
            return await self._call_gemini(provider, prompt, temperature, 
                                          max_tokens, response_schema)
        elif provider.value.startswith('llama') or provider.value.startswith('openai'):
            return await self._call_groq(provider, prompt, temperature, max_tokens)
        elif provider.value.startswith('mistral'):
            return await self._call_mistral(provider, prompt, temperature, max_tokens)
```

**Tests:** `tests/utils/test_llm_client.py`
- Test provider selection for each task type
- Test rate limit enforcement
- Test fallback chain execution
- Test token tracking
- Mock all external API calls

**Acceptance Criteria:**
- [ ] All 7 providers callable through unified interface
- [ ] Task-based routing working (FACT_EXTRACTION → Gemini 2.5)
- [ ] Rate limits enforced (10-60 RPM per provider)
- [ ] Fallback chain executes on provider failure
- [ ] 80%+ test coverage

---

#### **Day 3: Circuit Breaker Pattern**

**File:** `src/memory/engines/circuit_breaker.py`

**Tasks:**
1. Implement state machine (CLOSED → OPEN → HALF_OPEN)
2. Add failure threshold tracking
3. Add timeout management
4. Add success/failure recording

**Code Structure:**
```python
# src/memory/engines/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded, use fallback
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """
    Resilience pattern for LLM service failures.
    
    States:
    - CLOSED: Normal operation, LLM calls allowed
    - OPEN: Too many failures, use fallback (rule-based extraction)
    - HALF_OPEN: After timeout, test with single request
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        if breaker.is_open():
            # Use fallback
            result = rule_based_extraction(data)
        else:
            try:
                result = await llm_extraction(data)
                breaker.record_success()
            except Exception:
                breaker.record_failure()
                result = rule_based_extraction(data)
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Args:
            failure_threshold: Number of consecutive failures before opening
            timeout: Seconds to wait before testing recovery (OPEN → HALF_OPEN)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
    
    def is_open(self) -> bool:
        """Check if circuit is open (should use fallback)."""
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    return False
            return True
        return False
    
    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def get_metrics(self) -> dict:
        """Get circuit breaker metrics."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
        }
```

**Tests:** `tests/memory/test_circuit_breaker.py`
- Test state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Test failure threshold enforcement
- Test timeout recovery
- Test metrics reporting

**Acceptance Criteria:**
- [ ] Circuit opens after 5 consecutive failures
- [ ] Circuit tests recovery after 60s timeout
- [ ] Circuit closes on successful test
- [ ] 100% test coverage

---

#### **Day 4-5: Fact Extractor**

**File:** `src/memory/fact_extractor.py`

**Tasks:**
1. Implement LLM-based structured fact extraction
2. Implement rule-based fallback extraction
3. Integrate with circuit breaker
4. Add prompt templates for fact extraction
5. Parse LLM JSON responses into Fact objects

**Code Structure:**
```python
# src/memory/fact_extractor.py
from typing import List, Dict, Any
from src.utils.llm_client import MultiProviderLLMClient, LLMTask
from src.memory.engines.circuit_breaker import CircuitBreaker
from src.memory.models import Fact, FactType
import json
import re

class FactExtractor:
    """
    Extract structured facts from conversation turns.
    
    Uses LLM for structured extraction with circuit breaker fallback
    to rule-based extraction on LLM failures.
    """
    
    def __init__(self, llm_client: MultiProviderLLMClient, 
                 circuit_breaker: CircuitBreaker):
        self.llm = llm_client
        self.circuit_breaker = circuit_breaker
    
    async def extract_facts(self, turns: List[Dict[str, Any]], 
                          session_id: str) -> List[Fact]:
        """
        Extract facts from conversation turns.
        
        Args:
            turns: List of conversation turns [{'role': str, 'content': str}, ...]
            session_id: Session identifier
        
        Returns:
            List of Fact objects with CIAR components
        """
        if self.circuit_breaker.is_open():
            # Use fallback
            return await self._rule_based_extraction(turns, session_id)
        
        try:
            facts = await self._llm_extraction(turns, session_id)
            self.circuit_breaker.record_success()
            return facts
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            # Fallback to rule-based
            return await self._rule_based_extraction(turns, session_id)
    
    async def _llm_extraction(self, turns: List[Dict], session_id: str) -> List[Fact]:
        """Extract facts using LLM with structured output."""
        # Build prompt
        conversation_text = self._format_turns(turns)
        prompt = self._build_extraction_prompt(conversation_text)
        
        # Define JSON schema for structured output
        response_schema = {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "fact_type": {"type": "string", "enum": ["preference", "constraint", "entity", "mention"]},
                            "certainty": {"type": "number", "minimum": 0, "maximum": 1},
                            "impact": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "required": ["content", "fact_type", "certainty", "impact"]
                    }
                }
            }
        }
        
        # Call LLM
        response = await self.llm.generate(
            prompt=prompt,
            task=LLMTask.FACT_EXTRACTION,
            temperature=0.0,
            max_tokens=2000,
            response_schema=response_schema
        )
        
        # Parse response
        facts_data = json.loads(response['text'])
        
        # Convert to Fact objects
        facts = []
        for idx, fact_data in enumerate(facts_data.get('facts', [])):
            fact = Fact(
                fact_id=f"{session_id}_fact_{idx}",
                session_id=session_id,
                content=fact_data['content'],
                fact_type=FactType(fact_data['fact_type']),
                certainty=fact_data['certainty'],
                impact=fact_data['impact'],
                source_type='llm_extracted'
            )
            facts.append(fact)
        
        return facts
    
    async def _rule_based_extraction(self, turns: List[Dict], session_id: str) -> List[Fact]:
        """
        Fallback: Simple rule-based extraction.
        
        Rules:
        - Extract sentences containing "prefer", "like", "want" → preference facts
        - Extract sentences with "must", "require", "need" → constraint facts
        - Extract proper nouns → entity facts
        """
        facts = []
        conversation_text = self._format_turns(turns)
        
        # Preference patterns
        preference_patterns = [
            r'(I|we|they) (prefer|like|want|love) (.+?)[.!?]',
            r'(prefer|like|want) (.+?) (over|instead of|rather than) (.+?)[.!?]'
        ]
        
        for pattern in preference_patterns:
            matches = re.finditer(pattern, conversation_text, re.IGNORECASE)
            for idx, match in enumerate(matches):
                fact = Fact(
                    fact_id=f"{session_id}_rule_pref_{idx}",
                    session_id=session_id,
                    content=match.group(0),
                    fact_type=FactType.PREFERENCE,
                    certainty=0.6,  # Lower certainty for rule-based
                    impact=0.7,
                    source_type='rule_based'
                )
                facts.append(fact)
        
        # Similar for constraints, entities...
        
        return facts
    
    def _build_extraction_prompt(self, conversation: str) -> str:
        """Build prompt for LLM fact extraction."""
        return f"""Extract structured facts from this conversation.

For each fact, provide:
1. content: The fact statement
2. fact_type: One of [preference, constraint, entity, mention]
3. certainty: How confident you are (0.0-1.0)
4. impact: How important/impactful this fact is (0.0-1.0)

Conversation:
{conversation}

Extract facts as JSON."""
    
    def _format_turns(self, turns: List[Dict]) -> str:
        """Format conversation turns into text."""
        return "\n".join([
            f"{turn['role']}: {turn['content']}"
            for turn in turns
        ])
```

**Tests:** `tests/memory/test_fact_extractor.py`
- Test LLM extraction with mocked responses
- Test rule-based extraction
- Test circuit breaker integration
- Test Fact object creation
- Test JSON parsing

**Acceptance Criteria:**
- [ ] Extracts facts using LLM with structured output
- [ ] Falls back to rule-based on LLM failure
- [ ] Creates valid Fact objects with CIAR components
- [ ] Integrates with circuit breaker
- [ ] 80%+ test coverage

---

### **Week 2: Promotion Engine (Days 6-10)**

#### **Day 6-8: Promotion Engine Core**

**File:** `src/memory/engines/promotion_engine.py`

**Tasks:**
1. Implement async background processing loop
2. Integrate L1 (ActiveContextTier) for turn retrieval
3. Integrate L2 (WorkingMemoryTier) for fact storage
4. Integrate FactExtractor for extraction
5. Integrate CIARScorer for scoring
6. Add session batching and processing

**Code Structure:**
```python
# src/memory/engines/promotion_engine.py
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.fact_extractor import FactExtractor
from src.memory.ciar_scorer import CIARScorer
from src.memory.models import Fact

class PromotionEngine:
    """
    Autonomous L1→L2 promotion engine.
    
    Continuously processes conversation turns from L1 (Active Context),
    extracts facts, scores them with CIAR, and promotes significant
    facts (score ≥ threshold) to L2 (Working Memory).
    
    Example:
        l1_tier = ActiveContextTier(...)
        l2_tier = WorkingMemoryTier(...)
        extractor = FactExtractor(llm_client, circuit_breaker)
        scorer = CIARScorer()
        
        engine = PromotionEngine(l1_tier, l2_tier, extractor, scorer)
        await engine.run()  # Runs forever
    """
    
    def __init__(
        self,
        l1_tier: ActiveContextTier,
        l2_tier: WorkingMemoryTier,
        extractor: FactExtractor,
        scorer: CIARScorer,
        ciar_threshold: float = 0.6,
        batch_size: int = 5,
        cycle_interval: int = 60
    ):
        """
        Args:
            l1_tier: Active Context tier for reading turns
            l2_tier: Working Memory tier for storing facts
            extractor: Fact extractor (LLM-based)
            scorer: CIAR scorer
            ciar_threshold: Minimum CIAR score for promotion (default: 0.6)
            batch_size: Number of turns to process per batch (default: 5)
            cycle_interval: Seconds between processing cycles (default: 60)
        """
        self.l1 = l1_tier
        self.l2 = l2_tier
        self.extractor = extractor
        self.scorer = scorer
        self.ciar_threshold = ciar_threshold
        self.batch_size = batch_size
        self.cycle_interval = cycle_interval
        self.running = False
        self.metrics = {
            'cycles_run': 0,
            'turns_processed': 0,
            'facts_extracted': 0,
            'facts_promoted': 0,
            'facts_rejected': 0
        }
    
    async def run(self):
        """Run promotion engine (blocking, runs forever)."""
        self.running = True
        print(f"Promotion Engine started (cycle every {self.cycle_interval}s)")
        
        while self.running:
            try:
                await self._process_cycle()
                self.metrics['cycles_run'] += 1
                await asyncio.sleep(self.cycle_interval)
            
            except Exception as e:
                print(f"Promotion cycle error: {e}")
                await asyncio.sleep(self.cycle_interval)
    
    async def stop(self):
        """Stop promotion engine."""
        self.running = False
    
    async def _process_cycle(self):
        """Process one promotion cycle."""
        # Get active sessions from L1
        sessions = await self.l1.get_active_sessions()
        
        for session_id in sessions:
            await self._process_session(session_id)
    
    async def _process_session(self, session_id: str):
        """Process one session."""
        # Get recent turns that haven't been processed
        turns = await self.l1.get_recent_turns(
            session_id, 
            limit=self.batch_size,
            unprocessed_only=True
        )
        
        if not turns:
            return
        
        self.metrics['turns_processed'] += len(turns)
        
        # Extract facts
        facts = await self.extractor.extract_facts(turns, session_id)
        self.metrics['facts_extracted'] += len(facts)
        
        # Score and promote
        for fact in facts:
            # Calculate CIAR score
            ciar_score = self.scorer.calculate(fact.model_dump())
            fact.ciar_score = ciar_score
            
            # Promote if significant
            if ciar_score >= self.ciar_threshold:
                await self.l2.store(fact.model_dump())
                self.metrics['facts_promoted'] += 1
            else:
                self.metrics['facts_rejected'] += 1
        
        # Mark turns as processed in L1
        turn_ids = [turn['turn_id'] for turn in turns]
        await self.l1.mark_processed(turn_ids)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics."""
        return {
            **self.metrics,
            'promotion_rate': (
                self.metrics['facts_promoted'] / self.metrics['facts_extracted']
                if self.metrics['facts_extracted'] > 0 else 0
            )
        }
```

**Tests:** `tests/memory/test_promotion_engine.py`
- Test session processing
- Test turn batching
- Test fact extraction integration
- Test CIAR scoring integration
- Test threshold enforcement
- Test metrics tracking
- Mock all tier operations

**Acceptance Criteria:**
- [ ] Processes turns from L1 in batches
- [ ] Extracts facts using FactExtractor
- [ ] Scores facts with CIARScorer
- [ ] Promotes facts with score ≥ 0.6 to L2
- [ ] Tracks metrics (turns processed, facts promoted)
- [ ] Runs asynchronously without blocking
- [ ] 80%+ test coverage

---

#### **Day 9-10: Integration & End-to-End Testing**

**Tasks:**
1. Create integration tests with real L1/L2 tiers
2. Test full L1→L2 pipeline
3. Add configuration management
4. Add logging and monitoring
5. Performance testing (target: <200ms p95 latency)

**Integration Test:**
```python
# tests/integration/test_promotion_pipeline.py
import pytest
import asyncio
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.fact_extractor import FactExtractor
from src.memory.ciar_scorer import CIARScorer
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.engines.circuit_breaker import CircuitBreaker
from src.utils.llm_client import MultiProviderLLMClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_promotion_pipeline():
    """Test complete L1→L2 promotion pipeline."""
    # Setup
    l1_tier = ActiveContextTier(config={'redis_url': '...', 'postgres_url': '...'})
    l2_tier = WorkingMemoryTier(config={'postgres_url': '...'})
    llm_client = MultiProviderLLMClient(config={...})
    circuit_breaker = CircuitBreaker()
    extractor = FactExtractor(llm_client, circuit_breaker)
    scorer = CIARScorer()
    
    engine = PromotionEngine(l1_tier, l2_tier, extractor, scorer)
    
    # Add test conversation to L1
    session_id = "test_session_001"
    turns = [
        {'role': 'user', 'content': 'I prefer morning meetings'},
        {'role': 'assistant', 'content': 'Noted. I'll schedule meetings in the morning.'},
        {'role': 'user', 'content': 'I like coffee with no sugar'},
    ]
    
    for turn in turns:
        await l1_tier.store({
            'session_id': session_id,
            'turn_id': f"turn_{turns.index(turn)}",
            **turn
        })
    
    # Run one promotion cycle
    await engine._process_cycle()
    
    # Verify facts in L2
    facts = await l2_tier.query_by_session(session_id)
    
    assert len(facts) > 0
    assert any('morning meetings' in fact['content'] for fact in facts)
    assert all(fact['ciar_score'] >= 0.6 for fact in facts)
    
    # Verify metrics
    metrics = engine.get_metrics()
    assert metrics['facts_extracted'] > 0
    assert metrics['facts_promoted'] > 0
```

**Configuration File:**
```yaml
# config/promotion_config.yaml
promotion:
  ciar_threshold: 0.6
  batch_size: 5
  cycle_interval: 60
  
llm:
  google_api_key: ${GOOGLE_API_KEY}
  groq_api_key: ${GROQ_API_KEY}
  mistral_api_key: ${MISTRAL_API_KEY}
  
circuit_breaker:
  failure_threshold: 5
  timeout: 60
```

**Acceptance Criteria:**
- [ ] End-to-end test passing (L1 → extract → score → L2)
- [ ] Performance: <200ms p95 latency for 5-turn batch
- [ ] Configuration loading from YAML
- [ ] Logging at INFO level
- [ ] Integration tests with @pytest.mark.integration

---

## Testing Strategy

### **Unit Tests (80%+ coverage target)**
```bash
# LLM Client
pytest tests/utils/test_llm_client.py -v --cov=src/utils/llm_client

# Circuit Breaker
pytest tests/memory/test_circuit_breaker.py -v --cov=src/memory/engines/circuit_breaker

# Fact Extractor
pytest tests/memory/test_fact_extractor.py -v --cov=src/memory/fact_extractor

# Promotion Engine
pytest tests/memory/test_promotion_engine.py -v --cov=src/memory/engines/promotion_engine

# All unit tests
pytest tests/ -m "not integration" --cov=src --cov-report=html
```

### **Integration Tests**
```bash
# Mark integration tests
pytest tests/integration/ -m integration -v

# Run with real databases (requires .env)
pytest tests/integration/test_promotion_pipeline.py -v
```

### **Performance Tests**
```bash
# Benchmark promotion latency
pytest tests/benchmarks/bench_promotion_latency.py -v

# Target: <200ms p95 for 5-turn batch processing
```

---

## Documentation Requirements

### **Files to Create/Update:**

1. **`docs/LLM_CLIENT_USAGE.md`** - Usage guide for MultiProviderLLMClient
2. **`docs/PROMOTION_ENGINE.md`** - Architecture and usage
3. **Update `DEVLOG.md`** - Add Phase 2B completion entry
4. **Update `README.md`** - Update Phase 2B status to "Complete"

---

## Deployment Checklist

### **Before Production:**
- [ ] All unit tests passing (80%+ coverage)
- [ ] Integration tests passing with real databases
- [ ] Performance benchmarks met (<200ms p95)
- [ ] API keys configured in `.env` (not committed)
- [ ] Logging configured (INFO level)
- [ ] Metrics exported to Prometheus/JSON
- [ ] Circuit breaker tested with simulated failures
- [ ] Documentation complete

### **Production Configuration:**
```bash
# .env (DO NOT COMMIT)
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here

# Database URLs from infrastructure
REDIS_URL=redis://192.168.107.172:6379
POSTGRES_URL=postgresql://mas_memory:your_password@192.168.107.172:5432/mas_memory
```

---

## Success Criteria

**Phase 2B Complete When:**
1. ✅ Multi-provider LLM client implemented (`src/utils/llm_client.py`)
2. ✅ Circuit breaker implemented (`src/memory/engines/circuit_breaker.py`)
3. ✅ Fact extractor implemented (`src/memory/fact_extractor.py`)
4. ✅ Promotion engine implemented (`src/memory/engines/promotion_engine.py`)
5. ✅ All unit tests passing (80%+ coverage)
6. ✅ Integration test passing (L1→L2 pipeline)
7. ✅ Performance target met (<200ms p95)
8. ✅ Documentation complete

**Next Phase Unlocked:** Phase 2C - Consolidation Engine (L2→L3)

---

## References

- **ADR-006**: Multi-Provider LLM Strategy (`docs/ADR/006-free-tier-llm-strategy.md`)
- **Phase 2 Action Plan**: Week-by-week breakdown (`docs/reports/phase-2-action-plan.md`)
- **Phase 2 Spec**: Memory tiers specification (`docs/specs/spec-phase2-memory-tiers.md`)
- **CIAR Scorer**: Already implemented (`src/memory/ciar_scorer.py`)
- **Memory Tiers**: L1-L4 implemented (`src/memory/tiers/`)

---

## Questions & Support

- **Architecture questions**: See ADR-006 for multi-provider strategy rationale
- **CIAR scoring**: See `docs/ADR/004-ciar-scoring-formula.md`
- **Implementation status**: Check `DEVLOG.md` for latest updates
- **Test examples**: Review existing tier tests in `tests/memory/test_*_tier.py`

---

**Last Updated**: November 12, 2025  
**Status**: Ready for Development  
**Estimated Completion**: 2-3 weeks (12-18 days)