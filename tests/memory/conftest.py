"""
Test fixtures for memory tier tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def redis_adapter():
    """Mock Redis adapter for testing."""
    adapter = MagicMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.lpush = AsyncMock(return_value=1)
    adapter.ltrim = AsyncMock()
    adapter.expire = AsyncMock(return_value=True)
    adapter.lrange = AsyncMock(return_value=[])
    adapter.llen = AsyncMock(return_value=0)
    adapter.delete = AsyncMock(return_value=False)
    adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
    return adapter


@pytest.fixture
def postgres_adapter():
    """Mock PostgreSQL adapter for testing."""
    adapter = MagicMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.insert = AsyncMock(return_value='inserted_id')
    adapter.query = AsyncMock(return_value=[])
    adapter.delete = AsyncMock(return_value=False)
    adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
    return adapter
