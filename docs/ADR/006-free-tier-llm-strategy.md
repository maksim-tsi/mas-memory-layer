# **ADR-006: Free-Tier LLM Provider Strategy for Multi-Layered Memory System**

*   **Status:** Proposed
*   **Date:** 2025-11-02
*   **Supersedes:** ADR-005 (AgentRouter - Not Accessible)
*   **Decision Makers:** Maksim (Lead Developer)
*   **Consulted:** N/A
*   **Informed:** Development Team

---

## **Context and Problem Statement**

Following the abandonment of AgentRouter integration due to persistent authentication issues, we need a cost-effective LLM integration strategy for the Multi-Layered Memory System (mas-memory-layer) that leverages free-tier offerings from multiple providers. Our Phase 2 implementation requires:

1. **Fact Extraction** (Week 5): Processing conversation turns to extract structured facts
2. **CIAR Scoring** (Week 4): Certainty assessment for fact scoring
3. **Episode Summarization** (Week 7): Summarizing clustered facts into coherent narratives
4. **Knowledge Synthesis** (Week 10): Distilling patterns into generalized insights
5. **Pattern Mining** (Week 9): Identifying recurring themes and relationships

**Constraints:**
- Academic research project (AIMS 2025 conference submission) with limited budget
- Need for reproducibility and reliability in memory operations
- Multiple LLM calls per memory lifecycle engine (potentially 1000s of facts/episodes)
- Varying token requirements per task (100-2000 tokens per request)
- Three autonomous engines running async (Promotion, Consolidation, Distillation)

---

## **Decision Drivers**

*   **Cost Efficiency**: Maximize free-tier usage to minimize expenses (<$10/month target)
*   **Rate Limit Management**: Stay within provider rate limits without blocking async engines
*   **Reliability**: Implement automatic fallbacks for resilience (circuit breaker pattern)
*   **Flexibility**: Easy to add/remove providers as availability changes
*   **Quality**: Sufficient reasoning capability for certainty scoring and knowledge synthesis
*   **Reproducibility**: Maintain deterministic behavior where possible (low temperature)

---

## **Considered Options**

### **Option 1: Single Provider (Google Gemini 2.5 Flash)**
Use only Google Gemini's generous free tier.

### **Option 2: Multi-Provider with Priority-Based Selection**
Implement a smart router that selects providers based on rate limits and task requirements.

### **Option 3: Multi-Provider with Round-Robin Distribution**
Distribute requests evenly across all providers.

---

## **Decision Outcome**

**Chosen option: Option 2 - Multi-Provider with Priority-Based Selection**

We will implement a **multi-provider architecture** with intelligent rate limit management and automatic fallbacks. This approach:
- Maximizes free-tier capacity across providers
- Provides resilience against single-provider failures
- Allows task-specific provider optimization
- Enables graceful degradation under rate limits

---

## **Free-Tier Provider Analysis**

### **Provider 1: Google Gemini 2.5 Flash**

**Rate Limits (Free Tier):**
- **RPM (Requests Per Minute):** 10
- **TPM (Tokens Per Minute):** 250,000
- **RPD (Requests Per Day):** No published limit (effectively unlimited for free tier)
- **Context Window:** 1,000,000 tokens

**Cost:** FREE via Google AI Studio API

**Authentication:**
```bash
export GOOGLE_API_KEY='your-api-key'
# Get key from: https://aistudio.google.com/apikey
```

**SDK Installation:**
```bash
pip install google-generativeai
```

**Strengths:**
- Very high TPM (250k) suitable for large batch processing
- Massive context window (1M tokens) - can process long conversation histories
- Fast inference (Flash model optimized for speed)
- Reliable and well-documented
- Supports structured output and function calling
- Free embeddings available (gemini-embedding-001)

**Weaknesses:**
- Lower RPM (10) may require request pacing for high-volume scenarios
- Free tier usage data may be used to improve Google products

**Best For:**
- **Fact extraction** (Week 5) - process 5-10 turn windows efficiently
- **Episode summarization** (Week 7) - large context window handles clustered facts
- **Knowledge synthesis** (Week 10) - can process multiple episodes in one request
- **Primary provider** for most memory lifecycle tasks

