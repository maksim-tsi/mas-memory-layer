import pytest
from abc import ABC
from src.storage.base import (
    StorageAdapter,
    StorageError,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    StorageTimeoutError,
    StorageNotFoundError,
    validate_required_fields,
    validate_field_types,
)


def test_storage_exceptions():
    """Test exception hierarchy"""
    # All storage exceptions inherit from StorageError
    assert issubclass(StorageConnectionError, StorageError)
    assert issubclass(StorageQueryError, StorageError)
    assert issubclass(StorageDataError, StorageError)
    assert issubclass(StorageTimeoutError, StorageError)
    assert issubclass(StorageNotFoundError, StorageError)
    
    # Can raise and catch specific exceptions
    with pytest.raises(StorageConnectionError):
        raise StorageConnectionError("Connection failed")
    
    with pytest.raises(StorageQueryError):
        raise StorageQueryError("Query failed")
    
    with pytest.raises(StorageDataError):
        raise StorageDataError("Data error")
    
    with pytest.raises(StorageTimeoutError):
        raise StorageTimeoutError("Timeout error")
    
    with pytest.raises(StorageNotFoundError):
        raise StorageNotFoundError("Not found error")


def test_validate_required_fields():
    """Test field validation helper"""
    data = {'field1': 'value1', 'field2': 'value2'}
    
    # Should pass with all required fields
    validate_required_fields(data, ['field1'])
    validate_required_fields(data, ['field1', 'field2'])
    
    # Should raise with missing fields
    with pytest.raises(StorageDataError, match="Missing required fields: field2"):
        validate_required_fields({'field1': 'value1'}, ['field1', 'field2'])


def test_validate_field_types():
    """Test field type validation helper"""
    data = {'str_field': 'text', 'int_field': 42, 'bool_field': True}
    
    # Should pass with correct types
    validate_field_types(data, {'str_field': str})
    validate_field_types(data, {'int_field': int})
    validate_field_types(data, {'bool_field': bool})
    
    # Should raise with wrong types
    with pytest.raises(StorageDataError, match="Field 'str_field' must be int"):
        validate_field_types(data, {'str_field': int})
    
    with pytest.raises(StorageDataError, match="Field 'int_field' must be str"):
        validate_field_types(data, {'int_field': str})


class ConcreteTestAdapter(StorageAdapter):
    """Minimal concrete implementation for testing"""
    def __init__(self, config):
        super().__init__(config)
        self._connected = False
    
    async def connect(self): 
        self._connected = True
        pass
    
    async def disconnect(self): 
        self._connected = False
        pass
    
    async def store(self, data): 
        return "test-id"
    
    async def retrieve(self, id): 
        return None
    
    async def search(self, query): 
        return []
    
    async def delete(self, id): 
        return False


@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    adapter = ConcreteTestAdapter({})
    
    async with adapter:
        assert adapter.is_connected
    
    assert not adapter.is_connected


def test_storage_adapter_is_abstract():
    """Test that StorageAdapter is an abstract base class"""
    # Check that StorageAdapter is abstract
    assert issubclass(StorageAdapter, ABC)
    
    # Check that it has abstract methods
    assert hasattr(StorageAdapter, '__abstractmethods__')
    abstract_methods = StorageAdapter.__abstractmethods__
    expected_methods = {'connect', 'disconnect', 'store', 'retrieve', 'search', 'delete'}
    assert expected_methods.issubset(abstract_methods)