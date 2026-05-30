# YAAM Full Synthetic Readiness Report

- Verdict: **PASS**
- Project namespace: `agentic-scm-tra26`
- Session: `agentic-scm-tra26-readiness-20260530T153445Z`
- Task: `agentic-scm-tra26-readiness-20260530T153445Z-task`
- REST: `http://192.168.107.187:8002`
- MCP: `http://192.168.107.187:8003/mcp`
- Traceparent: `00-abcdefabcdefabcdefabcdefabcdefab-fedcbafedcbafedc-01`
- JSON evidence: `outputs/yaam_readiness/20260530T153445Z-agentic-scm-tra26-full-synthetic-results.json`

## Checks

| Check | Result |
| --- | --- |
| `health_ok` | pass |
| `l2_store_has_id` | pass |
| `l2_same_session_has_marker` | pass |
| `l2_isolation_empty_or_marker_absent` | pass |
| `l3_assimilate_has_id` | pass |
| `l3_after_no_dimension_error` | pass |
| `l4_finalize_has_id` | pass |
| `negative_l2_rejected` | pass |
| `mcp_discovery_ok` | pass |
| `mcp_health_project_ok` | pass |
| `mcp_read_tools_ok` | pass |
| `mcp_write_denied` | pass |

## Operation Summary

| Operation | Status | Detail |
| --- | ---: | --- |
| REST health | 200 / pass | `{"agent": {"agent_id": "mas-full__baseline", "llm_providers": ["openrouter", "gemini", "mistral"], "memory_system": true, "status": "healthy"}, "agent_type": "full", "agent_variant": "baseline", "l1": {"config": {"postgres_backup_enabled": true, "ttl_hours": 2...<truncated>` |
| REST L2 store synthetic fact | 200 / pass | `{"fact_id": "dd17ed71-3aa1-467e-84a3-0725a7762ca0", "status": "success"}` |
| REST L2 retrieve same session | 200 / pass | `{"facts": [{"access_count": 0, "age_decay": 1.0, "certainty": 1.0, "ciar_score": 1.0, "content": "TRA readiness deterministic L2 fact marker agentic-scm-tra26-readiness-20260530T153445Z", "created_at": "2026-05-30T15:34:45.214088", "extracted_at": "2026-05-30T...<truncated>` |
| REST L2 retrieve isolation session | 200 / pass | `{"facts": [], "status": "success"}` |
| REST L3 query before assimilation | 200 / pass | `{"provenance": {"agent_id": "tra-readiness-agent", "session_id": "agentic-scm-tra26-readiness-20260530T153445Z"}, "results": [], "status": "success"}` |
| REST L3 assimilate synthetic episode | 201 / pass | `{"episode_id": "ep-b2e83405", "status": "success"}` |
| REST L3 query after assimilation | 200 / pass | `{"provenance": {"agent_id": "tra-readiness-agent", "session_id": "agentic-scm-tra26-readiness-20260530T153445Z"}, "results": [{"content": "TRA readiness synthetic L3 episode marker agentic-scm-tra26-readiness-20260530T153445Z. Planner obse", "metadata": {"clie...<truncated>` |
| REST L4 finalize synthetic artifact | 201 / pass | `{"knowledge_id": "kd-6c832092", "status": "success"}` |
| REST public memory query after L4 finalize | 200 / pass | `{"leakage_guard": {"checked_item_count": 1, "filtered_item_count": 0, "forbidden_fields": ["rejected_task_diagnostics", "curation_record", "curation_notes", "ground_truth_reasoning", "hidden_gold", "judge_reasoning", "judge_notes", "ground_truth_answer"], "lea...<truncated>` |
| REST L2 negative missing content | 400 / pass | `{"detail": "Content requires for 'store' action."}` |
| MCP initialize | 200 / pass | `{"id": 1, "jsonrpc": "2.0", "result": {"capabilities": {"experimental": {}, "prompts": {"listChanged": false}, "resources": {"listChanged": false, "subscribe": false}, "tools": {"listChanged": false}}, "protocolVersion": "2025-03-26", "serverInfo": {"name": "y...<truncated>` |
| MCP tools/list | 200 / pass | `{"id": 2, "jsonrpc": "2.0", "result": {"tools": [{"description": "", "inputSchema": {"properties": {"agent_id": {"title": "Agent Id", "type": "string"}, "allowed_fields": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": ...<truncated>` |
| MCP resources/list | 200 / pass | `{"id": 3, "jsonrpc": "2.0", "result": {"resources": [{"description": "", "mimeType": "text/plain", "name": "health_resource", "uri": "yaam://health"}, {"description": "", "mimeType": "text/plain", "name": "ciar_config_resource", "uri": "yaam://config/ciar"}, {...<truncated>` |
| MCP prompts/list | 200 / pass | `{"id": 4, "jsonrpc": "2.0", "result": {"prompts": [{"arguments": [{"name": "query", "required": true}], "description": "", "name": "yaam.prompt.evidence_table"}, {"arguments": [{"name": "session_id", "required": true}], "description": "", "name": "yaam.prompt....<truncated>` |
| MCP yaam.health.check | 200 / pass | `{"id": 5, "jsonrpc": "2.0", "result": {"content": [{"text": "{\n  \"summary\": \"Health checked.\",\n  \"health\": {\n    \"status\": \"ok\",\n    \"checked_at\": \"2026-05-30T15:35:53.034529Z\",\n    \"tiers\": {\n      \"L1\": {\n        \"tier\": \"L1_activ...<truncated>` |
| MCP yaam.memory.get_context | 200 / pass | `{"id": 6, "jsonrpc": "2.0", "result": {"content": [{"text": "{\n  \"summary\": \"Context assembled.\",\n  \"context\": {\n    \"session_id\": \"agentic-scm-tra26-readiness-20260530T153445Z\",\n    \"items\": [\n      {\n        \"content\": \"TRA readiness det...<truncated>` |
| MCP yaam.memory.query | 200 / pass | `{"id": 7, "jsonrpc": "2.0", "result": {"content": [{"text": "{\n  \"summary\": \"Memory query complete.\",\n  \"results\": [\n    {\n      \"content\": \"TRA readiness synthetic L3 episode marker agentic-scm-tra26-readiness-20260530T153445Z. Planner obse\",\n ...<truncated>` |
| MCP yaam.evidence.table | 200 / pass | `{"id": 8, "jsonrpc": "2.0", "result": {"content": [{"text": "{\n  \"summary\": \"Evidence table assembled.\",\n  \"evidence_table\": {\n    \"rows\": [\n      {\n        \"claim\": \"TRA readiness synthetic L3 episode marker agentic-scm-tra26-readiness-2026053...<truncated>` |
| MCP yaam.l2.store_fact denied by default | 200 / pass | `{"id": 9, "jsonrpc": "2.0", "result": {"content": [{"text": "Error executing tool yaam.l2.store_fact: {\"error\":{\"code\":\"permission.writes_disabled\",\"message\":\"Write operations require YAAM_MCP_ENABLE_WRITES=true.\",\"retryable\":false,\"partial\":fals...<truncated>` |