---

### **Provider 2: Google Gemini 2.0 Flash**

**Rate Limits (Free Tier):**
- **RPM (Requests Per Minute):** 15
- **TPM (Tokens Per Minute):** 1,000,000
- **RPD (Requests Per Day):** No published limit
- **Context Window:** 1,000,000 tokens

**Cost:** FREE via Google AI Studio API

**Authentication:**
```bash
export GOOGLE_API_KEY='your-api-key'
# Same key as Gemini 2.5 Flash
```

**SDK Installation:**
```bash
pip install google-generativeai
```

**Strengths:**
- **Highest TPM** (1M) among free tiers - excellent for bulk processing
- Higher RPM (15) than 2.5 Flash
- Massive context window (1M tokens)
- Strong multimodal capabilities
- Mature model with proven reliability

**Weaknesses:**
- Older generation than 2.5 Flash (less advanced reasoning)
- Free tier usage data may be used to improve Google products

**Best For:**
- **High-volume fact extraction** (Week 5) when RPM becomes bottleneck
- **Batch episode processing** (Week 7-8) - can handle many episodes concurrently
- **Fallback for 2.5 Flash** when hitting rate limits
- **Embedding generation** with free gemini-embedding-001 model

---

### **Provider 3: Google Gemini 2.5 Flash-Lite**

**Rate Limits (Free Tier):**
- **RPM:** 15
- **TPM:** 250,000
- **RPD:** No published limit
- **Context Window:** 1,000,000 tokens

**Cost:** FREE via Google AI Studio API

**Authentication:**
```bash
export GOOGLE_API_KEY='your-api-key'
# Same key as other Gemini models
```

**SDK Installation:**
```bash
pip install google-generativeai
```

**Strengths:**
- **Fastest and most cost-effective** Gemini model
- Ultra-fast inference optimized for high throughput
- Same context window (1M) as larger models
- 50% higher RPM than standard 2.5 Flash
- Good for simple extraction and classification tasks

**Weaknesses:**
- Smaller model may have reduced reasoning capability
- Less suitable for complex synthesis tasks
- Free tier usage data may be used to improve Google products

**Best For:**
- **CIAR certainty scoring** (Week 4) - fast, simple classification
- **Fact type classification** (Week 5) - quick entity/preference/mention detection
- **High-volume processing** when speed > quality
- **Development/testing** with instant feedback

---

### **Provider 4: Mistral AI (Mistral Large / Mistral Small)**

**Rate Limits (Free Tier):**
- **RPM (Requests Per Minute):** 1 RPS = ~60 RPM (free tier for prototyping)
- **TPM (Tokens Per Minute):** No strict published limit for free tier
- **Context Window:** 128k tokens (Mistral Large), 32k (Mistral Small)

**Cost:** FREE for prototyping/evaluation; Pay-as-you-go for production

**Authentication:**
```bash
export MISTRAL_API_KEY='your-api-key'
# Get key from: https://console.mistral.ai/
```

**SDK Installation:**
```bash
pip install mistralai
```

**Strengths:**
- **Excellent reasoning capabilities** - strong for complex analysis
- **Structured output support** - JSON mode for fact extraction
- **European provider** - data sovereignty alternative to US providers
- **Function calling** - good for tool use and structured workflows
- **Competitive pricing** if upgrading to paid ($2-8 per 1M tokens)

**Weaknesses:**
- Low RPS (1 req/sec) on free tier requires careful pacing
- Free tier explicitly for evaluation/prototyping only
- Smaller context windows than Gemini (32k-128k vs 1M)

**Best For:**
- **Complex reasoning tasks** (Week 9-10) - pattern analysis, knowledge synthesis
- **Structured fact extraction** (Week 5) - when JSON schema enforcement critical
- **Fallback for Google outages** - provider diversity for resilience
- **Paid tier consideration** - if Gemini limits hit, Mistral is cost-effective alternative

---

### **Provider 5: Groq (with Meta Llama 3.3 70B / Mixtral / Gemma 2)**

