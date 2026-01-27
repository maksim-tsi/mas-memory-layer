"""
Tests configuration and fixtures

This module provides shared pytest configuration and fixtures for all tests.
"""

import os
import sys

import pytest
import redis
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables from .env file
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path, override=True)


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test (connectivity check)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow-running (real LLM calls)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Auto-mark connectivity tests as smoke tests
        if "test_connectivity" in item.nodeid:
            item.add_marker(pytest.mark.smoke)
        # Auto-mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def test_session_id():
    """Generate unique session ID for test isolation.
    
    Each test gets a unique session_id to namespace its data in the
    live research cluster, preventing collisions between concurrent tests.
    """
    import uuid
    return f"test-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation."""
    import uuid
    return f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_organization_id():
    """Return test organization ID."""
    return "test-org"


@pytest.fixture
def test_agent_id():
    """Return test agent ID."""
    return "test-agent"


@pytest.fixture
def redis_key_validator():
    """Return helper to assert Redis key counts by pattern."""

    def _validate(pattern: str, expected_count: int) -> list[str]:
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            pytest.skip("REDIS_URL not set; skipping Redis key validation.")
        client = redis.StrictRedis.from_url(redis_url, decode_responses=True)
        keys = client.keys(pattern)
        assert len(keys) == expected_count, (
            f"Expected {expected_count} Redis keys for pattern '{pattern}', "
            f"found {len(keys)}. Keys: {keys}"
        )
        return keys

    return _validate


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_redis_keys():
    """Clean up Redis test keys after the test session."""
    yield

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return
    try:
        client = redis.StrictRedis.from_url(redis_url, decode_responses=True)
        patterns = [
            "l1:session:test-*",
            "l1:session:full:test-*",
            "l1:session:rag:test-*",
            "l1:session:full_context:test-*",
        ]
        for pattern in patterns:
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
    except Exception:
        return

