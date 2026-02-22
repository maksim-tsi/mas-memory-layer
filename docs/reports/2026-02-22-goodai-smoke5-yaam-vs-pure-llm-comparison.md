# 2026-02-22 GoodAI Smoke5: YAAM vs Pure-LLM Comparison

Date: 2026-02-22

## Scope
Compare YAAM (mas-memory with skills) runs vs pure-LLM baselines for the same Smoke5 suite across providers. This is an artifact-driven comparison using run folders + HTML reports.

## Method
- YAAM runs: RemoteMASAgentSession via API Wall, `promotion=disabled`, `agent=full`, `v1-min-skillwiring`.
- Pure-LLM runs: baseline chat sessions (no YAAM memory or retrieval), isolated mode (`-i`), `-m 32000`.
- Datasets: Smoke5 (Instruction Recall, Prospective Memory, Restaurant, Spy Meeting, Trigger Response).
- Definitions were copied from the Groq YAAM run into pure-LLM runs to prevent regeneration drift.

## Run Inventory

### YAAM (with memory)
- Groq: `goodai__smoke5__provider=groq__model=openai-gpt-oss-120b__promotion=disabled__agent=full__v1-min-skillwiring__20260222_152232`
- Gemini: `goodai__smoke5__provider=gemini__model=gemini-3-flash-preview__promotion=disabled__agent=full__v1-min-skillwiring__20260222_190933`
- Mistral: `goodai__smoke5__provider=mistral__model=mistral-medium-2508__promotion=disabled__agent=full__v1-min-skillwiring__20260222_203516`

### Pure-LLM (no memory)
- Groq: `goodai__smoke5__baseline=llm__provider=groq__model=openai-gpt-oss-120b__agent=pure-llm__20260222_202058 (isolated)`
- Gemini: `goodai__smoke5__baseline=llm__provider=gemini__model=gemini-3-flash-preview__agent=pure-llm__20260222_200909 (isolated)`
- Mistral: `goodai__smoke5__baseline=llm__provider=mistral__model=mistral-medium-2508__agent=pure-llm__20260222_201718 (isolated)`

## Summary Metrics (runstats.json)
The runstats available in the artifacts are limited to total token counts and total duration for these runs.

| Provider | Mode | Model | Total Tokens | Duration (s) | Notes |
|---|---|---|---:|---:|---|
| Groq | YAAM | `openai-gpt-oss-120b` | 29,572 | 171.77 | Includes YAAM orchestration and storage overhead. |
| Groq | Pure | `openai-gpt-oss-120b` | 3,408 | 76.38 | Baseline chat session; no memory. |
| Gemini | YAAM | `gemini-3-flash-preview` | 29,736 | 155.16 | Includes YAAM orchestration and storage overhead. |
| Gemini | Pure | `gemini-3-flash-preview` | 3,777 | 80.51 | Baseline chat session; no memory. |
| Mistral | YAAM | `mistral-medium-2508` | 29,491 | 141.48 | Includes YAAM orchestration and storage overhead. |
| Mistral | Pure | `mistral-medium-2508` | 6,084 | 99.66 | Baseline chat session; no memory. |

## Observations
- Pure-LLM runs are substantially lower in total tokens than YAAM runs (expected: no memory augmentation, fewer internal messages).
- Pure-LLM duration is shorter across all providers, consistent with eliminating storage/retrieval and agent orchestration.
- Mistral parity is now fixed: both YAAM and pure-LLM runs use `mistral-medium-2508`.
- YAAM runs provide per-turn metadata (provider/model, storage timing, session ids, context counts) while pure-LLM runs are standard benchmark artifacts.

## Artifact References

### YAAM HTML reports
- Groq: `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 15_29_01 - Detailed Report - goodai__smoke5__provider=groq__model=openai-gpt-oss-120b__promotion=disabled__agent=full__v1-min-skillwiring__20260222_152232 - RemoteMASAgentSession - remote.html`
- Gemini: `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 19_15_54 - Detailed Report - goodai__smoke5__provider=gemini__model=gemini-3-flash-preview__promotion=disabled__agent=full__v1-min-skillwiring__20260222_190933 - RemoteMASAgentSession - remote.html`
- Mistral (updated): `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 20_41_09 - Detailed Report - goodai__smoke5__provider=mistral__model=mistral-medium-2508__promotion=disabled__agent=full__v1-min-skillwiring__20260222_203516 - RemoteMASAgentSession - remote.html`

### Pure-LLM HTML reports
- Groq: `benchmarks/goodai-ltm-benchmark/data/reports/Detailed Report - goodai__smoke5__baseline=llm__provider=groq__model=openai-gpt-oss-120b__agent=pure-llm__20260222_202058 - GroqChatSession.html`
- Gemini: `benchmarks/goodai-ltm-benchmark/data/reports/Detailed Report - goodai__smoke5__baseline=llm__provider=gemini__model=gemini-3-flash-preview__agent=pure-llm__20260222_200909 - GeminiProInterface.html`
- Mistral: `benchmarks/goodai-ltm-benchmark/data/reports/Detailed Report - goodai__smoke5__baseline=llm__provider=mistral__model=mistral-medium-2508__agent=pure-llm__20260222_201718 - MistralChatSession.html`

### Comparative HTML reports
- YAAM-only: `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 - Comparative Report - YAAM-only - promotion=disabled - v1-min-skillwiring - mistral-medium-2508.html`
- Pure-LLM-only: `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 - Comparative Report - Pure-LLM - isolated - m=32000.html`

## Known Limitations
- Pure-LLM and YAAM runs use different agent wrappers and emit different metadata. Direct per-turn timing comparisons (llm vs storage) are only available in YAAM artifacts.

## Next Steps
1. Produce a short executive summary focusing on qualitative differences per dataset (e.g., instruction adherence and trigger compliance).
2. If needed, generate a combined comparative report across YAAM vs pure-LLM (not recommended because metrics are not fully comparable).
