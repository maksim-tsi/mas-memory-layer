# Phase 1 Specification: Storage Layer Foundation

**Document Version**: 1.0  
**Date**: October 20, 2025  
**Status**: Ready for Implementation  
**Target Completion**: Week 1-2  
**Branch**: `dev`

---

## Executive Summary

This specification defines the implementation requirements for Phase 1 of the multi-layered memory system. Phase 1 establishes the storage layer foundation by creating abstract interfaces and concrete adapters for all backend services (PostgreSQL, Redis, Qdrant, Neo4j, Typesense).

**Objective**: Build a robust, testable storage abstraction layer that enables higher-level memory tier orchestration in Phase 2.

---

## Prerequisites

### Infrastructure Requirements ✅
- PostgreSQL 16.10 on 192.168.107.172:5432 (Database: `mas_memory`)
- Redis 6+ on 192.168.107.172:6379
- Qdrant 1.9+ on 192.168.107.187:6333
- Neo4j 5.22+ on 192.168.107.187:7687
- Typesense 8+ on 192.168.107.187:8108

**Status**: All services verified operational (see `docs/reports/smoke-tests-2025-10-20.md`)

### Development Environment ✅
- Python 3.13.5
- Virtual environment: `.venv/`
- Dependencies installed from `requirements.txt`
- Configuration: `.env` file with service credentials

**Status**: Environment configured and tested

---

## Architecture Overview

### Directory Structure

```
src/
├── storage/              # Storage adapters (Priority 1-5)
│   ├── __init__.py
│   ├── base.py          # Priority 1: Abstract base class
│   ├── postgres_adapter.py  # Priority 2: PostgreSQL adapter
│   ├── redis_adapter.py     # Priority 3: Redis adapter
│   ├── qdrant_adapter.py    # Priority 4: Qdrant adapter
│   ├── neo4j_adapter.py     # Priority 4: Neo4j adapter
│   └── typesense_adapter.py # Priority 4: Typesense adapter
├── memory/              # Memory tiers (Phase 2)
│   └── __init__.py
├── agents/              # LangGraph agents (Phase 3)
│   └── __init__.py
├── evaluation/          # Benchmark runners (Phase 4)
│   └── __init__.py
└── utils/               # Utilities
    ├── __init__.py
    ├── config.py        # Configuration loader
    └── logging.py       # Logging setup

migrations/              # Database migrations (Priority 5)
├── 001_active_context.sql
└── README.md

tests/
├── storage/             # Storage adapter tests (Priority 6)
│   ├── __init__.py
│   ├── test_base.py
│   ├── test_postgres_adapter.py
│   ├── test_redis_adapter.py
│   ├── test_qdrant_adapter.py
│   ├── test_neo4j_adapter.py
│   └── test_typesense_adapter.py
└── integration/         # Integration tests
    └── test_storage_integration.py
```

---

## Design Principles

### 1. Abstraction
- All storage backends implement a common `StorageAdapter` interface
- Business logic should never directly import concrete adapter classes
- Dependency injection pattern for adapter instantiation

### 2. Async-First
- All I/O operations must be async (`async`/`await`)
- Use appropriate async libraries:
  - PostgreSQL: `psycopg` (async mode) - **Note: NOT asyncpg due to Python 3.13**
  - Redis: `redis.asyncio`
  - Qdrant: `qdrant_client` (async support)
  - Neo4j: `neo4j` (async driver)
  - Typesense: `httpx` (async HTTP client)

### 3. Error Handling
- All adapter methods must handle connection errors gracefully
- Use custom exceptions (e.g., `StorageConnectionError`, `StorageQueryError`)
- Log errors with context (operation, parameters, timestamp)
- Never expose raw backend errors to calling code

### 4. Testability
- Each adapter must be testable against real backend instances
- Use environment variables for test configuration
- Tests must clean up after themselves (no orphaned data)
- Integration tests verify cross-adapter interactions

### 5. Performance
- Connection pooling for PostgreSQL (min: 2, max: 10)
- Redis pipelining for batch operations
- Lazy connection initialization (connect on first use)
- Proper connection lifecycle (context managers or explicit connect/disconnect)

---

## Implementation Priorities

### Overview

| Priority | Component | Time | Status | Dependencies |
|----------|-----------|------|--------|--------------|
| **0** | Project Setup | 30 min | ✅ Complete | None |
| **1** | Base Storage Interface | 2-3h | ✅ Complete | Priority 0 |
| **2** | PostgreSQL Adapter | 4-5h | ✅ Complete | Priority 1 |
| **3** | Redis Adapter | 3-4h | ✅ Complete | Priority 1 |
| **3A** | Redis Enhancements | 4-6h | 🔄 Planned | Priority 3 |
| **4** | Vector/Graph Adapters | 6-8h | Not Started | Priority 1 |
| **5** | Database Migrations | 1h | ✅ Complete | None |
| **6** | Unit Tests | 4-6h | ✅ Partial | Priorities 1-4 |

**Legend**: ✅ Complete | 🔄 Planned | ⚠️ In Progress | ❌ Blocked

---

### Priority 0: Project Setup
**Estimated Time**: 30 minutes  
**Assignee**: TBD  
**Status**: ✅ Complete

**Objective**: Establish the foundational directory structure and Python package organization for the storage layer implementation.

---

#### Detailed Requirements

**1. Create Source Directory Structure**

Create the main `src/` directory with subdirectories for each component:

```bash
mkdir -p src/storage
mkdir -p src/memory
mkdir -p src/agents
mkdir -p src/evaluation
mkdir -p src/utils
```

**2. Create Migrations Directory**

```bash
mkdir -p migrations
```

**3. Create Test Directory Structure**

```bash
mkdir -p tests/storage
mkdir -p tests/integration
mkdir -p tests/memory  # For Phase 2
mkdir -p tests/agents  # For Phase 3
```

**4. Initialize Python Packages**

Create `__init__.py` files to make directories importable as Python packages:

```bash
# Main source packages (active in Phase 1)
touch src/__init__.py
touch src/storage/__init__.py
touch src/utils/__init__.py

# Future phase packages (placeholders)
touch src/memory/__init__.py
touch src/agents/__init__.py
touch src/evaluation/__init__.py

# Test packages
touch tests/__init__.py
touch tests/storage/__init__.py
touch tests/integration/__init__.py
touch tests/memory/__init__.py
touch tests/agents/__init__.py
```

**5. Add Package-Level Exports**

Add convenient imports to `src/storage/__init__.py`:

```python
"""
Storage layer for multi-layered memory system.

This package provides abstract interfaces and concrete implementations
for all backend storage services (PostgreSQL, Redis, Qdrant, Neo4j, Typesense).
"""

__version__ = "0.1.0"

# Base interface will be imported here after Priority 1
# from .base import StorageAdapter

# Concrete adapters will be imported after their implementation
# from .postgres_adapter import PostgresAdapter
# from .redis_adapter import RedisAdapter
# from .qdrant_adapter import QdrantAdapter
# from .neo4j_adapter import Neo4jAdapter
# from .typesense_adapter import TypesenseAdapter

__all__ = [
    # "StorageAdapter",
    # "PostgresAdapter",
    # "RedisAdapter",
    # "QdrantAdapter",
    # "Neo4jAdapter",
    # "TypesenseAdapter",
]
```

**6. Create Migration README**

Create `migrations/README.md`:

```markdown
# Database Migrations

This directory contains SQL migration scripts for PostgreSQL schema changes.

## Migration Naming Convention

Format: `{number}_{description}.sql`

Example: `001_active_context.sql`

## Applying Migrations

```bash
# Load environment variables
source .env

# Apply migration
psql "$POSTGRES_URL" -f migrations/001_active_context.sql

# Verify tables created
psql "$POSTGRES_URL" -c "\dt"
```

## Current Migrations

- `001_active_context.sql` - L1/L2 memory tables (active_context, working_memory)
```

**7. Create Test Storage README**

Create `tests/storage/README.md`:

```markdown
# Storage Adapter Tests

Unit tests for storage layer adapters using real backend instances.

## Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all storage tests
pytest tests/storage/ -v

# Run specific adapter
pytest tests/storage/test_postgres_adapter.py -v

# Run with coverage
pytest tests/storage/ --cov=src/storage --cov-report=html --cov-report=term
```

## Test Data Cleanup

All tests must clean up their data. Use session IDs with format:
`test-{test_name}-{uuid4()}`

Example:
```python
import uuid

@pytest.fixture
def session_id():
    test_session = f"test-postgres-{uuid.uuid4()}"
    yield test_session
    # Cleanup happens in teardown
```

## Backend Requirements

Tests require access to:
- PostgreSQL (`mas_memory` database)
- Redis (DB 0, will be flushed in tests)
- Qdrant (test collections will be deleted)
- Neo4j (test data will be deleted)
- Typesense (test collections will be deleted)

Configuration from `.env` file.
```

**8. Create .gitkeep for Future Directories**

For directories that will be populated in later phases:

```bash
touch src/memory/.gitkeep
touch src/agents/.gitkeep
touch src/evaluation/.gitkeep
touch tests/memory/.gitkeep
touch tests/agents/.gitkeep
```

**9. Update .gitignore (if needed)**

Ensure these patterns are in `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Testing
.pytest_cache/
.coverage
htmlcov/
*.coverage

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.venv/
venv/

# OS
.DS_Store
```

---

#### Verification Steps

After completing the setup, verify the structure:

```bash
# 1. Check directory structure
tree src/ -L 2
tree tests/ -L 2
tree migrations/

# Expected output:
# src/
# ├── agents/
# │   └── __init__.py
# ├── evaluation/
# │   └── __init__.py
# ├── __init__.py
# ├── memory/
# │   └── __init__.py
# ├── storage/
# │   └── __init__.py
# └── utils/
#     └── __init__.py

# 2. Verify Python can import packages
python -c "import src; import src.storage; print('✓ Imports successful')"

# 3. Check git tracking
git status
# All new directories should appear in untracked files

# 4. Add to git
git add src/ tests/ migrations/
git status
# Files should now be staged
```

---

#### Common Issues & Solutions

**Issue**: `ModuleNotFoundError: No module named 'src'`
- **Solution**: Ensure you're running from project root and `__init__.py` exists in `src/`

**Issue**: Empty directories not showing in git
- **Solution**: Git doesn't track empty directories. Add `.gitkeep` or `README.md` files

**Issue**: Import errors between packages
- **Solution**: Ensure all parent directories have `__init__.py` files

---

#### Tasks Checklist

- [ ] Create `src/` directory with all subdirectories
- [ ] Create `migrations/` directory
- [ ] Create `tests/storage/` and `tests/integration/` directories
- [ ] Add `__init__.py` to all packages (src, src/storage, src/utils, etc.)
- [ ] Add package-level exports to `src/storage/__init__.py`
- [ ] Create `migrations/README.md` with instructions
- [ ] Create `tests/storage/README.md` with test guidelines
- [ ] Add `.gitkeep` files to future phase directories
- [ ] Verify `.gitignore` has necessary patterns
- [ ] Test imports: `python -c "import src.storage"`
- [ ] Add all files to git: `git add src/ tests/ migrations/`
- [ ] Commit: `git commit -m "feat: Initialize Phase 1 directory structure"`

---

#### Acceptance Criteria

✅ **Directory Structure**:
- All directories from specification exist
- Structure matches the architecture overview exactly

✅ **Python Packages**:
- All packages have `__init__.py` files
- Can import `src.storage` without errors
- Package docstrings present in `__init__.py`

✅ **Documentation**:
- `migrations/README.md` exists with clear instructions
- `tests/storage/README.md` exists with test guidelines

✅ **Git Tracking**:
- All directories are tracked by git (via files or `.gitkeep`)
- Changes committed to `dev` branch

✅ **Verification**:
- `python -c "import src.storage"` succeeds
- `tree src/` shows expected structure
- No errors when running `pytest --collect-only tests/storage/`

---

#### Deliverables

1. ✅ Complete directory structure (src, migrations, tests)
2. ✅ All `__init__.py` files created
3. ✅ README files for migrations and tests
4. ✅ Git commit with directory structure
5. ✅ Verification commands all pass

**Time Estimate**: 30 minutes  
**Complexity**: Low  
**Dependencies**: None  
**Blocks**: Priority 1 (needs src/storage/ directory)

---

### Priority 1: Base Storage Interface
**Estimated Time**: 2-3 hours  
**Assignee**: TBD  
**Status**: Not Started  
**File**: `src/storage/base.py`

**Objective**: Define the abstract `StorageAdapter` interface that all concrete adapters will implement, along with custom exception classes for consistent error handling across all storage backends.

---

#### Detailed Requirements

**1. Custom Exception Hierarchy**

Define a hierarchy of exceptions for storage operations:

```python
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
```

**2. Abstract Base Class Interface**

Define the `StorageAdapter` abstract base class:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager


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
```

**3. Helper Utilities (Optional but Recommended)**

Add helper functions for common validation tasks:

```python
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
```

---

#### File Structure

The complete `src/storage/base.py` should have this structure:

```python
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
    """Base exception for storage operations"""
    pass

# ... other exception classes ...


# Helper utilities
def validate_required_fields(data: Dict[str, Any], required: List[str]) -> None:
    """Validate required fields are present"""
    pass

# ... other helper functions ...


# Abstract base class
class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    # ... other abstract methods ...
    
    @property
    def is_connected(self) -> bool:
        pass
    
    async def __aenter__(self):
        pass
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


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
```

---

#### Implementation Notes

**1. Why Abstract Base Class?**
- Enforces consistent interface across all adapters
- Enables type checking and IDE autocomplete
- Documents expected behavior for all implementations
- Allows swapping adapters without changing client code

**2. Why Async?**
- All I/O operations are non-blocking
- Better performance with concurrent operations
- Matches modern Python async/await patterns
- Required for LangGraph integration (Phase 3)

**3. Context Manager Support**
- Ensures proper cleanup even if exceptions occur
- Simplifies client code (no manual connect/disconnect)
- Follows Python best practices for resource management

**4. Exception Hierarchy**
- Base `StorageError` allows catching all storage errors
- Specific exceptions enable fine-grained error handling
- Consistent error handling across all adapters

---

#### Testing Strategy

Create `tests/storage/test_base.py` to verify:

```python
import pytest
from src.storage.base import (
    StorageAdapter,
    StorageError,
    StorageConnectionError,
    validate_required_fields,
)

def test_storage_exceptions():
    """Test exception hierarchy"""
    # All storage exceptions inherit from StorageError
    assert issubclass(StorageConnectionError, StorageError)
    
    # Can raise and catch specific exceptions
    with pytest.raises(StorageConnectionError):
        raise StorageConnectionError("Connection failed")

def test_validate_required_fields():
    """Test field validation helper"""
    data = {'field1': 'value1'}
    
    # Should pass with all required fields
    validate_required_fields(data, ['field1'])
    
    # Should raise with missing fields
    with pytest.raises(StorageDataError):
        validate_required_fields(data, ['field1', 'field2'])

def test_cannot_instantiate_abstract_class():
    """Test that abstract class cannot be instantiated"""
    with pytest.raises(TypeError):
        adapter = StorageAdapter({})

class ConcreteTestAdapter(StorageAdapter):
    """Minimal concrete implementation for testing"""
    async def connect(self): pass
    async def disconnect(self): pass
    async def store(self, data): return "test-id"
    async def retrieve(self, id): return None
    async def search(self, query): return []
    async def delete(self, id): return False

@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    adapter = ConcreteTestAdapter({})
    
    async with adapter:
        assert adapter.is_connected
    
    assert not adapter.is_connected
```

---

#### Tasks Checklist

- [ ] Create `src/storage/base.py`
- [ ] Define all 6 exception classes with docstrings
- [ ] Implement `StorageAdapter` abstract base class
- [ ] Add all 6 abstract methods with full docstrings
- [ ] Implement `is_connected` property
- [ ] Implement `__aenter__` and `__aexit__` for context manager
- [ ] Add helper functions: `validate_required_fields`, `validate_field_types`
- [ ] Add module-level docstring
- [ ] Define `__all__` exports
- [ ] Create `tests/storage/test_base.py`
- [ ] Write tests for exception hierarchy
- [ ] Write tests for validation helpers
- [ ] Write tests for abstract class (cannot instantiate)
- [ ] Write tests for context manager protocol
- [ ] Run tests: `pytest tests/storage/test_base.py -v`
- [ ] Update `src/storage/__init__.py` to import from base
- [ ] Commit: `git commit -m "feat: Add storage adapter base interface"`

---

#### Acceptance Criteria

✅ **Code Quality**:
- All methods have comprehensive docstrings (Args, Returns, Raises, Examples)
- Type hints for all parameters and return values
- Module follows PEP 8 style guidelines
- No concrete implementation in abstract methods

✅ **Exception Hierarchy**:
- 6 exception classes defined
- All inherit from `StorageError`
- Each has descriptive docstring with examples

✅ **Interface Completeness**:
- All 6 required methods defined as abstract
- Context manager protocol implemented (`__aenter__`, `__aexit__`)
- `is_connected` property available
- Helper validation functions included

✅ **Testing**:
- Test file created with >80% coverage
- Tests verify exception hierarchy
- Tests verify cannot instantiate abstract class
- Tests verify context manager behavior
- All tests pass: `pytest tests/storage/test_base.py -v`

✅ **Documentation**:
- Module docstring explains purpose
- Each class/function has docstring
- Usage examples in docstrings
- `__all__` exports documented

✅ **Integration**:
- Can import from base: `from src.storage.base import StorageAdapter`
- Exports available in `src.storage.__init__.py`
- No circular import issues

---

#### Deliverables

1. ✅ `src/storage/base.py` - Complete abstract interface (~300-400 lines)
2. ✅ `tests/storage/test_base.py` - Unit tests (~100-150 lines)
3. ✅ Updated `src/storage/__init__.py` - Import exports from base
4. ✅ All tests passing
5. ✅ Git commit with base interface

**Time Estimate**: 2-3 hours  
**Complexity**: Medium  
**Dependencies**: Priority 0 (directory structure)  
**Blocks**: Priority 2-4 (all concrete adapters need this interface)

---

#### Common Pitfalls to Avoid

⚠️ **Don't implement concrete logic in base class**
- Keep all methods abstract (raise `NotImplementedError`)
- Only `is_connected` property and context manager can have logic

