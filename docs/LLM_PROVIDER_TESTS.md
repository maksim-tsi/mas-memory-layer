> WARNING (OUTDATED, 2026-02-10)
> This document is preserved for archive and transparency purposes.
> It combines the former `LLM_PROVIDER_TESTS.md` and `LLM_PROVIDER_TEST_RESULTS.md`.
> See `docs/llm_provider_guide.md` for the current provider guide.

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
./.venv/bin/python scripts/test_llm_providers.py
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

---

# LLM Provider Test Results (Archived)

# LLM Provider Test Results - November 2, 2025

## Test Execution Summary (Updated: 2025-12-27)

**Command:** `./scripts/test_llm_providers.py`

**Results:**
- ✅ **Mistral AI** - PASSED (both Small and Large models working)
- ✅ **Google Gemini** - PASSED (2.5 Flash, 2.0 Flash, 2.5 Flash-Lite)
- ⚠️  **Groq** - PARTIAL (8B model works, 70B model deprecated → use 3.3 70B)

---

## Issues & Resolutions

### 1. ✅ FIXED: Groq Model Deprecated

**Issue:**
```
Error: The model `llama-3.1-70b-versatile` has been decommissioned
```

**Root Cause:** Groq updated their model from Llama 3.1 70B to Llama 3.3 70B

**Resolution:**
- Updated test script: `llama-3.1-70b-versatile` → `llama-3.3-70b-versatile`
- Updated ADR-006 documentation
- Updated requirements.txt
- Model naming convention: `GROQ_LLAMA_3_1_70B` → `GROQ_LLAMA_3_3_70B`

**Status:** ✅ Fixed in codebase, ready for retest

---

### 2. ✅ RESOLVED: Google Gemini API Key

**Issue:**
```
400 INVALID_ARGUMENT
API key not valid. Please pass a valid API key.
Reason: API_KEY_INVALID
```

**Resolution:**
- Generated a valid Gemini API key and retested.
- `/home/max/code/mas-memory-layer/.venv/bin/python scripts/test_gemini.py` on 2025-12-27: all three models PASSED.

**Status:** ✅ Resolved

---

## Current Provider Status (2025-12-27)

| Provider | Status | Models Tested | Notes |
|----------|--------|---------------|-------|
| **Mistral AI** | ✅ WORKING | Small, Large | Both models responding correctly |
| **Groq** | ⚠️ PARTIAL | 8B ✅, 70B ❌ | 8B works; use `llama-3.3-70b-versatile` for updated 70B model |
| **Google Gemini** | ✅ WORKING | 2.5 Flash, 2.0 Flash, 2.5 Flash-Lite | All models passing after key refresh |

---

## Next Steps

### Immediate (Before Next Test Run)

1. **Fix Google Gemini API Key:**
   - Generate fresh key from AI Studio
   - Update `.env` file
   - Verify no extra spaces/characters

2. **Retest All Providers:**
   ```bash
   ./scripts/test_llm_providers.py
   ```

### Expected After Fixes

| Provider | Expected Result |
|----------|-----------------|
| Mistral AI | ✅ PASS (already working) |
| Groq | ✅ PASS (both 8B and 3.3 70B models) |
| Google Gemini | ✅ PASS (all 3 models: 2.5 Flash, 2.0 Flash, 2.5 Flash-Lite) |

**Target:** 3/3 providers working = Full resilience + task optimization

---

## Successful Test Output Example

From Mistral AI (working correctly):
```
Testing Mistral Small (Fast Tasks)
✓ Response received
Prompt: What is 2+2? Answer in one short sentence.
Response: 2+2 is 4.

Token Usage:
  Prompt tokens: 16
  Response tokens: 8
  Total tokens: 24

✅ Mistral Small (Fast Tasks) test passed!
```

This is what we expect from all providers once fixed.

---

## Documentation Updates

Files updated to reflect Groq model change:
- ✅ `scripts/test_groq.py` - Model name updated
- ✅ `docs/ADR/006-free-tier-llm-strategy.md` - ADR updated with 3.3 70B
- ✅ `requirements.txt` - Comment updated with correct model

No code changes needed for Gemini - just API key replacement.

---

**Date:** November 2, 2025  
**Tested By:** Automated test suite  
**Next Test:** After Google Gemini API key refresh