**Rate Limits (Free Tier):**
- **RPM:** 30 (varies by model)
- **RPD:** 14,400
- **TPM:** 20,000-200,000 (model-dependent)
- **TPD (Tokens Per Day):** 1,000,000+ (varies by model)
- **Context Window:** 8k-128k (model-dependent)

**Cost:** FREE

**Authentication:**
```bash
export GROQ_API_KEY='your-api-key'
# Get key from: https://console.groq.com/
```

**SDK Installation:**
```bash
pip install groq
```

**Available Free Models:**
- **openai/gpt-oss-120b** - Best reasoning, 120B parameters (reasoning fallback)
- **llama-3.3-70b-versatile** - Ultra-fast, 128k context, 70B parameters
- **mixtral-8x7b-32768** - Good reasoning, 32k context
- **gemma2-9b-it** - Fast, efficient, 8k context

**Strengths:**
- **ULTRA-FAST inference** (~250-800 tokens/sec with LPU hardware)
- **Highest throughput** - ideal for real-time responses
- **Multiple open models** - Llama, Mixtral, Gemma options
- **Good free tier** - much more generous than initial assessment
- **OpenAI-compatible API** - easy integration

**Weaknesses:**
- Smaller context windows (8k-128k) vs Gemini (1M)
- Model selection more limited than Gemini family
- LPU infrastructure newer, less battle-tested

**Best For:**
- **CIAR scoring validation** (Week 4) - ultra-fast simple classifications
- **Real-time fact classification** (Week 5) - instant entity/type detection
- **Development/testing** - immediate feedback loop
- **High-throughput tasks** - when speed is critical
- **Fallback for rate limits** - instant responses when Gemini RPM exhausted

---

## **Optimal Provider Strategy**

### **Task-to-Provider Mapping**

| **Task** | **Primary Provider** | **Fallback 1** | **Fallback 2** | **Fallback 3** | **Rationale** |
|----------|---------------------|----------------|----------------|----------------|---------------|
| **Fact Extraction (Week 5)** | Gemini 2.5 Flash | Mistral Large | Gemini 2.0 Flash | Gemini 2.5 Flash-Lite | 2.5 Flash's reasoning + 1M context; Mistral for structured JSON output; 2.0 Flash for high volume (1M TPM); Lite for emergency fallback |
| **CIAR Certainty Scoring (Week 4)** | Groq (Llama 3.3 70B) | Gemini 2.5 Flash-Lite | Gemini 2.5 Flash | N/A | Groq ultra-fast for simple classification; Lite optimized for speed; 2.5 Flash for nuanced scoring |
| **Episode Summarization (Week 7)** | Gemini 2.5 Flash | Gemini 2.0 Flash | Mistral Large | N/A | 2.5 Flash's reasoning for coherent narratives; 2.0 Flash for batch processing; Mistral for complex episodes |
| **Knowledge Synthesis (Week 10)** | Mistral Large | Gemini 2.5 Flash | Gemini 2.0 Flash | N/A | Mistral excels at complex reasoning/analysis; 2.5 Flash for distillation; 2.0 Flash handles multiple episodes |
| **Pattern Mining (Week 9)** | Gemini 2.5 Flash | Mistral Large | Gemini 2.0 Flash | Groq (GPT OSS 120B) | 2.5 Flash for pattern recognition; Mistral for complex theme analysis; 2.0 for high throughput; Groq reasoning fallback for complex patterns |
| **Development/Testing** | Groq (Llama 3.3 70B) | Gemini 2.5 Flash-Lite | Gemini 2.5 Flash | N/A | Groq ultra-fast (800 tok/sec) for instant feedback; Lite's speed for rapid iteration; 2.5 Flash for quality testing |

---

## **Multi-Provider Resilience Strategy**

### **Why 5 Providers?**

**Provider Diversity Benefits:**
1. **Fallback Resilience**: If one provider fails (API outage, rate limit exhaustion, regional restrictions), automatically failover to next provider
2. **Task-Specific Optimization**: Different models excel at different tasks:
   - **Groq**: Ultra-fast classification (CIAR scoring, development)
   - **Mistral**: Complex reasoning (knowledge synthesis, pattern analysis)
   - **Gemini**: Balanced quality + massive context (fact extraction, episode summarization)