⚠️ **Don't forget type hints**
- Every parameter needs a type hint
- Every return value needs a type hint
- Use `Optional`, `List`, `Dict` from `typing`

⚠️ **Don't skip docstrings**
- Every method needs Args, Returns, Raises sections
- Include usage examples where helpful

⚠️ **Don't make exceptions too specific**
- Keep hierarchy simple and logical
- 5-6 exception classes is sufficient
- All should inherit from `StorageError`

---

### Priority 2: PostgreSQL Adapter
**Estimated Time**: 4-6 hours  
**Assignee**: TBD  
**Status**: Not Started  
**File**: `src/storage/postgres_adapter.py`

**Objective**: Implement concrete adapter for PostgreSQL using `psycopg` (Python 3.13 compatible) to support L1 (Active Context) and L2 (Working Memory) storage tiers.

---

#### Detailed Requirements

**1. Import Dependencies**

```python
"""
PostgreSQL storage adapter for active context and working memory.

This adapter uses psycopg (v3) with connection pooling for high-performance
async operations on the mas_memory database.

Database Tables:
- active_context: L1 memory (recent conversation turns, TTL: 24h)
- working_memory: L2 memory (session facts, TTL: 7 days)
"""

import psycopg
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    StorageTimeoutError,
    StorageNotFoundError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)
```

**2. PostgresAdapter Class Structure**

```python
class PostgresAdapter(StorageAdapter):
    """
    PostgreSQL adapter for active context (L1) and working memory (L2).
    
    Features:
    - Connection pooling for high concurrency
    - Support for both active_context and working_memory tables
    - TTL-aware queries (automatic expiration filtering)
    - Parameterized queries (SQL injection protection)
    - Automatic reconnection on connection loss
    
    Configuration:
        {
            'url': 'postgresql://user:pass@host:port/database',
            'pool_size': 10,  # Maximum connections in pool
            'min_size': 2,    # Minimum connections to maintain
            'timeout': 5,     # Connection timeout in seconds
            'table': 'active_context'  # or 'working_memory'
        }
    
    Example:
        ```python
        config = {
            'url': os.getenv('POSTGRES_URL'),
            'pool_size': 10,
            'table': 'active_context'
        }
        adapter = PostgresAdapter(config)
        await adapter.connect()
        
        # Store a conversation turn
        turn_id = await adapter.store({
            'session_id': 'session-123',
            'turn_id': 1,
            'content': 'Hello, how can I help?',
            'metadata': {'role': 'assistant', 'tokens': 25}
        })
        
        # Retrieve recent turns
        turns = await adapter.search({
            'session_id': 'session-123',
            'limit': 10
        })
        
        await adapter.disconnect()
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL adapter.
        
        Args:
            config: Configuration dictionary with:
                - url: PostgreSQL connection URL (required)
                - pool_size: Max connections (default: 10)
                - min_size: Min connections (default: 2)
                - timeout: Connection timeout (default: 5)
                - table: Target table name (default: 'active_context')
        """
        super().__init__(config)
        self.url = config.get('url')
        if not self.url:
            raise StorageDataError("PostgreSQL URL is required in config")
        
        self.pool_size = config.get('pool_size', 10)
        self.min_size = config.get('min_size', 2)
        self.timeout = config.get('timeout', 5)
        self.table = config.get('table', 'active_context')
        self.pool: Optional[AsyncConnectionPool] = None
        
        logger.info(
            f"PostgresAdapter initialized for table '{self.table}' "
            f"(pool: {self.min_size}-{self.pool_size})"
        )
```

**3. Connection Management**

```python
    async def connect(self) -> None:
        """
        Create connection pool to PostgreSQL.
        
        Establishes a connection pool with configured min/max size.
        Verifies connectivity by executing a test query.
        
        Raises:
            StorageConnectionError: If connection fails
            StorageTimeoutError: If connection times out
        """
        if self._connected and self.pool:
            logger.warning("Already connected, skipping")
            return
        
        try:
            # Create connection pool
            self.pool = AsyncConnectionPool(
                conninfo=self.url,
                min_size=self.min_size,
                max_size=self.pool_size,
                timeout=self.timeout,
                open=True  # Open connections immediately
            )
            
            # Wait for pool to be ready
            await self.pool.wait()
            
            # Verify connection with test query
            async with self.pool.connection() as conn:
                result = await conn.execute("SELECT 1")
                await result.fetchone()
            
            self._connected = True
            logger.info(f"Connected to PostgreSQL (table: {self.table})")
            
        except psycopg.OperationalError as e:
            logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Failed to connect to PostgreSQL: {e}"
            ) from e
        except TimeoutError as e:
            logger.error(f"PostgreSQL connection timeout: {e}", exc_info=True)
            raise StorageTimeoutError(
                f"Connection timeout: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Connection failed: {e}"
            ) from e
    
    async def disconnect(self) -> None:
        """
        Close connection pool and cleanup resources.
        
        Gracefully closes all connections in the pool.
        Safe to call multiple times (idempotent).
        """
        if not self.pool:
            logger.warning("No active connection pool")
            return
        
        try:
            await self.pool.close()
            self.pool = None
            self._connected = False
            logger.info("Disconnected from PostgreSQL")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
            # Don't raise - disconnect should always succeed
```

**4. Store Method (Active Context)**

```python
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store data in PostgreSQL table.
        
        For active_context table:
            Required fields: session_id, turn_id, content
            Optional fields: metadata, ttl_expires_at
        
        For working_memory table:
            Required fields: session_id, fact_type, content
            Optional fields: confidence, source_turn_ids, metadata, ttl_expires_at
        
        Args:
            data: Dictionary with required fields for target table
        
        Returns:
            String representation of inserted record ID
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If required fields missing
            StorageQueryError: If insert fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            if self.table == 'active_context':
                return await self._store_active_context(data)
            elif self.table == 'working_memory':
                return await self._store_working_memory(data)
            else:
                raise StorageDataError(f"Unknown table: {self.table}")
                
        except StorageDataError:
            raise  # Re-raise validation errors
        except psycopg.Error as e:
            logger.error(f"PostgreSQL insert failed: {e}", exc_info=True)
            raise StorageQueryError(f"Insert failed: {e}") from e
    
    async def _store_active_context(self, data: Dict[str, Any]) -> str:
        """Store record in active_context table"""
        # Validate required fields
        validate_required_fields(data, ['session_id', 'turn_id', 'content'])
        
        # Set TTL if not provided (24 hours)
        if 'ttl_expires_at' not in data:
            data['ttl_expires_at'] = datetime.utcnow() + timedelta(hours=24)
        
        # Prepare metadata
        metadata = json.dumps(data.get('metadata', {}))
        
        query = """
            INSERT INTO active_context 
            (session_id, turn_id, content, metadata, created_at, ttl_expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (
                        data['session_id'],
                        data['turn_id'],
                        data['content'],
                        metadata,
                        datetime.utcnow(),
                        data['ttl_expires_at']
                    )
                )
                result = await cur.fetchone()
                record_id = str(result[0])
        
        logger.debug(f"Stored active_context record: {record_id}")
        return record_id
    
    async def _store_working_memory(self, data: Dict[str, Any]) -> str:
        """Store record in working_memory table"""
        # Validate required fields
        validate_required_fields(data, ['session_id', 'fact_type', 'content'])
        
        # Set TTL if not provided (7 days)
        if 'ttl_expires_at' not in data:
            data['ttl_expires_at'] = datetime.utcnow() + timedelta(days=7)
        
        # Prepare metadata and arrays
        metadata = json.dumps(data.get('metadata', {}))
        source_turn_ids = data.get('source_turn_ids', [])
        
        query = """
            INSERT INTO working_memory 
            (session_id, fact_type, content, confidence, source_turn_ids, 
             created_at, updated_at, ttl_expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (
                        data['session_id'],
                        data['fact_type'],
                        data['content'],
                        data.get('confidence', 1.0),
                        source_turn_ids,
                        datetime.utcnow(),
                        datetime.utcnow(),
                        data['ttl_expires_at']
                    )
                )
                result = await cur.fetchone()
                record_id = str(result[0])
        
        logger.debug(f"Stored working_memory record: {record_id}")
        return record_id
```

**5. Retrieve Method**

```python
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve record by ID.
        
        Args:
            id: Record ID (integer as string)
        
        Returns:
            Dictionary with record data, or None if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If query fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            query = f"SELECT * FROM {self.table} WHERE id = %s"
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (int(id),))
                    row = await cur.fetchone()
                    
                    if not row:
                        return None
                    
                    # Get column names
                    columns = [desc[0] for desc in cur.description]
                    
                    # Convert row to dictionary
                    result = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    if 'metadata' in result and result['metadata']:
                        result['metadata'] = json.loads(result['metadata']) \
                            if isinstance(result['metadata'], str) \
                            else result['metadata']
                    
                    # Convert datetime objects to ISO format
                    for key, value in result.items():
                        if isinstance(value, datetime):
                            result[key] = value.isoformat()
                    
                    return result
                    
        except psycopg.Error as e:
            logger.error(f"PostgreSQL retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Retrieve failed: {e}") from e
```

**6. Search Method**

```python
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search records with filters.
        
        Query Parameters:
            - session_id: Filter by session (required for most queries)
            - limit: Maximum results (default: 10)
            - offset: Skip N results (default: 0)
            - include_expired: Include expired records (default: False)
            - sort: Field to sort by (default: 'created_at' or 'turn_id')
            - order: 'asc' or 'desc' (default: 'desc')
        
        Args:
            query: Dictionary with search parameters
        
        Returns:
            List of dictionaries containing matching records
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If search fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            # Build query
            conditions = []
            params = []
            
            # Session filter
            if 'session_id' in query:
                conditions.append("session_id = %s")
                params.append(query['session_id'])
            
            # TTL filter (exclude expired by default)
            if not query.get('include_expired', False):
                conditions.append(
                    "(ttl_expires_at IS NULL OR ttl_expires_at > NOW())"
                )
            
            # Fact type filter (for working_memory)
            if 'fact_type' in query:
                conditions.append("fact_type = %s")
                params.append(query['fact_type'])
            
            # Build WHERE clause
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Sorting
            if self.table == 'active_context':
                sort_field = query.get('sort', 'turn_id')
            else:
                sort_field = query.get('sort', 'created_at')
            
            order = query.get('order', 'desc').upper()
            if order not in ['ASC', 'DESC']:
                order = 'DESC'
            
            # Pagination
            limit = query.get('limit', 10)
            offset = query.get('offset', 0)
            
            # Execute query
            sql = f"""
                SELECT * FROM {self.table}
                WHERE {where_clause}
                ORDER BY {sort_field} {order}
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    
                    if not rows:
                        return []
                    
                    # Get column names
                    columns = [desc[0] for desc in cur.description]
                    
                    # Convert rows to dictionaries
                    results = []
                    for row in rows:
                        result = dict(zip(columns, row))
                        
                        # Parse JSON fields
                        if 'metadata' in result and result['metadata']:
                            result['metadata'] = json.loads(result['metadata']) \
                                if isinstance(result['metadata'], str) \
                                else result['metadata']
                        
                        # Convert datetime to ISO format
                        for key, value in result.items():
                            if isinstance(value, datetime):
                                result[key] = value.isoformat()
                        
                        results.append(result)
                    
                    return results
                    
        except psycopg.Error as e:
            logger.error(f"PostgreSQL search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Search failed: {e}") from e
```

**7. Delete Method**

```python
    async def delete(self, id: str) -> bool:
        """
        Delete record by ID.
        
        Args:
            id: Record ID to delete
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If delete fails
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            query = f"DELETE FROM {self.table} WHERE id = %s"
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (int(id),))
                    deleted = cur.rowcount > 0
            
            if deleted:
                logger.debug(f"Deleted record {id} from {self.table}")
            
            return deleted
            
        except psycopg.Error as e:
            logger.error(f"PostgreSQL delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Delete failed: {e}") from e
```

**8. Utility Methods**

```python
    async def delete_expired(self) -> int:
        """
        Delete all expired records from table.
        
        This method should be called periodically as a cleanup job.
        
        Returns:
            Number of records deleted
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            query = f"""
                DELETE FROM {self.table}
                WHERE ttl_expires_at < NOW()
            """
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    count = cur.rowcount
            
            if count > 0:
                logger.info(f"Deleted {count} expired records from {self.table}")
            
            return count
            
        except psycopg.Error as e:
            logger.error(f"Failed to delete expired records: {e}", exc_info=True)
            raise StorageQueryError(f"Delete expired failed: {e}") from e
    
    async def count(self, session_id: Optional[str] = None) -> int:
        """
        Count records in table.
        
        Args:
            session_id: Optional session filter
        
        Returns:
            Number of records (excluding expired)
        """
        if not self._connected or not self.pool:
            raise StorageConnectionError("Not connected to PostgreSQL")
        
        try:
            if session_id:
                query = f"""
                    SELECT COUNT(*) FROM {self.table}
                    WHERE session_id = %s
                    AND (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                """
                params = (session_id,)
            else:
                query = f"""
                    SELECT COUNT(*) FROM {self.table}
                    WHERE (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                """
                params = ()
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    result = await cur.fetchone()
                    return result[0]
                    
        except psycopg.Error as e:
            logger.error(f"Count query failed: {e}", exc_info=True)
            raise StorageQueryError(f"Count failed: {e}") from e
```

---

#### Testing Strategy

Create `tests/storage/test_postgres_adapter.py`:

```python
import pytest
import os
import uuid
from datetime import datetime, timedelta
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.base import StorageConnectionError, StorageDataError

@pytest.fixture
async def postgres_adapter():
    """Create and connect PostgreSQL adapter"""
    config = {
        'url': os.getenv('POSTGRES_URL'),
        'pool_size': 5,
        'table': 'active_context'
    }
    adapter = PostgresAdapter(config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.fixture
def session_id():
    """Generate unique test session ID"""
    return f"test-postgres-{uuid.uuid4()}"

@pytest.mark.asyncio
async def test_connect_disconnect(postgres_adapter):
    """Test connection lifecycle"""
    assert postgres_adapter.is_connected
    await postgres_adapter.disconnect()
    assert not postgres_adapter.is_connected

@pytest.mark.asyncio
async def test_store_and_retrieve(postgres_adapter, session_id):
    """Test storing and retrieving a record"""
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test message',
        'metadata': {'test': True}
    }
    record_id = await postgres_adapter.store(data)
    assert record_id is not None
    
    # Retrieve
    retrieved = await postgres_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['session_id'] == session_id
    assert retrieved['content'] == 'Test message'
    assert retrieved['metadata']['test'] is True
    
    # Cleanup
    await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_search_with_filters(postgres_adapter, session_id):
    """Test search with various filters"""
    # Store multiple records
    ids = []
    for i in range(5):
        data = {
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        }
        record_id = await postgres_adapter.store(data)
        ids.append(record_id)
    
    # Search all
    results = await postgres_adapter.search({
        'session_id': session_id,
        'limit': 10
    })
    assert len(results) == 5
    
    # Search with limit
    results = await postgres_adapter.search({
        'session_id': session_id,
        'limit': 2
    })
    assert len(results) == 2
    
    # Cleanup
    for record_id in ids:
        await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_delete(postgres_adapter, session_id):
    """Test deletion"""
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'To be deleted'
    }
    record_id = await postgres_adapter.store(data)
    
    # Delete
    deleted = await postgres_adapter.delete(record_id)
    assert deleted is True
    
    # Verify deleted
    retrieved = await postgres_adapter.retrieve(record_id)
    assert retrieved is None
    
    # Delete again (should return False)
    deleted = await postgres_adapter.delete(record_id)
    assert deleted is False

@pytest.mark.asyncio
async def test_ttl_expiration(postgres_adapter, session_id):
    """Test TTL expiration filtering"""
    # Store expired record
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Expired message',
        'ttl_expires_at': datetime.utcnow() - timedelta(hours=1)
    }
    record_id = await postgres_adapter.store(data)
    
    # Search without expired
    results = await postgres_adapter.search({
        'session_id': session_id,
        'include_expired': False
    })
    assert len(results) == 0
    
    # Search with expired
    results = await postgres_adapter.search({
        'session_id': session_id,
        'include_expired': True
    })
    assert len(results) == 1
    
    # Cleanup
    await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    config = {
        'url': os.getenv('POSTGRES_URL'),
        'table': 'active_context'
    }
    
    async with PostgresAdapter(config) as adapter:
        assert adapter.is_connected
        count = await adapter.count()
        assert count >= 0
    
    # Should be disconnected after context
    assert not adapter.is_connected
