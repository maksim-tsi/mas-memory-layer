# Scripts README

This file consolidates the demo/test scripts in the `scripts/` folder and briefly documents their purpose and usage.

Why these scripts exist
-----------------------
- Provide quick, developer-friendly ways to exercise provider SDKs and the `LLMClient` implementation.
- Provide smoke/integration checks to verify connectivity, usage, and basic generation for provider-specific SDKs.

## Directory Structure

```
scripts/
├── archive/             # Archived legacy code (preserved for reference)
├── debug/               # One-off debug and verification scripts
├── *.py                 # Production utility scripts
├── *.sh                 # Shell scripts for tests and setup
└── README.md            # This file
```

### Database Infrastructure Scripts

| Script | Purpose |
|--------|---------|
| `create_qdrant_index.py` | Creates a payload index on `session_id` field in Qdrant's `episodes` collection |
| `ensure_episodes_collection.py` | Creates/refreshes the `episodes` collection in Qdrant with correct vector size |

**Usage:**
```bash
# Create Qdrant index
./.venv/bin/python scripts/create_qdrant_index.py

# Ensure episodes collection exists
./.venv/bin/python scripts/ensure_episodes_collection.py
```

### Subdirectories

- **`debug/`** - One-off debug and verification scripts for development troubleshooting. See [debug/README.md](debug/README.md).
- **`archive/`** - Archived legacy code that has been superseded by current architecture. See [archive/README.md](archive/README.md).

---

Script inventory
# Run demo with flags (run subset of providers and custom prompt):
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini,groq --prompt "Explain memory systems in one sentence."
 
# Run demo with JSON output (good for scripting/CI output):
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --prompt "Explain the CIAR scoring briefly" --json

# Use a default model for all providers --model or override per-provider:
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini,groq --model "gemini-2.5-flash" --prompt "Explain memory systems" --json
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --model-gemini "gemini-2.0-flash-exp" --prompt "Explain the CIAR scoring briefly" --json

# Increase demo verbosity (set logging level to DEBUG):
./.venv/bin/python scripts/llm_client_demo.py --providers=mistral --prompt "Summarize the project in one sentence" --verbose

# Skip provider health checks (faster demos):
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --skip-health-check --prompt "Explain the CIAR scoring briefly" --json

# Write JSON NDJSON output to file
./.venv/bin/python scripts/llm_client_demo.py --providers=groq --skip-health-check --prompt "Explain the CIAR scoring briefly" --json --output-file="/tmp/llm_demo_out.ndjson"
 
# JSON array output (overwrite existing file)
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --prompt "Explain memory" --json --output-format=json-array --output-mode=overwrite --output-file="/tmp/llm_demo_array.json"

# JSON array output (append to existing array)
./.venv/bin/python scripts/llm_client_demo.py --providers=gemini --prompt "Explain memory" --json --output-format=json-array --output-mode=append --output-file="/tmp/llm_demo_array.json"
----------------
New File Output Behavior (ndjson vs json-array)
--------------------------------------------
The demo supports two file output formats when the `--json` flag is used in combination with `--output-file`:

- `ndjson` (default): each provider response is appended as a single JSON object on its own line. Use `--output-mode=overwrite` to clear the file first or `--output-mode=append` to add to it.
- `json-array`: the demo will write a valid JSON array to the file. In `overwrite` mode the file is initialized to `[]` and replaced by the demo with a single-element array (or multiple elements if multiple providers are run). In `append` mode, if an existing JSON array is present the new elements are merged into the existing array; if parsing fails the file is overwritten with the new array.

Examples:

```bash
# NDJSON (overwrite - clears file):
./.venv/bin/python scripts/llm_client_demo.py --json --output-file "/tmp/llm_demo_out.ndjson" --output-format ndjson --output-mode overwrite

# NDJSON (append):
./.venv/bin/python scripts/llm_client_demo.py --json --output-file "/tmp/llm_demo_out.ndjson" --output-format ndjson --output-mode append

# JSON array (overwrite):
./.venv/bin/python scripts/llm_client_demo.py --json --output-file "/tmp/llm_demo_array.json" --output-format json-array --output-mode overwrite

# JSON array (append):
./.venv/bin/python scripts/llm_client_demo.py --json --output-file "/tmp/llm_demo_array.json" --output-format json-array --output-mode append
```

Notes:
- `--output-file` is only used when `--json` is provided.
- If `--output-format=json-array` is used and `--output-mode=overwrite` is selected, the file is initialized to an empty JSON array `[]` prior to writing.
- For append behavior with `json-array`, if the existing file contains invalid JSON the demo will overwrite it with a fresh array (failsafe behavior).

