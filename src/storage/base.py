"""
Base storage adapter interface for multi-layered memory system.

This module defines the abstract StorageAdapter class that all concrete
storage backends must implement, along with a hierarchy of exceptions
for consistent error handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager


# Exception hierarchy
class StorageError(Exception):
    """
    Base exception for all storage-related errors.
    
    This exception should be caught when handling any storage operation
    that might fail. More specific exceptions inherit from this base.
    """
    pass


class StorageConnectionError(StorageError):
    """
    Raised when connection to storage backend fails.
    
    Examples:
    - Cannot connect to PostgreSQL server
    - Redis connection timeout
    - Qdrant service unavailable
    """
    pass


class StorageQueryError(StorageError):
    """
    Raised when query execution fails.
    
    Examples:
    - Invalid SQL syntax
    - Malformed search query
    - Query timeout
    """
    pass


class StorageDataError(StorageError):
    """
    Raised when data validation or integrity errors occur.
    
    Examples:
    - Missing required fields
    - Invalid data types
    - Constraint violations
    """
    pass


class StorageTimeoutError(StorageError):
    """
    Raised when operation exceeds time limit.
    
    Examples:
    - Connection timeout
    - Query execution timeout
    - Lock acquisition timeout
    """
    pass


class StorageNotFoundError(StorageError):
    """
    Raised when requested resource is not found.
    
    Examples:
    - Record with given ID doesn't exist
    - Collection/table not found
    """
    pass


# Helper utilities
def validate_required_fields(data: Dict[str, Any], required: List[str]) -> None:
    """
    Validate that all required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required: List of required field names
    
    Raises:
        StorageDataError: If any required field is missing
    """
    missing = [field for field in required if field not in data]
    if missing:
        raise StorageDataError(
            f"Missing required fields: {', '.join(missing)}"
        )


def validate_field_types(
    data: Dict[str, Any],
    type_specs: Dict[str, type]
) -> None:
    """
    Validate that fields have expected types.
    
    Args:
        data: Dictionary to validate
        type_specs: Dict mapping field names to expected types
    
    Raises:
        StorageDataError: If any field has wrong type
    """
    for field, expected_type in type_specs.items():
        if field in data and not isinstance(data[field], expected_type):
            raise StorageDataError(
                f"Field '{field}' must be {expected_type.__name__}, "
                f"got {type(data[field]).__name__}"
            )


# Abstract base class
class StorageAdapter(ABC):
    """
    Abstract base class for all storage backend adapters.
    
    This interface defines the contract that all concrete storage adapters
    must implement. It provides a uniform API for:
    - Connection management
    - CRUD operations (Create, Read, Update, Delete)
    - Search/query operations
    - Resource cleanup
    
    All methods are async to support non-blocking I/O operations.
    
    Usage Example:
        ```python
        adapter = ConcreteAdapter(config)
        await adapter.connect()
        try:
            id = await adapter.store({"key": "value"})
            data = await adapter.retrieve(id)
        finally:
            await adapter.disconnect()
        ```
    
    Context Manager Usage:
        ```python
        async with ConcreteAdapter(config) as adapter:
            id = await adapter.store({"key": "value"})
            data = await adapter.retrieve(id)
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration.
        
        Args:
            config: Configuration dictionary with backend-specific settings.
                   Common keys: 'url', 'timeout', 'pool_size', etc.
        """
        self.config = config
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to storage backend.
        
        This method should:
        - Initialize connection pools
        - Verify backend is reachable
        - Set up any necessary resources
        - Set self._connected = True on success
        
        Raises:
            StorageConnectionError: If connection fails
            StorageTimeoutError: If connection times out
        """
        raise NotImplementedError
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection and cleanup resources.
        
        This method should:
        - Close connection pools gracefully
        - Release any held resources
        - Flush pending operations if needed
        - Set self._connected = False
        
        Should be safe to call multiple times (idempotent).
        """
        raise NotImplementedError
    
    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store data in backend and return unique identifier.
        
        Args:
            data: Dictionary containing data to store.
                 Required keys depend on specific adapter implementation.
        
        Returns:
            Unique identifier (ID) for the stored data.
            Format depends on backend (UUID, integer, composite key, etc.)
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageDataError: If data validation fails
            StorageQueryError: If storage operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            data = {
                'session_id': 'session-123',
                'content': 'User message',
                'metadata': {'timestamp': '2025-10-20T10:00:00Z'}
            }
            id = await adapter.store(data)
            # id = "550e8400-e29b-41d4-a716-446655440000"
            ```
        """
        raise NotImplementedError
    
    @abstractmethod
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data by unique identifier.
        
        Args:
            id: Unique identifier returned from store() method
        
        Returns:
            Dictionary containing stored data, or None if not found.
            The structure matches what was passed to store().
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageQueryError: If retrieval operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            data = await adapter.retrieve("550e8400-e29b-41d4-a716-446655440000")
            if data:
                print(data['content'])  # "User message"
            else:
                print("Not found")
            ```
        """
        raise NotImplementedError
    
    @abstractmethod
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for records matching query criteria.
        
        Args:
            query: Dictionary containing search parameters.
                  Common keys:
                  - 'filters': Dict of field:value pairs to match
                  - 'limit': Maximum number of results (default: 10)
                  - 'offset': Number of results to skip (default: 0)
                  - 'sort': Field to sort by (optional)
                  - 'order': 'asc' or 'desc' (default: 'desc')
                  
                  Backend-specific keys may also be supported.
        
        Returns:
            List of dictionaries, each containing matching data.
            Empty list if no matches found.
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageQueryError: If search query is invalid or fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            results = await adapter.search({
                'filters': {'session_id': 'session-123'},
                'limit': 5,
                'sort': 'created_at',
                'order': 'desc'
            })
            for record in results:
                print(record['content'])
            ```
        """
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete data by unique identifier.
        
        Args:
            id: Unique identifier of data to delete
        
        Returns:
            True if data was deleted, False if not found.
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageQueryError: If delete operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            success = await adapter.delete("550e8400-e29b-41d4-a716-446655440000")
            if success:
                print("Deleted successfully")
            else:
                print("Not found")
            ```
        """
        raise NotImplementedError
    
    # Batch operations (optional, with default implementations)
    
    async def store_batch(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Store multiple items in a single batch operation.
        
        Default implementation calls store() for each item sequentially.
        Concrete adapters should override this for better performance
        using backend-specific batch operations.
        
        Args:
            items: List of data dictionaries to store
        
        Returns:
            List of unique identifiers for stored items (same order as input)
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageDataError: If any item validation fails
            StorageQueryError: If batch operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            items = [
                {'content': 'Item 1', 'metadata': {}},
                {'content': 'Item 2', 'metadata': {}},
                {'content': 'Item 3', 'metadata': {}}
            ]
            ids = await adapter.store_batch(items)
            # ids = ['id1', 'id2', 'id3']
            ```
        """
        ids = []
        for item in items:
            id = await self.store(item)
            ids.append(id)
        return ids
    
    async def retrieve_batch(self, ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        Retrieve multiple items by their identifiers.
        
        Default implementation calls retrieve() for each ID sequentially.
        Concrete adapters should override this for better performance
        using backend-specific batch operations.
        
        Args:
            ids: List of unique identifiers
        
        Returns:
            List of data dictionaries (or None for not found items)
            Results in same order as input IDs
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageQueryError: If batch operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            ids = ['id1', 'id2', 'id3']
            items = await adapter.retrieve_batch(ids)
            # items = [{'content': 'Item 1'}, None, {'content': 'Item 3'}]
            ```
        """
        results = []
        for id in ids:
            result = await self.retrieve(id)
            results.append(result)
        return results
    
    async def delete_batch(self, ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple items by their identifiers.
        
        Default implementation calls delete() for each ID sequentially.
        Concrete adapters should override this for better performance
        using backend-specific batch operations.
        
        Args:
            ids: List of unique identifiers to delete
        
        Returns:
            Dictionary mapping IDs to deletion status (True=deleted, False=not found)
        
        Raises:
            StorageConnectionError: If not connected to backend
            StorageQueryError: If batch operation fails
            StorageTimeoutError: If operation times out
        
        Example:
            ```python
            ids = ['id1', 'id2', 'id3']
            results = await adapter.delete_batch(ids)
            # results = {'id1': True, 'id2': False, 'id3': True}
            ```
        """
        results = {}
        for id in ids:
            success = await self.delete(id)
            results[id] = success
        return results
    
    @property
    def is_connected(self) -> bool:
        """
        Check if adapter is currently connected to backend.
        
        Returns:
            True if connected, False otherwise.
        """
        return self._connected
    
    async def __aenter__(self):
        """
        Async context manager entry.
        
        Automatically connects to backend when entering context.
        
        Example:
            ```python
            async with adapter:
                await adapter.store(data)
            ```
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        
        Automatically disconnects from backend when exiting context,
        even if an exception occurred.
        """
        await self.disconnect()
        return False  # Don't suppress exceptions


__all__ = [
    # Exceptions
    'StorageError',
    'StorageConnectionError',
    'StorageQueryError',
    'StorageDataError',
    'StorageTimeoutError',
    'StorageNotFoundError',
    # Base class
    'StorageAdapter',
    # Utilities
    'validate_required_fields',
    'validate_field_types',
]