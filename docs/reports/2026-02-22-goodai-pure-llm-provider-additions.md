# Report: GoodAI Benchmark Pure-LLM Provider Additions (Groq + Mistral)

**Date:** 2026-02-22  
**Scope:** `benchmarks/goodai-ltm-benchmark/` (benchmark-only)  
**Goal:** Add Groq and Mistral pure-LLM baselines for Smoke5 parity without modifying YAAM codepaths or altering existing Gemini benchmark behavior.

## 1. Decision Rationale

The GoodAI benchmark’s pure-LLM path relies on `LLMChatSession` and `ask_llm`, which currently route exclusively to Gemini. This prevents provider-parity baselines for Groq and Mistral. To preserve the integrity of existing benchmark behavior while enabling new baselines, we adopted an **additive-only** approach:

- No changes to YAAM or API Wall codepaths.
- No modifications to existing Gemini benchmark logic.
- Two new provider modules were added as **parallel implementations** to `gemini_interface.py`, mirroring structure and behavior for traceability.

This approach minimizes architectural drift while making the baseline path explicit and auditable.

## 2. Implementation Summary (Additive Only)

### 2.1 New Provider Modules

The following modules were added to the benchmark model interface layer:

- `benchmarks/goodai-ltm-benchmark/model_interfaces/groq_interface.py`
- `benchmarks/goodai-ltm-benchmark/model_interfaces/mistral_interface.py`

Both are intentionally similar to the existing `GeminiProInterface` implementation to make provider differences explicit and reviewable.

### 2.2 Runner Wiring (Additive Change)

`benchmarks/goodai-ltm-benchmark/runner/run_benchmark.py` now recognizes two additional agent names:

- `groq` → `GroqChatSession`
- `mistral` → `MistralChatSession`

The default Gemini path remains unchanged; the runner change is limited to routing new agent names to the new provider modules.

## 3. Provider Configuration (Environment)

The new sessions use OpenAI-compatible REST endpoints and environment variables:

| Provider | Required Key | Base URL (default) | Model Env Var |
|---|---|---|---|
| Groq | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` | `GROQ_MODEL` (default `openai/gpt-oss-120b`) |
| Mistral | `MISTRAL_API_KEY` | `https://api.mistral.ai/v1` | `MISTRAL_MODEL` (default `mistral-large`) |

Optional per-provider settings:

- `GROQ_MAX_OUTPUT_TOKENS`, `GROQ_TEMPERATURE`
- `MISTRAL_MAX_OUTPUT_TOKENS`, `MISTRAL_TEMPERATURE`

## 4. Traceability Notes

These additions are **copies**, not refactors. Each provider resides in its own module to keep implementation decisions visible and attributable. This ensures that future behavior differences can be traced to a specific provider implementation without cross-cutting changes.

## 5. Next Steps

1. Run Smoke5 pure-LLM baselines using `-a groq`, `-a gemini`, and `-a mistral` (same config as YAAM runs).
2. Compare results against YAAM parity runs to quantify memory-layer impact per provider.

## 6. Verification Notes (Mypy Baseline)

Running `./.venv/bin/mypy . --exclude benchmarks/goodai-ltm-benchmark/tests` surfaced pre-existing type issues unrelated to the new provider modules:

- `scripts/validate_goodai_config.py`: missing stubs for `yaml`
- `scripts/grade_phase5_readiness.py`: `Any` return type mismatch
- `tests/benchmarks/results_analyzer.py`: `Any` return type mismatch
- `tests/benchmarks/workload_generator.py`: missing variable annotations
- `scripts/poll_memory_state.py`: `Any` return type mismatch

These baseline failures should be resolved separately; no additional mypy errors were introduced by the Groq/Mistral additions.
