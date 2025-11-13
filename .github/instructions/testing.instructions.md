---
applyTo: "tests/**/*.py"
---

# Testing Patterns and Guidelines

## Pytest and Pytest-Asyncio

All tests use `pytest` with `pytest-asyncio` for async test support:

```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations."""
    result = await some_async_function()
    assert result is not None
```

**Key patterns**:
- Use `@pytest.mark.asyncio` for all async test functions
- Use `pytest_asyncio.fixture` for async fixtures (not `@pytest.fixture`)
- Tests in `tests/conftest.py` automatically load `.env` via `python-dotenv`

## Test Markers

Use consistent markers to categorize tests:

```python
@pytest.mark.smoke
async def test_database_connectivity():
    """Smoke test: Verify database connection."""
    pass

@pytest.mark.integration
async def test_tier_storage_integration():
    """Integration test: Test tier with real storage."""
    pass

@pytest.mark.unit
def test_ciar_calculation():
    """Unit test: Test CIAR scoring logic in isolation."""
    pass
```

**Available markers** (configured in `tests/conftest.py`):
- `@pytest.mark.smoke` - Connectivity checks, infrastructure smoke tests
- `@pytest.mark.integration` - Multi-component integration tests
- `@pytest.mark.unit` - Isolated unit tests

**Note**: Tests in `test_connectivity.py` are automatically marked as smoke tests.

## Test Fixtures

Fixtures are provided in `tests/fixtures.py` and `tests/conftest.py`:

```python
import pytest
import pytest_asyncio
from tests.fixtures import get_redis_adapter, get_postgres_adapter

@pytest_asyncio.fixture
async def redis_adapter():
    """Provide Redis adapter for tests."""
    adapter = get_redis_adapter()
    await adapter.initialize()
    yield adapter
    await adapter.close()

@pytest.mark.asyncio
async def test_with_adapter(redis_adapter):
    """Test using the fixture."""
    result = await redis_adapter.store({'key': 'value'})
    assert result is not None
```

**Fixture patterns**:
- Use `@pytest_asyncio.fixture` for async fixtures
- Always clean up resources in fixture teardown (after `yield`)
- Scope fixtures appropriately (`function`, `class`, `module`, `session`)
- Fixtures automatically load environment variables from `.env`

## Test Structure

Follow consistent test structure:

```python
@pytest.mark.asyncio
async def test_operation_name():
    """
    Test description explaining what is being tested.
    
    This test verifies that [specific behavior] works correctly
    when [specific conditions].
    """
    # Arrange: Set up test data and dependencies
    data = {'key': 'value'}
    adapter = get_adapter()
    await adapter.initialize()
    
    # Act: Perform the operation
    result = await adapter.store(data)
    
    # Assert: Verify expected outcomes
    assert result is not None
    assert result['key'] == 'value'
    
    # Cleanup
    await adapter.close()
```

**Structure**:
1. **Docstring**: Clear description of what is tested
2. **Arrange**: Set up test data, mocks, fixtures
3. **Act**: Execute the operation under test
4. **Assert**: Verify expected behavior
5. **Cleanup**: Release resources (or use fixtures)

## Running Tests

Tests must be run with absolute paths following the Terminal Resiliency Protocol:

```bash
# All tests
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v > /tmp/copilot.out && cat /tmp/copilot.out

# Specific marker
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -m smoke > /tmp/copilot.out && cat /tmp/copilot.out

# Specific test file
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/storage/test_redis_adapter.py -v > /tmp/copilot.out && cat /tmp/copilot.out

# With coverage
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ --cov=src --cov-report=html > /tmp/copilot.out && cat /tmp/copilot.out
```

## Test Data and Mocking

**Test data**:
- Use realistic but anonymized data
- Avoid hardcoded credentials (use environment variables)
- Generate test data programmatically when possible

**Mocking**:
- Mock external dependencies (LLM APIs, external services)
- Don't mock storage adapters in integration tests
- Use `unittest.mock` or `pytest-mock` for mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked external dependency."""
    mock_llm = AsyncMock(return_value={'result': 'mocked'})
    
    with patch('src.utils.llm_client.LLMClient.generate', mock_llm):
        result = await some_function_using_llm()
        assert result == 'mocked'
        mock_llm.assert_called_once()
```

## Test Infrastructure Requirements

Tests require running infrastructure services:
- **PostgreSQL**: Running on `DEV_IP` (from `.env`)
- **Redis**: Running on `DEV_IP`
- **Qdrant**: Running on `STG_IP`
- **Neo4j**: Running on `STG_IP`
- **Typesense**: Running on `STG_IP`

**Distributed testing**: Tests can run from any machine with network access to these services.

## Coverage Requirements

- Generate coverage reports: `pytest --cov=src --cov-report=html`
- Coverage reports output to `htmlcov/` directory
- Aim for high coverage but prioritize meaningful tests over coverage metrics
- Focus on testing critical paths, error handling, and edge cases