```

---

#### Tasks Checklist

- [ ] Create `src/storage/postgres_adapter.py`
- [ ] Import dependencies (psycopg, base classes, typing)
- [ ] Implement `__init__` with configuration validation
- [ ] Implement `connect()` with connection pool
- [ ] Implement `disconnect()` with cleanup
- [ ] Implement `store()` with table routing
- [ ] Implement `_store_active_context()` helper
- [ ] Implement `_store_working_memory()` helper
- [ ] Implement `retrieve()` with JSON parsing
- [ ] Implement `search()` with filters and pagination
- [ ] Implement `delete()` method
- [ ] Implement `delete_expired()` utility
- [ ] Implement `count()` utility
- [ ] Add comprehensive docstrings to all methods
- [ ] Add logging statements for debugging
- [ ] Create `tests/storage/test_postgres_adapter.py`
- [ ] Write connection lifecycle tests
- [ ] Write CRUD operation tests
- [ ] Write search and filter tests
- [ ] Write TTL expiration tests
- [ ] Write context manager tests
- [ ] Run tests: `pytest tests/storage/test_postgres_adapter.py -v`
- [ ] Verify >80% code coverage
- [ ] Update `src/storage/__init__.py` to export PostgresAdapter
- [ ] Commit: `git commit -m "feat: Add PostgreSQL storage adapter"`

---

#### Acceptance Criteria

✅ **Implementation**:
- All methods from `StorageAdapter` implemented
- Support for both `active_context` and `working_memory` tables
- Connection pooling configured properly
- Parameterized queries (no SQL injection risk)
- TTL-aware queries exclude expired records by default

✅ **Error Handling**:
- All exceptions properly caught and wrapped
- Informative error messages with context
- Logging for debugging (info, debug, error levels)
- Connection errors don't crash the application

✅ **Features**:
- JSON metadata stored and retrieved correctly
- Datetime fields converted to ISO format in responses
- Pagination and sorting work correctly
- Helper methods (`delete_expired`, `count`) functional

✅ **Testing**:
- All tests pass with real PostgreSQL database
- Connection lifecycle tested
- CRUD operations verified
- Search filters and pagination tested
- TTL expiration behavior validated
- Context manager protocol works
- Coverage >80%

✅ **Documentation**:
- Class docstring with usage example
- All methods have comprehensive docstrings
- Configuration options documented
- Examples show real usage patterns

✅ **Integration**:
- Can import: `from src.storage import PostgresAdapter`
- Works with existing `mas_memory` database
- Compatible with smoke test infrastructure

---

#### Deliverables

1. ✅ `src/storage/postgres_adapter.py` - Complete implementation (~500-600 lines)
2. ✅ `tests/storage/test_postgres_adapter.py` - Comprehensive tests (~200-300 lines)
3. ✅ Updated `src/storage/__init__.py` - Export PostgresAdapter
4. ✅ All tests passing
5. ✅ Git commit with PostgreSQL adapter

**Time Estimate**: 4-6 hours  
**Complexity**: Medium-High  
**Dependencies**: Priority 1 (base interface), Migration 001 (database schema)  
**Blocks**: Priority 3-4 (other adapters can be developed in parallel)

---

#### Common Pitfalls to Avoid

⚠️ **Don't use string formatting for SQL queries**
- Always use parameterized queries: `execute(sql, params)`
- Prevents SQL injection vulnerabilities

⚠️ **Don't forget to parse JSON fields**
- PostgreSQL returns JSONB as string or dict
- Always check type before parsing

⚠️ **Don't forget TTL filtering in searches**
- Default behavior should exclude expired records
- Provide `include_expired` flag for special cases

⚠️ **Don't forget to clean up test data**
- Use unique session IDs for tests
- Delete test records in teardown/finally blocks

⚠️ **Don't ignore connection pool limits**
- Pool can be exhausted under high load
- Use `async with pool.connection()` pattern

---

### Priority 3: Redis Adapter
**Estimated Time**: 3-4 hours  
**Assignee**: TBD  
**Status**: Not Started  
**File**: `src/storage/redis_adapter.py`

**Objective**: Implement high-speed cache adapter for active context (L1) using Redis with automatic TTL management and windowing for recent conversation turns.

---

#### Detailed Requirements

**1. Import Dependencies**

```python
"""
Redis storage adapter for high-speed active context caching.

This adapter provides sub-millisecond read access to recent conversation
turns using Redis lists with automatic TTL and window size management.

Features:
- Session-based key namespacing
- List-based storage for conversation turns
- Automatic TTL (24 hours)
- Window size limiting (keep only N recent turns)
- Pipeline operations for batch writes
- JSON serialization for complex data

Key Design:
- Key format: session:{session_id}:turns
- Data structure: Redis LIST (FIFO with limited size)
- TTL: 24 hours (auto-renewed on access)
"""

import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    StorageTimeoutError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)
```

**2. RedisAdapter Class Structure**

```python
class RedisAdapter(StorageAdapter):
    """
    Redis adapter for high-speed active context caching (L1 memory).
    
    This adapter uses Redis LIST data structure to store recent conversation
    turns with automatic windowing (keeping only N most recent) and TTL
    management (24-hour expiration).
    
    Key Features:
    - Sub-millisecond read latency
    - Automatic window size limiting
    - TTL auto-renewal on access
    - JSON serialization for metadata
    - Pipeline support for batch operations
    
    Configuration:
        {
            'url': 'redis://host:port/db',
            'host': 'localhost',  # Alternative to url
            'port': 6379,         # Alternative to url
            'db': 0,              # Database number
            'password': None,     # Optional password
            'socket_timeout': 5,  # Connection timeout
            'window_size': 10,    # Max turns to keep
            'ttl_seconds': 86400  # 24 hours
        }
    
    Data Structure:
        Key: session:{session_id}:turns
        Type: LIST
        Value: JSON-encoded turn data
        
        Example:
        session:abc123:turns -> [
            '{"turn_id": 3, "content": "Latest", "timestamp": "2025-10-20T10:03:00"}',
            '{"turn_id": 2, "content": "Middle", "timestamp": "2025-10-20T10:02:00"}',
            '{"turn_id": 1, "content": "Oldest", "timestamp": "2025-10-20T10:01:00"}'
        ]
    
    Example Usage:
        ```python
        config = {
            'url': 'redis://localhost:6379/0',
            'window_size': 10
        }
        
        adapter = RedisAdapter(config)
        await adapter.connect()
        
        # Store a turn (automatically added to session list)
        await adapter.store({
            'session_id': 'session-123',
            'turn_id': 1,
            'content': 'Hello!',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Get recent turns (from cache)
        turns = await adapter.search({
            'session_id': 'session-123',
            'limit': 5
        })
        
        await adapter.disconnect()
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redis adapter.
        
        Args:
            config: Configuration dictionary with:
                - url: Redis connection URL (optional if host/port provided)
                - host: Redis host (default: 'localhost')
                - port: Redis port (default: 6379)
                - db: Database number (default: 0)
                - password: Optional password
                - socket_timeout: Connection timeout (default: 5)
                - window_size: Max turns per session (default: 10)
                - ttl_seconds: Key expiration (default: 86400 = 24h)
        """
        super().__init__(config)
        
        # Connection config
        self.url = config.get('url')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6379)
        self.db = config.get('db', 0)
        self.password = config.get('password')
        self.socket_timeout = config.get('socket_timeout', 5)
        
        # Cache behavior config
        self.window_size = config.get('window_size', 10)
        self.ttl_seconds = config.get('ttl_seconds', 86400)  # 24 hours
        
        self.client: Optional[Redis] = None
        
        logger.info(
            f"RedisAdapter initialized (window: {self.window_size}, "
            f"TTL: {self.ttl_seconds}s)"
        )
```

**3. Connection Management**

```python
    async def connect(self) -> None:
        """
        Establish connection to Redis server.
        
        Creates async Redis client and verifies connectivity with PING.
        
        Raises:
            StorageConnectionError: If connection fails
            StorageTimeoutError: If connection times out
        """
        if self._connected and self.client:
            logger.warning("Already connected to Redis")
            return
        
        try:
            # Create Redis client from URL or host/port
            if self.url:
                self.client = await redis.from_url(
                    self.url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_timeout
                )
            else:
                self.client = Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_timeout
                )
            
            # Verify connection with PING
            pong = await self.client.ping()
            if not pong:
                raise StorageConnectionError("Redis PING failed")
            
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Failed to connect to Redis: {e}"
            ) from e
        except redis.TimeoutError as e:
            logger.error(f"Redis connection timeout: {e}", exc_info=True)
            raise StorageTimeoutError(
                f"Connection timeout: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}", exc_info=True)
            raise StorageConnectionError(
                f"Redis connection failed: {e}"
            ) from e
    
    async def disconnect(self) -> None:
        """
        Close Redis connection and cleanup resources.
        
        Safe to call multiple times (idempotent).
        """
        if not self.client:
            logger.warning("No active Redis connection")
            return
        
        try:
            await self.client.close()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error during Redis disconnect: {e}", exc_info=True)
            # Don't raise - disconnect should always succeed
```

**4. Store Method**

```python
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store conversation turn in session's Redis list.
        
        Behavior:
        1. Serialize turn data to JSON
        2. Add to head of session list (LPUSH)
        3. Trim list to window_size (keep only N recent)
        4. Set TTL on key (24 hours)
        
        Required fields:
            - session_id: Session identifier
            - turn_id: Turn number
            - content: Turn content/message
        
        Optional fields:
            - timestamp: ISO format timestamp
            - metadata: Additional data
        
        Args:
            data: Dictionary with turn data
        
        Returns:
            String identifier in format "session:{id}:turns:{turn_id}"
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If required fields missing
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        # Validate required fields
        validate_required_fields(data, ['session_id', 'turn_id', 'content'])
        
        try:
            session_id = data['session_id']
            turn_id = data['turn_id']
            key = self._make_key(session_id)
            
            # Prepare turn data for storage
            turn_data = {
                'turn_id': turn_id,
                'content': data['content'],
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
                'metadata': data.get('metadata', {})
            }
            
            # Serialize to JSON
            serialized = json.dumps(turn_data)
            
            # Use pipeline for atomic operations
            async with self.client.pipeline(transaction=True) as pipe:
                # Add to head of list (most recent first)
                await pipe.lpush(key, serialized)
                
                # Trim to window size (keep only N most recent)
                await pipe.ltrim(key, 0, self.window_size - 1)
                
                # Set/refresh TTL
                await pipe.expire(key, self.ttl_seconds)
                
                # Execute pipeline
                await pipe.execute()
            
            # Generate ID for this turn
            record_id = f"{key}:{turn_id}"
            
            logger.debug(
                f"Stored turn {turn_id} in session {session_id} "
                f"(key: {key})"
            )
            
            return record_id
            
        except redis.RedisError as e:
            logger.error(f"Redis store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to store in Redis: {e}") from e
        except json.JSONEncodeError as e:
            logger.error(f"JSON encoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to encode data: {e}") from e
    
    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}:turns"
```

**5. Retrieve Method**

```python
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific turn from session list.
        
        ID format: "session:{session_id}:turns:{turn_id}"
        
        Args:
            id: Turn identifier from store()
        
        Returns:
            Dictionary with turn data, or None if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            # Parse ID to extract key and turn_id
            # Format: session:{id}:turns:{turn_id}
            parts = id.rsplit(':', 1)
            if len(parts) != 2:
                raise StorageDataError(f"Invalid ID format: {id}")
            
            key = parts[0]
            turn_id = int(parts[1])
            
            # Get all items from list
            items = await self.client.lrange(key, 0, -1)
            
            # Search for matching turn_id
            for item in items:
                turn_data = json.loads(item)
                if turn_data.get('turn_id') == turn_id:
                    logger.debug(f"Retrieved turn {turn_id} from {key}")
                    return turn_data
            
            logger.debug(f"Turn {turn_id} not found in {key}")
            return None
            
        except redis.RedisError as e:
            logger.error(f"Redis retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to retrieve from Redis: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to decode data: {e}") from e
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid ID format: {e}", exc_info=True)
            raise StorageDataError(f"Invalid ID: {id}") from e
```

**6. Search Method**

```python
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recent turns for a session.
        
        Query parameters:
            - session_id: Session identifier (required)
            - limit: Maximum turns to return (default: window_size)
            - offset: Skip N turns (default: 0)
        
        Returns turns in reverse chronological order (most recent first).
        
        Args:
            query: Search parameters
        
        Returns:
            List of turn dictionaries
        
        Raises:
            StorageConnectionError: If not connected
            StorageDataError: If session_id missing
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        # Validate required query parameters
        if 'session_id' not in query:
            raise StorageDataError("session_id required in query")
        
        try:
            session_id = query['session_id']
            key = self._make_key(session_id)
            
            # Get pagination parameters
            limit = query.get('limit', self.window_size)
            offset = query.get('offset', 0)
            
            # Calculate range (Redis uses 0-based indexing)
            start = offset
            end = offset + limit - 1
            
            # Get items from list
            items = await self.client.lrange(key, start, end)
            
            if not items:
                logger.debug(f"No turns found for session {session_id}")
                return []
            
            # Deserialize all items
            results = []
            for item in items:
                turn_data = json.loads(item)
                results.append(turn_data)
            
            logger.debug(
                f"Retrieved {len(results)} turns for session {session_id} "
                f"(limit: {limit}, offset: {offset})"
            )
            
            return results
            
        except redis.RedisError as e:
            logger.error(f"Redis search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to search Redis: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}", exc_info=True)
            raise StorageDataError(f"Failed to decode data: {e}") from e
```

**7. Delete Method**

```python
    async def delete(self, id: str) -> bool:
        """
        Delete entire session cache or specific turn.
        
        If id is in format "session:{id}:turns:{turn_id}", deletes specific turn.
        If id is in format "session:{id}:turns", deletes entire session cache.
        
        Args:
            id: Session key or turn identifier
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            StorageConnectionError: If not connected
            StorageQueryError: If Redis operation fails
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            # Check if deleting specific turn or entire session
            if id.count(':') == 3:
                # Specific turn: session:{id}:turns:{turn_id}
                return await self._delete_turn(id)
            else:
                # Entire session: session:{id}:turns
                key = id if ':' in id else self._make_key(id)
                result = await self.client.delete(key)
                deleted = result > 0
                
                if deleted:
                    logger.debug(f"Deleted session cache: {key}")
                
                return deleted
                
        except redis.RedisError as e:
            logger.error(f"Redis delete failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to delete from Redis: {e}") from e
    
    async def _delete_turn(self, id: str) -> bool:
        """Delete specific turn from session list"""
        # Parse ID
        parts = id.rsplit(':', 1)
        key = parts[0]
        turn_id = int(parts[1])
        
        # Get all items
        items = await self.client.lrange(key, 0, -1)
        
        # Find and remove matching turn
        for item in items:
            turn_data = json.loads(item)
            if turn_data.get('turn_id') == turn_id:
                # Remove this item from list
                removed = await self.client.lrem(key, 1, item)
                if removed > 0:
                    logger.debug(f"Deleted turn {turn_id} from {key}")
                    return True
        
        return False
```

**8. Utility Methods**

```python
    async def clear_session(self, session_id: str) -> bool:
        """
        Clear all cached turns for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if cache existed and was cleared
        """
        key = self._make_key(session_id)
        return await self.delete(key)
    
    async def get_session_size(self, session_id: str) -> int:
        """
        Get number of cached turns for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of turns in cache
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            size = await self.client.llen(key)
            return size
        except redis.RedisError as e:
            logger.error(f"Failed to get session size: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to get size: {e}") from e
    
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if session has cached turns.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session cache exists
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            exists = await self.client.exists(key)
            return exists > 0
        except redis.RedisError as e:
            logger.error(f"Failed to check session existence: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to check existence: {e}") from e
    
    async def refresh_ttl(self, session_id: str) -> bool:
        """
        Refresh TTL for session cache (extend expiration).
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if TTL was refreshed
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Redis")
        
        try:
            key = self._make_key(session_id)
            result = await self.client.expire(key, self.ttl_seconds)
            return result
        except redis.RedisError as e:
            logger.error(f"Failed to refresh TTL: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to refresh TTL: {e}") from e
```

---

#### Testing Strategy

Create `tests/storage/test_redis_adapter.py`:

```python
import pytest
import os
import uuid
from datetime import datetime
from src.storage.redis_adapter import RedisAdapter
from src.storage.base import StorageConnectionError, StorageDataError

@pytest.fixture
async def redis_adapter():
    """Create and connect Redis adapter"""
    config = {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'window_size': 5,
        'ttl_seconds': 3600  # 1 hour for tests
    }
    adapter = RedisAdapter(config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.fixture
def session_id():
    """Generate unique test session ID"""
    return f"test-redis-{uuid.uuid4()}"

@pytest.fixture
async def cleanup_session(redis_adapter):
    """Cleanup test sessions after test"""
    sessions_to_clean = []
    
    def register(session_id: str):
        sessions_to_clean.append(session_id)
    
    yield register
    
    # Cleanup
    for session_id in sessions_to_clean:
        await redis_adapter.clear_session(session_id)

@pytest.mark.asyncio
async def test_connect_disconnect(redis_adapter):
    """Test connection lifecycle"""
    assert redis_adapter.is_connected
    await redis_adapter.disconnect()
    assert not redis_adapter.is_connected

@pytest.mark.asyncio
async def test_store_and_retrieve(redis_adapter, session_id, cleanup_session):
    """Test storing and retrieving a turn"""
    cleanup_session(session_id)
    
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test message',
        'metadata': {'role': 'user'}
    }
    record_id = await redis_adapter.store(data)
    assert record_id is not None
    assert session_id in record_id
    
    # Retrieve
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['turn_id'] == 1
    assert retrieved['content'] == 'Test message'
    assert retrieved['metadata']['role'] == 'user'

@pytest.mark.asyncio
async def test_window_size_limiting(redis_adapter, session_id, cleanup_session):
    """Test that window size is enforced"""
    cleanup_session(session_id)
    
    # Store more than window_size turns
    for i in range(10):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Check that only window_size items are kept
    size = await redis_adapter.get_session_size(session_id)
    assert size == 5  # window_size from fixture
    
    # Most recent should be available
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 10
    })
    assert len(results) == 5
    assert results[0]['turn_id'] == 9  # Most recent first

@pytest.mark.asyncio
async def test_search_with_pagination(redis_adapter, session_id, cleanup_session):
    """Test search with limit and offset"""
    cleanup_session(session_id)
    
    # Store 5 turns
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Get first 2
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 2
    })
    assert len(results) == 2
    assert results[0]['turn_id'] == 4  # Most recent
    assert results[1]['turn_id'] == 3
    
    # Get next 2 with offset
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 2,
        'offset': 2
    })
    assert len(results) == 2
    assert results[0]['turn_id'] == 2
    assert results[1]['turn_id'] == 1

@pytest.mark.asyncio
async def test_delete_session(redis_adapter, session_id, cleanup_session):
    """Test deleting entire session cache"""
    cleanup_session(session_id)
    
    # Store some turns
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message'
    })
    
    # Verify exists
    exists = await redis_adapter.session_exists(session_id)
    assert exists is True
    
    # Delete session
    deleted = await redis_adapter.clear_session(session_id)
    assert deleted is True
    
    # Verify gone
    exists = await redis_adapter.session_exists(session_id)
    assert exists is False

@pytest.mark.asyncio
async def test_ttl_refresh(redis_adapter, session_id, cleanup_session):
    """Test TTL refresh"""
    cleanup_session(session_id)
    
    # Store turn
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message'
    })
    
    # Refresh TTL
    refreshed = await redis_adapter.refresh_ttl(session_id)
    assert refreshed is True

@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    config = {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'window_size': 10
    }
    
    async with RedisAdapter(config) as adapter:
        assert adapter.is_connected
        exists = await adapter.session_exists('test')
        assert isinstance(exists, bool)
    
    # Should be disconnected after context
    assert not adapter.is_connected

@pytest.mark.asyncio
async def test_missing_session_id():
    """Test error on missing session_id"""
    config = {'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0')}
    
    async with RedisAdapter(config) as adapter:
        with pytest.raises(StorageDataError):
            await adapter.search({})  # Missing session_id
```

---

#### Tasks Checklist

- [ ] Create `src/storage/redis_adapter.py`
- [ ] Import dependencies (redis.asyncio, base classes)
- [ ] Implement `__init__` with configuration
- [ ] Implement `connect()` with Redis client creation
- [ ] Implement `disconnect()` with cleanup
- [ ] Implement `_make_key()` helper for key generation
- [ ] Implement `store()` with pipeline operations
- [ ] Implement windowing (LTRIM) in store
- [ ] Implement TTL setting in store
- [ ] Implement `retrieve()` with turn lookup
- [ ] Implement `search()` with pagination
- [ ] Implement `delete()` with session/turn handling
- [ ] Implement `_delete_turn()` helper
- [ ] Implement `clear_session()` utility
- [ ] Implement `get_session_size()` utility
- [ ] Implement `session_exists()` utility
- [ ] Implement `refresh_ttl()` utility
- [ ] Add comprehensive docstrings
- [ ] Add logging statements
- [ ] Create `tests/storage/test_redis_adapter.py`
- [ ] Write connection tests
- [ ] Write store/retrieve tests
- [ ] Write window size tests
- [ ] Write pagination tests
- [ ] Write delete tests
- [ ] Write utility method tests
- [ ] Write context manager tests
- [ ] Run tests: `pytest tests/storage/test_redis_adapter.py -v`
- [ ] Verify >80% coverage
- [ ] Update `src/storage/__init__.py` to export RedisAdapter
- [ ] Commit: `git commit -m "feat: Add Redis cache adapter"`

---

#### Acceptance Criteria

✅ **Implementation**:
- All methods from `StorageAdapter` implemented
- Pipeline operations for atomic writes
- Window size properly enforced (LTRIM)
- TTL automatically set and renewable
- JSON serialization/deserialization working

✅ **Cache Behavior**:
- Most recent turns returned first (LIFO ordering)
- Old turns evicted when window size exceeded
- Keys auto-expire after TTL period
- TTL refreshed on access

✅ **Error Handling**:
- Connection errors properly caught
- JSON errors handled gracefully
- Missing session_id raises clear error
- Logging for all operations

✅ **Performance**:
- Pipeline operations for multi-step writes
- Single round-trip for search operations
- Sub-millisecond read latency (target: <1ms)
- No blocking operations

✅ **Testing**:
- All tests pass with real Redis
- Window size limiting verified
- Pagination tested
- TTL behavior validated
- Cleanup after tests (no orphaned keys)
- Coverage >80%

✅ **Documentation**:
- Class docstring with usage example
- All methods documented
- Key format explained
- Data structure documented

---

#### Deliverables

1. ✅ `src/storage/redis_adapter.py` - Complete implementation (~400-500 lines)
2. ✅ `tests/storage/test_redis_adapter.py` - Comprehensive tests (~200-250 lines)
3. ✅ Updated `src/storage/__init__.py` - Export RedisAdapter
4. ✅ All tests passing
5. ✅ Git commit with Redis adapter

**Time Estimate**: 3-4 hours  
**Complexity**: Medium  
**Dependencies**: Priority 1 (base interface)  
**Blocks**: None (can be developed in parallel with Priority 2)

---

#### Common Pitfalls to Avoid

⚠️ **Don't forget pipeline for atomic operations**
- Always use pipeline for multi-step operations (LPUSH + LTRIM + EXPIRE)
- Prevents race conditions and partial updates

⚠️ **Don't forget JSON encoding/decoding**
- Redis stores strings, must serialize/deserialize
- Handle JSONDecodeError gracefully

⚠️ **Don't forget TTL renewal**
- TTL should be refreshed on write operations
- Use EXPIRE command after each modification

⚠️ **Don't forget test cleanup**
- Use unique session IDs per test
- Clean up keys in teardown or fixture

⚠️ **Don't use RPUSH/RPOP pattern**
- Use LPUSH/LTRIM for FIFO with size limit
- Keeps most recent items at head of list

---

### Priority 3A: Redis Adapter Enhancements
**Estimated Time**: 4-6 hours  
**Assignee**: TBD  
**Status**: Not Started  
**Files**: 
- `src/storage/redis_adapter.py`
- `tests/storage/test_redis_adapter.py`
- `tests/benchmarks/bench_redis_adapter.py` (new)

**Objective**: Enhance the Redis adapter with performance benchmarks, TTL-on-read optimization, and comprehensive edge case testing to ensure production readiness and optimal performance.

**Context**: Following the Priority 3 code review (Grade A - 96/100), several short-term improvements were identified to further enhance the Redis adapter's robustness and observability.

**Dependencies**: Priority 3 (Redis adapter implementation)  
**Blocks**: None (optional enhancements)

---

#### Sub-Priority 3A.1: Performance Benchmarking

**Estimated Time**: 2-3 hours  
**File**: `tests/benchmarks/bench_redis_adapter.py`

**Objective**: Create comprehensive performance benchmarks to validate the "sub-millisecond" latency claims and establish performance baselines for future optimizations.

##### Implementation

**1. Create Benchmark Test Suite**

```python
"""
Performance benchmarks for Redis adapter.

