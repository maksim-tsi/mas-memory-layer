# Quick Implementation Guide for Remaining Adapters

## Neo4j Adapter - Complete Implementation

### Step 1: Wrap all methods with OperationTimer

Replace each method with the wrapped version:

```python
# connect
async def connect(self) -> None:
    """Connect to Neo4j database"""
    async with OperationTimer(self.metrics, 'connect'):
        if not self.uri or not self.password:
            raise StorageDataError("Neo4j URI and password required")
            
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # Verify connection
            if self.driver is not None:
                async with self.driver.session(database=self.database) as session:
                    result = await session.run("RETURN 1 AS test")
                    await result.single()
            
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.uri}")
            
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}", exc_info=True)
            raise StorageConnectionError(f"Failed to connect: {e}") from e

# disconnect  
async def disconnect(self) -> None:
    """Close Neo4j connection"""
    async with OperationTimer(self.metrics, 'disconnect'):
        if self.driver:
            await self.driver.close()
            self.driver = None
            self._connected = False

# store
async def store(self, data: Dict[str, Any]) -> str:
    """Store entity or relationship in graph"""
    async with OperationTimer(self.metrics, 'store'):
        # ... keep all existing code ...

# retrieve
async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
    """Retrieve entity by ID"""
    async with OperationTimer(self.metrics, 'retrieve'):
        # ... keep all existing code ...

# search
async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search entities by criteria"""
    async with OperationTimer(self.metrics, 'search'):
        # ... keep all existing code ...

# delete
async def delete(self, id: str) -> bool:
    """Delete entity by ID"""
    async with OperationTimer(self.metrics, 'delete'):
        # ... keep all existing code ...
```

### Step 2: Add backend metrics method

Add at the end of the class (before the last line):

```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    """Get Neo4j-specific metrics."""
    if not self._connected or not self.driver:
        return None
    
    try:
        async with self.driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (n)
                RETURN count(n) AS node_count
            """)
            record = await result.single()
            
            return {
                'node_count': record['node_count'] if record else 0,
                'database_name': self.database
            }
    except Exception as e:
        logger.error(f"Failed to get backend metrics: {e}")
        return {'error': str(e)}
```

### Step 3: Create test file

File: `tests/storage/test_neo4j_metrics.py`

```python
"""
Integration tests for Neo4j adapter metrics.
"""
import pytest
from src.storage.neo4j_adapter import Neo4jAdapter


@pytest.mark.asyncio
async def test_neo4j_metrics_integration():
    """Test that Neo4j adapter collects metrics correctly."""
    config = {
        'uri': 'bolt://localhost:7687',
        'user': 'neo4j',
        'password': 'password',
        'database': 'neo4j',
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = Neo4jAdapter(config)
    
    try:
        await adapter.connect()
        
        # Store, retrieve, search, delete
        entity_id = await adapter.store({
            'type': 'entity',
            'label': 'Person',
            'properties': {'name': 'Test', 'age': 30}
        })
        
        await adapter.retrieve(entity_id)
        await adapter.search({'label': 'Person', 'limit': 5})
        await adapter.delete(entity_id)
        
        # Verify metrics
        metrics = await adapter.get_metrics()
        
        assert 'operations' in metrics
        assert metrics['operations']['store']['total_count'] >= 1
        assert metrics['operations']['retrieve']['total_count'] >= 1
        assert metrics['operations']['search']['total_count'] >= 1
        assert metrics['operations']['delete']['total_count'] >= 1
        
        # Verify success rates
        assert metrics['operations']['store']['success_rate'] == 1.0
        
        # Test export
        json_metrics = await adapter.export_metrics('json')
        assert isinstance(json_metrics, str)
        
        # Test backend metrics
        if 'backend_specific' in metrics:
            assert 'node_count' in metrics['backend_specific']
            assert 'database_name' in metrics['backend_specific']
        
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except:
            pass
```

---

## Typesense Adapter - Complete Implementation

### Step 1: Add import

At the top, change:

```python
from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageQueryError,
    StorageDataError,
    validate_required_fields,
)
from .metrics import OperationTimer
```

### Step 2: Wrap all methods with OperationTimer

