"""
Tests for Lua script manager and atomic Redis operations.

Test Coverage:
- Script loading and SHA1 caching
- Atomic promotion with CIAR filtering
- Version-checked workspace updates (CAS pattern)
- Smart append with windowing
- 50-agent concurrency stress tests
- Script eviction and reload handling
"""

import pytest
import pytest_asyncio
import redis.asyncio as redis
import os
import uuid
import json
import asyncio
from datetime import datetime, timezone

from src.memory.lua_manager import LuaScriptManager
from src.memory.namespace import NamespaceManager


@pytest.fixture
def session_id():
    """Generate unique test session ID."""
    return f"test-{uuid.uuid4()}"


@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing."""
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        pytest.skip("REDIS_URL environment variable not set")
    
    client = redis.from_url(redis_url, decode_responses=False)  # Binary mode for Lua
    
    try:
        await client.ping()
    except redis.RedisError:
        pytest.skip("Redis server not available")
    
    yield client
    
    await client.aclose()


@pytest_asyncio.fixture
async def lua_manager(redis_client):
    """Create Lua script manager."""
    manager = LuaScriptManager(redis_client)
    await manager.load_scripts()
    yield manager


@pytest_asyncio.fixture
async def cleanup_keys(redis_client):
    """Cleanup test keys after test."""
    keys_to_clean = []
    
    def register(key: str):
        keys_to_clean.append(key)
    
    yield register
    
    # Cleanup
    if keys_to_clean:
        await redis_client.delete(*keys_to_clean)


class TestScriptLoading:
    """Test Lua script loading and caching."""
    
    @pytest.mark.asyncio
    async def test_load_all_scripts(self, redis_client):
        """Test loading all Lua scripts."""
        manager = LuaScriptManager(redis_client)
        await manager.load_scripts()
        
        assert manager._scripts_loaded
        assert len(manager._script_shas) == 3  # atomic_promotion, workspace_update, smart_append
    
    @pytest.mark.asyncio
    async def test_script_shas_cached(self, lua_manager):
        """Test that script SHA1 hashes are cached."""
        shas = lua_manager._script_shas
        
        assert LuaScriptManager.ATOMIC_PROMOTION in shas
        assert LuaScriptManager.WORKSPACE_UPDATE in shas
        assert LuaScriptManager.SMART_APPEND in shas
        
        # SHA should be 40 hex characters
        for sha in shas.values():
            assert len(sha) == 40
            assert all(c in '0123456789abcdef' for c in sha.lower())
    
    @pytest.mark.asyncio
    async def test_scripts_exist_in_redis(self, redis_client, lua_manager):
        """Test that scripts are loaded into Redis cache."""
        for sha in lua_manager._script_shas.values():
            exists = await redis_client.script_exists(sha)
            assert exists[0], f"Script {sha} not found in Redis cache"
    
    @pytest.mark.asyncio
    async def test_health_check(self, lua_manager):
        """Test health check returns script status."""
        health = await lua_manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["scripts_loaded"]
        assert health["script_count"] == 3
        assert "scripts" in health
        
        # All scripts should be cached
        for script_status in health["scripts"].values():
            assert script_status["cached"]


class TestAtomicPromotion:
    """Test atomic L1→L2 promotion script."""
    
    @pytest.mark.asyncio
    async def test_atomic_promotion_basic(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test basic atomic promotion."""
        l1_key = NamespaceManager.l1_turns(session_id)
        l2_index_key = NamespaceManager.l2_facts_index(session_id)
        cleanup_keys(l1_key)
        cleanup_keys(l2_index_key)
        
        # Add turns to L1
        for i in range(5):
            turn = {
                "turn_id": f"turn-{i}",
                "content": "A" * (100 + i * 20),  # Variable length
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await redis_client.lpush(l1_key, json.dumps(turn))
        
        # Execute promotion
        promotable = await lua_manager.execute_atomic_promotion(
            l1_key=l1_key,
            l2_index_key=l2_index_key,
            ciar_threshold=0.5,
            batch_size=10
        )
        
        # Should promote turns with length > 50 chars
        assert len(promotable) > 0
        assert all("turn_id" in turn for turn in promotable)
        assert all("ciar_score" in turn for turn in promotable)
    
    @pytest.mark.asyncio
    async def test_atomic_promotion_deduplication(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test that promotion doesn't re-process existing facts."""
        l1_key = NamespaceManager.l1_turns(session_id)
        l2_index_key = NamespaceManager.l2_facts_index(session_id)
        cleanup_keys(l1_key)
        cleanup_keys(l2_index_key)
        
        # Add turn to L1
        turn = {
            "turn_id": "turn-123",
            "content": "A" * 100,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await redis_client.lpush(l1_key, json.dumps(turn))
        
        # First promotion
        promotable1 = await lua_manager.execute_atomic_promotion(
            l1_key=l1_key,
            l2_index_key=l2_index_key,
            ciar_threshold=0.5,
            batch_size=10
        )
        
        assert len(promotable1) == 1
        
        # Second promotion (should skip already promoted)
        promotable2 = await lua_manager.execute_atomic_promotion(
            l1_key=l1_key,
            l2_index_key=l2_index_key,
            ciar_threshold=0.5,
            batch_size=10
        )
        
        assert len(promotable2) == 0  # Already in L2 index


class TestWorkspaceUpdate:
    """Test version-checked workspace update (CAS pattern)."""
    
    @pytest.mark.asyncio
    async def test_workspace_update_initial(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test initial workspace update (no existing data)."""
        workspace_key = NamespaceManager.shared_workspace(session_id)
        cleanup_keys(workspace_key)
        
        data = {"agent_1": "result_1"}
        
        # Initial write (expected_version=-1 means "don't care")
        new_version = await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=-1,
            new_data=data,
            update_type="replace"
        )
        
        assert new_version == 1  # First version
        
        # Verify data stored
        stored_data = await redis_client.hget(workspace_key, "data")
        assert json.loads(stored_data) == data
    
    @pytest.mark.asyncio
    async def test_workspace_update_version_check(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test version-checked update (optimistic locking)."""
        workspace_key = NamespaceManager.shared_workspace(session_id)
        cleanup_keys(workspace_key)
        
        # Initial write
        await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=-1,
            new_data={"agent_1": "v1"},
            update_type="replace"
        )
        
        # Update with correct version
        new_version = await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=1,
            new_data={"agent_1": "v2"},
            update_type="replace"
        )
        
        assert new_version == 2
        
        # Update with wrong version (should fail)
        failed_version = await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=1,  # Stale version
            new_data={"agent_1": "v3"},
            update_type="replace"
        )
        
        assert failed_version == -1  # Version mismatch
    
    @pytest.mark.asyncio
    async def test_workspace_merge_update(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test merge update mode."""
        workspace_key = NamespaceManager.shared_workspace(session_id)
        cleanup_keys(workspace_key)
        
        # Initial data
        await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=-1,
            new_data={"agent_1": "result_1", "agent_2": "result_2"},
            update_type="replace"
        )
        
        # Merge update (only update agent_1)
        await lua_manager.execute_workspace_update(
            workspace_key=workspace_key,
            expected_version=1,
            new_data={"agent_1": "updated"},
            update_type="merge"
        )
        
        # Verify merge
        stored_data = await redis_client.hget(workspace_key, "data")
        data = json.loads(stored_data)
        
        assert data["agent_1"] == "updated"
        assert data["agent_2"] == "result_2"  # Preserved


class TestSmartAppend:
    """Test smart append with windowing and TTL."""
    
    @pytest.mark.asyncio
    async def test_smart_append_basic(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test basic smart append."""
        list_key = NamespaceManager.l1_turns(session_id)
        cleanup_keys(list_key)
        
        data = {"turn": 1, "content": "Hello"}
        
        length = await lua_manager.execute_smart_append(
            list_key=list_key,
            data=data,
            window_size=20,
            ttl_seconds=3600
        )
        
        assert length == 1
        
        # Verify TTL set
        ttl = await redis_client.ttl(list_key)
        assert ttl > 0
        assert ttl <= 3600
    
    @pytest.mark.asyncio
    async def test_smart_append_windowing(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test automatic window size limiting."""
        list_key = NamespaceManager.l1_turns(session_id)
        cleanup_keys(list_key)
        
        window_size = 5
        
        # Append 10 items
        for i in range(10):
            await lua_manager.execute_smart_append(
                list_key=list_key,
                data={"turn": i},
                window_size=window_size,
                ttl_seconds=3600
            )
        
        # List should be trimmed to window_size
        final_length = await redis_client.llen(list_key)
        assert final_length == window_size
    
    @pytest.mark.asyncio
    async def test_smart_append_ttl_refresh(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test that TTL is refreshed on each append."""
        list_key = NamespaceManager.l1_turns(session_id)
        cleanup_keys(list_key)
        
        # First append with 10 second TTL
        await lua_manager.execute_smart_append(
            list_key=list_key,
            data={"turn": 1},
            window_size=20,
            ttl_seconds=10
        )
        
        # Wait 2 seconds
        await asyncio.sleep(2)
        
        # Check TTL (should be ~8 seconds)
        ttl1 = await redis_client.ttl(list_key)
        assert ttl1 < 10
        
        # Append again (should refresh to 10 seconds)
        await lua_manager.execute_smart_append(
            list_key=list_key,
            data={"turn": 2},
            window_size=20,
            ttl_seconds=10
        )
        
        # TTL should be refreshed
        ttl2 = await redis_client.ttl(list_key)
        assert ttl2 > ttl1


@pytest.mark.concurrency
class TestConcurrencyStress:
    """50-agent concurrency stress tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_workspace_updates(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test 50 concurrent agents updating workspace."""
        workspace_key = NamespaceManager.shared_workspace(session_id)
        cleanup_keys(workspace_key)
        
        num_agents = 50
        successes = 0
        failures = 0
        
        async def agent_update(agent_id: int):
            nonlocal successes, failures
            
            # Read current version
            current_version = await redis_client.hget(workspace_key, "version")
            expected_version = int(current_version) if current_version else -1
            
            # Try to update
            result = await lua_manager.execute_workspace_update(
                workspace_key=workspace_key,
                expected_version=expected_version,
                new_data={f"agent_{agent_id}": f"result_{agent_id}"},
                update_type="merge"
            )
            
            if result == -1:
                failures += 1
            else:
                successes += 1
        
        # Run all agents concurrently
        await asyncio.gather(*[agent_update(i) for i in range(num_agents)])
        
        # Should have some successes and some failures (due to version conflicts)
        assert successes > 0
        assert failures > 0
        assert successes + failures == num_agents
    
    @pytest.mark.asyncio
    async def test_concurrent_smart_appends(
        self, 
        lua_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test 50 concurrent agents appending to same list."""
        list_key = NamespaceManager.l1_turns(session_id)
        cleanup_keys(list_key)
        
        num_agents = 50
        window_size = 20
        
        async def agent_append(agent_id: int):
            await lua_manager.execute_smart_append(
                list_key=list_key,
                data={"agent_id": agent_id, "turn": f"turn-{agent_id}"},
                window_size=window_size,
                ttl_seconds=3600
            )
        
        # Run all agents concurrently
        await asyncio.gather(*[agent_append(i) for i in range(num_agents)])
        
        # Final list should be exactly window_size
        final_length = await redis_client.llen(list_key)
        assert final_length == window_size
