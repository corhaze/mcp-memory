"""
tests/conftest.py — session-wide test isolation.

Sets MCP_MEMORY_DB_PATH to a per-test temporary file before any test runs.
This works regardless of which module imports db_path, because db_path()
reads the env var at call time rather than at import time.

Individual test files do NOT need their own tmp_db fixtures; this fixture
provides the guarantee for the whole test suite.
"""

import pytest


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("MCP_MEMORY_DB_PATH", str(db_file))
    yield db_file
