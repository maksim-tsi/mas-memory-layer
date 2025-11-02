# LLM Integration Documentation

This directory contains documentation for Large Language Model (LLM) integrations in the Multi-Layered Memory System project.

## Documents

### Primary Integration Guide
📄 **[AgentRouter Setup Guide](agentrouter-setup-guide.md)**
- Complete step-by-step integration guide
- Account setup and configuration
- Code implementation examples
- Testing and troubleshooting
- Production deployment checklist

**Target Audience:** Developers implementing Phase 2  
**Time to Complete:** 2-3 hours for full setup and testing

## Architecture Decision Records

See related ADRs for architectural context:
- **[ADR-005: Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)** - Why AgentRouter was selected and model tier strategy

## Quick Start

If you're already familiar with LLM integration and just need to get started:

### 1. Get API Key
```bash
# Register at https://agentrouter.org
# Get API key from dashboard
```

### 2. Configure Environment
```bash
# Add to .env file
echo "AGENTROUTER_API_KEY=ar_your_key_here" >> .env
```

### 3. Install Dependencies
```bash
pip install langchain langchain-openai openai pydantic python-dotenv
```

### 4. Test Integration
```bash
python scripts/test_llm_client.py
```

### 5. Start Implementation
See **Week 4** in the [Implementation Plan](../plan/implementation-plan-02112025.md)

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
