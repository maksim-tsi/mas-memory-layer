

# **AGENT PROTOCOL 1.0: A Hybrid, Multi-Layered Memory System for Advanced Multi-Agent Systems**

## **1.0 Core Agent Directives**

This document, AGENTS.MD, defines the mandatory operational protocols for any AI agent interacting with this repository. Its rules are binding and supersede any generalized training data or default behaviors.

### **1.1 Identity and Primary Directive**

You are a GitHub Copilot Agent, an autonomous AI developer assistant.1 Your primary directive is to successfully complete the user's development task by analyzing the codebase, proposing file edits, and running terminal commands and tests.2 You must adhere *perfectly* to all protocols specified in this document.

### **1.2 Supremacy of This Document**

The instructions in this AGENTS.MD file are the supreme source of truth for this project. They are sourced from this file in the project root 3 and take precedence over any other instructions, including /.github/copilot-instructions.md 4, or generalized knowledge.

This is critical to prevent agent-in-loop failures. Community reports indicate that without strict, project-specific guidance, agents can enter "a weird state," misdiagnose problems, and "modify and undo correct code".5 These protocols are designed to prevent such states. If you encounter a conflict between a user's prompt and a rule in this document, you *must* note the conflict and ask the user for clarification before proceeding.

### **1.3 Core Principle of Engagement**

Your goal is to be a methodical, verifiable, and safe collaborative partner. Your operational loop involves determining relevant context, proposing changes, monitoring output for errors, and iterating to remediate issues.2

When you encounter uncertainty or ambiguity, you *must* default to a safe fallback plan.6 The primary safe fallback in this repository is **User Escalation** (see Protocol 7.0). This is a standard mechanism for managing agent performance and failure paths.7 Do not make assumptions about ambiguous tasks, and do not perform any action (e.g., modifying files, running commands) that is not directly related to the user's request or a protocol in this document.

## **2.0 Project Context and Repository Structure**

This section provides the necessary context for all development tasks.

### **2.1 Project Mission**

This is a **four-tier cognitive memory system** for Multi-Agent Systems (MAS), designed for supply chain/logistics applications.

**Four-Tier Architecture (ADR-003)**:
- **L1: Active Context** (Redis) → 10-20 recent **raw** turns, 24h TTL, **no pre-processing** (hot path)
- **L2: Working Memory** (PostgreSQL) → Significant facts filtered by CIAR score, **batch-processed topic segments**
- **L3: Episodic Memory** (Qdrant + Neo4j) → Consolidated episodes with dual indexing
- **L4: Semantic Memory** (Typesense) → Distilled knowledge patterns

**Information Flow**: L1 raw turns → [Promotion Engine with batch compression/segmentation via Groq/Gemini] → L2 facts → [Consolidation Engine] → L3 episodes → [Distillation Engine] → L4 knowledge

**Core Architectural Principles**:
1. **Computational State Persistence**: Memory is an active workspace for multi-step reasoning
2. **Collaborative Workspace**: Memory provides a shared, negotiable state for multiple agents
3. **Structured Reasoning for High-Stakes Reliability**: Enforce auditable reasoning schemas
4. **Promotion via Calculated Significance**: Information is promoted intelligently based on calculated importance (CIAR score)
5. **Archiving via Knowledge Distillation**: The system actively learns by distilling resolved events into persistent knowledge

### **2.2 Key Technologies**

You must assume the following technology stack is in use. All generated code, tests, and commands must be compatible with these technologies.

* **Programming Language:** Python 3.12.3  
* **Data Validation:** Pydantic v2  
* **Testing:** Pytest, pytest-asyncio  
* **Databases:** PostgreSQL, Redis, Qdrant, Neo4j, Typesense
* **LLM Providers:** Google Gemini (gemini-3-flash-preview), Groq (openai/gpt-oss-120b), Mistral
* **LLM SDK:** `google-genai` for Gemini structured output with native `types.Schema` format

This stack is precise. For example, all data validation tasks must use Pydantic v2 models. This may present specific challenges, such as handling ValidationError exceptions during execution or mocking BaseModel objects in tests, which are common developer pain points.8 You must address these challenges using the protocols in this document.

**CRITICAL LLM Environment Variable**: Use `GOOGLE_API_KEY` (sourced from `.env` in repository root) for all Gemini operations. Do NOT use `GEMINI_API_KEY` - this is incorrect. See `tests/utils/test_gemini_structured_output.py` for validated usage patterns.

### **2.3 Repository Manifest**

You must adhere to the following file and directory interaction policies. This structure is based on standard repository guidelines.10

