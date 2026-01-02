"""
Tests for unified memory tools.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.agents.tools.unified_tools import (
    memory_query,
    get_context_block,
    memory_store,
    MemoryQueryInput,
    GetContextBlockInput,
    MemoryStoreInput
)
from src.memory.models import Fact, Episode, KnowledgeDocument, ContextBlock, SearchWeights


class TestToolInputSchemas:
    """Test Pydantic input schemas for tools."""
    
    def test_memory_query_input_defaults(self):
        """Test MemoryQueryInput defaults."""
        input_data = MemoryQueryInput(query="test query")
        
        assert input_data.query == "test query"
        assert input_data.limit == 10
        assert input_data.l2_weight == 0.3
        assert input_data.l3_weight == 0.5
        assert input_data.l4_weight == 0.2
    
    def test_memory_query_input_validation(self):
        """Test MemoryQueryInput validation."""
        # Valid input
        input_data = MemoryQueryInput(
            query="test",
            limit=25,
            l2_weight=0.4,
            l3_weight=0.3,
            l4_weight=0.3
        )
        assert input_data.limit == 25
        
        # Test limit boundaries
        with pytest.raises(ValueError):
            MemoryQueryInput(query="test", limit=0)  # Below minimum
        
        with pytest.raises(ValueError):
            MemoryQueryInput(query="test", limit=100)  # Above maximum
    
    def test_get_context_block_input_defaults(self):
        """Test GetContextBlockInput defaults."""
        input_data = GetContextBlockInput()
        
        assert input_data.min_ciar == 0.6
        assert input_data.max_turns == 20
        assert input_data.max_facts == 10
        assert input_data.format == "structured"
    
    def test_get_context_block_input_validation(self):
        """Test GetContextBlockInput validation."""
        input_data = GetContextBlockInput(
            min_ciar=0.8,
            max_turns=50,
            max_facts=20,
            format="text"
        )
        
        assert input_data.min_ciar == 0.8
        assert input_data.max_turns == 50
        assert input_data.max_facts == 20
        assert input_data.format == "text"
    
    def test_memory_store_input_defaults(self):
        """Test MemoryStoreInput defaults."""
        input_data = MemoryStoreInput(content="test content")
        
        assert input_data.content == "test content"
        assert input_data.tier == "auto"
        assert input_data.metadata is None
    
    def test_memory_store_input_with_metadata(self):
        """Test MemoryStoreInput with metadata."""
        metadata = {"type": "preference", "priority": "high"}
        input_data = MemoryStoreInput(
            content="user likes coffee",
            tier="L2",
            metadata=metadata
        )
        
        assert input_data.content == "user likes coffee"
        assert input_data.tier == "L2"
        assert input_data.metadata == metadata


class TestToolFunctionSignatures:
    """Test that tools have correct LangChain structure."""
    
    def test_memory_query_has_coroutine(self):
        """Test memory_query has coroutine for execution."""
        # LangChain stores async function in coroutine attribute
        assert hasattr(memory_query, 'coroutine')
        import inspect
        assert inspect.iscoroutinefunction(memory_query.coroutine)
    
    def test_get_context_block_has_coroutine(self):
        """Test get_context_block has coroutine for execution."""
        assert hasattr(get_context_block, 'coroutine')
        import inspect
        assert inspect.iscoroutinefunction(get_context_block.coroutine)
    
    def test_memory_store_has_coroutine(self):
        """Test memory_store has coroutine for execution."""
        assert hasattr(memory_store, 'coroutine')
        import inspect
        assert inspect.iscoroutinefunction(memory_store.coroutine)


class TestToolMetadata:
    """Test that tools have proper metadata for LangChain."""
    
    def test_memory_query_has_name(self):
        """Test memory_query has name."""
        assert hasattr(memory_query, 'name')
        assert memory_query.name == 'memory_query'
    
    def test_memory_query_has_description(self):
        """Test memory_query has description."""
        assert hasattr(memory_query, 'description')
        assert 'search' in memory_query.description.lower()
        assert 'memory' in memory_query.description.lower()
    
    def test_memory_query_has_args_schema(self):
        """Test memory_query has args_schema."""
        assert hasattr(memory_query, 'args_schema')
        assert memory_query.args_schema == MemoryQueryInput
    
    def test_get_context_block_has_name(self):
        """Test get_context_block has name."""
        assert hasattr(get_context_block, 'name')
        assert get_context_block.name == 'get_context_block'
    
    def test_get_context_block_has_description(self):
        """Test get_context_block has description."""
        assert hasattr(get_context_block, 'description')
        assert 'context' in get_context_block.description.lower()
    
    def test_get_context_block_has_args_schema(self):
        """Test get_context_block has args_schema."""
        assert hasattr(get_context_block, 'args_schema')
        assert get_context_block.args_schema == GetContextBlockInput
    
    def test_memory_store_has_name(self):
        """Test memory_store has name."""
        assert hasattr(memory_store, 'name')
        assert memory_store.name == 'memory_store'
    
    def test_memory_store_has_description(self):
        """Test memory_store has description."""
        assert hasattr(memory_store, 'description')
        assert 'store' in memory_store.description.lower()
    
    def test_memory_store_has_args_schema(self):
        """Test memory_store has args_schema."""
        assert hasattr(memory_store, 'args_schema')
        assert memory_store.args_schema == MemoryStoreInput


@pytest.mark.asyncio
class TestMemoryQueryTool:
    """Test memory_query tool behavior."""
    
    async def test_memory_query_error_when_no_memory_system(self):
        """Test error handling when memory system not available."""
        from dataclasses import dataclass
        
        @dataclass
        class MockToolRuntime:
            context: object
            state: dict
        
        @dataclass
        class MockContext:
            session_id: str = "test-123"
            memory_system: object = None
        
        mock_runtime = MockToolRuntime(
            context=MockContext(),
            state={}
        )
        
        # Call the coroutine directly (langchain_core stores it there)
        result = await memory_query.coroutine(
            query="test",
            runtime=mock_runtime
        )
        
        assert "Error" in result
        assert "Memory system not available" in result


@pytest.mark.asyncio
class TestGetContextBlockTool:
    """Test get_context_block tool behavior."""
    
    async def test_get_context_block_error_when_no_memory_system(self):
        """Test error handling when memory system not available."""
        from dataclasses import dataclass
        
        @dataclass
        class MockToolRuntime:
            context: object
            state: dict
        
        @dataclass
        class MockContext:
            session_id: str = "test-123"
            memory_system: object = None
        
        mock_runtime = MockToolRuntime(
            context=MockContext(),
            state={}
        )
        
        result = await get_context_block.coroutine(
            runtime=mock_runtime
        )
        
        assert "Error" in result
        assert "Memory system not available" in result


@pytest.mark.asyncio
class TestMemoryStoreTool:
    """Test memory_store tool behavior."""
    
    async def test_memory_store_error_when_no_memory_system(self):
        """Test error handling when memory system not available."""
        from dataclasses import dataclass
        
        @dataclass
        class MockToolRuntime:
            context: object
            state: dict
        
        @dataclass
        class MockContext:
            session_id: str = "test-123"
            memory_system: object = None
        
        mock_runtime = MockToolRuntime(
            context=MockContext(),
            state={}
        )
        
        result = await memory_store.coroutine(
            content="test content",
            runtime=mock_runtime
        )
        
        assert "Error" in result
        assert "Memory system not available" in result