Measures latency and throughput for all operations to validate
performance characteristics and establish baselines.

Run with: pytest tests/benchmarks/bench_redis_adapter.py -v --benchmark-only
"""

import pytest
import os
import uuid
import time
from datetime import datetime, timezone
from src.storage.redis_adapter import RedisAdapter

@pytest.fixture
def redis_config():
    """Redis configuration for benchmarks"""
    return {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'window_size': 10,
        'ttl_seconds': 3600
    }

@pytest.fixture
async def redis_adapter(redis_config):
    """Create and connect Redis adapter"""
    adapter = RedisAdapter(redis_config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_store_single(redis_adapter, benchmark):
    """Benchmark single store operation"""
    session_id = f"bench-{uuid.uuid4()}"
    
    async def store_operation():
        return await redis_adapter.store({
            'session_id': session_id,
            'turn_id': 1,
            'content': 'Benchmark message',
            'metadata': {'test': True}
        })
    
    result = await benchmark(store_operation)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    assert result is not None

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_retrieve_single(redis_adapter, benchmark):
    """Benchmark single retrieve operation"""
    session_id = f"bench-{uuid.uuid4()}"
    
    # Setup: Store a record
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Benchmark message'
    })
    
    async def retrieve_operation():
        return await redis_adapter.retrieve(record_id)
    
    result = await benchmark(retrieve_operation)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    assert result is not None

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_search_10_items(redis_adapter, benchmark):
    """Benchmark search with 10 items"""
    session_id = f"bench-{uuid.uuid4()}"
    
    # Setup: Store 10 records
    for i in range(10):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    async def search_operation():
        return await redis_adapter.search({
            'session_id': session_id,
            'limit': 10
        })
    
    results = await benchmark(search_operation)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    assert len(results) == 10

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_throughput_100_stores(redis_adapter):
    """Benchmark throughput with 100 consecutive stores"""
    session_id = f"bench-{uuid.uuid4()}"
    
    start_time = time.perf_counter()
    
    for i in range(100):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    throughput = 100 / elapsed
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    print(f"\nThroughput: {throughput:.0f} ops/sec")
    print(f"Average latency: {elapsed/100*1000:.2f}ms per operation")
    
    # Assert minimum throughput (should be >1000 ops/sec on local Redis)
    assert throughput > 500, f"Throughput too low: {throughput:.0f} ops/sec"

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_session_size(redis_adapter, benchmark):
    """Benchmark session size query"""
    session_id = f"bench-{uuid.uuid4()}"
    
    # Setup: Store 5 records
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    async def size_operation():
        return await redis_adapter.get_session_size(session_id)
    
    size = await benchmark(size_operation)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    assert size == 5
```

**2. Manual Latency Measurement**

Add to `tests/benchmarks/bench_redis_adapter.py`:

```python
@pytest.mark.asyncio
async def test_measure_latencies(redis_adapter):
    """Measure and report detailed latencies"""
    session_id = f"bench-{uuid.uuid4()}"
    iterations = 100
    
    # Measure store latency
    store_times = []
    for i in range(iterations):
        start = time.perf_counter()
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
        store_times.append((time.perf_counter() - start) * 1000)  # ms
    
    # Measure retrieve latency
    record_id = f"session:{session_id}:turns:50"
    retrieve_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await redis_adapter.retrieve(record_id)
        retrieve_times.append((time.perf_counter() - start) * 1000)
    
    # Measure search latency
    search_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await redis_adapter.search({
            'session_id': session_id,
            'limit': 10
        })
        search_times.append((time.perf_counter() - start) * 1000)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Report results
    print("\n" + "="*60)
    print("Redis Adapter Performance Metrics")
    print("="*60)
    print(f"\nStore Operation (pipeline):")
    print(f"  Mean:   {sum(store_times)/len(store_times):.3f}ms")
    print(f"  Min:    {min(store_times):.3f}ms")
    print(f"  Max:    {max(store_times):.3f}ms")
    print(f"  P50:    {sorted(store_times)[50]:.3f}ms")
    print(f"  P95:    {sorted(store_times)[95]:.3f}ms")
    print(f"  P99:    {sorted(store_times)[99]:.3f}ms")
    
    print(f"\nRetrieve Operation:")
    print(f"  Mean:   {sum(retrieve_times)/len(retrieve_times):.3f}ms")
    print(f"  Min:    {min(retrieve_times):.3f}ms")
    print(f"  Max:    {max(retrieve_times):.3f}ms")
    print(f"  P50:    {sorted(retrieve_times)[50]:.3f}ms")
    print(f"  P95:    {sorted(retrieve_times)[95]:.3f}ms")
    print(f"  P99:    {sorted(retrieve_times)[99]:.3f}ms")
    
    print(f"\nSearch Operation (10 items):")
    print(f"  Mean:   {sum(search_times)/len(search_times):.3f}ms")
    print(f"  Min:    {min(search_times):.3f}ms")
    print(f"  Max:    {max(search_times):.3f}ms")
    print(f"  P50:    {sorted(search_times)[50]:.3f}ms")
    print(f"  P95:    {sorted(search_times)[95]:.3f}ms")
    print(f"  P99:    {sorted(search_times)[99]:.3f}ms")
    print("="*60)
    
    # Validate sub-millisecond claims for reads
    assert sum(retrieve_times)/len(retrieve_times) < 1.0, \
        "Retrieve should be <1ms on average"
```

**3. Documentation Update**

Update `src/storage/redis_adapter.py` module docstring to include actual benchmarks:

```python
"""
Performance Characteristics (measured on Redis 7.0, localhost, Python 3.13):
- Store latency (pipeline): 0.5-1.0ms (mean: 0.8ms)
- Retrieve latency: 0.2-0.5ms (mean: 0.3ms)
- Search latency (10 items): 0.3-0.6ms (mean: 0.4ms)
- Session size query: 0.1-0.2ms (mean: 0.15ms)
- Throughput: 1000-2000 ops/sec (single connection)

Benchmarks run with: pytest tests/benchmarks/bench_redis_adapter.py -v
"""
```

##### Deliverables

- [ ] Create `tests/benchmarks/` directory
- [ ] Create `tests/benchmarks/__init__.py`
- [ ] Create `tests/benchmarks/bench_redis_adapter.py`
- [ ] Implement benchmark tests
- [ ] Run benchmarks and document results
- [ ] Update module docstring with actual metrics
- [ ] Add benchmark results to code review report

##### Acceptance Criteria

✅ Benchmark suite runs successfully  
✅ All operations meet performance targets:
- Store: <2ms average
- Retrieve: <1ms average  
- Search (10 items): <1ms average
- Throughput: >500 ops/sec

✅ Metrics documented in code
✅ Percentiles (P50, P95, P99) measured

---

#### Sub-Priority 3A.2: TTL-on-Read Enhancement

**Estimated Time**: 1 hour  
**File**: `src/storage/redis_adapter.py`

**Objective**: Add configurable TTL refresh on read operations to support "active cache" semantics where frequently accessed sessions stay cached longer.

##### Implementation

**1. Add Configuration Option**

```python
class RedisAdapter(StorageAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # ... existing config ...
        
        # New: TTL refresh behavior
        self.refresh_ttl_on_read = config.get('refresh_ttl_on_read', False)
        
        logger.info(
            f"RedisAdapter initialized (window: {self.window_size}, "
            f"TTL: {self.ttl_seconds}s, refresh_on_read: {self.refresh_ttl_on_read})"
        )
```

**2. Update retrieve() Method**

```python
async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve specific turn from session list.
    
    If refresh_ttl_on_read is enabled, extends session TTL on access.
    """
    if not self._connected or not self.client:
        raise StorageConnectionError("Not connected to Redis")
    
    try:
        parts = id.rsplit(':', 1)
        if len(parts) != 2:
            raise StorageDataError(f"Invalid ID format: {id}")
        
        key = parts[0]
        turn_id = int(parts[1])
        
        # Get items from list
        items = await self.client.lrange(key, 0, -1)
        
        # Optional: Refresh TTL on access
        if self.refresh_ttl_on_read and items:
            await self.client.expire(key, self.ttl_seconds)
            logger.debug(f"Refreshed TTL for {key}")
        
        # Search for matching turn_id
        for item in items:
            turn_data = json.loads(item)
            if turn_data.get('turn_id') == turn_id:
                logger.debug(f"Retrieved turn {turn_id} from {key}")
                return turn_data
        
        logger.debug(f"Turn {turn_id} not found in {key}")
        return None
        
    except redis.RedisError as e:
        logger.error(f"Redis retrieve failed: {e}", exc_info=True)
        raise StorageQueryError(f"Failed to retrieve from Redis: {e}") from e
    # ... rest of error handling ...
```

**3. Update search() Method**

```python
async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get recent turns for a session.
    
    If refresh_ttl_on_read is enabled, extends session TTL on access.
    """
    if not self._connected or not self.client:
        raise StorageConnectionError("Not connected to Redis")
    
    if 'session_id' not in query:
        raise StorageDataError("session_id required in query")
    
    try:
        session_id = query['session_id']
        key = self._make_key(session_id)
        
        limit = query.get('limit', self.window_size)
        offset = query.get('offset', 0)
        
        start = offset
        end = offset + limit - 1
        
        items = await self.client.lrange(key, start, end)
        
        if not items:
            logger.debug(f"No turns found for session {session_id}")
            return []
        
        # Optional: Refresh TTL on access
        if self.refresh_ttl_on_read:
            await self.client.expire(key, self.ttl_seconds)
            logger.debug(f"Refreshed TTL for {key}")
        
        # Deserialize all items
        results = []
        for item in items:
            turn_data = json.loads(item)
            results.append(turn_data)
        
        logger.debug(
            f"Retrieved {len(results)} turns for session {session_id} "
            f"(limit: {limit}, offset: {offset})"
        )
        
        return results
        
    except redis.RedisError as e:
        logger.error(f"Redis search failed: {e}", exc_info=True)
        raise StorageQueryError(f"Failed to search Redis: {e}") from e
    # ... rest of error handling ...
```

**4. Update Documentation**

Add to class docstring:

```python
"""
Configuration:
    {
        'url': 'redis://host:port/db',
        'window_size': 10,
        'ttl_seconds': 86400,
        'refresh_ttl_on_read': False  # Set True for active cache behavior
    }

TTL Behavior:
    - refresh_ttl_on_read=False (default): TTL expires 24h after last write
    - refresh_ttl_on_read=True: TTL extends on every read, keeps active sessions cached
    
    Use refresh_ttl_on_read=True when:
    - Sessions have read-heavy access patterns
    - Want to keep frequently accessed sessions "hot"
    - Acceptable for inactive sessions to expire faster
"""
```

##### Deliverables

- [x] Add `refresh_ttl_on_read` configuration parameter
- [x] Update `retrieve()` to conditionally refresh TTL
- [x] Update `search()` to conditionally refresh TTL
- [x] Update class docstring with behavior explanation
- [x] Add tests for TTL refresh on read
- [x] Update code review report (see `docs/reports/implementation-report-3a2-ttl-on-read.md`)

##### Acceptance Criteria

✅ Configuration parameter added and documented  
✅ TTL refreshed on read when enabled  
✅ No TTL refresh on read when disabled (default)  
✅ Tests validate both behaviors  
✅ No performance regression  
✅ Backward compatible (default OFF)

---

#### Sub-Priority 3A.3: Edge Case Testing

**Estimated Time**: 1-2 hours  
**File**: `tests/storage/test_redis_adapter.py`

**Objective**: Add comprehensive edge case tests to ensure robustness in production scenarios including concurrent access, large payloads, and failure conditions.

##### Implementation

**1. Concurrent Access Tests**

```python
import asyncio

@pytest.mark.asyncio
async def test_concurrent_writes_same_session(redis_adapter, cleanup_session):
    """Test concurrent writes to the same session"""
    session_id = f"test-concurrent-{uuid.uuid4()}"
    cleanup_session(session_id)
    
    # Write 10 turns concurrently
    tasks = [
        redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Concurrent message {i}'
        })
        for i in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert len(results) == 10
    assert all(r is not None for r in results)
    
    # Verify window size still enforced
    size = await redis_adapter.get_session_size(session_id)
    assert size <= redis_adapter.window_size

@pytest.mark.asyncio
async def test_concurrent_reads(redis_adapter, session_id, cleanup_session):
    """Test concurrent reads don't cause issues"""
    cleanup_session(session_id)
    
    # Setup: Store some data
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Read concurrently
    tasks = [
        redis_adapter.search({
            'session_id': session_id,
            'limit': 5
        })
        for _ in range(20)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should return same data
    assert len(results) == 20
    assert all(len(r) == 5 for r in results)
```

**2. Large Payload Tests**

```python
@pytest.mark.asyncio
async def test_large_content(redis_adapter, session_id, cleanup_session):
    """Test storing large content (1MB)"""
    cleanup_session(session_id)
    
    # Create 1MB of content
    large_content = 'x' * (1024 * 1024)
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': large_content
    })
    
    # Verify retrieval
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert len(retrieved['content']) == 1024 * 1024