```python
async def connect(self) -> None:
    """Connect to Typesense"""
    async with OperationTimer(self.metrics, 'connect'):
        # ... keep all existing code ...

async def disconnect(self) -> None:
    """Close Typesense connection"""
    async with OperationTimer(self.metrics, 'disconnect'):
        # ... keep all existing code ...

async def store(self, data: Dict[str, Any]) -> str:
    """Store document in Typesense"""
    async with OperationTimer(self.metrics, 'store'):
        # ... keep all existing code ...

async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
    """Retrieve document by ID"""
    async with OperationTimer(self.metrics, 'retrieve'):
        # ... keep all existing code ...

async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search documents"""
    async with OperationTimer(self.metrics, 'search'):
        # ... keep all existing code ...

async def delete(self, id: str) -> bool:
    """Delete document by ID"""
    async with OperationTimer(self.metrics, 'delete'):
        # ... keep all existing code ...
```

### Step 3: Add backend metrics method

Add at the end of the class:

```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    """Get Typesense-specific metrics."""
    if not self._connected or not self.client:
        return None
    
    try:
        collection = await self.client.collections[self.collection_name].retrieve()
        return {
            'document_count': collection.get('num_documents', 0),
            'collection_name': self.collection_name,
            'schema_fields': len(collection.get('fields', []))
        }
    except Exception as e:
        logger.error(f"Failed to get backend metrics: {e}")
        return {'error': str(e)}
```

### Step 4: Create test file

File: `tests/storage/test_typesense_metrics.py`

```python
"""
Integration tests for Typesense adapter metrics.
"""
import pytest
from src.storage.typesense_adapter import TypesenseAdapter


@pytest.mark.asyncio
async def test_typesense_metrics_integration():
    """Test that Typesense adapter collects metrics correctly."""
    config = {
        'host': 'localhost',
        'port': 8108,
        'protocol': 'http',
        'api_key': 'xyz',
        'collection_name': 'test_metrics',
        'collection_schema': {
            'name': 'test_metrics',
            'fields': [
                {'name': 'content', 'type': 'string'},
                {'name': 'session_id', 'type': 'string', 'facet': True}
            ]
        },
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = TypesenseAdapter(config)
    
    try:
        await adapter.connect()
        
        # Store, retrieve, search, delete
        doc_id = await adapter.store({
            'content': 'Test document',
            'session_id': 'test-session'
        })
        
        await adapter.retrieve(doc_id)
        await adapter.search({
            'q': 'test',
            'query_by': 'content',
            'limit': 5
        })
        await adapter.delete(doc_id)
        
        # Verify metrics
        metrics = await adapter.get_metrics()
        
        assert 'operations' in metrics
        assert metrics['operations']['store']['total_count'] >= 1
        assert metrics['operations']['retrieve']['total_count'] >= 1
        assert metrics['operations']['search']['total_count'] >= 1
        assert metrics['operations']['delete']['total_count'] >= 1
        
        # Verify success rates
        assert metrics['operations']['store']['success_rate'] == 1.0
        
        # Test export
        json_metrics = await adapter.export_metrics('json')
        assert isinstance(json_metrics, str)
        
        # Test backend metrics
        if 'backend_specific' in metrics:
            assert 'document_count' in metrics['backend_specific']
            assert 'collection_name' in metrics['backend_specific']
        
    except Exception as e:
        pytest.skip(f"Typesense not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except:
            pass
```

---

## Quick Checklist

For each adapter (Neo4j, Typesense):

- [ ] Add `from .metrics import OperationTimer` import
- [ ] Wrap `connect()` with `async with OperationTimer(self.metrics, 'connect'):`
- [ ] Wrap `disconnect()` with `async with OperationTimer(self.metrics, 'disconnect'):`
- [ ] Wrap `store()` with `async with OperationTimer(self.metrics, 'store'):`
- [ ] Wrap `retrieve()` with `async with OperationTimer(self.metrics, 'retrieve'):`
- [ ] Wrap `search()` with `async with OperationTimer(self.metrics, 'search'):`
- [ ] Wrap `delete()` with `async with OperationTimer(self.metrics, 'delete'):`
- [ ] Add `_get_backend_metrics()` method at end of class
- [ ] Create `tests/storage/test_<adapter>_metrics.py` integration test
- [ ] Run tests to verify

---

## Testing Commands

```bash
# Test individual adapters
.venv/bin/python -m pytest tests/storage/test_neo4j_metrics.py -v
.venv/bin/python -m pytest tests/storage/test_typesense_metrics.py -v

# Test all metrics
.venv/bin/python -m pytest tests/storage/test_*_metrics.py -v

# Test everything
.venv/bin/python -m pytest tests/storage/ -v
```

---

**Time estimate**: 30 minutes per adapter = 1 hour total