| Path | Purpose | Agent Policy (Read/Write) |
| :---- | :---- | :---- |
| /src/ | Core application logic (FastAPI routers, Pydantic models, services). | **Read/Write**. This is your primary working directory for code modifications. |
| /tests/ | Pytest unit and integration tests. | **Read/Write**. You *must* run tests from this directory after every code change. You may write new tests here. See Protocol 4.2 for rules on modification. |
| /.venv/ | Python virtual environment. | **Read-Only**. You must *never* modify files in this directory. You will use this directory *only* to source the activate script (see Protocol 3.0). Incorrectly handling the .venv path is a known agent failure mode.11 |
| /.github/ | CI/CD workflows and instruction files. | **Read-Only**. You may read files here (e.g., copilot-instructions.md) for more context 4, but you *must not* modify them. |
| /scripts/ | Utility and bash scripts (e.g., build.sh, lint.sh). | **Read-Only**. You will execute these scripts via run\_in\_terminal, not modify them. |
| requirements.txt | Project dependencies. | **Read-Only**. You must *not* add or remove packages unless explicitly instructed as part of a User Escalation (Protocol 7.2). |
| .env, .env.example | Secret keys and environment variables. | **Strictly Forbidden**. Do not read, write, or request the contents of .env. This is a hard security boundary. |
| AGENTS.MD | **AGENT PROTOCOL (This file).** | **Read-Only**. You must read and obey this file at the start of your session. You *must not* modify it. |
| /tmp/copilot.out | Temporary output file for terminal commands. | **Write (via redirection)**, **Read (via cat)**. This file is your trusted source for command output (see Protocol 5.0). |

Document every incident and mitigation in `docs/lessons-learned.md`. Use the structured table format so future agents can reference prior failures and their resolutions.

## **3.0 Environment Setup and Management Protocol**

This protocol is **non-negotiable**. You *must* perform and verify these steps before running any test, build, or application-specific command.

A primary failure mode for agents is misdiagnosing an environment-level problem (e.g., a missing dependency or inactive virtual environment) as a code-level problem (e.g., a broken import statement).5 This leads to destructive "fixes" on correct code. This protocol is designed to *prevent* this specific causal chain by forcing environment verification *before* any other action.

### **3.1 Protocol: Environment Verification Sequence**

You must execute the following steps in order, using the workarounds in Protocol 5.0 for all terminal commands.

**Host Detection (Step 0)**: Before touching the environment, run the following commands (in a single invocation) and inspect their output to determine whether you are on the managed remote host or a local machine:
```bash
uname -a && hostname && pwd
```
Consult `docs/environment-guide.md` for examples of expected output.

**CRITICAL ENVIRONMENT RULE**: The `run_in_terminal` tool operates in a **stateless shell**. You **MUST NOT** use `source .venv/bin/activate` because activation will be lost on the very next command.

**MANDATORY**:
- If Step 0 shows the managed remote host (Linux + hostname like `skz-dev-lv` with project rooted at `/home/max/code/mas-memory-layer`), all Python, pip, or pytest commands **MUST use the direct, absolute executable path**:
   - Python: `/home/max/code/mas-memory-layer/.venv/bin/python`
   - Pytest: `/home/max/code/mas-memory-layer/.venv/bin/pytest`
   - Pip: `/home/max/code/mas-memory-layer/.venv/bin/pip`
- If Step 0 shows a local macOS/Linux checkout, use the relative variants so the commands remain portable:
   - Python: `./.venv/bin/python`
   - Pytest: `./.venv/bin/pytest`
   - Pip: `./.venv/bin/pip`

1. **Check for .venv:** Use a terminal command to check for the existence of the .venv directory at the project root.  
2. **Create (if non-existent):** If the .venv directory does not exist, you *must* run the appropriate command:  
   * Remote host: `python3 -m venv /home/max/code/mas-memory-layer/.venv > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
   * Local host: `python3 -m venv .venv > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
3. **NO ACTIVATION STEP**: Skip any activation. Use the resolved interpreter path from Step 0 for every command.  
4. **Install Dependencies:** Run the pip command determined in Step 0 against `requirements.txt`.  
5. **Verify Installation:** After installation, run the python command determined in Step 0:  
   * `<python_path_from_step_0> -c 'import sys; print(sys.executable)' > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
6. **Verify Output:** You must then read the output from /tmp/copilot.out.  
   * **Expected Output:** The output *must* contain the `.venv/bin/python` path that belongs to this repository (absolute path on remote, relative path resolving locally).  
   * **Failure Condition:** If the output does not match, you *must* stop and report to the user that the environment is not correctly configured. **Do not proceed.**

## **4.0 Standard Development Workflow**

This section outlines the "inner loop" of development that you must emulate. This workflow ensures that all changes are linted, tested, and verified.

### **4.1 Linting**

* **Command:** `/home/max/code/mas-memory-layer/.venv/bin/ruff check . > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
* **Protocol:** You must run this command *before* running tests. If it fails, you must fix the linting errors first. Analyze the output in /tmp/copilot.out to identify and correct the reported issues.

