# LLM Integration Documentation

This directory contains documentation for Large Language Model (LLM) integrations in the Multi-Layered Memory System project.

## GoodAI LTM Benchmark Integration (Phase 5)

The Phase 5 evaluation pipeline integrates the GoodAI LTM Benchmark with the MAS Memory Layer via
the YAAM API Wall. YAAM exposes OpenAI-compatible `/v1/chat/completions` plus operational health
endpoints. Benchmark-facing model interfaces now live in the external
`goodai-ltm-benchmark-yaam` repository and apply session IDs through HTTP headers for database
isolation.

For installation, configuration, and execution guidance, see
[docs/integrations/goodai-benchmark-setup.md](goodai-benchmark-setup.md).

## Phoenix Tracing Strategy

The repository-level tracing strategy for YAAM and the GoodAI benchmark integration is documented in
[docs/RFC/phoenix-tracing-rfc.md](../RFC/phoenix-tracing-rfc.md).

The reusable execution and evidence-collection procedure for live Phoenix experiments is documented
in [docs/runbooks/phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md).

## ✅ Provider Status

**Multi-Provider Strategy: SELECTED**

Current V2 API runtime uses OpenRouter as the primary path, with additional providers available
for fallback or specialized workloads.

- **OpenRouter** - Primary V2 provider for generation and embeddings
- **Google Gemini** - Secondary/fallback provider
- **Groq** - Low-latency fallback provider
- **Mistral AI** - Reasoning-focused fallback provider

**Implementation Status:** Ready for Phase 2 integration (Week 4-11)

## Architecture Decision Records

See related ADRs for LLM provider strategy:
- **[ADR-006: Free-Tier LLM Provider Strategy](../ADR/006-free-tier-llm-strategy.md)** ✅ **CURRENT** - Multi-provider strategy with 5 models
- **[ADR-005: Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)** - ~~Superseded~~ (AgentRouter not accessible)

## Quick Start

### 1. Get API Keys

Register and get free API keys from all providers:
```bash
# OpenRouter
# Visit: https://openrouter.ai/keys

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
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_MODEL=tencent/hy3-preview
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
EMBEDDING_DIMENSIONS=4096
MAS_L3_COLLECTION=episodes_qwen_v2
MAS_L4_COLLECTION=knowledge_base_v2
MAS_V2_MODE=true
GOOGLE_API_KEY=your-google-api-key-here
GROQ_API_KEY=your-groq-api-key-here
MISTRAL_API_KEY=your-mistral-api-key-here
EOF
```

### 3. Install Dependencies

```bash
poetry install --with test,dev
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
| **V2 Chat/Reasoning** | OpenRouter (`tencent/hy3-preview`) | Gemini | Groq/Mistral | Unified API path with stable routing |
| **V2 Embeddings** | OpenRouter (`qwen/qwen3-embedding-8b`) | Gemini embeddings | - | Aligns L3 vector dimensions to 4096 |
| **Development/Testing** | Groq (Llama 8B) | OpenRouter | Gemini | Fast turnaround with fallback coverage |

## V2 Verification Sequence

After configuration changes, validate runtime behavior with:

```bash
docker compose up -d --build mas-agent
make healthcheck
set -a && . ./.env && set +a && ./.venv/bin/python scripts/debug/check_tier_collection.py
```

Expected introspection output pattern:
- `Adapter collection: episodes_v2 vector_size: 1024`
- `Tier collection: episodes_v2 vector_size: 1024`

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

**Last Updated:** April 17, 2026  
**Maintained By:** Development Team
