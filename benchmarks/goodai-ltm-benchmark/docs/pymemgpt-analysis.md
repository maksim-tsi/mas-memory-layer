# Analysis: `pymemgpt` Usage in GoodAI LTM Benchmark

**Date:** February 10, 2026  
**Status:** Active Baseline Agent (Under Review)  
**Successor:** Letta (https://pypi.org/project/letta/)

---

## Executive Summary

`pymemgpt` **IS actively used** in the GoodAI benchmark as a **baseline competitor agent** for memory system comparison. While MAS agents (mas-full, mas-rag) use a custom L1-L4 architecture, the benchmark infrastructure requires `pymemgpt` to evaluate MemGPT's proprietary memory management approach against our system.

**Key Finding:** The dependency is NOT vestigial—removing it breaks MemGPT baseline comparisons.

---

## 1. Active Usage Confirmed

### 1.1 Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| [`model_interfaces/memgpt_interface.py`](../model_interfaces/memgpt_interface.py) | 131 | MemGPT agent wrapper using official Python SDK |
| [`model_interfaces/memgpt_proxy.py`](../model_interfaces/memgpt_proxy.py) | 44 | Flask proxy for OpenAI API interception & cost tracking |
| [`runner/run_benchmark.py`](../runner/run_benchmark.py) | 443 | Orchestrator that instantiates MemGPT agent (line 72) |

### 1.2 Import Analysis

```bash
# Command executed:
cd benchmarks/goodai-ltm-benchmark
grep -r "from.*memgpt" . --include="*.py" --exclude-dir=".venv"

# Results (3 active imports):
./runner/run_benchmark.py:from model_interfaces.memgpt_interface import MemGPTChatSession
./model_interfaces/memgpt_interface.py:from memgpt import create_client
./model_interfaces/memgpt_interface.py:from memgpt.client.client import LocalClient
./model_interfaces/memgpt_interface.py:from memgpt.data_types import AgentState
```

---

## 2. Architecture: MemGPT vs MAS Agents

The benchmark compares **two distinct memory architectures**:

```
┌─────────────────────────────────────────────────────────────┐
│               GoodAI LTM Benchmark Harness                   │
│                  (run_benchmark.py)                          │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
    ┌───────▼────────┐                ┌───────▼────────────┐
    │  MemGPT Agent  │                │   MAS Agents       │
    │  (Baseline)    │                │   (Custom L1-L4)   │
    └───────┬────────┘                └───────┬────────────┘
            │                                 │
    ┌───────▼────────────────┐        ┌───────▼────────────────┐
    │ memgpt.client.         │        │ UnifiedMemorySystem    │
    │ LocalClient            │        │                        │
    │ ↓                      │        │ L1: Redis (turns)      │
    │ MemGPT Server          │        │ L2: PostgreSQL (facts) │
    │ (manages agent memory) │        │ L3: Qdrant + Neo4j     │
    │                        │        │ L4: Typesense          │
    └────────────────────────┘        └────────────────────────┘
```

### Available Agent Identifiers

From [README.md](../README.md#agents):

| Agent | Implementation | Uses pymemgpt? |
|-------|----------------|----------------|
| `memgpt` | MemGPT SDK | ✅ **Yes** |
| `mas-full` | Custom L1-L4 | ❌ No |
| `mas-rag` | Custom L3 only | ❌ No |
| `mas-full-context` | No memory | ❌ No |
| `mas-remote` | HTTP wrapper | ❌ No |
| `gemini-2.5-flash-lite` | Native Gemini | ❌ No |
| `ltm_agent_1/2/3` | GoodAI research | ❌ No |

**Critical Distinction:** Only the `memgpt` agent identifier requires `pymemgpt`. All MAS agents use the custom memory system.

---

## 3. MemGPT Integration Architecture

### 3.1 Initialization Flow

From [`memgpt_interface.py:67-76`](../model_interfaces/memgpt_interface.py#L67-L76):

```python
def __post_init__(self) -> None:
    self.client = create_client()  # Creates MemGPT LocalClient
    
    # Override MemGPT's LLM endpoint to route through cost-tracking proxy
    self.client.server.server_llm_config.model_endpoint = "http://localhost:5000/v1"
    self.client.server.server_embedding_config.embedding_endpoint = "http://localhost:5000/v1"
    
    # Apply context window constraint from config
    if self.max_prompt_size is None:
        self.max_prompt_size = self.client.server.server_llm_config.context_window
    self.client.server.server_llm_config.context_window = self.max_prompt_size
```

### 3.2 Message Processing Flow

From [`memgpt_interface.py:78-91`](../model_interfaces/memgpt_interface.py#L78-L91):

```python
def reply(self, user_message: str, agent_response: str | None = None) -> str:
    if not self.agent_initialised:
        self.reset()
    
    # Launch Flask proxy subprocess for API interception
    with proxy(self._proxy_path):  # Starts memgpt_proxy.py on port 5000
        response = self.client.user_message(
            agent_id=self.agent_info.id, 
            message=user_message
        )
    
    # Extract assistant messages from MemGPT structured response
    messages = [res["assistant_message"] 
                for res in response 
                if "assistant_message" in res]
    
    # Aggregate token costs from proxy logs
    self.costs_usd += read_cost_info()  # Parses memgpt-logs.jsonl
    return "\n".join(messages)
```

### 3.3 Proxy Cost Tracking

From [`memgpt_proxy.py:9-41`](../model_interfaces/memgpt_proxy.py#L9-L41):

```python
@app.route("/<path:url_path>", methods=["POST"])
def proxy_request(url_path: str):
    """
    Flask proxy that intercepts MemGPT → OpenAI API calls.
    Logs token usage for benchmark cost tracking.
    """
    openai_api_url = f"https://api.openai.com/{url_path}"
    headers = {k: v for k, v in request.headers.items()}
    headers["Host"] = "api.openai.com:5000"
    
    # Forward request with retry logic
    response = requests.post(openai_api_url, data=request.get_data(), headers=headers)
    
    # Log successful responses for cost analysis
    if response.status_code == 200:
        with open("model_interfaces/memgpt-logs.jsonl", "a") as fd:
            fd.write(f"{json.dumps(json.loads(response.text))}\n")
    
    return response.json(), response.status_code, headers.items()

app.run(port=5000, use_reloader=False)
```

**Log Format:** `memgpt-logs.jsonl` contains OpenAI API responses with token counts:
```json
{"usage": {"prompt_tokens": 1234, "completion_tokens": 567}, "model": "gpt-4-turbo"}
```

---

## 4. Python <3.13 Constraint Analysis

### 4.1 Dependency Chain

From [`pyproject.toml`](../pyproject.toml):

```toml
[tool.poetry.dependencies]
python = ">=3.10,<3.13"  # ⚠️ Constrained by pymemgpt
pymemgpt = "^0.3.25"
```

### 4.2 Root Cause

All `pymemgpt` releases (0.1.0 through 0.3.25) declare:
```toml
python = ">=3.10,<3.13"
```

**Impact:** The benchmark environment cannot use Python 3.13+, even though:
- Root MAS project supports: `python = ">=3.12,<3.14"`
- Modern dependencies prefer: Python 3.12+

### 4.3 Dependency Conflicts

From analysis:

| pymemgpt Requires | Conflicts With |
|-------------------|----------------|
| `openai < 1.0.0` | Modern `openai >= 1.50+` |
| `tiktoken < 0.6.0` | `langchain-openai` (needs `tiktoken >= 0.7`) |
| `python < 3.13` | Latest runtime features |

---

## 5. Deprecation Status

### 5.1 Official Status

* **Last PyPI Release:** 0.3.25 (August 25, 2024)
* **Project Status:** Rebranded as **Letta**
* **Successor Package:** `letta` on PyPI (https://pypi.org/project/letta/)
* **Architectural Change:** Letta represents a re-architected version with breaking API changes

### 5.2 Migration Challenges

The `letta` package is NOT a drop-in replacement:
- Different client initialization API
- Modified agent configuration schema
- Incompatible persistence layer

**Migration would require:** Complete rewrite of `memgpt_interface.py` and `memgpt_proxy.py`.

---

## 6. Decision Matrix

### Option A: Keep pymemgpt (Status Quo)

**Pros:**
- ✅ Maintain MemGPT baseline comparison capability
- ✅ Preserve historical benchmark reproducibility
- ✅ No code changes required

**Cons:**
- ❌ Locks benchmark to Python <3.13
- ❌ Prevents modern dependency upgrades
- ❌ Uses deprecated/unmaintained package

### Option B: Remove pymemgpt

**Pros:**
- ✅ Unlocks Python 3.13+ runtime
- ✅ Enables modern dependency versions
- ✅ Reduces unmaintained code surface

**Cons:**
- ❌ **BREAKS MemGPT baseline comparisons**
- ❌ Loses academic comparison rigor
- ❌ Invalidates historical benchmarks

### Option C: Make pymemgpt Optional (Recommended)

**Pros:**
- ✅ MAS-only runs unlock Python 3.13+
- ✅ MemGPT comparison remains available when needed
- ✅ Explicit dependency opt-in

**Cons:**
- ⚠️ Requires Poetry extras configuration
- ⚠️ CI/CD must handle two installation modes

---

## 7. Recommended Action

### Make pymemgpt an Optional Dependency

**Modification to [`pyproject.toml`](../pyproject.toml):**

```toml
[tool.poetry.dependencies]
python = ">=3.10,<3.14"  # Unlock Python 3.13 for base install
pymemgpt = { version = "^0.3.25", optional = true }

[tool.poetry.extras]
memgpt-baseline = ["pymemgpt"]
```

**Installation Commands:**

```bash
# MAS-only benchmarks (Python 3.13 compatible)
poetry install

# Full comparison including MemGPT baseline (Python <3.13)
poetry install -E memgpt-baseline
```

**Fallback Check in Code:**

Add to [`model_interfaces/memgpt_interface.py`](../model_interfaces/memgpt_interface.py):

```python
try:
    from memgpt import create_client
    from memgpt.client.client import LocalClient
    from memgpt.data_types import AgentState
    MEMGPT_AVAILABLE = True
except ImportError:
    MEMGPT_AVAILABLE = False
    
    # Stub class to prevent import errors
    class MemGPTChatSession:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "MemGPT baseline requires optional dependencies. "
                "Install with: poetry install -E memgpt-baseline"
            )
```

Update [`runner/run_benchmark.py`](../runner/run_benchmark.py#L72):

```python
if name == "memgpt":
    from model_interfaces.memgpt_interface import MEMGPT_AVAILABLE, MemGPTChatSession
    if not MEMGPT_AVAILABLE:
        raise ValueError(
            "Agent 'memgpt' requires optional dependencies.\n"
            "Install with: poetry install -E memgpt-baseline"
        )
    return MemGPTChatSession(run_name=run_name)
```

---

## 8. Alternative: Migrate to Letta

If MemGPT baseline comparisons are critical long-term:

### Migration Checklist

1. **Replace dependency:**
   ```bash
   poetry remove pymemgpt
   poetry add letta
   ```

2. **Refactor `memgpt_interface.py`:**
   - Replace `from memgpt import create_client` with Letta SDK imports
   - Update client initialization to Letta API
   - Adapt agent configuration schema

3. **Update proxy layer:**
   - Verify Letta's API endpoint structure
   - Confirm token logging compatibility

4. **Regression testing:**
   - Re-run historical benchmarks
   - Document API incompatibilities
   - Update baseline metrics

**Estimated Effort:** 2-4 developer days + validation

---

## 9. Current Recommendation

**Short-term (Next 2 Weeks):**
1. Implement Option C (Optional Dependency)
2. Document installation modes in README
3. Update CI/CD workflows to test both modes

**Long-term (Next Quarter):**
1. Evaluate Letta stability and API maturity
2. Plan migration if Letta adoption grows in research community
3. Consider deprecating MemGPT baseline if migration proves too costly

---

## 10. Verification Commands

```bash
# Confirm actual usage (excluding .venv)
cd benchmarks/goodai-ltm-benchmark
grep -r "from memgpt" . --include="*.py" --exclude-dir=".venv"

# Expected results:
# ./model_interfaces/memgpt_interface.py (3 imports)
# ./runner/run_benchmark.py (1 import)

# Check for MemGPT agent references
grep -r "memgpt" . --include="*.py" --include="*.md" --exclude-dir=".venv"
```

---

## Appendix: File Inventory

| File | Purpose | Status |
|------|---------|--------|
| `model_interfaces/memgpt_interface.py` | MemGPT agent wrapper | ✅ Active |
| `model_interfaces/memgpt_proxy.py` | OpenAI API proxy | ✅ Active |
| `model_interfaces/memgpt-logs.jsonl` | Token usage logs | 🔄 Runtime artifact |
| `runner/run_benchmark.py` | Agent orchestrator | ✅ Active (line 72) |
| `README.md` | Agent documentation | ✅ Active (line 85) |

**Total Active Lines:** ~200 lines of MemGPT-specific code