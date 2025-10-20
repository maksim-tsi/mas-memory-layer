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