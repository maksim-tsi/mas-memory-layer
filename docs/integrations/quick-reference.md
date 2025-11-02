# AgentRouter Quick Reference Card

**Purpose:** Fast lookup for common LLM operations during Phase 2 implementation

---

## 🔑 Configuration

```bash
# Environment (.env)
AGENTROUTER_API_KEY=ar_your_key_here
LLM_PROVIDER=agentrouter
LLM_BASE_URL=https://agentrouter.org/v1
```

## 📦 Import

```python
from src.utils.llm_client import LLMClient

# Initialize
llm = LLMClient()
```

## 🎯 Common Operations

### Extract Facts (Week 5)
```python
turns = ["User: I prefer Hamburg", "Agent: Hamburg has capacity"]
facts = await llm.extract_facts(turns)
# Uses: DeepSeek-V3 (Tier 2) - $0.38/1M tokens
```

### Score CIAR Certainty (Week 4)
```python
certainty = await llm.score_certainty("User explicitly stated preference")
# Uses: GPT-5 Mini (Tier 1) - $0.33/1M tokens
# Returns: 0.0-1.0
```

### Summarize Episode (Week 7)
```python
facts = [{"fact_type": "preference", "content": "..."}]
summary = await llm.summarize_episode(facts, max_length=500)
# Uses: GLM-4.6 (Tier 2) - $0.31/1M tokens
```

### Synthesize Knowledge (Week 10)
```python
episodes = [{"summary": "..."}, {"summary": "..."}]
knowledge = await llm.synthesize_knowledge(episodes)
# Uses: GPT-5 (Tier 3) - $3.44/1M tokens
```

### Custom Prompt
```python
response = await llm.generate(
    prompt="Your prompt here",
    model="gpt-5-mini",  # Optional: specify model
    task_type="fact_extraction",  # Or let it auto-select
    temperature=0.3
)
```

## 💰 Cost Tracking

```python
# Check daily cost
cost = llm.get_daily_cost()
print(f"Today: ${cost:.2f}")

# Check budget status
if llm.check_budget(daily_budget=3.0):
    print("⚠️ Over budget!")
```

```bash
# Run daily cost report
python scripts/check_llm_costs.py
```

## 🎨 Model Selection

| Task | Model | Tier | Cost/1M |
|------|-------|------|---------|
| **CIAR Certainty** | gpt-5-mini | 1 | $0.33 |
| **Entity Extract** | claude-3-5-haiku | 1 | $1.00 |
| **Fact Extract** | deepseek-v3 | 2 | $0.38 |
| **Episode Summary** | glm-4.6 | 2 | $0.31 |
| **Knowledge Synth** | gpt-5 | 3 | $3.44 |
| **Critical Accuracy** | claude-3-5-sonnet | 3 | $6.00 |

## 🔧 Explicit Model Selection

```python
# Override automatic selection
facts = await llm.extract_facts(
    turns,
    model="claude-3-5-sonnet"  # Use premium for critical extraction
)

response = await llm.generate(
    prompt,
    model="gpt-5"  # Force Tier 3 for complex reasoning
)
```

## 🛡️ Circuit Breaker Pattern (Week 5)

```python
from src.memory.circuit_breaker import CircuitBreaker

cb = CircuitBreaker(failure_threshold=5, timeout=60)

async def extract_with_fallback(turns):
    if cb.is_open():
        return rule_based_extraction(turns)  # Fallback
    
    try:
        facts = await llm.extract_facts(turns)
        cb.record_success()
        return facts
    except Exception as e:
        cb.record_failure()
        return rule_based_extraction(turns)  # Fallback
```

## 📊 Budget Targets

| Metric | Target |
|--------|--------|
| **Daily** | $3.00 |
| **Weekly** | $15-20 |
| **Monthly** | $60-80 |
| **Per Fact** | <$0.002 |
| **Per Episode** | <$0.01 |
| **Per Knowledge** | <$0.05 |

## ⚠️ Common Errors

### API Key Not Found
```bash
echo "AGENTROUTER_API_KEY=ar_your_key" >> .env
```

### Timeout
```python
# Increase in config/llm_config.yaml
llm:
  timeout_seconds: 60  # Default: 30
```

### Rate Limit
```python
import asyncio
await asyncio.sleep(1)  # Add delay between calls
```

### JSON Parse Error
```python
# Already handled - returns [] on failure
# Check logs for details
```

## 🧪 Testing

```bash
# Full integration test
python scripts/test_llm_client.py

# Verify config
python scripts/verify_llm_config.py

# Check costs
python scripts/check_llm_costs.py
```

## 📚 Documentation

- **Full Guide:** [docs/integrations/agentrouter-setup-guide.md](agentrouter-setup-guide.md)
- **Architecture:** [docs/ADR/005-multi-tier-llm-provider-strategy.md](../ADR/005-multi-tier-llm-provider-strategy.md)
- **Implementation Plan:** [docs/plan/implementation-plan-02112025.md](../plan/implementation-plan-02112025.md)

## 🔗 Links

- **Dashboard:** https://agentrouter.org/dashboard
- **API Docs:** https://agentrouter.org/docs
- **Support:** support@agentrouter.org

---

**Version:** 1.0  
**Updated:** November 2, 2025
