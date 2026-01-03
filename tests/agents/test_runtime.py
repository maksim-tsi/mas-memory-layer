"""
Tests for MASToolRuntime wrapper.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass
from typing import Any, Optional

from src.agents.runtime import MASToolRuntime, MASContext


@dataclass
class MockToolRuntime:
    """Mock LangChain ToolRuntime for testing."""
    context: Any
    state: dict
    store: Optional[Any] = None
    stream_writer: Optional[Any] = None
    tool_call_id: Optional[str] = None
    config: Optional[Any] = None


class TestMASContext:
    """Test MASContext dataclass."""
    
    def test_create_basic_context(self):
        """Test creating basic context with session_id."""
        context = MASContext(session_id="test-session-123")
        assert context.session_id == "test-session-123"
        assert context.user_id is None
        assert context.organization_id is None
        assert context.agent_id is None
    
    def test_create_full_context(self):
        """Test creating context with all fields."""
        mock_memory = Mock()
        context = MASContext(
            session_id="session-123",
            user_id="user-456",
            organization_id="org-789",
            agent_id="agent-001",
            memory_system=mock_memory,
            enable_l1_cache=False,
            enable_ciar_filtering=False,
            default_min_ciar=0.7
        )
        
        assert context.session_id == "session-123"
        assert context.user_id == "user-456"
        assert context.organization_id == "org-789"
        assert context.agent_id == "agent-001"
        assert context.memory_system is mock_memory
        assert context.enable_l1_cache is False
        assert context.enable_ciar_filtering is False
        assert context.default_min_ciar == 0.7


class TestMASToolRuntime:
    """Test MASToolRuntime wrapper."""
    
    def test_initialization(self):
        """Test runtime wrapper initialization."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="test-123"),
            state={"messages": []}
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        assert mas_runtime.native_runtime is mock_runtime
    
    def test_get_session_id_from_mas_context(self):
        """Test retrieving session_id from MASContext."""
        context = MASContext(session_id="session-abc")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        session_id = mas_runtime.get_session_id()
        
        assert session_id == "session-abc"
    
    def test_get_session_id_from_dict_context(self):
        """Test retrieving session_id from dict-like context."""
        mock_context = Mock()
        mock_context.session_id = "session-xyz"
        mock_runtime = MockToolRuntime(context=mock_context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        session_id = mas_runtime.get_session_id()
        
        assert session_id == "session-xyz"
    
    def test_get_session_id_missing_raises_error(self):
        """Test that missing session_id raises KeyError."""
        mock_context = Mock(spec=[])  # No attributes
        mock_runtime = MockToolRuntime(context=mock_context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        
        with pytest.raises(KeyError, match="session_id not found"):
            mas_runtime.get_session_id()
    
    def test_get_user_id(self):
        """Test retrieving user_id."""
        context = MASContext(session_id="s1", user_id="user-123")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        user_id = mas_runtime.get_user_id()
        
        assert user_id == "user-123"
    
    def test_get_user_id_returns_none_if_missing(self):
        """Test that missing user_id returns None."""
        context = MASContext(session_id="s1")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        user_id = mas_runtime.get_user_id()
        
        assert user_id is None
    
    def test_get_agent_id(self):
        """Test retrieving agent_id."""
        context = MASContext(session_id="s1", agent_id="agent-007")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        agent_id = mas_runtime.get_agent_id()
        
        assert agent_id == "agent-007"
    
    def test_get_organization_id(self):
        """Test retrieving organization_id."""
        context = MASContext(session_id="s1", organization_id="org-456")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        org_id = mas_runtime.get_organization_id()
        
        assert org_id == "org-456"
    
    def test_get_memory_system(self):
        """Test retrieving memory_system reference."""
        mock_memory = Mock()
        context = MASContext(session_id="s1", memory_system=mock_memory)
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        memory = mas_runtime.get_memory_system()
        
        assert memory is mock_memory
    
    def test_get_memory_system_returns_none_if_missing(self):
        """Test that missing memory_system returns None."""
        context = MASContext(session_id="s1")
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        memory = mas_runtime.get_memory_system()
        
        assert memory is None
    
    def test_get_config_flag(self):
        """Test retrieving config flags."""
        context = MASContext(
            session_id="s1",
            enable_l1_cache=False,
            default_min_ciar=0.8
        )
        mock_runtime = MockToolRuntime(context=context, state={})
        
        mas_runtime = MASToolRuntime(mock_runtime)
        
        assert mas_runtime.get_config_flag("enable_l1_cache") is False
        assert mas_runtime.get_config_flag("default_min_ciar") == 0.8
        assert mas_runtime.get_config_flag("nonexistent", "default") == "default"
    
    def test_get_state_value(self):
        """Test retrieving values from graph state."""
        state = {"counter": 42, "mode": "active"}
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state=state
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        
        assert mas_runtime.get_state_value("counter") == 42
        assert mas_runtime.get_state_value("mode") == "active"
        assert mas_runtime.get_state_value("missing", "default") == "default"
    
    def test_get_messages(self):
        """Test retrieving messages from state."""
        messages = [{"role": "user", "content": "hello"}]
        state = {"messages": messages}
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state=state
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        retrieved_messages = mas_runtime.get_messages()
        
        assert retrieved_messages == messages
    
    def test_get_messages_returns_empty_list_if_missing(self):
        """Test that missing messages returns empty list."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={}
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        messages = mas_runtime.get_messages()
        
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_get_from_store(self):
        """Test retrieving from persistent store."""
        mock_item = Mock()
        mock_item.value = {"data": "test"}
        
        mock_store = AsyncMock()
        mock_store.get.return_value = mock_item
        
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            store=mock_store
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        value = await mas_runtime.get_from_store(("users",), "user-123")
        
        assert value == {"data": "test"}
        mock_store.get.assert_called_once_with(("users",), "user-123")
    
    @pytest.mark.asyncio
    async def test_get_from_store_returns_none_if_not_found(self):
        """Test that missing store item returns None."""
        mock_store = AsyncMock()
        mock_store.get.return_value = None
        
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            store=mock_store
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        value = await mas_runtime.get_from_store(("users",), "missing")
        
        assert value is None
    
    @pytest.mark.asyncio
    async def test_get_from_store_returns_none_if_no_store(self):
        """Test that missing store returns None."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            store=None
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        value = await mas_runtime.get_from_store(("users",), "user-123")
        
        assert value is None
    
    @pytest.mark.asyncio
    async def test_put_to_store(self):
        """Test storing to persistent store."""
        mock_store = AsyncMock()
        
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            store=mock_store
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        await mas_runtime.put_to_store(("users",), "user-123", {"name": "Alice"})
        
        mock_store.put.assert_called_once_with(("users",), "user-123", {"name": "Alice"})
    
    @pytest.mark.asyncio
    async def test_put_to_store_does_nothing_if_no_store(self):
        """Test that put_to_store handles missing store gracefully."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            store=None
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        # Should not raise
        await mas_runtime.put_to_store(("users",), "user-123", {"name": "Alice"})
    
    @pytest.mark.asyncio
    async def test_stream_update(self):
        """Test streaming custom updates."""
        mock_writer = AsyncMock()
        
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            stream_writer=mock_writer
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        await mas_runtime.stream_update({"progress": 50, "status": "processing"})
        
        mock_writer.assert_called_once_with({"progress": 50, "status": "processing"})
    
    @pytest.mark.asyncio
    async def test_stream_status(self):
        """Test streaming status messages."""
        mock_writer = AsyncMock()
        
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            stream_writer=mock_writer
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        await mas_runtime.stream_status("Loading data...")
        
        mock_writer.assert_called_once_with({"status": "Loading data..."})
    
    def test_get_tool_call_id(self):
        """Test retrieving tool call ID."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            tool_call_id="call-123"
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        call_id = mas_runtime.get_tool_call_id()
        
        assert call_id == "call-123"
    
    def test_get_tool_call_id_returns_none_if_missing(self):
        """Test that missing tool_call_id returns None."""
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={}
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        call_id = mas_runtime.get_tool_call_id()
        
        assert call_id is None
    
    def test_get_config(self):
        """Test retrieving RunnableConfig."""
        mock_config = Mock()
        mock_runtime = MockToolRuntime(
            context=MASContext(session_id="s1"),
            state={},
            config=mock_config
        )
        
        mas_runtime = MASToolRuntime(mock_runtime)
        config = mas_runtime.get_config()
        
        assert config is mock_config