Testing:
--------
Unit tests for the demo output behaviors are provided at `tests/utils/test_llm_client_demo_output.py` and mock the LLM client to validate treatment of `ndjson` and `json-array` modes as well as append/overwrite semantics.
- `scripts/llm_client_demo.py` - Demo harness that registers provider adapters (Gemini, Groq, Mistral) and iterates through each provider to print responses and usage. Uses environment variables (or `.env`) for API keys.
- `scripts/test_gemini.py` - Small script to validate Google Gemini connectivity and basic generation flows.
- `scripts/test_groq.py` - Small script to validate Groq connectivity and basic generation flows.
- `scripts/test_mistral.py` - Small script to validate Mistral connectivity and basic generation flows.
- `scripts/run_smoke_tests.sh` - Higher-level script to run smoke tests (see the scripts folder for details).
- `scripts/run_memory_integration_tests.sh` - Integration harness for memory system tests (includes storage and LLM connectivity checks).
- `scripts/archive_docs_to_typesense.py` - Archive markdown documentation to Typesense for semantic search. Scans the repository for `.md` files, excludes benchmark code, and uploads with doc_type tagging.
- `scripts/verify_typesense_docs.py` - Quick verification of uploaded documents in Typesense. Checks collection existence, document count, search functionality, and doc_type distribution.

Archive Docs to Typesense
-------------------------
The `archive_docs_to_typesense.py` script performs selective ingestion of markdown documentation into Typesense for semantic search capabilities.

**Features:**
- Scans the repository root for `.md` files
- Excludes benchmark code (`benchmarks/goodai-ltm-benchmark`) and standard noise (`.git`, `node_modules`, `.venv`, etc.)
- Adds `repository_label: "mas-memory-layer-repo"` to all documents
- Auto-tags documents by type: `adr`, `specification`, `plan`, `report`, `readme`, or `documentation`

**Environment Variables (from `.env`):**
- `TYPESENSE_API_KEY` - API key for authentication (required)
- `TYPESENSE_HOST` - Host address (default: `DATA_NODE_IP` or `192.168.107.187`)
- `TYPESENSE_PORT` - Port number (default: `8108`)
- `TYPESENSE_PROTOCOL` - Protocol (default: `http`)

**Usage:**

```bash
# Dry run - scan and list files without uploading
./.venv/bin/python scripts/archive_docs_to_typesense.py --dry-run

# Full upload to Typesense
./.venv/bin/python scripts/archive_docs_to_typesense.py

# Verbose output with custom collection
./.venv/bin/python scripts/archive_docs_to_typesense.py -v --collection my_docs

# Scan a specific directory
./.venv/bin/python scripts/archive_docs_to_typesense.py --root-dir /path/to/docs
```

**Tests:**

```bash
./.venv/bin/pytest tests/scripts/test_archive_docs_to_typesense.py -v
```

Verify Typesense Docs
---------------------
The `verify_typesense_docs.py` script provides quick verification of uploaded documents in Typesense.

**Features:**
- Checks collection existence and document count
- Displays sample documents with content preview
- Shows document type distribution
- Verifies repository_label filter

**Usage:**

```bash
# Verify documents in default collection (mas_project_archive)
./.venv/bin/python scripts/verify_typesense_docs.py

# Override collection name
TYPESENSE_COLLECTION=my_docs ./.venv/bin/python scripts/verify_typesense_docs.py
```

**Sample Output:**
```
✓ Collection exists
  - Number of documents: 160
  - Fields: ['filename', 'path', 'content', 'doc_type', 'repository_label']
✓ Search working - 160 total documents

Document type distribution:
  - adr: 10 documents
  - readme: 16 documents
  - plan: 21 documents
  - documentation: 49 documents
  - report: 51 documents
✓ Documents with repository_label 'mas-memory-layer-repo': 160
```

Usage
-----
These scripts are entry-level utilities intended for rapid debugging and integration validation. They rely on the environment or `.env` for credentials.

Examples (run inside project venv):

```bash
# Run demo (queries each configured provider, prints usage):
./.venv/bin/python scripts/llm_client_demo.py

# Run provider-specific checks
./.venv/bin/python scripts/test_gemini.py
./.venv/bin/python scripts/test_groq.py
./.venv/bin/python scripts/test_mistral.py
```

Integration tests (skipped when no env keys):

```bash
./.venv/bin/pytest tests/integration/test_llmclient_real.py -q
```

Readiness grading and markers
-----------------------------
- Use `./scripts/grade_phase5_readiness.sh --mode fast` for lint + unit/mocked tests; `--mode full` adds integration and `llm_real` markers when env vars are present.
- Real LLM/provider checks require `GOOGLE_API_KEY` exported in the shell (from `.env`, not committed). Add `--skip-llm` to suppress them even if the key is set.
- Marker scopes: unit/mocked `-m "not integration and not llm_real"`; integration `-m "integration"`; real LLM `-m "llm_real"`.
- Optional summary JSON: `./scripts/grade_phase5_readiness.sh --mode full --summary-out /tmp/phase5-readiness.json` (feeds docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md).

Environment variables
---------------------
Always keep API keys out of version control—prefer using environment variables or a local `.env` file and never store secrets in the repo.

The scripts check for these environment variables (if present they will be used):
- `GOOGLE_API_KEY`
- `GROQ_API_KEY`
- `MISTRAL_API_KEY`

See `.env.example` for a template. If you create a `.env` file for local testing, ensure it is not committed.

Safety & cost notes
------------------
- These are real API calls and may incur charges; run them selectively and with minimal token settings.
- The demo and provider test scripts use short prompts and small output token limits to keep costs low, but repeated or long-run tests can still accumulate charges.

Extending scripts
-----------------
- Add `--providers` CLI flag to limit demo to a subset of providers when running.
- Add timing/warmup metrics and rate-limiting to emulate production constraints.
