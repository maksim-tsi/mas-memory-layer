# LLM Client Demo - scripts/llm_client_demo.py

Short demo script to help developers exercise the new `LLMClient` and provider adapters (Gemini, Groq, Mistral) in a controlled, non-production context.

Purpose
-------
- Demonstrates a simple orchestration for calling multiple LLM providers and prints a per-provider response and usage.
- Provides a small health check and a request-per-provider example useful for debugging adapters and provider configuration.

Prerequisites
-------------
- Python 3.12 with a virtual environment (project `.venv` is preferred).
- The repository dependencies installed in the venv:
  - `pip install -r requirements.txt` (or use the project venv as recommended in the project docs)
- Set API keys for providers in `.env` or environment variables (see next section).

Environment variables
---------------------
Do NOT store API keys inside VCS or expose them in your work. The demo reads keys from environment variables or a `.env` file - see `.env.example` for variable names.

Supported environment variables (optional - only register/adapt providers you have keys for):
- `GOOGLE_API_KEY` — API key for Google Gemini (gemini-2.* models)
- `GROQ_API_KEY` — API key for Groq
- `MISTRAL_API_KEY` — API key for Mistral AI

If you plan to run the demo locally, copy `.env.example` to `.env` and add the keys (never commit or share this file):

```bash
cp .env.example .env
# Edit .env and add your API keys
```

File output flags (ndjson / json-array)
-------------------------------------
The demo provides two file output formats for JSON output (requires `--json`):

- `--output-format=ndjson` — default; each provider's response is written as one separate JSON object per line. Useful for streaming/line-based parsing with `jq` or similar.
- `--output-format=json-array` — writes a valid JSON array. Useful for tools that expect a JSON array. The array is written in a single write operation at the end of the run.

Append/Overwrite modes:
- `--output-mode=overwrite` — clears the file before writing (for NDJSON) or sets the file to `[]` before collecting output (for JSON array mode).
- `--output-mode=append` — appends NDJSON lines or merges elements into an existing JSON array (JSON array mode). If JSON parsing fails during append, the demo will overwrite the file with the new JSON array.

Note: to use file output, always include `--json` alongside `--output-file`.


Usage
-----
Run the demo with the project venv Python (the script will register all providers that have keys in environment):

```bash
./.venv/bin/python scripts/llm_client_demo.py

# Run demo with CLI flags:
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini,groq --prompt "Explain memory systems in one sentence."

# JSON output
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --prompt "Explain the CIAR scoring briefly" --json
# JSON output
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --prompt "Explain the CIAR scoring briefly" --json

# Default model and per-provider model override
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini,groq --model "gemini-2.5-flash" --prompt "Explain memory systems" --json
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --model-gemini "gemini-2.0-flash-exp" --prompt "Explain the CIAR scoring briefly" --json

# Verbose (DEBUG) logging
./.venv/bin/python scripts/llm_client_demo.py --providers=mistral --prompt "Summarize the project in one sentence" --verbose

# Skip provider health checks (faster demo runs)
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --skip-health-check --prompt "Explain CIAR" --json

# Write JSON NDJSON output to file
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --skip-health-check --prompt "Explain CIAR" --json --output-file "/tmp/llm_demo_out.ndjson"

# JSON array output (overwrite)
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --prompt "Explain memory" --json --output-format=json-array --output-mode=overwrite --output-file "/tmp/llm_demo_array.json"

# JSON array output (append)
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --prompt "Explain memory" --json --output-format=json-array --output-mode=append --output-file "/tmp/llm_demo_array.json"
```

What the demo does
------------------
- Loads environment from `.env` using `python-dotenv` (if present)
- Registers available provider adapters (Gemini, Groq, Mistral) using their SDK clients
- Runs a lightweight `health_check()` for each registered provider
- Iterates through registered providers one-by-one and requests the same prompt from each provider so you can compare model responses, usage, and model name

Safety and cost considerations
------------------------------
- The demo performs real API calls when keys are present; these calls may be billable depending on your provider plan.
- To minimize charges, keep `max_output_tokens` and repeated calls to a minimum
- Monitor provider dashboards and usage quotas while running integrations.

Extending or debugging
----------------------
- To limit the demo to a subset of providers, set only the environment variables for the providers you want to test.
- The demo intentionally uses short prompts and minimal token settings to limit cost and speed up tests.
- If you want to test real latency/throughput, update the demo script to measure and log timing and response metadata.

Next steps
----------
- Integrate `LLMClient` into a lifecycle engine such as the PromotionEngine to perform L1→L2 operations.
- Add retry/backoff logic or rate limiters in `LLMClient` for robust production use.

Testing
-------
Unit tests validating NDJSON and JSON-array file output behaviors were added at:
- `tests/utils/test_llm_client_demo_output.py` (mocks the demo's LLM client and checks file content and append/overwrite behavior)

