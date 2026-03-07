"""
tests/test_search.py — FTS5 keyword search tests for mcp-memory.
"""

import pytest
from mcp_memory.db import (
    create_project, create_task, create_decision, create_note,
    create_document, add_chunks,
    search_tasks, search_decisions, search_notes, search_chunks,
)

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_search.db"
    monkeypatch.setattr("mcp_memory.db.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def proj():
    return create_project("search-proj")


class TestSearchTasks:
    def test_basic_keyword(self, proj):
        create_task(proj.id, "Fix authentication bug", description="Login fails on timeout")
        create_task(proj.id, "Improve caching layer", description="Cache miss rate too high")
        results = search_tasks("authentication", proj.id)
        assert len(results) == 1
        assert "authentication" in results[0].title.lower()

    def test_search_in_description(self, proj):
        create_task(proj.id, "Investigate issue", description="The websocket connection drops")
        results = search_tasks("websocket", proj.id)
        assert len(results) == 1

    def test_no_match_returns_empty(self, proj):
        create_task(proj.id, "Unrelated task", description="Nothing here")
        results = search_tasks("kubernetes", proj.id)
        assert len(results) == 0

    def test_project_filter(self, proj):
        proj2 = create_project("other-search-proj")
        create_task(proj.id, "SQLite task", description="Use SQLite")
        create_task(proj2.id, "SQLite task 2", description="Also SQLite")
        results = search_tasks("SQLite", proj.id)
        assert len(results) == 1

    def test_prefix_search(self, proj):
        create_task(proj.id, "Refactoring auth module")
        results = search_tasks("refactor*", proj.id)
        assert len(results) == 1

    def test_cross_project_search(self, proj):
        proj2 = create_project("proj-two")
        create_task(proj.id, "Common keyword task")
        create_task(proj2.id, "Common keyword task 2")
        results = search_tasks("keyword")  # no project filter
        assert len(results) == 2


class TestSearchDecisions:
    def test_search_in_decision_text(self, proj):
        create_decision(proj.id, "Architecture choice",
                        "We will use a microservice architecture.",
                        rationale="Better scalability")
        create_decision(proj.id, "DB choice",
                        "We will use PostgreSQL for the main store.",
                        rationale="ACID compliance")
        results = search_decisions("microservice", proj.id)
        assert len(results) == 1
        assert results[0].title == "Architecture choice"

    def test_search_in_rationale(self, proj):
        create_decision(proj.id, "Use FTS5",
                        "Use SQLite FTS5 for text search.",
                        rationale="Fast ranked keyword indexing built into SQLite")
        results = search_decisions("ranked keyword", proj.id)
        assert len(results) == 1

    def test_no_match(self, proj):
        create_decision(proj.id, "Go with Python", "Python is the language.")
        results = search_decisions("rust blazing fast", proj.id)
        assert len(results) == 0


class TestSearchNotes:
    def test_basic_search(self, proj):
        create_note(proj.id, "Investigation finding",
                    "The memory leak is in the connection pool.", note_type="investigation")
        create_note(proj.id, "Deployment note",
                    "Deploy to staging first always.", note_type="implementation")
        results = search_notes("memory leak", proj.id)
        assert len(results) == 1
        assert "memory leak" in results[0].note_text

    def test_search_by_title(self, proj):
        create_note(proj.id, "Redis caching strategy", "Use Redis for session cache.")
        results = search_notes("Redis caching", proj.id)
        assert len(results) == 1


class TestSearchChunks:
    def test_search_chunks(self, proj):
        doc = create_document(proj.id, "Architecture Guide")
        add_chunks(doc.id, proj.id, [
            "The system uses event-driven architecture with async queues.",
            "All API endpoints follow REST conventions.",
            "Authentication is handled by JWT tokens.",
        ])
        results = search_chunks("JWT tokens", proj.id)
        assert len(results) == 1
        assert "JWT" in results[0].chunk_text

    def test_search_chunks_no_match(self, proj):
        doc = create_document(proj.id, "Simple doc")
        add_chunks(doc.id, proj.id, ["This is a test document."])
        results = search_chunks("kubernetes", proj.id)
        assert len(results) == 0