3. **Rate Limit Distribution**: Spread load across providers to avoid single-provider saturation
4. **Cost Optimization**: Use faster/cheaper models (Groq, Gemini Lite) for simple tasks, reserve premium models (Mistral Large, Gemini 2.5 Flash) for complex reasoning
5. **Vendor Independence**: Reduce lock-in to single provider (Google, Mistral, Groq are all independent companies)

**Practical Example:**
- **Week 4 (CIAR Scoring)**: Use Groq Llama 3.3 70B for ultra-fast classification (800 tok/sec)
- **Week 5 (Fact Extraction)**: Use Gemini 2.5 Flash for structured output + massive context (1M tokens)
- **Week 9 (Pattern Mining)**: Use Mistral Large for complex theme analysis and reasoning
- **Rate Limit Hit**: Automatically failover to Gemini 2.0 Flash (1M TPM) for high-volume processing
- **Provider Outage**: Circuit breaker switches to Groq or Mistral as fallback

---

## **Rate Limit Management Strategy**

### **1. Token Budget Tracking**

Track per-provider token usage and remaining daily budgets:

```python
DAILY_LIMITS = {
    'gemini_2_5_flash': {
        'rpm': 10,
        'tpm': 250000,
        'rpd': None,  # No published daily limit
        'tpd': None,  # No daily token limit
        'context_window': 1000000,
    },
    'gemini_2_0_flash': {
        'rpm': 15,
        'tpm': 1000000,
        'rpd': None,  # No published daily limit
        'tpd': None,  # No daily token limit
        'context_window': 1000000,
    },
    'gemini_2_5_flash_lite': {
        'rpm': 15,
        'tpm': 250000,
        'rpd': None,  # No published daily limit
        'tpd': None,  # No daily token limit
        'context_window': 1000000,
    },
    'mistral_large': {
        'rpm': 60,  # 1 RPS
        'tpm': None,  # No strict limit for free tier
        'rpd': None,  # Evaluation tier - fair use
        'tpd': None,  # Evaluation tier - fair use
        'context_window': 128000,
    },
    'mistral_small': {
        'rpm': 60,  # 1 RPS
        'tpm': None,  # No strict limit for free tier
        'rpd': None,  # Evaluation tier - fair use
        'tpd': None,  # Evaluation tier - fair use
        'context_window': 32000,
    },
    'groq_gpt_oss_120b': {
        'rpm': 30,
        'tpm': 20000,
        'rpd': 14400,
        'tpd': 1000000,
        'context_window': 8000,  # GPT OSS 120B context window
    },
    'llama-3.3-70b-versatile': {
        'rpm': 30,
        'tpm': 6000,
        'rpd': 14400,
        'tpd': 100000,
        'context_window': 128000,
    },
    'groq_mixtral_8x7b': {
        'rpm': 30,
        'tpm': 20000,
        'rpd': 14400,
        'tpd': 1000000,
        'context_window': 32000,
    },
}
```

### **2. Request Pacing**

Implement per-provider request queues with automatic throttling:

- **Gemini 2.5 Flash**: Max 10 req/min - requires 6-second minimum spacing
- **Gemini 2.0 Flash**: Max 15 req/min - requires 4-second minimum spacing
- **Gemini 2.5 Flash-Lite**: Max 15 req/min - ideal for high-volume simple tasks

### **3. Exponential Backoff for Rate Limits**

When rate limit (429) errors occur:
1. **Initial backoff:** 2 seconds
2. **Max backoff:** 60 seconds
3. **Jitter:** ±20% randomization to avoid thundering herd
4. **Fallback trigger:** After 3 retries, switch to next provider in priority list

### **4. Daily Budget Monitoring**

For all Gemini models (unlimited daily tokens but subject to fair use):
- Track cumulative requests and tokens per day
- **Monitor for fair use policy** (no published hard limits, but excessive use may be throttled)
- **Distribute load across models** to avoid single-model saturation
- **Primary (2.5 Flash)** for quality tasks, **2.0 Flash** for volume, **Lite** for speed

---

## **Implementation Architecture**

