# Developer Quickstart

This document provides a short guide for developers to run the demo scripts and provider checks in the `scripts/` folder.

See also: `scripts/README.md` for more details.

Prerequisites
-------------
- Python 3.12 and a project virtual environment (`.venv`) as described in the project `docs/environment-guide.md`.
- Install dependencies in the virtual environment:

```bash
./.venv/bin/pip install -r requirements.txt
```

Running the demo and provider scripts
------------------------------------
Use the `llm_client_demo.py` script to query each registered LLM provider and compare outputs:

```bash
./.venv/bin/python scripts/llm_client_demo.py
```

Example: Writing output files (NDJSON or JSON array):

```bash
./.venv/bin/python scripts/llm_client_demo.py --json --output-file /tmp/llm_demo_out.ndjson --output-format ndjson --output-mode overwrite --skip-health-check
./.venv/bin/python scripts/llm_client_demo.py --json --output-file /tmp/llm_demo_array.json --output-format json-array --output-mode append --skip-health-check
```

Check provider-specific SDK connectivity using the per-provider test scripts:

```bash
./.venv/bin/python scripts/test_gemini.py
./.venv/bin/python scripts/test_groq.py
./.venv/bin/python scripts/test_mistral.py
```

Integration tests
-----------------
If you have provider keys configured in your environment (or `.env`), the integration test will run (otherwise it is skipped):

```bash
./.venv/bin/pytest tests/integration/test_llmclient_real.py -q
```

Setting environment variables
-----------------------------
Use `.env.example` as a template and add your keys locally to a `.env` (do not commit this file):

```bash
cp .env.example .env
# Edit .env and add your keys as needed
```

Safety/Caution
--------------
- These scripts perform real API calls when keys are present and may be billable.
- Keep tokens and calls minimal during development and monitor usage in provider dashboards.
