"""
Tests configuration and fixtures

This module provides shared pytest configuration and fixtures for all tests.
"""

import pytest
import sys
import os
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


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Auto-mark connectivity tests as smoke tests
        if "test_connectivity" in item.nodeid:
            item.add_marker(pytest.mark.smoke)