### **Multi-Provider LLM Client**

```python
# generation/llm_client.py

from enum import Enum
from typing import Optional, List
import time

class LLMProvider(Enum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_SMALL = "mistral-small-latest"
    GROQ_GPT_OSS_120B = "openai/gpt-oss-120b"
    GROQ_LLAMA_3_3_70B = "llama-3.3-70b-versatile"
    GROQ_MIXTRAL_8X7B = "mixtral-8x7b-32768"

class LLMTask(Enum):
    FACT_EXTRACTION = "fact_extraction"
    CIAR_CERTAINTY_SCORING = "ciar_certainty_scoring"
    EPISODE_SUMMARIZATION = "episode_summarization"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"
    PATTERN_MINING = "pattern_mining"
    DEVELOPMENT = "development"

TASK_PROVIDER_PRIORITY = {
    LLMTask.FACT_EXTRACTION: [
        LLMProvider.GEMINI_2_5_FLASH,
        LLMProvider.MISTRAL_LARGE,
        LLMProvider.GEMINI_2_0_FLASH,
        LLMProvider.GEMINI_2_5_FLASH_LITE
    ],
    LLMTask.CIAR_CERTAINTY_SCORING: [
        LLMProvider.GROQ_LLAMA_3_3_70B,
        LLMProvider.GEMINI_2_5_FLASH_LITE,
        LLMProvider.GEMINI_2_5_FLASH
    ],
    LLMTask.EPISODE_SUMMARIZATION: [
        LLMProvider.GEMINI_2_5_FLASH,
        LLMProvider.GEMINI_2_0_FLASH,
        LLMProvider.MISTRAL_LARGE
    ],
    LLMTask.KNOWLEDGE_SYNTHESIS: [
        LLMProvider.MISTRAL_LARGE,
        LLMProvider.GEMINI_2_5_FLASH,
        LLMProvider.GEMINI_2_0_FLASH
    ],
    LLMTask.PATTERN_MINING: [
        LLMProvider.GEMINI_2_5_FLASH,
        LLMProvider.MISTRAL_LARGE,
        LLMProvider.GEMINI_2_0_FLASH,
        LLMProvider.GROQ_GPT_OSS_120B
    ],
    LLMTask.DEVELOPMENT: [
        LLMProvider.GROQ_LLAMA_3_3_70B,
        LLMProvider.GEMINI_2_5_FLASH_LITE,
        LLMProvider.GEMINI_2_5_FLASH
    ],
}

class MultiProviderLLMClient:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.rate_limiters = self._initialize_rate_limiters()
        self.token_trackers = self._initialize_token_trackers()

    def generate(
        self,
        prompt: str,
        task: LLMTask,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text using the optimal provider for the task."""
        provider_priority = TASK_PROVIDER_PRIORITY[task]

        for provider in provider_priority:
            try:
                # Check rate limits and token budgets
                if not self._can_make_request(provider, max_tokens):
                    continue

                # Apply provider-specific throttling
                self._wait_for_rate_limit(provider)

                # Make request
                response = self._call_provider(
                    provider, prompt, temperature, max_tokens
                )

                # Track token usage
                self._track_tokens(provider, response.usage)

                return response.text

            except RateLimitError:
                # Exponential backoff and try next provider
                self._handle_rate_limit(provider)
                continue

            except Exception as e:
                # Log error and try next provider
                self._log_error(provider, e)
                continue

        raise Exception("All providers exhausted or rate limited")
```

### **Provider-Specific Wrappers**

```python
# src/utils/providers/gemini_provider.py
import google.generativeai as genai
from typing import Optional, Dict, Any

class GeminiProvider:
    """Wrapper for Google Gemini models with unified interface."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    def generate(
        self, 
        prompt: str, 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        response_schema: Optional[Dict[str, Any]] = None
    ):
        """Generate text with optional structured output."""
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # Support structured output for fact extraction
        if response_schema:
            generation_config.response_mime_type = "application/json"
            generation_config.response_schema = response_schema
        
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config,
        )
        
        return {
            'text': response.text,
            'usage': {
                'prompt_tokens': response.usage_metadata.prompt_token_count,
                'completion_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': response.usage_metadata.total_token_count,
            }
        }

# src/utils/providers/gemini_embedding_provider.py
class GeminiEmbeddingProvider:
    """Wrapper for Gemini embedding model (free tier)."""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model_name = "gemini-embedding-001"
    
    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        result = genai.embed_content(
            model=f"models/{self.model_name}",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
```

