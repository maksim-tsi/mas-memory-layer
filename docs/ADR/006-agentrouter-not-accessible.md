# ADR-006: AgentRouter Provider Inaccessible - Alternative LLM Strategy Required

**Status:** Accepted  
**Date:** 2025-11-02  
**Supersedes:** ADR-005 (Multi-Tier LLM Provider Strategy)

## Context

During Phase 2 implementation setup, we attempted to integrate AgentRouter (https://agentrouter.org) as our multi-model LLM provider based on the analysis documented in ADR-005. AgentRouter was selected for:

- **Cost efficiency**: 85% savings vs direct premium API usage ($60-80/month vs $350/month)
- **Multi-provider redundancy**: Single API for OpenAI, Anthropic, Google, DeepSeek, Zhipu models
- **OpenAI API compatibility**: Drop-in replacement requiring minimal code changes
- **Intelligent routing**: Automatic model selection via "gpt-5" routing model

## Problem

After extensive testing and troubleshooting, we encountered persistent authentication failures:

### Technical Issues Encountered

1. **401 UNAUTHENTICATED errors** on all API requests
   - Tested with correct base URL: `https://agentrouter.org/v1`
   - Tested with documented environment variables: `AGENT_ROUTER_TOKEN`, `OPENAI_API_KEY`
   - Tested with properly formatted Bearer tokens (sk-xxx format)
   - Verified with multiple methods: curl, Python OpenAI SDK, custom scripts

2. **Documentation gaps**
   - Main documentation at https://docs.agentrouter.org/en/ focused on specific IDE integrations (Codex, Claude Code)
   - Limited information on direct API access authentication
   - Unclear distinction between system tokens vs API tokens
   - No clear guidance on account activation or token validation process

3. **Access barriers**
   - Unable to verify token validity through their console
   - No clear error messages indicating root cause (invalid token, unactivated account, IP restrictions, etc.)
   - Possible service availability issues or regional restrictions

### Investigation Summary

- ✓ Verified request format matches OpenAI specification
- ✓ Tested multiple environment variable names per their docs
- ✓ Confirmed token format (sk- prefix, 40+ characters)
- ✓ Tested with both direct curl and Python SDK
- ✗ All requests returned 401 UNAUTHENTICATED
- ✗ Unable to establish working authentication

## Decision

**We will NOT use AgentRouter as our LLM provider.**

The integration attempt is abandoned due to:
1. **Blocking authentication issues** preventing any API usage
2. **Time constraints**: Phase 2 implementation (Week 4-11) cannot be delayed
3. **Uncertainty around access**: Unclear if service is generally available or requires special access
4. **Risk to project timeline**: Cannot build Phase 2 components on inaccessible infrastructure

## Alternative Approaches

We need to select a new LLM provider strategy. Options:

### Option 1: Direct Provider APIs (Recommended for MVP)
**Use OpenAI directly for initial implementation**

- ✅ **Immediate availability**: API keys work instantly
- ✅ **Proven reliability**: Industry standard with 99.9% uptime
- ✅ **Comprehensive documentation**: Well-documented with many examples
- ✅ **Quick start**: Can begin Phase 2 implementation immediately
- ⚠️ **Higher cost**: ~$350/month for premium models (vs $60-80 planned)
- ⚠️ **Single vendor**: No automatic fallback

**Implementation:**
```python
# Direct OpenAI integration
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = await client.chat.completions.create(
    model="gpt-4o-mini",  # Use budget model where possible
    messages=[{"role": "user", "content": prompt}]
)
```

### Option 2: LiteLLM (Recommended for Production)
**Use LiteLLM as unified multi-provider interface**

- ✅ **Multi-provider support**: OpenAI, Anthropic, Google, Azure, etc.
- ✅ **Cost optimization**: Built-in request routing and caching
- ✅ **OpenAI-compatible**: Same API interface as AgentRouter would have provided
- ✅ **Self-hosted option**: Can run own proxy for control
- ✅ **Active development**: Well-maintained OSS project
- ⚠️ **Additional dependency**: Need to manage LiteLLM proxy
- ⚠️ **Setup overhead**: More complex than direct API

**Resources:**
- GitHub: https://github.com/BerriAI/litellm
- Docs: https://docs.litellm.ai/

### Option 3: Multiple Direct Providers
**Implement fallback logic with direct provider SDKs**

- ✅ **No intermediary**: Direct control over each provider
- ✅ **Maximum flexibility**: Can optimize per-provider
- ✅ **No routing dependency**: Not blocked by proxy issues
- ⚠️ **More code complexity**: Need to handle multiple SDKs
- ⚠️ **Manual fallback logic**: Must implement routing ourselves

### Option 4: Local Models (Ollama)
**Use local models for development, cloud for production**

- ✅ **Zero cost for development**: Run models locally
- ✅ **Privacy**: No data leaves development environment
- ✅ **Fast iteration**: No API rate limits
- ⚠️ **Performance gap**: Local models less capable than GPT-4/Claude
- ⚠️ **Different deployment**: Need separate config for prod
- ⚠️ **Hardware requirements**: Need GPU for reasonable performance

## Recommended Path Forward

### Immediate (Week 4): Direct OpenAI
1. Use OpenAI API directly for Phase 2 implementation
2. Start with budget models (gpt-4o-mini) to control costs
3. Use premium models (gpt-4o) only for complex tasks requiring high quality

### Short-term (Week 6-8): Evaluate LiteLLM
1. Set up LiteLLM proxy in parallel with development
2. Test with multiple providers (OpenAI, Anthropic, Google)
3. Migrate to LiteLLM if testing proves successful

### Long-term (Week 12+): Production Optimization
1. Implement cost monitoring and model selection logic
2. Add fallback chains for reliability
3. Optimize model usage based on actual costs and performance

## Cost Management Strategy

To mitigate higher costs with direct OpenAI:

1. **Aggressive model tiering**:
   - Tier 1 (gpt-4o-mini): Simple extractions, classifications, confirmations
   - Tier 2 (gpt-4o): Complex reasoning, summarization, synthesis
   
2. **Prompt optimization**:
   - Minimize token usage through concise prompts
   - Use function calling instead of text parsing where possible
   
3. **Caching and deduplication**:
   - Cache common LLM responses
   - Avoid redundant API calls
   
4. **Budget alerts**:
   - Set OpenAI billing alerts at $100, $200, $300
   - Monitor daily usage and costs
   
5. **Development constraints**:
   - Use smaller test datasets during development
   - Implement mock responses for unit tests

## Implementation Changes

### Files to Remove
- `config/llm_config.yaml` - AgentRouter-specific configuration
- `scripts/validate_agentrouter_models.py` - AgentRouter validation script
- `scripts/test_agentrouter_models.py` - AgentRouter connectivity tests
- `scripts/setup_agentrouter.sh` - AgentRouter setup script
- `docs/integrations/agentrouter-setup-guide.md` - Integration guide
- `docs/integrations/TROUBLESHOOTING.md` - AgentRouter troubleshooting
- AgentRouter references in `docs/integrations/README.md`
- AgentRouter references in `docs/integrations/quick-reference.md`

### Files to Update
- `README.md` - Remove AgentRouter references, add note about provider selection
- `docs/ADR/005-multi-tier-llm-provider-strategy.md` - Mark as superseded
- `.env` - Remove AGENT_ROUTER_TOKEN, AGENTROUTER_API_KEY

### Files to Create
- `docs/integrations/openai-setup-guide.md` - Direct OpenAI integration guide
- `config/llm_config.yaml` - New config for direct provider approach
- Environment variable documentation for OPENAI_API_KEY

## Consequences

### Positive
- ✅ **Unblocked**: Can proceed with Phase 2 implementation immediately
- ✅ **Proven infrastructure**: Using battle-tested OpenAI API
- ✅ **Simpler architecture**: Direct API calls easier to debug
- ✅ **Flexibility**: Can switch providers later with LiteLLM

### Negative
- ⚠️ **Higher initial costs**: ~$350/month vs $60-80 planned with AgentRouter
- ⚠️ **Single provider risk**: No automatic fallback without additional work
- ⚠️ **Wasted effort**: Time spent on AgentRouter evaluation and setup

### Neutral
- 📋 **Timeline impact**: Minimal delay (1-2 days for OpenAI setup vs continued AgentRouter debugging)
- 📋 **Architecture pivot**: Still using OpenAI-compatible API, so LiteLLM migration is straightforward
- 📋 **Learning**: Better understanding of LLM provider landscape

## Lessons Learned

1. **Validate authentication early**: Test API access before deep integration
2. **Have backup plans**: Critical dependencies should have alternatives identified
3. **Consider maturity**: Newer services may have access/documentation issues
4. **Direct > Proxy for MVP**: Start simple, optimize later

## Future Considerations

- Monitor AgentRouter service status and documentation improvements
- Revisit AgentRouter if authentication issues are resolved and documented
- Consider LiteLLM as production-ready alternative providing similar benefits
- Evaluate other aggregator services: OpenRouter, Portkey, etc.

## References

- ADR-005: Multi-Tier LLM Provider Strategy (superseded)
- AgentRouter documentation: https://docs.agentrouter.org/en/
- LiteLLM documentation: https://docs.litellm.ai/
- OpenAI API documentation: https://platform.openai.com/docs/api-reference
