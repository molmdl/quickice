"""Project-level pytest configuration.

Registers custom markers used across test modules.
"""

import pytest


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
