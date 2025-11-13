# LLM Provider Connectivity Tests

Quick reference for testing LLM provider connectivity before implementing the multi-provider client.

## Overview

Test scripts located in `scripts/` directory validate API connectivity and basic functionality for all providers defined in **ADR-006: Free-Tier LLM Strategy**.

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys in `.env`:**
   ```bash
   # Copy example file
   cp .env.example .env
   
   # Edit .env and add your API keys:
   GOOGLE_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   MISTRAL_API_KEY=your_key_here
   ```

3. **Get API keys:**
   - **Google Gemini**: https://aistudio.google.com/app/apikey
   - **Groq**: https://console.groq.com/keys
   - **Mistral AI**: https://console.mistral.ai/api-keys/

## Test Scripts

### 1. Master Test (All Providers)

**Recommended:** Test all providers at once with comprehensive summary.

```bash
./scripts/test_llm_providers.py
```

**Features:**
- Checks API key configuration
- Tests all configured providers
- Provides comprehensive summary and recommendations
- Interactive (press Enter to start)

**Output:**
- Provider status (passed/failed/skipped)
- Count summary (X passed, Y failed, Z skipped)
- Recommendations based on results
- Next steps for implementation

---

### 2. Individual Provider Tests

Test providers individually for detailed diagnostics.

#### Google Gemini (3 models)

```bash
./scripts/test_gemini.py
```

**Tests:**
- Gemini 2.5 Flash (primary - complex tasks)
- Gemini 2.0 Flash (high-volume tasks)
- Gemini 2.5 Flash-Lite (fast tasks)

**Validates:**
- API key authentication
- Basic chat completion
- System instructions
- Token usage tracking
- Rate limit information

#### Groq (2 models)

```bash
./scripts/test_groq.py
```

**Tests:**
- Llama 3.1 8B Instant (ultra-fast)
- Llama 3.1 70B Versatile (complex reasoning)

**Validates:**
- API key authentication
- Basic chat completion
- System messages
- Token usage tracking
- **Inference speed measurement** (tokens/sec)
- Rate limit handling

#### Mistral AI (2 models)

```bash
./scripts/test_mistral.py
```

**Tests:**
- Mistral Small (fast tasks)
- Mistral Large (complex reasoning)

**Validates:**
- API key authentication
- Basic chat completion
- System messages
- Token usage tracking
- Rate limit handling (1 RPS with delays)

---

## Expected Results

### ✅ Success

All providers should return:
```
✅ All [Provider] tests passed!
```

**Example output:**
```
Prompt: What is 2+2? Answer in one short sentence.
Response: 2 + 2 = 4.

Token Usage:
  Prompt tokens: 15
  Response tokens: 8
  Total tokens: 23
```

### ❌ Failure Cases

#### 1. API Key Not Configured

```
❌ ERROR: [PROVIDER]_API_KEY not found in .env
   Get your API key from: [URL]
```

**Solution:** Add API key to `.env` file

#### 2. Invalid API Key

```
❌ ERROR: AuthenticationError
   Invalid API key or key not activated
```

**Solution:** 
- Verify API key is correct (no extra spaces)
- Check if key is activated on provider console
- Generate new key if needed

#### 3. Rate Limit Exceeded

```
❌ ERROR: This is a rate limit error.
   Too many requests in short time
```

**Solution:** Wait 60 seconds and retry

#### 4. Network/Connectivity Issues

```
❌ ERROR: ConnectionError
   Failed to connect to [provider] API
```

**Solution:**
- Check internet connectivity
- Verify no firewall blocking API requests
- Try VPN if regional restrictions apply

---

## Rate Limits (Free Tier)

| Provider | RPM | TPM | TPD | Context | Notes |
|----------|-----|-----|-----|---------|-------|
| **Gemini 2.5 Flash** | 10 | 250k | ∞ | 1M | Primary for complex tasks |
| **Gemini 2.0 Flash** | 15 | 1M | ∞ | 1M | High-volume processing |
| **Gemini 2.5 Flash-Lite** | 15 | 250k | ∞ | 1M | Fast classification |
| **Groq Llama 8B** | 30 | 200k | 1M+ | 8k | Ultra-fast (800 tok/sec) |
| **Groq Llama 70B** | 30 | 20k | 1M+ | 128k | Fast + reasoning |
| **Mistral Small** | 60 | ∞ | ∞ | 32k | 1 RPS limit |
| **Mistral Large** | 60 | ∞ | ∞ | 128k | 1 RPS limit, evaluation tier |

**Legend:** RPM = Requests/min, TPM = Tokens/min, TPD = Tokens/day

---

## Troubleshooting

### Problem: Script won't run (Permission Denied)

**Solution:**
```bash
chmod +x scripts/test_*.py
```

### Problem: Import errors (module not found)

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Problem: All tests fail with "API key not found"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify API keys are set (should show your keys)
grep "_API_KEY" .env

# If .env doesn't exist:
cp .env.example .env
# Edit .env and add your keys
```

### Problem: Mistral tests timeout

**Cause:** Free tier requires 1-second delay between requests

**Solution:** The test script already includes 2-second delays. If still failing:
- Wait longer between retries (60 seconds)
- Check Mistral console for rate limit status

### Problem: Groq "Daily token limit exceeded"

**Cause:** Free tier has 300k tokens/day cap

**Solution:**
- Wait until next day (resets at midnight UTC)
- Use lighter models (Llama 8B instead of 70B)
- Reduce max_tokens parameter in tests

---

## Next Steps

After successful connectivity tests:

1. ✅ **Verify at least 1 provider works** (minimum for development)
2. ✅ **Verify 2+ providers work** (recommended for resilience)
3. ⏳ **Implement multi-provider LLM client** (`src/utils/llm_client.py`)
4. ⏳ **Integrate with CIAR scorer** (Week 4)
5. ⏳ **Integrate with fact extraction** (Week 5)
6. ⏳ **Integrate with episode summarization** (Week 7)
7. ⏳ **Integrate with knowledge synthesis** (Week 10)

**See ADR-006** for detailed task-to-provider mappings and implementation architecture.

---

## References

- **ADR-006**: `/docs/ADR/006-free-tier-llm-strategy.md`
- **Provider Docs**:
  - Gemini: https://ai.google.dev/docs
  - Groq: https://console.groq.com/docs
  - Mistral: https://docs.mistral.ai/
- **Implementation Timeline**: `README.md` (Weeks 4-11)
