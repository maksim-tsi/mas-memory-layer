# GoodAI LTM Benchmark Setup Guide

## Overview

This document describes how to set up and integrate the GoodAI LTM Benchmark for evaluating the MAS Memory Layer architecture. The benchmark runs in an isolated environment with HTTP boundaries to prevent dependency conflicts.

## Prerequisites

- Python 3.10+ (GoodAI requirement; Python 3.12.3 validated)
- System package: `python3-venv` (for Ubuntu/Debian)
- Git

## Installation Steps

### 1. System Dependencies

```bash
# Ubuntu/Debian (if venv creation fails)
sudo apt install python3.12-venv
```

### 2. Download and Extract Benchmark

```bash
cd /home/max/code/mas-memory-layer/benchmarks

# Download from GitHub (already completed if you see goodai-ltm-benchmark/ directory)
wget -O /tmp/goodai-ltm-benchmark.zip https://github.com/GoodAI/goodai-ltm-benchmark/archive/refs/heads/main.zip
unzip -q /tmp/goodai-ltm-benchmark.zip
mv goodai-ltm-benchmark-main goodai-ltm-benchmark
```

### 3. Create Isolated Virtual Environment

```bash
cd /home/max/code/mas-memory-layer/benchmarks

# Create separate venv (isolated from main project)
python3 -m venv .venv-benchmark

# Activate (for manual testing only - orchestration scripts handle activation)
source .venv-benchmark/bin/activate

# Install GoodAI benchmark and dependencies
cd goodai-ltm-benchmark
pip install -e .

# Verify installation
python -m pytest --version  # Should show pytest installed
```

### 4. Verify Test Types

```bash
# Check available test types (should include prospective_memory and restaurant)
ls -1 datasets/*.py | grep -E "(prospective_memory|restaurant)"

# Expected output:
# datasets/prospective_memory.py
# datasets/restaurant.py
```

## Architecture: HTTP Boundary Isolation

The GoodAI benchmark runs in its own process with a separate virtual environment. It communicates with MAS agents via HTTP:

```
┌─────────────────────────────────────────────────────────────────┐
│ GoodAI Benchmark Process (.venv-benchmark)                      │
│                                                                   │
│  ┌──────────────────────┐        HTTP POST /run_turn            │
│  │  GoodAI Test Runner  │ ─────────────────────────────────────>│
│  │  (prospective_memory,│                                        │
│  │   restaurant, etc.)  │ <─────────────────────────────────────│
│  └──────────────────────┘        JSON Response                  │
└─────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP (ports 8080/8081/8082)
                                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ MAS Memory Layer (Main .venv)                                   │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  │ FastAPI Wrapper  │  │ FastAPI Wrapper  │  │ FastAPI Wrapper │
│  │   (mas-full)     │  │    (mas-rag)     │  │(mas-full-context)│
│  │   Port 8080      │  │   Port 8081      │  │   Port 8082     │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘
│          │                      │                      │         │
│          └──────────────────────┴──────────────────────┘         │
│                             │                                     │
│                   UnifiedMemorySystem                            │
│                   (L1 → L2 → L3 → L4)                           │
└─────────────────────────────────────────────────────────────────┘
```

## HTTP API Schema

### POST /run_turn

**Request** (from GoodAI):
```json
{
  "session_id": "session_123",
  "role": "user",
  "content": "Remember to buy milk tomorrow",
  "turn_id": 5
}
```

**Response** (from MAS agent):
```json
{
  "session_id": "full:session_123",  // Prefixed by agent type
  "role": "assistant",
  "content": "I'll remember to remind you about buying milk tomorrow.",
  "turn_id": 5
}
```

### GET /sessions

Returns list of active session IDs:

```json
{
  "sessions": [
    "full:session_123",
    "full:session_456"
  ]
}
```

### GET /memory_state

Query memory accumulation for a session:

**Request**:
```
GET /memory_state?session_id=full:session_123
```

**Response**:
```json
{
  "session_id": "full:session_123",
  "l1_turns": 15,
  "l2_facts": 8,
  "l3_episodes": 2,
  "l4_docs": 1,
  "timestamp": "2026-01-26T22:15:30Z"
}
```

## Session ID Prefixing Convention

To prevent collisions when multiple agents process the same GoodAI session, we prefix session IDs:

| Agent Type | Prefix | Example |
|------------|--------|---------|
| mas-full | `full:` | `full:session_123` |
| mas-rag | `rag:` | `rag:session_123` |
| mas-full-context | `full_context:` | `full_context:session_123` |

**Implementation**: Each FastAPI wrapper prepends its prefix to incoming `session_id` values before passing to `UnifiedMemorySystem`.

## Configuration Files

### Subset Baseline Config

Location: `benchmarks/goodai-ltm-benchmark/configs/mas_subset_32k.yaml`

```yaml
memory_span: 32000
test_types:
  - prospective_memory
  - restaurant
model: mas-full  # Overridden by -a flag during execution
```

### Validation

Run config validator before execution:

```bash
/home/max/code/mas-memory-layer/.venv/bin/python scripts/validate_goodai_config.py \
  benchmarks/goodai-ltm-benchmark/configs/mas_subset_32k.yaml
```

## Execution

### Manual Test (Single Agent)