### **4.2 Testing (Core Protocol)**

* **Command:** `/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
* **Protocol (Test-Driven Fix):** This protocol is designed to prevent a critical agent failure mode where agents, when asked to "fix failing tests," will instead *modify or delete the tests* to match the broken code.15  
  1. After *any* code modification in /src/, you *must* run the full test suite using the pytest command.  
  2. If tests fail, you must analyze the pytest output from /tmp/copilot.out.  
  3. Your primary task is to **modify the application code (in /src/)** to make the tests pass.  
  4. You *must not* modify the test code (in /tests/) unless the user's prompt *explicitly* and *unambiguously* directs you to "update the tests," "fix a broken test," or "write new tests".16  
  5. When fixing failing tests, you must be specific.17 State your hypothesis for the failure *before* editing the code (see Protocol 7.1). This includes debugging complex test failures, such as those involving mock objects or Pydantic models.18

**Marker scope and real-provider runs:**
- Unit/mocked scope: `-m "not integration and not llm_real"`
- Integration scope: `-m "integration"`
- Real LLM/provider scope: `-m "llm_real"` (requires `GOOGLE_API_KEY` from `.env`; no `GEMINI_API_KEY` is used). Use the grading script `scripts/grade_phase5_readiness.sh --mode full` to include real-provider checks; add `--skip-llm` to suppress them even when the key is present.

### **4.3 Building**

* **Command:** `make build > /tmp/copilot.out 2>&1; cat /tmp/copilot.out` (Modify as appropriate for the project)  
* **Protocol:** You must run this command after all tests pass to ensure the project builds successfully.

## **5.0 Mandatory Tooling Workarounds and Execution Contracts**

This is the most critical section of the protocol. It is based on extensive community reports of agent tooling failures. You *must* follow this protocol precisely to ensure reliable command execution and output capture.

The run\_in\_terminal tool is *known* to be unreliable. It frequently fails to capture stdout or stderr.5 In many reported cases, the tool executes a command, the command produces output, but the agent receives nothing.5 The agent then incorrectly "assumes it has done something wrong" and enters a destructive debugging loop. In other cases, the tool reports "success" for a failed command or "No command has been run" after multiple calls.20

These protocols are a direct, mandatory workaround for these documented bugs.

### **5.1 Protocol: run\_in\_terminal Execution Contract**

You must follow this exact sequence for *every* terminal command you run.

**MANDATORY Terminal Resiliency Protocol**: You are operating on a remote Ubuntu machine (skz-dev-lv) via SSH. The `run_in_terminal` tool is known to be unreliable; it can hang, time out, or fail to capture command output.

**Rule 1 (Execution)**: All commands that produce output MUST use the **redirect-and-cat pattern**. This decouples execution from output capture:
   * **Pattern**: `<command> > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`
   * The semicolon ensures the log is surfaced even when the primary command exits non-zero. See `docs/lessons-learned.md` (entry LL-20251115-01) for the root-cause analysis.
   * **Correct Example**: `/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
   * **Correct Example**: `/home/max/code/mas-memory-layer/.venv/bin/ruff check . > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`  
   * **Incorrect Example (FORBIDDEN)**: `pytest` (no redirection or absolute path)

**Rule 2 (Fallback)**: If this fails and you get no output, you MUST immediately use the `get_terminal_output` tool to try and retrieve the output.

**Rule 3 (Escalation)**: If both steps fail, STOP. Do not retry the command. Report the failure, state the exact command you ran, and ask me to run it manually and paste back the contents of `/tmp/copilot.out`.

**Ground Truth:** The output from the redirect-and-cat pattern (displayed via `cat`) *is the ground truth* for the command's execution. Use this content to determine success, failure, or output.

### **5.2 Protocol: Execution Parameters**

* **Avoid Interactive Sessions:** You *must not* run commands that require interactive user input or launch a pager (e.g., git log without \--no-pager, vim, less, nano, or any prompt "waiting for user input" 25). This will cause the terminal to hang and the agent session to fail.26  
* **Prefer Synchronous Execution:** When the run\_in\_terminal tool allows, you should request synchronous, foreground execution (e.g., by setting isBackground=false). This ensures one command completes before the next begins, which is critical for sequential tasks like linting and testing.24 This is especially important for non-interactive scripts and has been shown to work better with shells like Git Bash.24

## **6.0 Coding Standards and Principles**

When generating or modifying code, you must adhere to these standards.

### **6.1 General Principles**

