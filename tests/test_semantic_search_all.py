"""
tests/test_semantic_search_all.py — unit tests for semantic_search_all.

All tests stub out the embedding model so the real fastembed model is never
needed.  Mocking is applied at the module level where `_emb` is imported:
  - mcp_memory.repository.search (repository layer)
  - mcp_memory.server.search     (MCP tool layer)

The approach mirrors the pattern in tests/test_embeddings.py — use monkeypatch
on the module-level attributes of `mcp_memory.embeddings` so that all
consumers of the shared module see the same patched state.
"""

import pickle
import unittest.mock as mock
from typing import List

import pytest

import mcp_memory.embeddings as _emb
from mcp_memory.db import (
    create_project,
    create_task,
    create_decision,
    create_note,
    create_global_note,
    create_task_note,
    semantic_search_all,
)
from mcp_memory.repository.connection import get_conn, _now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_vec(value: float) -> List[float]:
    """Return a trivial 3-d unit vector whose cosine similarity to itself is 1.0."""
    return [value, 0.0, 0.0]


def _insert_embedding(project_id, entity_type: str, entity_id: str, vec: List[float]) -> None:
    """Directly insert a pre-computed embedding into the embeddings table."""
    import uuid
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO embeddings
                (id, project_id, entity_type, entity_id,
                 embedding_model, embedding_vector, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                embedding_vector = excluded.embedding_vector,
                embedding_model  = excluded.embedding_model
            """,
            (
                str(uuid.uuid4()),
                project_id,
                entity_type,
                entity_id,
                "test-model",
                pickle.dumps(vec),
                _now(),
            ),
        )


@pytest.fixture
def emb_on(monkeypatch):
    """Patch the embeddings module so is_available() is True and all calls are stubbed."""
    monkeypatch.setattr(_emb, "_model_available", True)
    # generate_embedding returns a trivial vector; cosine_similarity returns
    # a fixed value — tests that need specific scores insert embeddings directly.
    monkeypatch.setattr(_emb, "generate_embedding", lambda text: _fake_vec(1.0))
    monkeypatch.setattr(_emb, "cosine_similarity", lambda v1, v2: float(v1[0]) * float(v2[0]))
    yield


@pytest.fixture
def emb_off(monkeypatch):
    """Patch the embeddings module so is_available() is False."""
    monkeypatch.setattr(_emb, "_model_available", False)
    yield


# ---------------------------------------------------------------------------
# Case 1: Returns [] when embeddings unavailable
# ---------------------------------------------------------------------------

def test_returns_empty_when_embeddings_unavailable(emb_off):
    """semantic_search_all returns [] immediately when embeddings are off."""
    proj = create_project("proj-off")
    create_task(proj.id, "A task")

    results = semantic_search_all("anything", proj.id, limit=10)

    assert results == []


# ---------------------------------------------------------------------------
# Case 2: Results are merged and sorted by score descending
# ---------------------------------------------------------------------------

def test_results_sorted_by_score_descending(emb_on):
    """Merged results are ordered highest score first across entity types."""
    proj = create_project("proj-sort")
    task = create_task(proj.id, "Task alpha")
    decision = create_decision(proj.id, "Decision beta", "text", rationale=None)
    note = create_note(proj.id, "Note gamma", "body", note_type="general")

    # Insert embeddings with distinct, known scores.
    # cosine_similarity mock: score = v1[0] * v2[0].
    # query vec = [1.0, 0, 0], so score = 1.0 * stored_vec[0].
    _insert_embedding(proj.id, "task",     task.id,     _fake_vec(0.9))
    _insert_embedding(proj.id, "decision", decision.id, _fake_vec(0.5))
    _insert_embedding(proj.id, "note",     note.id,     _fake_vec(0.7))

    results = semantic_search_all("query", proj.id, limit=10)

    assert len(results) == 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by score descending"


# ---------------------------------------------------------------------------
# Case 3: Task, note, and decision all appear in a single result list
# ---------------------------------------------------------------------------

def test_task_note_decision_all_appear(emb_on):
    """A task, note, decision, and task_note with embeddings all show up in results."""
    proj = create_project("proj-all-types")
    task = create_task(proj.id, "My task")
    decision = create_decision(proj.id, "My decision", "text", rationale=None)
    note = create_note(proj.id, "My note", "body", note_type="general")
    task_note = create_task_note(proj.id, task.id, "My task note", "note body", note_type="context")

    _insert_embedding(proj.id, "task",      task.id,      _fake_vec(0.8))
    _insert_embedding(proj.id, "decision",  decision.id,  _fake_vec(0.6))
    _insert_embedding(proj.id, "note",      note.id,      _fake_vec(0.4))
    _insert_embedding(proj.id, "task_note", task_note.id, _fake_vec(0.3))

    results = semantic_search_all("query", proj.id, limit=10)

    entity_types = {r["entity_type"] for r in results}
    assert "task" in entity_types
    assert "note" in entity_types
    assert "decision" in entity_types
    assert "task_note" in entity_types
    entity_ids = {r["entity"].id for r in results}
    assert task.id in entity_ids
    assert decision.id in entity_ids
    assert note.id in entity_ids
    assert task_note.id in entity_ids


# ---------------------------------------------------------------------------
# Case 4: project_id filter excludes other projects, but global_notes always included
# ---------------------------------------------------------------------------

def test_project_filter_excludes_other_project_but_includes_global_notes(emb_on):
    """Entities from a different project are excluded; global_notes always appear."""
    proj_a = create_project("proj-a")
    proj_b = create_project("proj-b")

    task_a = create_task(proj_a.id, "Task in A")
    task_b = create_task(proj_b.id, "Task in B")
    global_note = create_global_note("Global note", "body", note_type="general")

    _insert_embedding(proj_a.id, "task",        task_a.id,      _fake_vec(0.9))
    _insert_embedding(proj_b.id, "task",        task_b.id,      _fake_vec(0.8))
    _insert_embedding(None,      "global_note", global_note.id, _fake_vec(0.7))

    results = semantic_search_all("query", proj_a.id, limit=10)

    result_ids = {r["entity"].id for r in results}

    assert task_a.id in result_ids, "task from searched project must be included"
    assert task_b.id not in result_ids, "task from other project must be excluded"
    assert global_note.id in result_ids, "global_note must always be included"


# ---------------------------------------------------------------------------
# Case 5: limit is respected
# ---------------------------------------------------------------------------

def test_limit_is_respected(emb_on):
    """Never returns more than limit results total."""
    proj = create_project("proj-limit")
    # Create 8 tasks and insert embeddings for all of them.
    tasks = [create_task(proj.id, f"Task {i}") for i in range(8)]
    for i, t in enumerate(tasks):
        _insert_embedding(proj.id, "task", t.id, _fake_vec(0.1 + i * 0.1))

    results = semantic_search_all("query", proj.id, limit=3)

    assert len(results) == 3


# ---------------------------------------------------------------------------
# Case 6: MCP tool returns _EMBEDDINGS_UNAVAILABLE when embeddings are off
# ---------------------------------------------------------------------------

def test_mcp_tool_returns_unavailable_string_when_embeddings_off(emb_off):
    """MCP tool returns the _EMBEDDINGS_UNAVAILABLE sentinel when embeddings are off."""
    from mcp_memory.server.search import semantic_search_all as mcp_tool
    from mcp_memory.server.search import _EMBEDDINGS_UNAVAILABLE

    result = mcp_tool("any query")

    assert result == _EMBEDDINGS_UNAVAILABLE


# ---------------------------------------------------------------------------
# Case 7: MCP tool formats output correctly
# ---------------------------------------------------------------------------

def test_mcp_tool_formats_output_correctly(emb_on):
    """MCP tool output includes count header, entity_type label, title, score, and 8-char id."""
    from mcp_memory.server.search import semantic_search_all as mcp_tool

    proj = create_project("proj-fmt")
    task = create_task(proj.id, "Formatted task title")
    note = create_note(proj.id, "Formatted note title", "body", note_type="general")
    task_note = create_task_note(proj.id, task.id, "Formatted task note title", "body", note_type="context")

    _insert_embedding(proj.id, "task",      task.id,      _fake_vec(0.9))
    _insert_embedding(proj.id, "note",      note.id,      _fake_vec(0.6))
    _insert_embedding(proj.id, "task_note", task_note.id, _fake_vec(0.4))

    output = mcp_tool("some query", project_id=proj.id, limit=10)

    # Count header must be present.
    assert "result(s):" in output

    # Each result line must contain: [entity_type], title, score:, and an 8-char id.
    assert "[task]" in output
    assert "Formatted task title" in output
    assert "score:" in output

    # The id field shows the first 8 characters of the entity UUID.
    assert task.id[:8] in output

    assert "[note]" in output
    assert "Formatted note title" in output
    assert note.id[:8] in output

    assert "[task_note]" in output
    assert "Formatted task note title" in output
    assert task_note.id[:8] in output