---

## **Daily Capacity Estimation**

### **Scenario: Process 1000 Facts Through Promotion Engine (Week 5)**

Assuming each fact extraction request requires:
- Prompt: ~500 tokens (5-10 conversation turns)
- Response: ~300 tokens (structured facts JSON)
- Total per request: ~800 tokens

**Provider Capacity Analysis:**

| **Provider** | **RPM** | **TPM** | **Max Requests/Hour** | **Max Tokens/Hour** | **Daily Capacity (24hr)** |
|--------------|---------|---------|----------------------|---------------------|---------------------------|
| **Gemini 2.5 Flash** | 10 | 250,000 | 600 | 15M | **14,400 req** (11.5M facts @ 800 tok/req) |
| **Gemini 2.0 Flash** | 15 | 1,000,000 | 900 | 60M | **21,600 req** (46M facts) |
| **Gemini 2.5 Flash-Lite** | 15 | 250,000 | 900 | 15M | **21,600 req** (11.5M facts) |

### **Real-World Memory System Throughput:**

**Typical Usage (per day):**
- Active sessions: 100-200
- Facts extracted per session: 10-50
- Total facts/day: 1,000-10,000
- **With 10 RPM limit**: Can process ~600 req/hr = ~14,400 req/day = **enough for 14,400-144,000 facts/day**

**Optimal Strategy:**
- **Use 2.5 Flash as primary**: Best quality for fact extraction
- **Use 2.0 Flash for high volume**: Switch when approaching 10 RPM limit
- **Use Lite for CIAR scoring**: Fast simple classification doesn't need premium model

---

## **Cost Projections**

### **Provider Comparison Summary**

| **Provider** | **Best For** | **Free Tier RPM** | **Free Tier TPM** | **Context Window** | **Key Strength** |
|--------------|--------------|-------------------|-------------------|--------------------|--------------------|
| **Gemini 2.5 Flash** | Complex reasoning, fact extraction | 10 | 250k | 1M tokens | Latest model, best quality |
| **Gemini 2.0 Flash** | High-volume batch processing | 15 | 1M | 1M tokens | Highest TPM (1M) |
| **Gemini 2.5 Flash-Lite** | Fast classification, dev/test | 15 | 250k | 1M tokens | Ultra-fast inference |
| **Mistral Large** | Complex analysis, structured output | 60 | N/A | 128k tokens | Excellent reasoning, JSON mode |
| **Groq (Llama 3.3 70B)** | Real-time responses, dev/test | 30 | 6k | 128k tokens | Ultra-fast (800 tok/sec), 70B params |
| **Groq (GPT OSS 120B)** | Complex reasoning fallback | 30 | 20k | 8k tokens | Strong reasoning, 120B params |

### **Worst-Case Scenario: Exceed Free Tiers**

If free tiers are exhausted and we need to upgrade to paid tier:

| **Model** | **Paid Tier Pricing (per 1M tokens)** | **Cost for 10k Facts (8M tokens @ 800/fact)** |
|-----------|----------------------------------------|----------------------------------------------|
| **Gemini 2.5 Flash** | Input: $0.30, Output: $2.50 | **Input: $2.40, Output: $6.00 = $8.40** |
| **Gemini 2.0 Flash** | Input: $0.10, Output: $0.40 | **Input: $0.80, Output: $0.96 = $1.76** |
| **Gemini 2.5 Flash-Lite** | Input: $0.10, Output: $0.40 | **Input: $0.80, Output: $0.96 = $1.76** |
| **Mistral Large** | Input: $2.00, Output: $6.00 | **Input: $16, Output: $14.40 = $30.40** |
| **Groq (GPT OSS 120B)** | Input: $0.59, Output: $0.79 | **Input: $4.72, Output: $1.90 = $6.62** |