```bash
# Start wrapper service
/home/max/code/mas-memory-layer/.venv/bin/python src/evaluation/agent_wrapper.py \
  --agent-type full \
  --port 8080 \
  --model gemini-2.5-flash-lite &

# Wait for health check
sleep 5

# Run GoodAI benchmark
cd /home/max/code/mas-memory-layer/benchmarks
source .venv-benchmark/bin/activate
cd goodai-ltm-benchmark
python -m goodai_ltm_benchmark.run \
  -a mas-full \
  -c configs/mas_subset_32k.yaml
```

### Automated Orchestration

Use the orchestration script for full subset baseline:

```bash
bash /home/max/code/mas-memory-layer/scripts/run_subset_experiments.sh
```

This script:
1. Starts all three wrapper services (ports 8080/8081/8082)
2. Verifies health checks
3. Runs each agent serially (mas-full, mas-rag, mas-full-context)
4. Verifies cleanup after each run (GET /sessions → expect [])
5. Forces cleanup if needed (POST /cleanup_force?session_id=all)
6. Copies results to timestamped directory

## Result File Mapping

### GoodAI Output Locations

```
benchmarks/goodai-ltm-benchmark/data/tests/
├── prospective_memory/
│   └── results/
│       ├── mas-full/
│       │   └── results.json
│       ├── mas-rag/
│       │   └── results.json
│       └── mas-full-context/
│           └── results.json
└── restaurant/
    └── results/
        ├── mas-full/
        │   └── results.json
        ├── mas-rag/
        │   └── results.json
        └── mas-full-context/
            └── results.json
```

### Analysis Input Location

Orchestration script copies results to:

```
benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/
├── mas-full/
│   ├── prospective_memory/
│   │   └── results.json
│   └── restaurant/
│       └── results.json
├── mas-rag/
│   └── ...
├── mas-full-context/
│   └── ...
└── logs/
    ├── mas_full_memory_timeline.jsonl
    ├── mas_rag_memory_timeline.jsonl
    ├── mas_full_context_memory_timeline.jsonl
    └── subset_cleanup_*.log
```

## Debug Endpoints

### Memory Timeline Polling

Background script polls `/memory_state` every 10 turns:

```bash
/home/max/code/mas-memory-layer/.venv/bin/python scripts/poll_memory_state.py \
  --port 8080 \
  --output logs/mas_full_memory_timeline.jsonl \
  --error-log logs/mas_full_memory_polling_errors.log \
  --interval 10 &
```

**Output Format** (`memory_timeline.jsonl`):
```jsonl
{"timestamp": "2026-01-26T22:15:30Z", "session_id": "full:session_123", "l1_turns": 5, "l2_facts": 2, "l3_episodes": 0, "l4_docs": 0}
{"timestamp": "2026-01-26T22:16:45Z", "session_id": "full:session_123", "l1_turns": 15, "l2_facts": 8, "l3_episodes": 1, "l4_docs": 0}
```

### Cleanup Verification

After each run:

```bash
# Check for active sessions (should be empty)
curl http://localhost:8080/sessions

# Expected response:
{"sessions": []}

# Force cleanup if needed
curl -X POST http://localhost:8080/cleanup_force?session_id=all
```

## Troubleshooting

### Issue: "No module named 'goodai_ltm_benchmark'"

**Cause**: GoodAI benchmark not installed or wrong venv activated.

**Fix**:
```bash
cd /home/max/code/mas-memory-layer/benchmarks
source .venv-benchmark/bin/activate
cd goodai-ltm-benchmark
pip install -e .
```

### Issue: Wrapper service fails to start

**Cause**: Database connectivity issue or port already in use.

**Fix**:
```bash
# Check health endpoint manually
curl http://localhost:8080/health

# Kill existing process on port
lsof -ti:8080 | xargs kill -9

# Check database connectivity
redis-cli ping                           # Should return PONG
psql -h $DATA_NODE_IP -U postgres -d mas_memory -c "SELECT 1;"  # Should return 1
```

### Issue: Session ID collision

**Cause**: Prefix not applied correctly in wrapper.

**Verify**: Check logs for session ID format. Should see `full:session_123`, not just `session_123`.

**Fix**: Review `src/evaluation/agent_wrapper.py` session ID prefixing logic.

## Next Steps

1. **Complete Infrastructure Setup** (Phase 5A):
   - ✅ Download and extract GoodAI benchmark
   - ✅ Add to .gitignore
   - ⏳ Install in isolated venv (requires `python3-venv` system package)
   - ⏳ Create config validator script
   - ⏳ Verify test types exist

2. **Implement Agents** (Phase 5B):
   - Create BaseAgent abstract class
   - Implement MemoryAgent with LangGraph
   - Implement RAGAgent with incremental indexing
   - Implement FullContextAgent with truncation

3. **Build Wrapper Services** (Phase 5C):
   - FastAPI wrapper with CLI args
   - Database isolation logic
   - GoodAI agent interfaces (mas-full, mas-rag, mas-full-context)

4. **Execute Subset Baseline** (Phase 5F):
   - Run orchestration script
   - Analyze results
   - Identify bottlenecks

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-26  
**Status**: GoodAI benchmark downloaded and extracted, awaiting isolated venv setup
