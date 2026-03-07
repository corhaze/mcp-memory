"""
tests/test_search.py — verification tests for FTS5 search capabilities.
"""

import pytest
from mcp_memory.db import (
    add_insight,
    search_insights,
    upsert_context,
    search_contexts,
)

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_search.db"
    monkeypatch.setattr("mcp_memory.db.db_path", lambda: db_file)
    yield db_file


class TestSearchInsights:
    def test_fts5_basic_search(self):
        add_insight("Python Tips", "Use list comprehensions for speed.", tags=["python"])
        add_insight("Go Tips", "Use goroutines for concurrency.", tags=["go"])
        
        results = search_insights("python")
        assert len(results) == 1
        assert results[0].title == "Python Tips"

    def test_fts5_bm25_ranking(self):
        # Result A has 'sqlite' twice
        add_insight("SQLite A", "sqlite is great. I love sqlite.", tags=["db"])
        # Result B has 'sqlite' once
        add_insight("SQLite B", "sqlite is okay.", tags=["db"])
        
        results = search_insights("sqlite")
        assert len(results) == 2
        assert results[0].title == "SQLite A"  # Should be ranked higher

    def test_fts5_snippets(self):
        add_insight("Complex Insight", "The quick brown fox jumps over the lazy dog.")
        results = search_insights("brown fox")
        assert len(results) == 1
        assert "<b>brown</b> <b>fox</b>" in results[0].snippet

    def test_fts5_prefix_search(self):
        add_insight("Prefix Test", "Interstellar travel is hard.")
        results = search_insights("inter*")
        assert len(results) == 1
        assert results[0].title == "Prefix Test"


class TestSearchContexts:
    def test_search_contexts(self):
        upsert_context("proj-x", "backend", "Python/FastAPI")
        upsert_context("proj-x", "frontend", "React/Typescript")
        
        results = search_contexts("react")
        assert len(results) == 1
        assert results[0].key == "frontend"
        assert results[0].value == "React/Typescript"

    def test_search_contexts_no_match(self):
        upsert_context("proj-x", "backend", "Python")
        results = search_contexts("rust")
        assert len(results) == 0