@pytest.mark.asyncio
async def test_large_metadata(redis_adapter, session_id, cleanup_session):
    """Test storing large metadata objects"""
    cleanup_session(session_id)
    
    # Create complex nested metadata
    large_metadata = {
        'nested': {
            'level1': {
                'level2': {
                    'level3': {
                        'data': ['item'] * 1000
                    }
                }
            }
        },
        'list': list(range(1000)),
        'strings': {f'key_{i}': f'value_{i}' for i in range(100)}
    }
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test',
        'metadata': large_metadata
    })
    
    # Verify retrieval
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert len(retrieved['metadata']['list']) == 1000
```

**3. Error Condition Tests**

```python
@pytest.mark.asyncio
async def test_invalid_turn_id_format(redis_adapter):
    """Test handling of invalid turn_id in retrieve"""
    with pytest.raises(StorageDataError):
        await redis_adapter.retrieve("invalid:id:format")

@pytest.mark.asyncio
async def test_nonexistent_session(redis_adapter):
    """Test searching nonexistent session"""
    results = await redis_adapter.search({
        'session_id': 'nonexistent-session-12345',
        'limit': 10
    })
    assert results == []

@pytest.mark.asyncio
async def test_empty_content(redis_adapter, session_id, cleanup_session):
    """Test storing empty content"""
    cleanup_session(session_id)
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': ''  # Empty string
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['content'] == ''

@pytest.mark.asyncio
async def test_special_characters_in_content(redis_adapter, session_id, cleanup_session):
    """Test storing special characters"""
    cleanup_session(session_id)
    
    special_content = "Test\n\t\r\x00emoji🎉unicode中文"
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': special_content
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['content'] == special_content

@pytest.mark.asyncio
async def test_delete_nonexistent_session(redis_adapter):
    """Test deleting nonexistent session returns False"""
    deleted = await redis_adapter.delete('session:nonexistent:turns')
    assert deleted is False
```

**4. Boundary Tests**

```python
@pytest.mark.asyncio
async def test_zero_window_size():
    """Test adapter with window_size=0"""
    config = {
        'url': os.getenv('REDIS_URL'),
        'window_size': 0  # Edge case
    }
    
    adapter = RedisAdapter(config)
    await adapter.connect()
    
    session_id = f"test-{uuid.uuid4()}"
    
    # Should not store anything with window_size=0
    await adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test'
    })
    
    size = await adapter.get_session_size(session_id)
    assert size == 0
    
    await adapter.disconnect()

@pytest.mark.asyncio
async def test_negative_offset(redis_adapter, session_id, cleanup_session):
    """Test search with negative offset"""
    cleanup_session(session_id)
    
    # Store some data
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Negative offset should return empty or handle gracefully
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 5,
        'offset': -1
    })
    
    # Should handle gracefully (Redis LRANGE handles negative indices)
    assert isinstance(results, list)
```

##### Deliverables

- [x] Add concurrent access tests (2 tests)
- [x] Add large payload tests (2 tests)
- [x] Add error condition tests (5 tests)
- [x] Add boundary tests (2 tests)
- [x] Add session isolation tests (3 tests)
- [x] Update test documentation
- [x] Run full test suite to verify compatibility

##### Acceptance Criteria

✅ All new tests pass (26 total tests)  
✅ Concurrent writes don't cause data corruption  
✅ Large payloads (up to 1MB) handled correctly  
✅ Error conditions handled gracefully  
✅ Boundary conditions tested  
✅ Total test count: 11 (original) + 15 (new) = 26 tests  
✅ Test coverage comprehensive

---

#### Priority 3A Summary

**Total Time Estimate**: 4-6 hours

| Sub-Priority | Task | Time | Status |
|--------------|------|------|--------|
| 3A.1 | Performance Benchmarks | 2-3h | Not Started |
| 3A.2 | TTL-on-Read Enhancement | 1h | Not Started |
| 3A.3 | Edge Case Testing | 1-2h | Not Started |

**Dependencies**:
- ✅ Priority 3 complete (Redis adapter implemented)
- ✅ Priority 3 code review complete
- ✅ All immediate fixes applied

**Deliverables**:
1. `tests/benchmarks/bench_redis_adapter.py` - Performance benchmark suite
2. Updated `src/storage/redis_adapter.py` - TTL-on-read feature
3. Enhanced `tests/storage/test_redis_adapter.py` - 11 new edge case tests
4. Performance metrics documentation

**Success Metrics**:
- ✅ All benchmarks passing with targets met
- ✅ TTL-on-read feature working and configurable
- ✅ 19+ total tests all passing
- ✅ Test coverage >98%
- ✅ Performance baseline established
- ✅ Redis adapter Grade A+ (98-100/100)

**Optional Enhancements** (can be deferred to Phase 2):
- Connection pool implementation
- Compression support
- Monitoring/metrics integration

---

### Priority 4: Vector & Graph Adapters
**Estimated Time**: 6-8 hours (combined)  
**Assignee**: TBD  
**Status**: Not Started  
**Files**: 
- `src/storage/qdrant_adapter.py`
- `src/storage/neo4j_adapter.py`
- `src/storage/typesense_adapter.py`

**Objective**: Implement adapters for long-term storage backends (L3/L4 memory) - vector search, graph relationships, and full-text search.

---

## 4A. Qdrant Adapter (Vector Search - L3 Episodic Memory)

**File**: `src/storage/qdrant_adapter.py`  
**Estimated Time**: 2-3 hours

### Detailed Requirements

**1. Import Dependencies**

```python
"""
Qdrant vector store adapter for episodic memory (L3).

This adapter provides vector similarity search for conversation embeddings,
enabling semantic retrieval of past interactions.

Features:
- Vector embedding storage and retrieval
- Similarity search with configurable thresholds
- Collection management
- Batch upload support
- Metadata filtering
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from typing import Dict, Any, List, Optional
import uuid
import logging

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)
```

**2. QdrantAdapter Class**

```python
class QdrantAdapter(StorageAdapter):
    """
    Qdrant adapter for vector similarity search (L3 episodic memory).
    
    Configuration:
        {
            'url': 'http://host:port',
            'host': 'localhost',  # Alternative to url
            'port': 6333,
            'collection_name': 'episodic_memory',
            'vector_size': 384,  # Embedding dimension
            'distance': 'Cosine'  # or 'Euclid', 'Dot'
        }
    
    Example:
        ```python
        config = {
            'url': 'http://192.168.107.187:6333',
            'collection_name': 'episodic_memory',
            'vector_size': 384
        }
        
        adapter = QdrantAdapter(config)
        await adapter.connect()
        
        # Store embedding
        await adapter.store({
            'vector': [0.1, 0.2, ...],  # 384-dim embedding
            'content': 'Original text',
            'session_id': 'session-123',
            'metadata': {'timestamp': '2025-10-20T10:00:00Z'}
        })
        
        # Search similar vectors
        results = await adapter.search({
            'vector': query_embedding,
            'limit': 5,
            'score_threshold': 0.7
        })
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get('url')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6333)
        self.collection_name = config.get('collection_name', 'episodic_memory')
        self.vector_size = config.get('vector_size', 384)
        self.distance = config.get('distance', 'Cosine')
        self.client: Optional[QdrantClient] = None
        
        logger.info(
            f"QdrantAdapter initialized (collection: {self.collection_name}, "
            f"vector_size: {self.vector_size})"
        )
    
    async def connect(self) -> None:
        """Connect to Qdrant and ensure collection exists"""
        try:
            if self.url:
                self.client = QdrantClient(url=self.url)
            else:
                self.client = QdrantClient(host=self.host, port=self.port)
            
            # Verify connection
            collections = self.client.get_collections()
            
            # Create collection if doesn't exist
            collection_exists = any(
                c.name == self.collection_name 
                for c in collections.collections
            )
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance[self.distance.upper()]
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            
            self._connected = True
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Close Qdrant connection"""
        if self.client:
            self.client.close()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Qdrant")
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Store vector embedding with metadata"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        validate_required_fields(data, ['vector'])
        
        try:
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=data['vector'],
                payload={
                    'content': data.get('content', ''),
                    'session_id': data.get('session_id', ''),
                    'metadata': data.get('metadata', {}),
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Stored vector: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Qdrant store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to store: {e}") from e
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve vector and metadata by ID"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id]
            )
            
            if not points:
                return None
            
            point = points[0]
            return {
                'id': str(point.id),
                'vector': point.vector,
                **point.payload
            }
            
        except Exception as e:
            logger.error(f"Qdrant retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Failed to retrieve: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Query params:
            - vector: Query embedding (required)
            - limit: Max results (default: 10)
            - score_threshold: Min similarity score (optional)
            - filter: Metadata filters (optional)
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        validate_required_fields(query, ['vector'])
        
        try:
            search_params = {
                'collection_name': self.collection_name,
                'query_vector': query['vector'],
                'limit': query.get('limit', 10),
            }
            
            if 'score_threshold' in query:
                search_params['score_threshold'] = query['score_threshold']
            
            # Add filters if provided
            if 'filter' in query:
                search_params['query_filter'] = Filter(
                    must=[
                        FieldCondition(
                            key=k,
                            match=MatchValue(value=v)
                        )
                        for k, v in query['filter'].items()
                    ]
                )
            
            results = self.client.search(**search_params)
            
            return [
                {
                    'id': str(r.id),
                    'score': r.score,
                    **r.payload
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Search failed: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """Delete vector by ID"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )
            logger.debug(f"Deleted vector: {id}")
            return True
        except Exception as e:
            logger.error(f"Qdrant delete failed: {e}", exc_info=True)
            return False
```

---

## 4B. Neo4j Adapter (Graph Database - L3 Relationships)

**File**: `src/storage/neo4j_adapter.py`  
**Estimated Time**: 2-3 hours

### Detailed Requirements

**1. Import Dependencies**

```python
"""
Neo4j graph database adapter for entity relationships (L3).

This adapter manages entities and their relationships, enabling
graph-based traversal and relationship queries.

Features:
- Entity node creation and retrieval
- Relationship management
- Cypher query execution
- Graph traversal operations
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Dict, Any, List, Optional
import logging

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)
```

**2. Neo4jAdapter Class**

```python
class Neo4jAdapter(StorageAdapter):
    """
    Neo4j adapter for entity and relationship storage (L3).
    
    Configuration:
        {
            'uri': 'bolt://host:port',
            'user': 'neo4j',
            'password': 'password',
            'database': 'neo4j'  # Optional, default DB
        }
    
    Example:
        ```python
        config = {
            'uri': 'bolt://192.168.107.187:7687',
            'user': 'neo4j',
            'password': 'your_password'
        }
        
        adapter = Neo4jAdapter(config)
        await adapter.connect()
        
        # Store entity
        await adapter.store({
            'type': 'entity',
            'label': 'Person',
            'properties': {'name': 'Alice', 'age': 30}
        })
        
        # Store relationship
        await adapter.store({
            'type': 'relationship',
            'from': 'Alice',
            'to': 'Bob',
            'relationship': 'KNOWS',
            'properties': {'since': '2020'}
        })
        
        # Query relationships
        results = await adapter.search({
            'cypher': 'MATCH (p:Person)-[r:KNOWS]->(f) RETURN p, r, f',
            'params': {}
        })
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.uri = config.get('uri')
        self.user = config.get('user', 'neo4j')
        self.password = config.get('password')
        self.database = config.get('database', 'neo4j')
        self.driver: Optional[AsyncDriver] = None
        
        if not self.uri or not self.password:
            raise StorageDataError("Neo4j URI and password required")
        
        logger.info(f"Neo4jAdapter initialized (uri: {self.uri})")
    
    async def connect(self) -> None:
        """Connect to Neo4j database"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # Verify connection
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS test")
                await result.single()
            
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.uri}")
            
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            self.driver = None
            self._connected = False
            logger.info("Disconnected from Neo4j")
    
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store entity or relationship.
        
        For entities:
            - type: 'entity'
            - label: Node label
            - properties: Dict of properties
        
        For relationships:
            - type: 'relationship'
            - from: Source node identifier
            - to: Target node identifier
            - relationship: Relationship type
            - properties: Dict of properties
        """
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        validate_required_fields(data, ['type'])
        
        try:
            if data['type'] == 'entity':
                return await self._store_entity(data)
            elif data['type'] == 'relationship':
                return await self._store_relationship(data)
            else:
                raise StorageDataError(f"Unknown type: {data['type']}")
                
        except Exception as e:
            logger.error(f"Neo4j store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Store failed: {e}") from e
    
    async def _store_entity(self, data: Dict[str, Any]) -> str:
        """Store entity node"""
        validate_required_fields(data, ['label', 'properties'])
        
        label = data['label']
        props = data['properties']
        
        # Generate ID from name or use UUID
        node_id = props.get('name', str(uuid.uuid4()))
        props['id'] = node_id
        
        cypher = f"""
            MERGE (n:{label} {{id: $id}})
            SET n += $props
            RETURN n.id AS id
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(cypher, id=node_id, props=props)
            record = await result.single()
            return record['id']
    
    async def _store_relationship(self, data: Dict[str, Any]) -> str:
        """Store relationship between nodes"""
        validate_required_fields(data, ['from', 'to', 'relationship'])
        
        from_id = data['from']
        to_id = data['to']
        rel_type = data['relationship']
        props = data.get('properties', {})
        
        cypher = f"""
            MATCH (from {{id: $from_id}})
            MATCH (to {{id: $to_id}})
            MERGE (from)-[r:{rel_type}]->(to)
            SET r += $props
            RETURN id(r) AS id
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                cypher,
                from_id=from_id,
                to_id=to_id,
                props=props
            )
            record = await result.single()
            return str(record['id'])
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity by ID"""
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        try:
            cypher = "MATCH (n {id: $id}) RETURN n"
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, id=id)
                record = await result.single()
                
                if not record:
                    return None
                
                node = record['n']
                return dict(node)
                
        except Exception as e:
            logger.error(f"Neo4j retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Retrieve failed: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute Cypher query.
        
        Query params:
            - cypher: Cypher query string
            - params: Query parameters (optional)
        """
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        validate_required_fields(query, ['cypher'])
        
        try:
            cypher = query['cypher']
            params = query.get('params', {})
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, **params)
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Search failed: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        if not self._connected or not self.driver:
            raise StorageConnectionError("Not connected to Neo4j")
        
        try:
            cypher = "MATCH (n {id: $id}) DETACH DELETE n"
            
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, id=id)
                summary = await result.consume()
                return summary.counters.nodes_deleted > 0
                
        except Exception as e:
            logger.error(f"Neo4j delete failed: {e}", exc_info=True)
            return False
```

---

## 4C. Typesense Adapter (Full-Text Search - L4 Semantic Memory)

**File**: `src/storage/typesense_adapter.py`  
**Estimated Time**: 2-3 hours

### Detailed Requirements

**1. Import Dependencies**

```python
"""
Typesense full-text search adapter for semantic memory (L4).

This adapter provides fast, typo-tolerant full-text search for
distilled knowledge and facts.

Features:
- Document indexing
- Full-text search with typo tolerance
- Faceted search
- Schema management
"""

import httpx
from typing import Dict, Any, List, Optional
import logging

from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    validate_required_fields,
)

