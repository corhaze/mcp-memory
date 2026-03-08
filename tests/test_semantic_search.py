"""
tests/test_semantic_search.py — vector/semantic search tests for mcp-memory.

These tests use the real FastEmbed model (BAAI/bge-small-en-v1.5).
On first run, the model will be downloaded (~25MB) and cached.
Subsequent runs are fast. Tests assert semantic relevance, not exact matches.
"""

import pytest
from mcp_memory.db import (
    create_project, create_task, create_decision, create_note,
    create_document, add_chunks,
    semantic_search_tasks, semantic_search_decisions,
    semantic_search_notes, semantic_search_chunks,
)

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_semantic.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def proj():
    return create_project("semantic-proj")


def test_semantic_search_tasks_relevance(proj):
    """Semantic search returns the most conceptually similar task first."""
    create_task(proj.id, "Fix login bug",
                description="Users cannot sign in — authentication fails on timeout")
    create_task(proj.id, "Update documentation",
                description="Write API docs for the endpoints")

    results = semantic_search_tasks("user sign-in is broken", proj.id, limit=5)
    assert len(results) > 0
    # The auth task should rank above the documentation task
    assert "login" in results[0].title.lower() or "auth" in (results[0].description or "").lower()


def test_semantic_search_decisions_relevance(proj):
    """Finds decisions about a topic even without exact keyword match."""
    create_decision(proj.id, "Choose data store",
                    "We will persist all data in SQLite using WAL mode for performance.",
                    rationale="Simple deployment, no extra infrastructure")
    create_decision(proj.id, "Frontend framework",
                    "Use React with TypeScript for the frontend.",
                    rationale="Team familiarity and ecosystem")

    results = semantic_search_decisions("database technology selection", proj.id, limit=5)
    assert len(results) > 0
    assert "data store" in results[0].title.lower() or "sqlite" in results[0].decision_text.lower()


def test_semantic_search_notes_relevance(proj):
    """Finds investigation notes about a topic via semantic similarity."""
    create_note(proj.id, "Memory profiling session",
                "Found that connection pool grows unboundedly under load — likely a leak.",
                note_type="investigation")
    create_note(proj.id, "Deployment procedure",
                "Always run migrations before deploying the new container image.",
                note_type="implementation")

    results = semantic_search_notes("application is using too much RAM", proj.id, limit=5)
    assert len(results) > 0
    # The memory profiling note should rank first
    assert "memory" in results[0].title.lower() or "leak" in results[0].note_text.lower()


def test_semantic_search_chunks_relevance(proj):
    """Finds the relevant document chunk without exact keyword match."""
    doc = create_document(proj.id, "Architecture Notes")
    add_chunks(doc.id, proj.id, [
        "Authentication is handled by issuing signed JWT tokens valid for 24 hours.",
        "The system uses a blue-green deployment strategy for zero-downtime releases.",
        "Database migrations are run automatically as part of the release pipeline.",
    ])

    results = semantic_search_chunks("how does login and session management work", proj.id, limit=3)
    assert len(results) > 0
    # JWT / auth chunk should be most relevant
    assert "JWT" in results[0].chunk_text or "Authentication" in results[0].chunk_text


def test_semantic_search_respects_project_filter(proj):
    """Results are filtered to the specified project."""
    proj2 = create_project("other-semantic-proj")
    create_task(proj.id, "Implement OAuth", description="Add Google OAuth sign-in")
    create_task(proj2.id, "Implement OAuth", description="Add Google OAuth sign-in")

    results = semantic_search_tasks("Google sign-in integration", proj.id, limit=5)
    assert all(t.project_id == proj.id for t in results)


def test_semantic_search_empty_returns_empty(proj):
    """No embeddings stored means empty results."""
    # No tasks created — should return empty list
    results = semantic_search_tasks("any query at all", proj.id, limit=5)
    assert results == []
