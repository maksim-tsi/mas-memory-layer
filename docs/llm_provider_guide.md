# LLM Provider Guide

**Status:** Active reference for provider setup and connectivity checks

This guide consolidates the previous LLM provider docs into a single source. It reflects the
current codebase. For model names, always treat the test scripts as the source of truth:

- `scripts/test_gemini.py`
- `scripts/test_groq.py`
- `scripts/test_mistral.py`
- `scripts/test_llm_providers.py`

Model identifiers change faster than documentation. When in doubt, check the scripts first.

---

## Prerequisites

1. Install dependencies using the project environment (Poetry + `.venv`).
2. Ensure API keys are available in your environment or `.env`:
   - `GOOGLE_API_KEY`
   - `GROQ_API_KEY`
   - `MISTRAL_API_KEY`

Note: The repository uses `GOOGLE_API_KEY` (not `GEMINI_API_KEY`).

---

## Current Model Targets (from scripts)

### Google Gemini
From `scripts/test_gemini.py`:
- `gemini-3-flash-preview`
- `gemini-3-pro-preview`

### Groq
From `scripts/test_groq.py`:
- `llama-3.1-8b-instant`
- `openai/gpt-oss-120b`

### Mistral
From `scripts/test_mistral.py`:
- `mistral-small-latest`
- `mistral-large-latest`

---

## Connectivity Tests

### Master Test (All Providers)

```bash
./.venv/bin/python scripts/test_llm_providers.py
```

### Individual Provider Tests

```bash
./.venv/bin/python scripts/test_gemini.py
./.venv/bin/python scripts/test_groq.py
./.venv/bin/python scripts/test_mistral.py
```

If you are on the managed remote host, use the absolute interpreter path documented in
`docs/environment-guide.md`.

---

## Troubleshooting Notes

- Missing key errors mean the environment variables are not set or `.env` is absent.
- Authentication errors typically indicate an expired or revoked key.
- Rate limit errors can be resolved by waiting and retrying later.

---

## Archived References (Outdated)

These are kept for historical context only:
- `docs/llm_provider_setup_complete.md`
- `docs/llm_provider_tests.md`