### **Monthly Cost Estimate (Paid Tier)**

**Scenario: Research deployment with 100k facts/month**
- **Gemini 2.0 Flash (primary)**: 60M tokens × ($0.10 + $0.40) = **$30/month**
- **Gemini 2.5 Flash (quality tasks)**: 20M tokens × ($0.30 + $2.50) = **$56/month**
- **Mistral Large (complex reasoning)**: 10M tokens × ($2.00 + $6.00) = **$80/month**
- **Groq (fast classification)**: 10M tokens × ($0.59 + $0.79) = **$13.80/month**
- **Total**: ~**$50-180/month** depending on provider mix

**Conclusion:** Free tiers across 5 providers provide excellent resilience. Even with paid tier, costs remain reasonable for academic research. Multi-provider strategy offers fallback options and task-specific optimization.

---

## **Migration Path**

### **Phase 1: Implement Multi-Provider Client (Week 4 - CIAR Scorer)**
- [ ] Create `src/utils/llm_client.py` with provider abstraction
- [ ] Implement Gemini provider wrappers (2.5 Flash, 2.0 Flash, 2.5 Flash-Lite)
- [ ] Implement Groq provider wrapper (Llama 3.3 70B, Mixtral)
- [ ] Implement Mistral provider wrapper (Large, Small)
- [ ] Add per-provider rate limit tracking and exponential backoff
- [ ] Create task-to-provider priority mapping with automatic fallback
- [ ] Add circuit breaker pattern for resilience (3 retries → next provider)
- [ ] Test with CIAR scoring using Groq as primary (ultra-fast)

### **Phase 2: Integration with Lifecycle Engines (Week 5-8)**
- [ ] Week 5: Integrate with Promotion Engine for fact extraction
- [ ] Week 6-7: Add episode consolidation and summarization
- [ ] Week 7: Implement bi-temporal model with LLM summarization
- [ ] Week 8: Test consolidation engine with multiple providers
- [ ] Add comprehensive unit tests for rate limit handling

### **Phase 3: Advanced Features (Week 9-10)**
- [ ] Week 9: Pattern mining with LLM support
- [ ] Week 10: Knowledge synthesis and distillation
- [ ] Monitor rate limits and token usage across all engines
- [ ] Document actual daily capacity in production
- [ ] Optimize provider priority based on real-world performance

### **Phase 4: Production Optimization (Week 11+)**
- [ ] Add structured output support for fact extraction
- [ ] Implement embedding generation with gemini-embedding-001
- [ ] Add cost monitoring and alerts
- [ ] Optimize prompt engineering for token efficiency
- [ ] Consider upgrading to paid tier if needed based on usage

---

## **Consequences**

### **Positive:**
- ✅ **Zero cost** for development and moderate production workloads (all providers have free tiers)
- ✅ **High reliability** with automatic fallbacks across 5 providers (3 Gemini + Mistral + Groq)
- ✅ **Provider diversity** - reduces vendor lock-in, enables resilience against single provider failures
- ✅ **Task-specific optimization** - match tasks to provider strengths (Groq for speed, Mistral for reasoning, Gemini for context)
- ✅ **Rate limit distribution** - spread load across providers to avoid single-provider saturation
- ✅ **Ultra-fast inference** with Groq (800 tok/sec) for real-time classification tasks
- ✅ **Massive context windows** (1M tokens with Gemini) ideal for processing long conversation histories
- ✅ **Strong reasoning** with Mistral Large for complex analysis and knowledge synthesis
- ✅ **Free embeddings** with gemini-embedding-001 for episode clustering

### **Negative:**
- ⚠️ **Complexity increase** - managing 5 providers vs. 1 (3 API keys, different SDKs)
- ⚠️ **RPM limitations** vary by provider (10-60 req/min) requiring per-provider pacing
- ⚠️ **Context window variance** - Groq models limited to 8k-128k vs Gemini's 1M
- ⚠️ **Free tier constraints** - Mistral free tier explicitly for evaluation/prototyping only
- ⚠️ **Fair use policies** - multiple providers means tracking multiple quota systems
- ⚠️ **Data usage** - Gemini free tier data may be used to improve Google products

