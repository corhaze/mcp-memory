"""
tests/test_db.py — pytest unit tests for the storage layer.
Uses a temporary in-memory SQLite database (no disk side-effects).
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile

# Point db at a temp file for all tests
@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("mcp_memory.db.db_path", lambda: db_file)
    yield db_file


from mcp_memory.db import (
    upsert_context,
    get_context,
    list_contexts,
    delete_context,
    log_event,
    get_timeline,
)


class TestContextCRUD:
    def test_upsert_and_get(self):
        upsert_context("proj", "lang", "Python")
        entry = get_context("proj", "lang")
        assert entry is not None
        assert entry.value == "Python"
        assert entry.project == "proj"
        assert entry.category == "general"

    def test_upsert_overwrites(self):
        upsert_context("proj", "lang", "Go")
        upsert_context("proj", "lang", "Python")
        entry = get_context("proj", "lang")
        assert entry.value == "Python"

    def test_upsert_preserves_created_timestamp(self):
        e1 = upsert_context("proj", "lang", "Go")
        e2 = upsert_context("proj", "lang", "Python")
        assert e1.created == e2.created
        assert e1.updated != e2.updated

    def test_get_missing_returns_none(self):
        assert get_context("proj", "nonexistent") is None

    def test_category_isolation(self):
        upsert_context("proj", "db", "SQLite", category="stack")
        upsert_context("proj", "db", "Postgres", category="alternatives")
        assert get_context("proj", "db", "stack").value == "SQLite"
        assert get_context("proj", "db", "alternatives").value == "Postgres"

    def test_delete(self):
        upsert_context("proj", "lang", "Python")
        assert delete_context("proj", "lang") is True
        assert get_context("proj", "lang") is None

    def test_delete_missing_returns_false(self):
        assert delete_context("proj", "nope") is False


class TestListContexts:
    def test_list_all(self):
        upsert_context("proj", "lang", "Python", "stack")
        upsert_context("proj", "db", "SQLite", "stack")
        upsert_context("proj", "auth", "JWT", "decisions")
        entries = list_contexts("proj")
        assert len(entries) == 3

    def test_list_by_category(self):
        upsert_context("proj", "lang", "Python", "stack")
        upsert_context("proj", "db", "SQLite", "stack")
        upsert_context("proj", "auth", "JWT", "decisions")
        stack = list_contexts("proj", category="stack")
        assert len(stack) == 2
        assert all(e.category == "stack" for e in stack)

    def test_list_by_tag(self):
        upsert_context("proj", "lang", "Python", tags=["core"])
        upsert_context("proj", "db", "SQLite", tags=["core", "storage"])
        upsert_context("proj", "cdn", "Cloudflare", tags=["infra"])
        core = list_contexts("proj", tag="core")
        assert len(core) == 2

    def test_project_isolation(self):
        upsert_context("proj-a", "lang", "Python")
        upsert_context("proj-b", "lang", "Go")
        assert len(list_contexts("proj-a")) == 1
        assert list_contexts("proj-a")[0].value == "Python"


class TestEvents:
    def test_log_and_retrieve(self):
        log_event("proj", "decision", "Use FastMCP")
        log_event("proj", "milestone", "v0.1 shipped", "all tests pass")
        events = get_timeline("proj")
        assert len(events) == 2

    def test_timeline_ordered_newest_first(self):
        log_event("proj", "decision", "first")
        log_event("proj", "decision", "second")
        events = get_timeline("proj")
        assert events[0].summary == "second"

    def test_timeline_limit(self):
        for i in range(10):
            log_event("proj", "note", f"event {i}")
        events = get_timeline("proj", limit=3)
        assert len(events) == 3

    def test_detail_stored(self):
        log_event("proj", "issue", "bug found", "stack overflow in export")
        events = get_timeline("proj")
        assert events[0].detail == "stack overflow in export"
