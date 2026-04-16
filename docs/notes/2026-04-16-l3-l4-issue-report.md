The SCM TRA team reported a High-severity bug. The newly deployed YAAM v2 API container returns `501 Not Implemented` for L3 and L4 endpoints. The root cause is missing Dependency Injection in `src/evaluation/agent_wrapper.py`. We mocked/bypassed this in our tests, but the physical Docker container lifespan relies on this file to instantiate the `UnifiedMemorySystem`, and it currently leaves `l3_tier` and `l4_tier` as `None`.

**Task:** Fix the missing Dependency Injection in `src/evaluation/agent_wrapper.py`.

**Step 1: Instantiate Adapters and Tiers**
1. Locate the initialization sequence in `src/evaluation/agent_wrapper.py` (likely inside `initialize_state` or the `AgentWrapperState` factory).
2. Import the physical adapters and tiers: `QdrantAdapter`, `Neo4jAdapter`, `TypesenseAdapter`, `EpisodicMemoryTier`, and `SemanticMemoryTier`.
3. Instantiate the adapters (they will automatically pick up the environment variables like `QDRANT_URL`, etc.).
4. Instantiate the tiers:
   - `episodic_tier = EpisodicMemoryTier(vector_db=qdrant_adapter, graph_db=neo4j_adapter)`
   - `semantic_tier = SemanticMemoryTier(search_db=typesense_adapter)`

**Step 2: Inject into UnifiedMemorySystem**
1. Update the `UnifiedMemorySystem` constructor to explicitly include the new tiers:
   ```python
   memory_system = UnifiedMemorySystem(
       redis_client=redis_client,
       knowledge_manager=NullKnowledgeStoreManager(), # Keep existing
       llm_client=llm_client,
       l1_tier=l1_tier,
       l2_tier=l2_tier,
       promotion_engine=promotion_engine,
       l3_tier=episodic_tier, # ADDED
       l4_tier=semantic_tier  # ADDED
   )
   ```

**Step 3: Lifecycle Management (Important)**
1. Ensure that if the adapters require an asynchronous `await adapter.connect()` or `await tier.initialize()`, it is properly called during the FastAPI lifespan startup logic inside `server.py` or wherever `wrapper.initialize()` is awaited.

**Step 4: Rebuild & Verify**
1. Rebuild the container: `docker-compose up -d --build mas-agent`
2. Perform a local `curl` test against `/v2/memory/l3/query` (even with an empty/dummy payload, it should now return a `422 Validation Error` or `502 Bad Gateway` from LLM, but **NOT** `501 Not Implemented`).

**Output:** Provide the specific lines of code you changed in `agent_wrapper.py` and confirm the successful startup and curl test of the rebuilt container.

----


In addition to the hotfix for `agent_wrapper.py`, we need to implement an automated verification mechanism to ensure L1-L4 tiers are always properly instantiated in the container. This will prevent regressions like the 501 error we just encountered.

**Task 1: Apply the Hotfix**
1. Update `src/evaluation/agent_wrapper.py` to correctly instantiate `EpisodicMemoryTier` (L3) and `SemanticMemoryTier` (L4) and inject them into the `UnifiedMemorySystem`. (Refer to the previous architectural RCA).

**Task 2: Create a V2 Healthcheck Script**
1. Create a bash script at `scripts/healthcheck_v2.sh`.
2. The script should:
   - Accept an optional `BASE_URL` argument (default: `http://localhost:8080`).
   - Use `curl` to probe the following endpoints:
     - `POST /v2/memory/l2/facts` (action: retrieve)
     - `POST /v2/memory/l3/query` (with dummy payload)
   - **Crucial Logic:** The script must fail (exit code 1) if it receives an **HTTP 501 Not Implemented**.
   - **Note:** It should accept `HTTP 422` (Validation Error) or `HTTP 502` (LLM Error) as a "partial success" for the purpose of this check, as these codes prove that the Tiers are at least initialized and reachable.

**Task 3: Integration (Optional but recommended)**
1. Add a `make healthcheck` command to the `Makefile` that triggers this script.
2. Update the `docker-compose.yml` (if appropriate) or provide a one-liner command to run this check immediately after `docker-compose up`.

**Output:**
1. Confirm the `agent_wrapper.py` changes.
2. Provide the content of `scripts/healthcheck_v2.sh`.
3. Provide the output of the script running against the newly rebuilt container on `skz-dev-lv`.