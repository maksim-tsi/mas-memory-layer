# LLM Integration Documentation

This directory contains documentation for Large Language Model (LLM) integrations in the Multi-Layered Memory System project.

## ⚠️ Provider Status

**AgentRouter Integration: ABANDONED**

AgentRouter was initially selected (see ADR-005) but encountered persistent authentication issues during setup. Integration attempt abandoned on 2025-11-02. See **[ADR-006](../ADR/006-agentrouter-not-accessible.md)** for details.

**Current Status:** Selecting alternative LLM provider for Phase 2 implementation.

## Architecture Decision Records

See related ADRs for LLM provider strategy:
- **[ADR-006: AgentRouter Not Accessible - Alternative Strategy Required](../ADR/006-agentrouter-not-accessible.md)** - Why AgentRouter was abandoned, alternative options
- **[ADR-005: Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)** - ~~Superseded~~ Original AgentRouter evaluation

## Next Steps

LLM provider selection in progress. Options being evaluated:
1. **Direct OpenAI** - Immediate availability, higher cost
2. **LiteLLM** - Multi-provider proxy, requires setup
3. **Multiple Direct Providers** - Maximum flexibility, more complexity
4. **Local Models (Ollama)** - Development only, zero cost

See ADR-006 for detailed analysis and recommendations

## Model Selection Quick Reference

| Task | Model | Cost/1M tokens | When to Use |
|------|-------|---------------|-------------|
| CIAR Scoring | GPT-5 Mini | $0.33 | High frequency, simple classification |
| Fact Extraction | DeepSeek-V3 | $0.38 | Primary workload, balanced quality/cost |
| Episode Summary | GLM-4.6 | $0.31 | Narrative generation |
| Knowledge Synthesis | GPT-5 | $3.44 | Complex reasoning, low frequency |

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