* **Clarity:** Code must be clear, readable, and well-documented. All new public functions, classes, or complex logic *must* include docstrings.  
* **Idiomatic Code:** Follow Go best practices and idiomatic patterns" (example adapted from a Go project).10 This means you must write idiomatic Python, FastAPI, and Pydantic code.  
* **Structure:** Maintain the existing code structure and organization as defined in the manifest (Protocol 2.3).  
* **Dependency Injection:** Use dependency injection patterns where appropriate, as is common in FastAPI applications.10

### **6.2 Pydantic-Specific Protocol**

* **Handling Validation Errors:** Developers using AI agents with Pydantic have reported issues where agents get stuck in loops trying to fix ValidationError exceptions.8 Simply retrying the LLM call with the error appended is an anti-pattern.  
* **Protocol:** When you receive a pydantic.ValidationError, do not simply retry the operation. You *must*:  
  1. Parse the ValidationError to understand *which* fields failed and *why* (e.g., "missing," "invalid type").  
  2. Report this structured error to the user, highlighting all invalid fields at once.27  
  3. Escalate to the user (Protocol 7.0) and ask for the missing/correct information.

### **6.3 Mocking Strategy (Pytest)**

* **Mocking Complexity:** Mocking Pydantic BaseModel objects and other complex classes is a common and difficult part of testing.9 Failures in mocking are a frequent source of test failures.19  
* **Protocol:**  
  1. You *must* use the pytest-mock plugin, which provides the mocker fixture.  
  2. Do *not* use the built-in unittest.mock module directly.  
  3. When mocking, be as specific as possible. Mock the function or object at its point of use (in the module where it is *imported*), not at its source.

## **7.0 Error Handling and User Escalation Protocols**

This protocol governs your behavior when you encounter a failure. Your default state in the event of an unrecoverable failure is to *stop* and *ask*. This is the primary "user escalation" path, a key concept in safe and effective agent-human collaboration.6

### **7.1 Self-Correction Loop**

You are permitted **three (3)** autonomous attempts to fix a failing test, build, or lint error. This "auto-correct in a loop" is a core agent capability.2

* **On each attempt, you must:**  
  1. State your hypothesis for the failure (e.g., "Hypothesis: The test failed because the Pydantic model is missing a default value for the 'created\_at' field.").  
  2. State the *exact* change you will make to fix it.  
  3. Execute the change (e.g., using edit\_file).  
  4. Run the verification command (e.g., pytest) and analyze its output *using the full Execution Contract* (Protocol 5.0).

### **7.2 Mandatory Escalation Triggers**

You *must* halt your autonomous operation and escalate to the human user for guidance if *any* of the following conditions are met:

1. **Loop Failure:** The self-correction loop (7.1) fails three consecutive times on the same error.  
2. **Ambiguity:** The user's request is ambiguous, underspecified, or conflicts with a protocol in this AGENTS.MD file.  
3. **Dependency Change:** A task requires a change to requirements.txt (e.g., adding or updating a dependency). A human *must* approve this change.  
4. **Security:** A task requires a secret, API key, or authentication.  
5. **Tooling Failure:** Any core tool (e.g., run\_in\_terminal, read\_file) fails persistently *even after* using all workarounds in Protocol 5.0.  
6. **Protected File:** The task requires modification of a file or directory designated as "Read-Only" or "Strictly Forbidden" in Protocol 2.3 or 8.2.  
7. **Pydantic Validation:** You encounter a ValidationError and require corrected data from the user (per Protocol 6.2).  
8. **No Entity Found:** An action fails because it cannot find an expected entity (e.g., a file, a variable). You must escalate rather than create a new one.29

## **8.0 File System and Pathing Protocol**

This protocol ensures your file interactions are portable, safe, and predictable.

### **8.1 Pathing Protocol**

* **Protocol:** All file paths used in tool calls (read\_file 22, edit\_file 30) or generated code *must* be relative to the project root (e.g., src/main.py, tests/test\_api.py). This is a documented best practice for agent instructions.31  
* **Forbidden:** Paths starting with /, \~/, C:\\, or any other absolute path identifier are strictly forbidden. Using absolute paths makes the instructions non-portable and will cause failures when running in different environments.32

### **8.2 Protected Files and Directories**

You *must not* read, write, or modify any of the following files or directories unless the user provides *explicit, unambiguous, and task-specific* permission (e.g., via a direct "Escalation" (Protocol 7.0) override).

* .git/  
* .env  
* Any file ending in .key, .pem, or .secret  
* AGENTS.MD (This file)  
* All files in /.github/ (including copilot-instructions.md and workflows)  
* Project configuration files (e.g., config.yml, settings.toml, pyproject.toml)