### **Risks:**
- **Provider policy changes**: Any provider may reduce free tier limits (mitigation: 5 providers provides redundancy)
- **Rate limit saturation**: High concurrent usage may hit RPM limits across providers (mitigation: intelligent queue management, exponential backoff, priority routing)
- **Regional restrictions**: Some providers may not be available in all regions (mitigation: check availability, VPN fallback)
- **Model deprecations**: Older models may be deprecated (mitigation: abstract provider interface, easy to swap models)
- **Increased maintenance burden**: More providers means more SDK updates and compatibility testing (mitigation: unified interface abstraction)
- **Mistral free tier expiration**: Mistral free tier is evaluation-only; may need paid upgrade (mitigation: Gemini and Groq as primary providers)

---

## **Related Decisions**

- **ADR-005**: Multi-Tier LLM Provider Strategy with AgentRouter (superseded - AgentRouter not accessible)
- **ADR-003**: Four-Tier Cognitive Memory Architecture (defines memory layer requirements)
- **ADR-004**: CIAR Scoring Formula (defines certainty scoring requirements for LLM)
- **Implementation Plan**: Week 4-11 Phase 2 implementation (LLM integration timeline)

---

## **References**

- **Google Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **Gemini Models**: https://ai.google.dev/gemini-api/docs/models/gemini
- **Gemini Pricing**: https://ai.google.dev/gemini-api/docs/pricing
- **Gemini Rate Limits**: https://ai.google.dev/gemini-api/docs/rate-limits
- **Gemini Structured Output**: https://ai.google.dev/gemini-api/docs/structured-output
- **Gemini Embeddings**: https://ai.google.dev/gemini-api/docs/embeddings
- **Get API Key**: https://aistudio.google.com/apikey

---

## **Decision Log**

| **Date** | **Decision** | **Rationale** |
|----------|-------------|---------------|
| 2025-11-02 | Abandon AgentRouter integration | Persistent 401 authentication errors, inaccessible API |
| 2025-11-02 | Adopt Google Gemini as exclusive provider (3 models) | Unified API, generous free tier, massive context windows (1M tokens) |
| 2025-11-02 | Use Gemini 2.5 Flash as primary for quality tasks | Best reasoning capability for fact extraction, summarization, synthesis |
| 2025-11-02 | Use Gemini 2.0 Flash for high-volume tasks | Highest TPM (1M), higher RPM (15), good for batch processing |
| 2025-11-02 | Use Gemini 2.5 Flash-Lite for speed-critical tasks | Fastest model, ideal for CIAR certainty scoring and simple classification |
| 2025-11-02 | Implement circuit breaker pattern | Resilience against LLM failures, graceful degradation to rule-based extraction |
| 2025-11-02 | Plan for paid tier at ~$50-100/month | Budget for potential upgrade if free tier insufficient for production |
| **2025-12-29** | **Transition to Gemini 3 family** | **Adopt `gemini-3-flash-preview` (64K output tokens) and `gemini-3-pro-preview` as primary models. These support native structured output with `types.Schema` format, validated with fact extraction tests (see `tests/utils/test_gemini_structured_output.py`). Previous models (gemini-2.0-flash-exp, gemini-2.5-flash) deprecated. Groq's llama-3.3-70b-versatile excluded due to output reliability issues (truncated JSON, harmony format incompatibility). Also integrated Groq's `openai/gpt-oss-120b` reasoning model as fallback.** |

---

**Status:** ✅ Proposed  
**Next Review Date:** After Week 5 (Promotion Engine integration testing)  
**Approval Required From:** Lead Developer (Maksim)

---

## **Next Steps**

1. **Week 4** (CIAR Scorer): Implement basic LLM client for certainty scoring
2. **Week 5** (Promotion Engine): Full integration with fact extraction
3. **Week 6-8** (Consolidation): Episode summarization and dual-indexing
4. **Week 9-10** (Distillation): Knowledge synthesis and pattern mining
5. **Monitor usage**: Track tokens/day and RPM to stay within free tier
6. **Evaluate paid tier**: If approaching limits, upgrade to paid tier (~$50-100/month)