logger = logging.getLogger(__name__)
```

**2. TypesenseAdapter Class**

```python
class TypesenseAdapter(StorageAdapter):
    """
    Typesense adapter for full-text search (L4 semantic memory).
    
    Configuration:
        {
            'url': 'http://host:port',
            'api_key': 'your_api_key',
            'collection_name': 'semantic_memory',
            'schema': {
                'name': 'semantic_memory',
                'fields': [
                    {'name': 'content', 'type': 'string'},
                    {'name': 'session_id', 'type': 'string', 'facet': True},
                    {'name': 'created_at', 'type': 'int64'}
                ]
            }
        }
    
    Example:
        ```python
        config = {
            'url': 'http://192.168.107.187:8108',
            'api_key': os.getenv('TYPESENSE_API_KEY'),
            'collection_name': 'semantic_memory'
        }
        
        adapter = TypesenseAdapter(config)
        await adapter.connect()
        
        # Index document
        await adapter.store({
            'content': 'User prefers dark mode',
            'session_id': 'session-123',
            'fact_type': 'preference'
        })
        
        # Search
        results = await adapter.search({
            'q': 'dark mode',
            'query_by': 'content',
            'limit': 5
        })
        ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get('url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.collection_name = config.get('collection_name', 'semantic_memory')
        self.schema = config.get('schema')
        self.client: Optional[httpx.AsyncClient] = None
        
        if not self.url or not self.api_key:
            raise StorageDataError("Typesense URL and API key required")
        
        logger.info(f"TypesenseAdapter initialized (collection: {self.collection_name})")
    
    async def connect(self) -> None:
        """Connect to Typesense and ensure collection exists"""
        try:
            self.client = httpx.AsyncClient(
                headers={'X-TYPESENSE-API-KEY': self.api_key},
                timeout=10.0
            )
            
            # Check if collection exists
            response = await self.client.get(
                f"{self.url}/collections/{self.collection_name}"
            )
            
            if response.status_code == 404 and self.schema:
                # Create collection
                response = await self.client.post(
                    f"{self.url}/collections",
                    json=self.schema
                )
                response.raise_for_status()
                logger.info(f"Created collection: {self.collection_name}")
            
            self._connected = True
            logger.info(f"Connected to Typesense at {self.url}")
            
        except Exception as e:
            logger.error(f"Typesense connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Close Typesense connection"""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Typesense")
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Index document in Typesense"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")
        
        try:
            # Add auto-generated ID if not present
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            response = await self.client.post(
                f"{self.url}/collections/{self.collection_name}/documents",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Indexed document: {result['id']}")
            return result['id']
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Typesense store failed: {e}", exc_info=True)
            raise StorageQueryError(f"Store failed: {e}") from e
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")
        
        try:
            response = await self.client.get(
                f"{self.url}/collections/{self.collection_name}/documents/{id}"
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Typesense retrieve failed: {e}", exc_info=True)
            raise StorageQueryError(f"Retrieve failed: {e}") from e
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Full-text search.
        
        Query params:
            - q: Search query
            - query_by: Fields to search
            - filter_by: Optional filters
            - limit: Max results (default: 10)
        """
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")
        
        validate_required_fields(query, ['q', 'query_by'])
        
        try:
            params = {
                'q': query['q'],
                'query_by': query['query_by'],
                'per_page': query.get('limit', 10),
            }
            
            if 'filter_by' in query:
                params['filter_by'] = query['filter_by']
            
            response = await self.client.get(
                f"{self.url}/collections/{self.collection_name}/documents/search",
                params=params
            )
            response.raise_for_status()
            
            result = response.json()
            return [hit['document'] for hit in result.get('hits', [])]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Typesense search failed: {e}", exc_info=True)
            raise StorageQueryError(f"Search failed: {e}") from e
    
    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Typesense")
        
        try:
            response = await self.client.delete(
                f"{self.url}/collections/{self.collection_name}/documents/{id}"
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Typesense delete failed: {e}", exc_info=True)
            return False
```

---

## Testing Strategy

Create test files for each adapter:

**1. `tests/storage/test_qdrant_adapter.py`** - Vector search tests
**2. `tests/storage/test_neo4j_adapter.py`** - Graph operations tests
**3. `tests/storage/test_typesense_adapter.py`** - Full-text search tests

Each test suite should cover:
- Connection lifecycle
- Store and retrieve operations
- Search functionality (specific to adapter type)
- Delete operations
- Error handling
- Context manager protocol

---

## Tasks Checklist

### Qdrant Adapter
- [ ] Create `src/storage/qdrant_adapter.py`
- [ ] Implement connection and collection management
- [ ] Implement vector storage
- [ ] Implement similarity search with filters
- [ ] Implement retrieval and deletion
- [ ] Add comprehensive docstrings
- [ ] Create `tests/storage/test_qdrant_adapter.py`
- [ ] Write and run tests
- [ ] Verify >80% coverage

### Neo4j Adapter
- [ ] Create `src/storage/neo4j_adapter.py`
- [ ] Implement async driver connection
- [ ] Implement entity storage
- [ ] Implement relationship storage
- [ ] Implement Cypher query execution
- [ ] Add comprehensive docstrings
- [ ] Create `tests/storage/test_neo4j_adapter.py`
- [ ] Write and run tests
- [ ] Verify >80% coverage

### Typesense Adapter
- [ ] Create `src/storage/typesense_adapter.py`
- [ ] Implement HTTP client connection
- [ ] Implement document indexing
- [ ] Implement full-text search
- [ ] Implement schema management
- [ ] Add comprehensive docstrings
- [ ] Create `tests/storage/test_typesense_adapter.py`
- [ ] Write and run tests
- [ ] Verify >80% coverage

### Integration
- [ ] Update `src/storage/__init__.py` to export all three adapters
- [ ] Run all storage tests: `pytest tests/storage/ -v`
- [ ] Verify overall coverage >80%
- [ ] Commit: `git commit -m "feat: Add vector, graph, and search adapters"`

---

## Acceptance Criteria

✅ **Qdrant Adapter**:
- Vector storage and retrieval working
- Similarity search with score thresholds
- Collection auto-creation
- Metadata filtering functional

✅ **Neo4j Adapter**:
- Entity and relationship creation
- Cypher query execution
- Graph traversal operations
- Proper transaction handling

✅ **Typesense Adapter**:
- Document indexing
- Full-text search with typo tolerance
- Schema management
- Faceted search support

✅ **All Adapters**:
- Implement `StorageAdapter` interface
- Comprehensive error handling
- Logging for debugging
- Tests with real backends
- Coverage >80%
- Documentation complete

---

## Deliverables

1. ✅ `src/storage/qdrant_adapter.py` - Vector search (~300-400 lines)
2. ✅ `src/storage/neo4j_adapter.py` - Graph database (~300-400 lines)
3. ✅ `src/storage/typesense_adapter.py` - Full-text search (~300-400 lines)
4. ✅ Test files for all three adapters (~150-200 lines each)
5. ✅ Updated `src/storage/__init__.py`
6. ✅ All tests passing
7. ✅ Git commit

**Time Estimate**: 6-8 hours (2-3 hours per adapter)  
**Complexity**: Medium-High  
**Dependencies**: Priority 1 (base interface)  
**Blocks**: None (can develop in parallel with Priority 2-3)

---

## Common Pitfalls

⚠️ **Qdrant**: Vector dimension must match configuration
⚠️ **Neo4j**: Always use parameterized Cypher queries  
⚠️ **Typesense**: Schema must be defined before indexing  
⚠️ **All**: Import `uuid` module for ID generation  
⚠️ **All**: Clean up test data to avoid accumulation

---

### Priority 5: Database Migrations
**Estimated Time**: 2-3 hours  
**Assignee**: TBD  
**Status**: Not Started  
**File**: `migrations/001_active_context.sql`

**Objective**: Create PostgreSQL schema for L1 (Active Context) and L2 (Working Memory) storage with proper tables, indexes, and constraints.

---

#### Detailed Requirements

**1. Migration File Structure**

The migration file should be idempotent and well-documented:

```sql
-- ============================================================================
-- Migration: 001_active_context
-- Description: Create tables for L1 (Active Context) and L2 (Working Memory)
-- Author: Development Team
-- Date: 2025-10-20
-- Dependencies: None (first migration)
-- ============================================================================

-- This migration creates the foundational tables for the memory system:
-- 1. active_context: Recent conversation turns (L1 memory, TTL: 24h)
-- 2. working_memory: Session-scoped facts (L2 memory, TTL: 7 days)

-- Both tables support TTL-based expiration for automatic cleanup
-- ============================================================================
```

**2. Active Context Table (L1 Memory)**

```sql
-- ============================================================================
-- Table: active_context
-- Purpose: Store recent conversation turns for immediate context
-- Memory Tier: L1 (Active Context)
-- TTL: 24 hours
-- Expected Size: 10-20 records per session
-- ============================================================================

CREATE TABLE IF NOT EXISTS active_context (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Session identification
    session_id VARCHAR(255) NOT NULL,
    
    -- Turn identification (sequential within session)
    turn_id INTEGER NOT NULL,
    
    -- Content
    content TEXT NOT NULL,
    
    -- Metadata (flexible JSON storage for role, tokens, embeddings, etc.)
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- TTL expiration (NULL = never expires)
    ttl_expires_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_session_turn UNIQUE (session_id, turn_id),
    
    -- Check constraints
    CONSTRAINT valid_turn_id CHECK (turn_id >= 0),
    CONSTRAINT valid_ttl CHECK (ttl_expires_at IS NULL OR ttl_expires_at > created_at)
);

-- Add table comment
COMMENT ON TABLE active_context IS 'L1 memory: Recent conversation turns with 24-hour TTL';
COMMENT ON COLUMN active_context.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN active_context.session_id IS 'Session identifier (UUID or custom ID)';
COMMENT ON COLUMN active_context.turn_id IS 'Sequential turn number within session';
COMMENT ON COLUMN active_context.content IS 'Turn content (user message or assistant response)';
COMMENT ON COLUMN active_context.metadata IS 'Flexible metadata (role, tokens, embeddings, etc.)';
COMMENT ON COLUMN active_context.created_at IS 'Timestamp when turn was created';
COMMENT ON COLUMN active_context.ttl_expires_at IS 'Expiration timestamp (NULL = never expires)';
```

**3. Active Context Indexes**

```sql
-- ============================================================================
-- Indexes for active_context table
-- ============================================================================

-- Index for session lookups (most common query pattern)
-- Covers: SELECT * FROM active_context WHERE session_id = ?
CREATE INDEX IF NOT EXISTS idx_active_context_session 
ON active_context(session_id);

-- Composite index for session + turn lookups
-- Covers: SELECT * FROM active_context WHERE session_id = ? AND turn_id = ?
CREATE INDEX IF NOT EXISTS idx_active_context_session_turn 
ON active_context(session_id, turn_id DESC);

-- Index for TTL-based cleanup queries
-- Covers: DELETE FROM active_context WHERE ttl_expires_at < NOW()
-- Partial index (only indexes rows with TTL set)
CREATE INDEX IF NOT EXISTS idx_active_context_expires 
ON active_context(ttl_expires_at) 
WHERE ttl_expires_at IS NOT NULL;

-- Index for created_at ordering (time-based queries)
-- Covers: SELECT * FROM active_context ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_active_context_created 
ON active_context(created_at DESC);

-- GIN index for metadata searches (optional, for advanced queries)
-- Covers: SELECT * FROM active_context WHERE metadata @> '{"role": "user"}'
-- Uncomment if needed:
-- CREATE INDEX IF NOT EXISTS idx_active_context_metadata 
-- ON active_context USING GIN (metadata);
```

**4. Working Memory Table (L2 Memory)**

```sql
-- ============================================================================
-- Table: working_memory
-- Purpose: Store session-scoped facts, entities, and preferences
-- Memory Tier: L2 (Working Memory)
-- TTL: 7 days
-- Expected Size: Variable, depends on session complexity
-- ============================================================================

CREATE TABLE IF NOT EXISTS working_memory (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Session identification
    session_id VARCHAR(255) NOT NULL,
    
    -- Fact classification
    fact_type VARCHAR(50) NOT NULL,  -- 'entity', 'preference', 'constraint', 'goal', etc.
    
    -- Content
    content TEXT NOT NULL,
    
    -- Confidence score (0.0 to 1.0)
    confidence FLOAT DEFAULT 1.0,
    
    -- Source tracking (which turns contributed to this fact)
    source_turn_ids INTEGER[] DEFAULT '{}',
    
    -- Metadata (flexible JSON storage)
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- TTL expiration (NULL = never expires)
    ttl_expires_at TIMESTAMP,
    
    -- Check constraints
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT valid_fact_type CHECK (LENGTH(fact_type) > 0),
    CONSTRAINT valid_ttl_wm CHECK (ttl_expires_at IS NULL OR ttl_expires_at > created_at)
);

-- Add table comments
COMMENT ON TABLE working_memory IS 'L2 memory: Session-scoped facts and entities with 7-day TTL';
COMMENT ON COLUMN working_memory.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN working_memory.session_id IS 'Session identifier';
COMMENT ON COLUMN working_memory.fact_type IS 'Fact classification (entity, preference, constraint, goal, etc.)';
COMMENT ON COLUMN working_memory.content IS 'Fact content or description';
COMMENT ON COLUMN working_memory.confidence IS 'Confidence score (0.0 = uncertain, 1.0 = certain)';
COMMENT ON COLUMN working_memory.source_turn_ids IS 'Array of turn IDs that contributed to this fact';
COMMENT ON COLUMN working_memory.metadata IS 'Additional metadata (embeddings, references, etc.)';
COMMENT ON COLUMN working_memory.created_at IS 'Timestamp when fact was first created';
COMMENT ON COLUMN working_memory.updated_at IS 'Timestamp when fact was last updated';
COMMENT ON COLUMN working_memory.ttl_expires_at IS 'Expiration timestamp (NULL = never expires)';
```

**5. Working Memory Indexes**

```sql
-- ============================================================================
-- Indexes for working_memory table
-- ============================================================================

-- Index for session lookups
-- Covers: SELECT * FROM working_memory WHERE session_id = ?
CREATE INDEX IF NOT EXISTS idx_working_memory_session 
ON working_memory(session_id);

-- Composite index for session + fact_type lookups
-- Covers: SELECT * FROM working_memory WHERE session_id = ? AND fact_type = ?
CREATE INDEX IF NOT EXISTS idx_working_memory_session_type 
ON working_memory(session_id, fact_type);

-- Index for fact type filtering
-- Covers: SELECT * FROM working_memory WHERE fact_type = ?
CREATE INDEX IF NOT EXISTS idx_working_memory_type 
ON working_memory(fact_type);

-- Index for confidence-based filtering (high-confidence facts)
-- Covers: SELECT * FROM working_memory WHERE confidence > 0.7
CREATE INDEX IF NOT EXISTS idx_working_memory_confidence 
ON working_memory(confidence DESC);

-- Index for TTL-based cleanup queries
-- Covers: DELETE FROM working_memory WHERE ttl_expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_working_memory_expires 
ON working_memory(ttl_expires_at) 
WHERE ttl_expires_at IS NOT NULL;

-- Index for updated_at ordering (recently updated facts)
-- Covers: SELECT * FROM working_memory ORDER BY updated_at DESC
CREATE INDEX IF NOT EXISTS idx_working_memory_updated 
ON working_memory(updated_at DESC);

-- GIN index for metadata searches (optional)
-- Uncomment if needed:
-- CREATE INDEX IF NOT EXISTS idx_working_memory_metadata 
-- ON working_memory USING GIN (metadata);

-- GIN index for source_turn_ids array searches (optional)
-- Covers: SELECT * FROM working_memory WHERE 5 = ANY(source_turn_ids)
-- Uncomment if needed:
-- CREATE INDEX IF NOT EXISTS idx_working_memory_source_turns 
-- ON working_memory USING GIN (source_turn_ids);
```

**6. Helper Functions (Optional but Recommended)**

```sql
-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on working_memory updates
CREATE TRIGGER trigger_working_memory_updated_at
    BEFORE UPDATE ON working_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp on row modification';
```

**7. Cleanup Functions (Optional but Recommended)**

```sql
-- ============================================================================
-- Cleanup Functions (for scheduled jobs)
-- ============================================================================

-- Function to delete expired records from active_context
CREATE OR REPLACE FUNCTION cleanup_expired_active_context()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM active_context
    WHERE ttl_expires_at IS NOT NULL 
    AND ttl_expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_active_context() IS 'Delete expired active context records, returns count';

-- Function to delete expired records from working_memory
CREATE OR REPLACE FUNCTION cleanup_expired_working_memory()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM working_memory
    WHERE ttl_expires_at IS NOT NULL 
    AND ttl_expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_working_memory() IS 'Delete expired working memory records, returns count';

-- Convenience function to cleanup both tables
CREATE OR REPLACE FUNCTION cleanup_expired_records()
RETURNS TABLE(
    active_context_deleted INTEGER,
    working_memory_deleted INTEGER,
    total_deleted INTEGER
) AS $$
DECLARE
    ac_count INTEGER;
    wm_count INTEGER;
BEGIN
    ac_count := cleanup_expired_active_context();
    wm_count := cleanup_expired_working_memory();
    
    RETURN QUERY SELECT ac_count, wm_count, (ac_count + wm_count);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_records() IS 'Cleanup expired records from all tables, returns counts';
```

**8. Statistics and Monitoring Views (Optional)**

```sql
-- ============================================================================
-- Monitoring Views (optional, for observability)
-- ============================================================================

-- View for active context statistics per session
CREATE OR REPLACE VIEW v_active_context_stats AS
SELECT 
    session_id,
    COUNT(*) as turn_count,
    MIN(created_at) as first_turn_at,
    MAX(created_at) as last_turn_at,
    COUNT(*) FILTER (WHERE ttl_expires_at < NOW()) as expired_count,
    COUNT(*) FILTER (WHERE ttl_expires_at >= NOW() OR ttl_expires_at IS NULL) as active_count
FROM active_context
GROUP BY session_id;

COMMENT ON VIEW v_active_context_stats IS 'Statistics for active context by session';

-- View for working memory statistics per session
CREATE OR REPLACE VIEW v_working_memory_stats AS
SELECT 
    session_id,
    COUNT(*) as fact_count,
    COUNT(DISTINCT fact_type) as fact_type_count,
    AVG(confidence) as avg_confidence,
    MIN(created_at) as first_fact_at,
    MAX(updated_at) as last_updated_at,
    COUNT(*) FILTER (WHERE ttl_expires_at < NOW()) as expired_count,
    COUNT(*) FILTER (WHERE ttl_expires_at >= NOW() OR ttl_expires_at IS NULL) as active_count
FROM working_memory
GROUP BY session_id;

COMMENT ON VIEW v_working_memory_stats IS 'Statistics for working memory by session';
```

**9. Grant Permissions (Adjust as needed)**

```sql
-- ============================================================================
-- Permissions (adjust user as needed)
-- ============================================================================

-- Grant permissions to application user
-- Replace 'app_user' with your actual application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON active_context TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON working_memory TO app_user;
-- GRANT USAGE, SELECT ON SEQUENCE active_context_id_seq TO app_user;
-- GRANT USAGE, SELECT ON SEQUENCE working_memory_id_seq TO app_user;
-- GRANT EXECUTE ON FUNCTION cleanup_expired_active_context() TO app_user;
-- GRANT EXECUTE ON FUNCTION cleanup_expired_working_memory() TO app_user;
-- GRANT EXECUTE ON FUNCTION cleanup_expired_records() TO app_user;
```

**10. Migration Verification Queries**

```sql
-- ============================================================================
-- Verification Queries (run after migration to verify)
-- ============================================================================

-- List all tables
\dt

-- Describe active_context table
\d active_context

-- Describe working_memory table
\d working_memory

-- List all indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('active_context', 'working_memory')
ORDER BY tablename, indexname;

-- List all functions
SELECT 
    proname as function_name,
    pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname LIKE '%cleanup%' OR proname LIKE '%update_updated_at%';

-- Test cleanup functions
SELECT cleanup_expired_records();
```

---

#### Migration Execution

**Apply Migration**

```bash
# Load environment variables
source .env

# Apply migration (creates tables if they don't exist)
psql "$POSTGRES_URL" -f migrations/001_active_context.sql

# Verify tables created
psql "$POSTGRES_URL" -c "\dt"

# Verify indexes created
psql "$POSTGRES_URL" -c "SELECT tablename, indexname FROM pg_indexes WHERE tablename IN ('active_context', 'working_memory');"

# Test insert into active_context
psql "$POSTGRES_URL" -c "
INSERT INTO active_context (session_id, turn_id, content, ttl_expires_at)
VALUES ('test-session', 1, 'Test message', NOW() + INTERVAL '24 hours')
RETURNING *;
"

# Test insert into working_memory
psql "$POSTGRES_URL" -c "
INSERT INTO working_memory (session_id, fact_type, content, confidence, ttl_expires_at)
VALUES ('test-session', 'preference', 'User prefers dark mode', 0.95, NOW() + INTERVAL '7 days')
RETURNING *;
"

# Test cleanup function
psql "$POSTGRES_URL" -c "SELECT cleanup_expired_records();"

# Clean up test data
psql "$POSTGRES_URL" -c "DELETE FROM active_context WHERE session_id = 'test-session';"
psql "$POSTGRES_URL" -c "DELETE FROM working_memory WHERE session_id = 'test-session';"
```

---

#### Rollback Script (Optional)

Create `migrations/001_active_context_rollback.sql`:

```sql
-- ============================================================================
-- Rollback: 001_active_context
-- Description: Remove L1/L2 memory tables and related objects
-- WARNING: This will delete all data in these tables
-- ============================================================================

-- Drop views
DROP VIEW IF EXISTS v_working_memory_stats;
DROP VIEW IF EXISTS v_active_context_stats;

-- Drop functions
DROP FUNCTION IF EXISTS cleanup_expired_records();
DROP FUNCTION IF EXISTS cleanup_expired_working_memory();
DROP FUNCTION IF EXISTS cleanup_expired_active_context();
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop tables (CASCADE removes dependent objects)
DROP TABLE IF EXISTS working_memory CASCADE;
DROP TABLE IF EXISTS active_context CASCADE;

-- Verify cleanup
\dt
\df

SELECT 'Rollback completed successfully' AS status;
```

---

#### Tasks Checklist

- [ ] Create `migrations/001_active_context.sql`
- [ ] Add migration header with metadata
- [ ] Create `active_context` table with all columns
- [ ] Add constraints to `active_context` table
- [ ] Add comments to `active_context` table and columns
- [ ] Create indexes for `active_context` table (4-5 indexes)
- [ ] Create `working_memory` table with all columns
- [ ] Add constraints to `working_memory` table
- [ ] Add comments to `working_memory` table and columns
- [ ] Create indexes for `working_memory` table (5-6 indexes)
- [ ] Add `update_updated_at_column()` function and trigger
- [ ] Add cleanup functions (`cleanup_expired_*`)
- [ ] Add monitoring views (optional)
- [ ] Add permission grants (commented, adjust as needed)
- [ ] Add verification queries at end of file
- [ ] Create `migrations/001_active_context_rollback.sql` (optional)
- [ ] Test migration on development database
- [ ] Verify all tables created: `psql "$POSTGRES_URL" -c "\dt"`
- [ ] Verify all indexes created
- [ ] Test insert operations on both tables
- [ ] Test cleanup functions
- [ ] Clean up test data
- [ ] Update `migrations/README.md` with instructions
- [ ] Commit: `git commit -m "feat: Add L1/L2 database schema migration"`

---

#### Acceptance Criteria

✅ **Tables**:
- `active_context` table created with proper schema
- `working_memory` table created with proper schema
- All columns have appropriate types and constraints
- TTL columns support NULL (permanent records)
- Unique constraints prevent duplicate records

✅ **Indexes**:
- Session lookup indexes for fast queries
- TTL expiration indexes for cleanup jobs
- Composite indexes for common query patterns
- Partial indexes where appropriate (TTL only)
- GIN indexes commented for optional advanced queries

✅ **Functions**:
- `update_updated_at_column()` trigger function working
- Cleanup functions delete expired records
- Functions return meaningful results

✅ **Idempotency**:
- Migration can run multiple times safely
- Uses `CREATE TABLE IF NOT EXISTS`
- Uses `CREATE OR REPLACE` for functions
- No errors on re-run

✅ **Documentation**:
- Comments on all tables and columns
- Clear section headers
- Purpose and usage documented
- Verification queries included

✅ **Testing**:
- Migration applies without errors
- Tables queryable
- Inserts work correctly
- Constraints enforced
- Cleanup functions operational
- Can rollback if needed

---

#### Deliverables

1. ✅ `migrations/001_active_context.sql` - Complete schema (~300-400 lines)
2. ✅ `migrations/001_active_context_rollback.sql` - Rollback script (~30-40 lines)
3. ✅ Updated `migrations/README.md` - Execution instructions
4. ✅ Verified migration on `mas_memory` database
5. ✅ Test data inserted and cleaned up
6. ✅ Git commit with migration files

**Time Estimate**: 2-3 hours  
**Complexity**: Medium  
**Dependencies**: Priority 0 (migrations directory), mas_memory database created  
**Blocks**: Priority 2 (PostgreSQL adapter needs these tables)

---

#### Common Pitfalls to Avoid

⚠️ **Don't forget IF NOT EXISTS**
- Use `CREATE TABLE IF NOT EXISTS` for idempotency
- Use `CREATE INDEX IF NOT EXISTS` for indexes

⚠️ **Don't forget comments**
- Add table and column comments for documentation
- Helps future developers understand schema

⚠️ **Don't use bare CREATE TABLE**
- Always include constraints (CHECK, UNIQUE)
- Define sensible defaults

⚠️ **Don't forget to test**
- Run verification queries after migration
- Test inserts on both tables
- Test cleanup functions

⚠️ **Don't grant excessive permissions**
- Only grant necessary permissions
- Comment out permission grants by default
- Let admin configure per environment

---

### Priority 6: Unit Tests
**Estimated Time**: 4-5 hours  
**Assignee**: TBD  
**Status**: Not Started  
**Files**: 
- `tests/test_postgres_adapter.py`
- `tests/test_redis_adapter.py`
- `tests/test_qdrant_adapter.py`
- `tests/test_neo4j_adapter.py`
- `tests/test_typesense_adapter.py`

**Objective**: Comprehensive test coverage for all storage adapters with >80% code coverage per adapter.

---

#### Test Strategy Overview

**Test Pyramid**:
1. **Unit Tests** (70%): Test individual methods in isolation with mocked dependencies
2. **Integration Tests** (25%): Test adapter interactions with real databases (using test containers or separate test DBs)
3. **Smoke Tests** (5%): Already implemented in `test_connectivity.py`

**Testing Approach**:
- Use **pytest** with async support (`pytest-asyncio`)
- Use **fixtures** for setup/teardown and dependency injection
- Use **mocks** for unit tests (avoid hitting real services)
- Use **real services** for integration tests (mark with `@pytest.mark.integration`)
- Maintain **test isolation** - each test should be independent
- Follow **AAA pattern** - Arrange, Act, Assert

---

#### Test Fixtures (Common)

Create `tests/fixtures.py` for shared test utilities:

```python
"""
Shared test fixtures for storage adapter tests.
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio

# ============================================================================
# Sample Test Data
# ============================================================================

@pytest.fixture
def sample_session_id():
    """Generate consistent test session ID."""
    return "test-session-12345"

@pytest.fixture
def sample_turn_data():
    """Generate sample conversation turn data."""
    return {
        "turn_id": 1,
        "content": "Hello, how are you?",
        "metadata": {
            "role": "user",
            "tokens": 5,
            "timestamp": "2025-10-20T10:00:00Z"
        }
    }

@pytest.fixture
def sample_working_memory_data():
    """Generate sample working memory fact."""
    return {
        "fact_type": "preference",
        "content": "User prefers dark mode",
        "confidence": 0.95,
        "source_turn_ids": [1, 3]
    }

@pytest.fixture
def sample_vector_embedding():
    """Generate sample embedding vector."""
    return [0.1] * 384  # 384-dimensional vector

@pytest.fixture
def sample_graph_entity():
    """Generate sample graph entity."""
    return {
        "entity_id": "person_001",
        "entity_type": "Person",
        "properties": {
            "name": "Alice",
            "age": 30,
            "occupation": "Engineer"
        }
    }

# ============================================================================
# Time-based Fixtures
# ============================================================================

@pytest.fixture
def current_time():
    """Provide consistent current time for tests."""
    return datetime(2025, 10, 20, 12, 0, 0)

@pytest.fixture
def expired_time():
    """Provide time that's already expired."""
    return datetime(2025, 10, 19, 12, 0, 0)  # Yesterday

@pytest.fixture
def future_time():
    """Provide future time for TTL tests."""
    return datetime(2025, 10, 21, 12, 0, 0)  # Tomorrow

# ============================================================================
# Database Connection Fixtures (for integration tests)
# ============================================================================

@pytest.fixture
async def postgres_connection():
    """
    Provide real PostgreSQL connection for integration tests.
    Requires mas_memory database to be running.
    """
    import psycopg
    from tests.config import POSTGRES_URL
    
    conn = await psycopg.AsyncConnection.connect(POSTGRES_URL)
    
    # Setup: Clear test data
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM active_context WHERE session_id LIKE 'test-%'")
        await cur.execute("DELETE FROM working_memory WHERE session_id LIKE 'test-%'")
        await conn.commit()
    
    yield conn
    
    # Teardown: Clear test data
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM active_context WHERE session_id LIKE 'test-%'")
        await cur.execute("DELETE FROM working_memory WHERE session_id LIKE 'test-%'")
        await conn.commit()
    
    await conn.close()

@pytest.fixture
async def redis_connection():
    """
    Provide real Redis connection for integration tests.
    """
    import redis.asyncio as aioredis
    from tests.config import REDIS_URL
    
    client = await aioredis.from_url(REDIS_URL, decode_responses=True)
    
    # Setup: Clear test data
    keys = await client.keys("test:*")
    if keys:
        await client.delete(*keys)
    
    yield client
    
    # Teardown: Clear test data
    keys = await client.keys("test:*")
    if keys:
        await client.delete(*keys)
    
    await client.close()

# ============================================================================
# Mock Fixtures (for unit tests)
# ============================================================================

@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection for unit tests."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    
    # Setup cursor context manager
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__aexit__.return_value = None
    
    # Setup fetchone/fetchall defaults
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    
    return mock_conn

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit tests."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.keys.return_value = []
    return mock

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for unit tests."""
    from qdrant_client.models import PointStruct, ScoredPoint
    
    mock = Mock()
    mock.get_collections.return_value.collections = []
    mock.upsert.return_value = None
    mock.retrieve.return_value = []
    mock.search.return_value = []
    mock.delete.return_value = None
    
    return mock

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for unit tests."""
    mock_driver = Mock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    mock_session.run.return_value = AsyncMock()
    
    return mock_driver

@pytest.fixture
def mock_typesense_client():
    """Mock Typesense client for unit tests."""
    mock = Mock()
    mock.collections.create.return_value = {"name": "test_collection"}
    mock.collections.__getitem__.return_value.documents.create.return_value = {"id": "1"}
    mock.collections.__getitem__.return_value.documents.search.return_value = {"hits": []}
    
    return mock
```

---

#### Test Configuration

Create `tests/config.py`:

```python
"""
Test configuration - loads from environment or uses defaults.
"""
import os

# Database URLs (use environment variables or defaults)
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@192.168.107.172:5432/mas_memory")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.107.172:6379/0")
QDRANT_URL = os.getenv("QDRANT_URL", "http://192.168.107.187:6333")
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://192.168.107.187:7687")
TYPESENSE_URL = os.getenv("TYPESENSE_URL", "http://192.168.107.187:8108")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")

# Test configuration
TEST_TIMEOUT = 10  # seconds
```

---

#### PostgreSQL Adapter Tests

Create `tests/test_postgres_adapter.py`:

```python
"""
Unit and integration tests for PostgresAdapter.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.base import StorageError, ConnectionError

# ============================================================================
# Unit Tests (with mocks)
# ============================================================================

@pytest.mark.asyncio
class TestPostgresAdapterUnit:
    """Unit tests for PostgresAdapter (mocked dependencies)."""
    
    async def test_init(self):
        """Test adapter initialization."""
        adapter = PostgresAdapter("postgresql://localhost/test")
        assert adapter.connection_string == "postgresql://localhost/test"
        assert adapter.pool is None
    
    async def test_connect_success(self, mock_postgres_connection):
        """Test successful connection."""
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            assert adapter.pool is not None
    
    async def test_connect_failure(self):
        """Test connection failure handling."""
        with patch('psycopg.AsyncConnection.connect', side_effect=Exception("Connection failed")):
            adapter = PostgresAdapter("postgresql://localhost/test")
            with pytest.raises(ConnectionError):
                await adapter.connect()
    
    async def test_disconnect(self, mock_postgres_connection):
        """Test disconnection."""
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            await adapter.disconnect()
            mock_postgres_connection.close.assert_called_once()
    
    async def test_add_turn_success(self, mock_postgres_connection, sample_session_id, sample_turn_data):
        """Test adding a conversation turn."""
        mock_cursor = mock_postgres_connection.cursor.return_value.__aenter__.return_value
        mock_cursor.fetchone.return_value = (1,)  # Return turn_id
        
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            
            turn_id = await adapter.add_turn(
                sample_session_id,
                sample_turn_data["content"],
                sample_turn_data["metadata"]
            )
            
            assert turn_id == 1
            mock_cursor.execute.assert_called_once()
    
    async def test_get_recent_turns(self, mock_postgres_connection, sample_session_id):
        """Test retrieving recent turns."""
        mock_cursor = mock_postgres_connection.cursor.return_value.__aenter__.return_value
        mock_cursor.fetchall.return_value = [
            (1, "test-session", 1, "Hello", {"role": "user"}, datetime.now()),
            (2, "test-session", 2, "Hi!", {"role": "assistant"}, datetime.now())
        ]
        
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            
            turns = await adapter.get_recent_turns(sample_session_id, limit=10)
            
            assert len(turns) == 2
            assert turns[0]["turn_id"] == 1
            assert turns[1]["turn_id"] == 2
    
    async def test_add_fact_success(self, mock_postgres_connection, sample_session_id, sample_working_memory_data):
        """Test adding a working memory fact."""
        mock_cursor = mock_postgres_connection.cursor.return_value.__aenter__.return_value
        mock_cursor.fetchone.return_value = (1,)  # Return fact_id
        
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            
            fact_id = await adapter.add_fact(
                sample_session_id,
                sample_working_memory_data["fact_type"],
                sample_working_memory_data["content"],
                confidence=sample_working_memory_data["confidence"]
            )
            
            assert fact_id == 1
    
    async def test_get_facts_by_type(self, mock_postgres_connection, sample_session_id):
        """Test retrieving facts by type."""
        mock_cursor = mock_postgres_connection.cursor.return_value.__aenter__.return_value
        mock_cursor.fetchall.return_value = [
            (1, "test-session", "preference", "Dark mode", 0.95, [], {}, datetime.now(), datetime.now())
        ]
        
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            
            facts = await adapter.get_facts(sample_session_id, fact_type="preference")
            
            assert len(facts) == 1
            assert facts[0]["fact_type"] == "preference"
    
    async def test_cleanup_expired_turns(self, mock_postgres_connection):
        """Test cleanup of expired turns."""
        mock_cursor = mock_postgres_connection.cursor.return_value.__aenter__.return_value
        mock_cursor.rowcount = 5
        
        with patch('psycopg.AsyncConnection.connect', return_value=mock_postgres_connection):
            adapter = PostgresAdapter("postgresql://localhost/test")
            await adapter.connect()
            
            deleted = await adapter.cleanup_expired_turns()
            
            assert deleted == 5

# ============================================================================
# Integration Tests (real database)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestPostgresAdapterIntegration:
    """Integration tests for PostgresAdapter (real database)."""
    
    async def test_full_workflow(self, sample_session_id):
        """Test complete CRUD workflow."""
        from tests.config import POSTGRES_URL
        
        adapter = PostgresAdapter(POSTGRES_URL)
        await adapter.connect()
        
        try:
            # Add turns
            turn1 = await adapter.add_turn(sample_session_id, "Hello", {"role": "user"})
            turn2 = await adapter.add_turn(sample_session_id, "Hi!", {"role": "assistant"})
            
            assert turn1 > 0
            assert turn2 > turn1
            
            # Retrieve turns
            turns = await adapter.get_recent_turns(sample_session_id, limit=10)
            assert len(turns) == 2
            assert turns[0]["content"] == "Hello"
            
            # Add fact
            fact_id = await adapter.add_fact(
                sample_session_id,
                "preference",
                "User likes Python",
                confidence=0.9
            )
            assert fact_id > 0
            
            # Retrieve facts
            facts = await adapter.get_facts(sample_session_id)
            assert len(facts) == 1
            assert facts[0]["fact_type"] == "preference"
            
            # Update fact
            await adapter.update_fact(fact_id, content="User loves Python", confidence=0.95)
            updated_facts = await adapter.get_facts(sample_session_id)
            assert updated_facts[0]["content"] == "User loves Python"
            assert updated_facts[0]["confidence"] == 0.95
            
            # Delete turn
            await adapter.delete_turn(sample_session_id, turn1)
            remaining_turns = await adapter.get_recent_turns(sample_session_id)
            assert len(remaining_turns) == 1
            
            # Clear session
            await adapter.clear_session(sample_session_id)
            final_turns = await adapter.get_recent_turns(sample_session_id)
            final_facts = await adapter.get_facts(sample_session_id)
            assert len(final_turns) == 0
            assert len(final_facts) == 0
            
        finally:
            await adapter.disconnect()
    
    async def test_ttl_expiration(self, sample_session_id):
        """Test TTL-based expiration."""
        from tests.config import POSTGRES_URL
        
        adapter = PostgresAdapter(POSTGRES_URL)
        await adapter.connect()
        
        try:
            # Add turn with past TTL (expired)
            expired_ttl = datetime.now() - timedelta(hours=1)
            await adapter.add_turn(
                sample_session_id,
                "Expired message",
                {"role": "user"},
                ttl=expired_ttl
            )
            
            # Cleanup expired
            deleted = await adapter.cleanup_expired_turns()
            assert deleted >= 1
            
            # Verify turn is gone
            turns = await adapter.get_recent_turns(sample_session_id)
            assert len(turns) == 0
            
        finally:
            await adapter.disconnect()
```

---

#### Redis Adapter Tests

Create `tests/test_redis_adapter.py`:

```python
"""
Unit and integration tests for RedisAdapter.
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.storage.redis_adapter import RedisAdapter
from src.storage.base import StorageError, ConnectionError

# ============================================================================
# Unit Tests (with mocks)
# ============================================================================

@pytest.mark.asyncio
class TestRedisAdapterUnit:
    """Unit tests for RedisAdapter (mocked dependencies)."""
    
    async def test_init(self):
        """Test adapter initialization."""
        adapter = RedisAdapter("redis://localhost:6379")
        assert adapter.redis_url == "redis://localhost:6379"
        assert adapter.client is None
    
    async def test_connect_success(self, mock_redis_client):
        """Test successful connection."""
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            adapter = RedisAdapter("redis://localhost:6379")
            await adapter.connect()
            assert adapter.client is not None
            mock_redis_client.ping.assert_called_once()
    
    async def test_cache_turn(self, mock_redis_client, sample_session_id, sample_turn_data):
        """Test caching a conversation turn."""
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            adapter = RedisAdapter("redis://localhost:6379")
            await adapter.connect()
            
            await adapter.cache_turn(
                sample_session_id,
                sample_turn_data["turn_id"],
                sample_turn_data["content"],
                sample_turn_data["metadata"]
            )
            
            mock_redis_client.set.assert_called_once()
    
    async def test_get_cached_turns(self, mock_redis_client, sample_session_id):
        """Test retrieving cached turns."""
        import json
        mock_redis_client.keys.return_value = [f"active:{sample_session_id}:1", f"active:{sample_session_id}:2"]
        mock_redis_client.get.side_effect = [
            json.dumps({"turn_id": 1, "content": "Hello"}),
            json.dumps({"turn_id": 2, "content": "Hi"})
        ]
        
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            adapter = RedisAdapter("redis://localhost:6379")
            await adapter.connect()
            
            turns = await adapter.get_cached_turns(sample_session_id)
            
            assert len(turns) == 2
            assert turns[0]["turn_id"] == 1
    
    async def test_window_management(self, mock_redis_client, sample_session_id):
        """Test sliding window size management."""
        mock_redis_client.keys.return_value = [f"active:{sample_session_id}:{i}" for i in range(25)]
        
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            adapter = RedisAdapter("redis://localhost:6379", window_size=20)
            await adapter.connect()
            
            await adapter.enforce_window_size(sample_session_id)
            
            # Should delete oldest 5 keys
            assert mock_redis_client.delete.call_count >= 1

# ============================================================================
# Integration Tests (real Redis)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestRedisAdapterIntegration:
    """Integration tests for RedisAdapter (real Redis)."""
    
    async def test_cache_and_retrieve(self, sample_session_id):
        """Test caching and retrieving turns."""
        from tests.config import REDIS_URL
        
        adapter = RedisAdapter(REDIS_URL)
        await adapter.connect()
        
        try:
            # Cache turns
            await adapter.cache_turn(sample_session_id, 1, "Hello", {"role": "user"})
            await adapter.cache_turn(sample_session_id, 2, "Hi!", {"role": "assistant"})
            
            # Retrieve
            turns = await adapter.get_cached_turns(sample_session_id)
            
            assert len(turns) == 2
            assert any(t["content"] == "Hello" for t in turns)
            assert any(t["content"] == "Hi!" for t in turns)
            
            # Clear
            await adapter.clear_session(sample_session_id)
            cleared_turns = await adapter.get_cached_turns(sample_session_id)
            assert len(cleared_turns) == 0
            
        finally:
            await adapter.disconnect()
    
    async def test_ttl_expiration(self, sample_session_id):
        """Test TTL expiration."""
        from tests.config import REDIS_URL
        import asyncio
        
        adapter = RedisAdapter(REDIS_URL)
        await adapter.connect()
        
        try:
            # Cache with short TTL (2 seconds)
            await adapter.cache_turn(sample_session_id, 1, "Expires soon", {}, ttl=2)
            
            # Should exist immediately
            turns = await adapter.get_cached_turns(sample_session_id)
            assert len(turns) == 1
            
            # Wait for expiration
            await asyncio.sleep(3)
            
            # Should be gone
            expired_turns = await adapter.get_cached_turns(sample_session_id)
            assert len(expired_turns) == 0
            
        finally:
            await adapter.disconnect()
```

---

#### Qdrant, Neo4j, Typesense Tests

Create similar test files following the same pattern:

- `tests/test_qdrant_adapter.py` - Vector search tests
- `tests/test_neo4j_adapter.py` - Graph database tests
- `tests/test_typesense_adapter.py` - Full-text search tests

Each should include:
- Unit tests with mocked clients
- Integration tests with real services
- CRUD operation tests
- Error handling tests
- Edge case tests

---

#### Running Tests

**Run all tests**:
```bash
pytest tests/
```

**Run unit tests only** (fast, no external dependencies):
```bash
pytest tests/ -m "not integration"
```

**Run integration tests only** (requires services):
```bash
pytest tests/ -m integration
```

**Run with coverage**:
```bash
pytest tests/ --cov=src/storage --cov-report=html --cov-report=term
```

**Run specific test file**:
```bash
pytest tests/test_postgres_adapter.py -v
```

**Run specific test**:
```bash
pytest tests/test_postgres_adapter.py::TestPostgresAdapterUnit::test_add_turn_success -v
```

---

#### Coverage Requirements

**Minimum Coverage per Adapter**:
- `base.py`: 90%+ (simple interface)
- `postgres_adapter.py`: 80%+
- `redis_adapter.py`: 80%+
- `qdrant_adapter.py`: 80%+
- `neo4j_adapter.py`: 80%+
- `typesense_adapter.py`: 80%+

**How to achieve 80%+ coverage**:
1. Test all public methods
2. Test both success and failure paths
3. Test edge cases (empty results, null values, etc.)
4. Test error handling (connection failures, invalid inputs)
5. Use integration tests for complex workflows

---

#### pytest Configuration

Update `pyproject.toml` (or create `pytest.ini`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "integration: marks tests as integration tests (require external services)",
    "slow: marks tests as slow running",
]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--disable-warnings",
]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

#### Tasks Checklist

- [ ] Create `tests/fixtures.py` with shared test fixtures
- [ ] Create `tests/config.py` with test configuration
- [ ] Create `tests/test_postgres_adapter.py`
  - [ ] Unit tests for connection/initialization
  - [ ] Unit tests for add_turn, get_recent_turns
  - [ ] Unit tests for add_fact, get_facts, update_fact
  - [ ] Unit tests for cleanup operations
  - [ ] Integration test for full CRUD workflow
  - [ ] Integration test for TTL expiration
- [ ] Create `tests/test_redis_adapter.py`
  - [ ] Unit tests for connection/initialization
  - [ ] Unit tests for cache_turn, get_cached_turns
  - [ ] Unit tests for window size management
  - [ ] Integration test for cache and retrieve
  - [ ] Integration test for TTL expiration
- [ ] Create `tests/test_qdrant_adapter.py`
  - [ ] Unit tests for connection/initialization
  - [ ] Unit tests for store_embedding, search_similar
  - [ ] Integration test for vector similarity search
- [ ] Create `tests/test_neo4j_adapter.py`
  - [ ] Unit tests for connection/initialization
  - [ ] Unit tests for create_entity, create_relationship
  - [ ] Integration test for graph traversal
- [ ] Create `tests/test_typesense_adapter.py`
  - [ ] Unit tests for connection/initialization
  - [ ] Unit tests for index_document, search
  - [ ] Integration test for full-text search
- [ ] Update `pytest.ini` or `pyproject.toml` with test configuration
- [ ] Add coverage configuration
- [ ] Run unit tests: `pytest -m "not integration" --cov`
- [ ] Verify >80% coverage per adapter
- [ ] Run integration tests: `pytest -m integration`
- [ ] Verify all integration tests pass
- [ ] Generate coverage report: `pytest --cov-report=html`
- [ ] Update `tests/README.md` with testing guidelines
- [ ] Commit: `git commit -m "test: Add comprehensive unit tests for storage adapters"`

---

#### Acceptance Criteria

✅ **Test Coverage**:
- Each adapter has >80% code coverage
- All public methods tested
- Both success and failure paths covered
- Edge cases handled

✅ **Test Organization**:
- Unit tests separate from integration tests
- Tests use pytest markers (`@pytest.mark.integration`)
- Fixtures used for setup/teardown
- Tests can run in isolation

✅ **Test Quality**:
- Tests follow AAA pattern (Arrange, Act, Assert)
- Clear test names describing what's tested
- No flaky tests (consistent results)
- Fast unit tests (<1s each), slower integration tests marked

✅ **Integration Tests**:
- Test against real services (PostgreSQL, Redis, etc.)
- Proper cleanup after each test
- Use test-specific prefixes ("test-session-*")
- Can run on CI/CD pipeline

✅ **Coverage Report**:
- HTML coverage report generated
- Coverage visible in terminal
- Missing lines identified
- Coverage badge (optional)

✅ **Documentation**:
- `tests/README.md` explains how to run tests
- Test fixtures documented
- Integration test requirements documented
- Coverage requirements documented

---

#### Deliverables

1. ✅ `tests/fixtures.py` - Shared test fixtures (~150-200 lines)
2. ✅ `tests/config.py` - Test configuration (~20-30 lines)
3. ✅ `tests/test_postgres_adapter.py` - PostgreSQL tests (~300-400 lines)
4. ✅ `tests/test_redis_adapter.py` - Redis tests (~200-300 lines)
5. ✅ `tests/test_qdrant_adapter.py` - Qdrant tests (~200-300 lines)
6. ✅ `tests/test_neo4j_adapter.py` - Neo4j tests (~200-300 lines)
7. ✅ `tests/test_typesense_adapter.py` - Typesense tests (~200-300 lines)
8. ✅ Updated `pytest.ini` or `pyproject.toml` - Test configuration
9. ✅ Coverage report (HTML) - Verify >80% coverage
10. ✅ Updated `tests/README.md` - Testing guidelines
11. ✅ Git commit with all test files

**Total Lines**: ~1,500-2,000 lines of test code  
**Time Estimate**: 4-5 hours  
**Complexity**: Medium-High  
**Dependencies**: Priorities 1-4 (all adapters must be implemented)  
**Blocks**: None (final priority in Phase 1)

---

#### Common Pitfalls to Avoid

⚠️ **Don't skip mocking in unit tests**
- Unit tests should NOT hit real services
- Use mocks for fast, isolated tests
- Save integration tests for end-to-end validation

⚠️ **Don't forget test isolation**
- Each test should be independent
- Use fixtures for setup/teardown
- Clean up test data after each test

⚠️ **Don't ignore edge cases**
- Test empty results, null values, invalid inputs
- Test boundary conditions (window size limits, etc.)
- Test error handling (connection failures, etc.)

⚠️ **Don't hardcode test data**
- Use fixtures for reusable test data
- Use unique session IDs per test
- Use `"test-"` prefix for easy cleanup

⚠️ **Don't skip integration tests**
- Integration tests catch real-world issues
- Test against actual services when possible
- Mark integration tests appropriately

---

## Phase 1 Specification Complete! 🎉

All **6 Priorities** have been fully populated with detailed implementation instructions, code templates, testing strategies, and acceptance criteria. The specification document is now **100% complete** and ready for development teams to begin Phase 1 implementation.

**Total Specification Size**: ~30-35KB of comprehensive documentation
**Ready for**: Phase 1 Storage Layer Implementation

---

```bash
# PostgreSQL
POSTGRES_URL=postgresql://user:pass@192.168.107.172:5432/mas_memory

# Redis
REDIS_URL=redis://192.168.107.172:6379/0

# Qdrant
QDRANT_URL=http://192.168.107.187:6333

# Neo4j
NEO4J_URL=bolt://192.168.107.187:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Typesense
TYPESENSE_URL=http://192.168.107.187:8108
TYPESENSE_API_KEY=your_api_key
```

### Test Execution

```bash
# Activate environment
source .venv/bin/activate

# Run all storage tests
pytest tests/storage/ -v

# Run specific adapter tests
pytest tests/storage/test_postgres_adapter.py -v

# Run with coverage
pytest tests/storage/ --cov=src/storage --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

### Test Data Management

- Use unique session IDs per test (e.g., `test-{uuid4()}`)
- Clean up test data in `teardown` or `finally` blocks
- Document any test data that cannot be cleaned up automatically

---

## Error Handling Specification

### Custom Exceptions

Define in `src/storage/base.py`:

```python
class StorageError(Exception):
    """Base exception for storage operations"""
    pass

class StorageConnectionError(StorageError):
    """Connection to storage backend failed"""
    pass

class StorageQueryError(StorageError):
    """Query execution failed"""
    pass

class StorageDataError(StorageError):
    """Data validation or integrity error"""
    pass

class StorageTimeoutError(StorageError):
    """Operation timed out"""
    pass
```

### Error Handling Pattern

All adapter methods should follow this pattern:

```python
async def store(self, data: Dict[str, Any]) -> str:
    """Store data in backend"""
    try:
        # Validate input
        self._validate_data(data)
        
        # Perform operation
        result = await self._backend_operation(data)
        
        # Return result
        return result
        
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}", exc_info=True)
        raise StorageConnectionError(f"Failed to connect: {e}") from e
        
    except ValidationError as e:
        logger.error(f"Invalid data: {e}", exc_info=True)
        raise StorageDataError(f"Data validation failed: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise StorageError(f"Storage operation failed: {e}") from e
```

---

## Configuration Management

### Config File: `src/utils/config.py`

```python
from typing import Dict, Any
import os
from dotenv import load_dotenv

class Config:
    """Configuration loader for storage adapters"""
    
    def __init__(self):
        load_dotenv()
        
    def get_postgres_config(self) -> Dict[str, Any]:
        return {
            'url': os.getenv('POSTGRES_URL'),
            'pool_size': int(os.getenv('POSTGRES_POOL_SIZE', '10'))
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        return {
            'url': os.getenv('REDIS_URL'),
            'decode_responses': True
        }
    
    # ... additional config getters
```

---

## Performance Requirements

### Latency Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Redis read | <1ms | 5ms |
| Redis write | <2ms | 10ms |
| PostgreSQL read | <10ms | 50ms |
| PostgreSQL write | <20ms | 100ms |
| Qdrant search | <50ms | 200ms |
| Neo4j query | <100ms | 500ms |
| Typesense search | <50ms | 200ms |

### Throughput Targets

| Adapter | Operations/sec |
|---------|----------------|
| Redis | >10,000 ops/s |
| PostgreSQL | >1,000 ops/s |
| Qdrant | >100 searches/s |
| Neo4j | >50 queries/s |
| Typesense | >100 searches/s |

---

## Documentation Requirements

### Code Documentation

Each adapter must include:

1. **Module Docstring**: Purpose, backend details, usage example
2. **Class Docstring**: Initialization parameters, configuration options
3. **Method Docstrings**: Parameters, return values, exceptions raised
4. **Type Hints**: All parameters and return values must be typed

### README Files

1. `migrations/README.md`: Migration execution instructions
2. `tests/storage/README.md`: Test execution and data cleanup guide

---

## Deliverables Checklist

### Code Deliverables
- [ ] `src/storage/base.py` - Base interface (Priority 1)
- [ ] `src/storage/postgres_adapter.py` - PostgreSQL adapter (Priority 2)
- [ ] `src/storage/redis_adapter.py` - Redis adapter (Priority 3)
- [ ] `src/storage/qdrant_adapter.py` - Qdrant adapter (Priority 4)
- [ ] `src/storage/neo4j_adapter.py` - Neo4j adapter (Priority 4)
- [ ] `src/storage/typesense_adapter.py` - Typesense adapter (Priority 4)
- [ ] `src/utils/config.py` - Configuration loader
- [ ] `src/utils/logging.py` - Logging setup
- [ ] `migrations/001_active_context.sql` - Database schema (Priority 5)

### Test Deliverables
- [ ] `tests/storage/test_postgres_adapter.py` - PostgreSQL tests
- [ ] `tests/storage/test_redis_adapter.py` - Redis tests
- [ ] `tests/storage/test_qdrant_adapter.py` - Qdrant tests
- [ ] `tests/storage/test_neo4j_adapter.py` - Neo4j tests
- [ ] `tests/storage/test_typesense_adapter.py` - Typesense tests
- [ ] `tests/integration/test_storage_integration.py` - Integration tests
- [ ] All tests passing (coverage >80%)

### Documentation Deliverables
- [ ] `migrations/README.md` - Migration instructions
- [ ] `tests/storage/README.md` - Test documentation
- [ ] Updated `DEVLOG.md` - Phase 1 completion entry
- [ ] Code review completed and approved

---

## Success Criteria

Phase 1 is considered complete when:

1. ✅ All Priority 0-6 tasks are completed
2. ✅ All adapters implement the `StorageAdapter` interface
3. ✅ Database migrations successfully applied to `mas_memory`
4. ✅ All unit tests pass with >80% code coverage
5. ✅ Integration tests verify cross-adapter workflows
6. ✅ Code review completed with no blocking issues
7. ✅ Documentation is complete and accurate
8. ✅ Performance targets met for all adapters

---

## Known Considerations

### Python 3.13 Compatibility
⚠️ **Important**: The implementation plan references `asyncpg` for PostgreSQL, but we must use `psycopg[binary]` due to Python 3.13 compatibility issues. See `docs/python-3.13-compatibility.md` for details.

### Connection Management
All adapters must support both:
- Explicit connection management (`connect()`/`disconnect()`)
- Context manager protocol (`async with adapter:`)

### Backward Compatibility
Phase 1 must not break existing smoke tests in `tests/test_connectivity.py`.

---

## Next Steps After Phase 1

Upon completion of Phase 1, proceed to:

**Phase 2: Memory Tiers (Week 3-4)**
- Implement `ActiveContextTier` (L1)
- Implement `WorkingMemoryTier` (L2)
- Implement `EpisodicMemoryTier` (L3)
- Implement `SemanticMemoryTier` (L4)
- Implement `MemoryOrchestrator` for tier coordination

See `docs/plan/implementation-plan-20102025.md` for full roadmap.

---

## Appendix

### References
- Implementation Plan: `docs/plan/implementation-plan-20102025.md`
- ADR-001: Benchmarking Strategy: `docs/ADR/001-benchmarking-strategy.md`
- Database Setup: `docs/IAC/database-setup.md`
- Python Environment: `docs/python-environment-setup.md`
- Smoke Test Report: `docs/reports/smoke-tests-2025-10-20.md`

### Contact
- Project Lead: TBD
- Technical Lead: TBD
- Infrastructure: Home Lab (skz-dev-lv, skz-stg-lv)

---

**Document Status**: Draft - Ready for Priority Detail Population  
**Last Updated**: October 20, 2025  
**Next Review**: After Priority 1 completion
