# LLM Integration Documentation

This directory contains documentation for Large Language Model (LLM) integrations in the Multi-Layered Memory System project.

## GoodAI LTM Benchmark Integration (Phase 5)

The Phase 5 evaluation pipeline integrates the GoodAI LTM Benchmark with the MAS Memory Layer via
FastAPI wrapper services. The wrapper exposes `/run_turn`, `/sessions`, `/memory_state`, and `/health`
endpoints and is configured per agent type (full, rag, full_context). Benchmark-facing model
interfaces are implemented in `benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py` and
apply session prefixing (`full:`, `rag:`, `full_context:`) for database isolation.

For installation, configuration, and execution guidance, see
[docs/integrations/goodai-benchmark-setup.md](goodai-benchmark-setup.md).

## Phoenix Tracing Strategy

The repository-level tracing strategy for YAAM and the GoodAI benchmark integration is documented in
[docs/RFC/phoenix-tracing-rfc.md](../RFC/phoenix-tracing-rfc.md).

The reusable execution and evidence-collection procedure for live Phoenix experiments is documented
in [docs/runbooks/phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md).

## ✅ Provider Status

**Multi-Provider Strategy: SELECTED**

5 providers with automatic fallback and task-specific optimization:
- **Google Gemini** (3 models) - Primary provider, massive context (1M tokens)
- **Groq** (2 models) - Ultra-fast inference (250-800 tok/sec)
- **Mistral AI** (2 models) - Complex reasoning and analysis

**Implementation Status:** Ready for Phase 2 integration (Week 4-11)

## Architecture Decision Records

See related ADRs for LLM provider strategy:
- **[ADR-006: Free-Tier LLM Provider Strategy](../ADR/006-free-tier-llm-strategy.md)** ✅ **CURRENT** - Multi-provider strategy with 5 models
- **[ADR-005: Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)** - ~~Superseded~~ (AgentRouter not accessible)

## Quick Start

### 1. Get API Keys

Register and get free API keys from all providers:
```bash
# Google Gemini
# Visit: https://aistudio.google.com/apikey

# Groq
# Visit: https://console.groq.com/keys

# Mistral AI
# Visit: https://console.mistral.ai/api-keys/
```

### 2. Configure Environment

```bash
# Add to .env file (or copy from .env.example)
cat >> .env << EOF
GOOGLE_API_KEY=your-google-api-key-here
GROQ_API_KEY=your-groq-api-key-here
MISTRAL_API_KEY=your-mistral-api-key-here
EOF
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
# Installs: google-genai, groq, mistralai
```

### 4. Test Connectivity

```bash
# Test all providers at once (recommended)
./scripts/test_llm_providers.py

# Or test individually
./scripts/test_gemini.py
./scripts/test_groq.py
./scripts/test_mistral.py
```

**See [LLM Provider Tests Documentation](../llm_provider_guide.md)** for detailed testing guide.

### 5. Start Implementation

See **Week 4-5** in the [Implementation Plan](../plan/implementation_master_plan_version-0.9.md) for CIAR Scorer and Fact Extraction integration

## Provider Selection Quick Reference

| Task | Primary Provider | Fallback 1 | Fallback 2 | Rationale |
|------|------------------|------------|------------|-----------|
| **CIAR Scoring** | Groq (Llama 8B) | Gemini 2.5 Flash-Lite | Gemini 2.5 Flash | Ultra-fast classification (800 tok/sec) |
| **Fact Extraction** | Gemini 2.5 Flash | Mistral Large | Gemini 2.0 Flash | Best quality + 1M context |
| **Episode Summary** | Gemini 2.5 Flash | Gemini 2.0 Flash | Mistral Large | Narrative generation |
| **Knowledge Synthesis** | Mistral Large | Gemini 2.5 Flash | Gemini 2.0 Flash | Complex reasoning |
| **Pattern Mining** | Gemini 2.5 Flash | Mistral Large | Groq (GPT OSS 120B) | Pattern recognition |
| **Development/Testing** | Groq (Llama 8B) | Gemini 2.5 Flash-Lite | - | Instant feedback (800 tok/sec) |

**See ADR-006** for detailed task-to-provider mappings and fallback logic.

## Cost Targets

- **Daily Budget:** $3.00 (≈ $90/month pace)
- **Monthly Budget:** $60-80 (with buffer)
- **Per Operation:**
  - Fact extraction: <$0.002 per fact
  - Episode summary: <$0.01 per episode
  - Knowledge synthesis: <$0.05 per document

## Support

**Technical Issues:**
- Review troubleshooting section in [Setup Guide](agentrouter-setup-guide.md#10-troubleshooting)
- Check [ADR-005](../ADR/005-multi-tier-llm-provider-strategy.md) for architectural decisions

**AgentRouter Issues:**
- Dashboard: https://agentrouter.org/dashboard
- Support: support@agentrouter.org

---

**Last Updated:** November 2, 2025  
**Maintained By:** Development Team
