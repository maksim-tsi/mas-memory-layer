# 2026-02-22 GoodAI Smoke5 Pure-LLM Baselines (Groq + Gemini + Mistral)

Date: 2026-02-22

## Scope
Run GoodAI Smoke5 with pure-LLM (no YAAM) for Groq, Gemini, and Mistral. All runs use the same dataset definitions copied from the Groq YAAM run to avoid regeneration.

## Run Configuration
- Configuration: `benchmarks/goodai-ltm-benchmark/configurations/mas_variant_a_smoke_5.yml`
- Mode: isolated (`-i`)
- Max prompt size: 32000 (`-m 32000`)

## Runs and Artifacts

### Groq (completed)
- Run name: `goodai__smoke5__baseline=llm__provider=groq__model=openai-gpt-oss-120b__agent=pure-llm__20260222_202058 (isolated)`
- Run folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=groq__model=openai-gpt-oss-120b__agent=pure-llm__20260222_202058 (isolated)`
- Results folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=groq__model=openai-gpt-oss-120b__agent=pure-llm__20260222_202058 (isolated)/results/GroqChatSession`
- Status: completed
- Notes:
  - Ran with `GROQ_MAX_OUTPUT_TOKENS=512` to reduce token usage per request.
  - Prior attempts failed due to Groq TPD rate limit. This run used the refreshed key successfully.

### Gemini (completed)
- Run name: `goodai__smoke5__baseline=llm__provider=gemini__model=gemini-3-flash-preview__agent=pure-llm__20260222_200909 (isolated)`
- Run folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=gemini__model=gemini-3-flash-preview__agent=pure-llm__20260222_200909 (isolated)`
- Results folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=gemini__model=gemini-3-flash-preview__agent=pure-llm__20260222_200909 (isolated)/results/GeminiProInterface`
- Status: completed

### Mistral (completed)
- Run name: `goodai__smoke5__baseline=llm__provider=mistral__model=mistral-medium-2508__agent=pure-llm__20260222_201718 (isolated)`
- Run folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=mistral__model=mistral-medium-2508__agent=pure-llm__20260222_201718 (isolated)`
- Results folder: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__baseline=llm__provider=mistral__model=mistral-medium-2508__agent=pure-llm__20260222_201718 (isolated)/results/MistralChatSession`
- Status: completed
- Note: An earlier attempt with `mistral-large` failed with `Invalid model: mistral-large`. The correct model is `mistral-medium-2508`.

## Notes
- All pure-LLM runs are isolated and do not use YAAM memory or retrieval. Observed latency is provider-side, not storage or retrieval.
- Definitions copied from Groq YAAM run:
  - `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=groq__model=openai-gpt-oss-120b__promotion=disabled__agent=full__v1-min-skillwiring__20260222_152232/definitions`

## Proposed Next Steps
1. Generate HTML reports for the pure-LLM baselines (Groq/Gemini/Mistral) if needed for side-by-side comparison with YAAM runs.
2. Compile a comparison summary across YAAM vs pure-LLM for each provider (accuracy + qualitative failure modes).
