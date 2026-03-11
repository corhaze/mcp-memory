"""
tests/test_reembed.py — tests for the reembed_all repository function,
the reembed MCP tool, and the POST /api/reembed REST endpoint.

Pattern: create entities with embeddings disabled, then call reembed_all
with embeddings enabled to verify embeddings are generated.
"""

import pickle
import pytest

import mcp_memory.embeddings as _emb
from mcp_memory.db import (
    create_project,
    create_task,
    create_decision,
    create_note,
    create_task_note,
    create_global_note,
)
from mcp_memory.repository.connection import get_conn


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_reembed.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def emb_off(monkeypatch):
    monkeypatch.setattr(_emb, "_model_available", False)
    yield


@pytest.fixture
def emb_on(monkeypatch):
    call_count = {"n": 0}

    def fake_generate(text):
        call_count["n"] += 1
        return [float(call_count["n"]), 0.0, 0.0]

    monkeypatch.setattr(_emb, "_model_available", True)
    monkeypatch.setattr(_emb, "generate_embedding", fake_generate)
    yield call_count


def _embedding_count(entity_type: str, entity_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM embeddings WHERE entity_type=? AND entity_id=?",
            (entity_type, entity_id),
        ).fetchone()
    return row["cnt"]


def _get_embedding_vector(entity_type: str, entity_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT embedding_vector FROM embeddings WHERE entity_type=? AND entity_id=?",
            (entity_type, entity_id),
        ).fetchone()
    return pickle.loads(row["embedding_vector"]) if row else None


# ── Repository layer ───────────────────────────────────────────────────────────

class TestReembedAll:
    def test_fills_missing_embeddings_for_all_entity_types(self, emb_on):
        """reembed_all generates embeddings for entities that have none."""
        from mcp_memory.repository.search import reembed_all

        proj = create_project("proj-reembed")
        task = create_task(proj.id, "A task", description="do something")
        decision = create_decision(proj.id, "A decision", "the text")
        note = create_note(proj.id, "A note", "note body")
        task_note = create_task_note(proj.id, task.id, "A task note", "tn body")
        global_note = create_global_note("A global note", "gn body")

        # Wipe all embeddings to simulate entities created without embeddings enabled
        with get_conn() as conn:
            conn.execute("DELETE FROM embeddings")

        assert _embedding_count("task", task.id) == 0
        assert _embedding_count("decision", decision.id) == 0

        with get_conn() as conn:
            counts = reembed_all(conn)

        assert _embedding_count("task", task.id) == 1
        assert _embedding_count("decision", decision.id) == 1
        assert _embedding_count("note", note.id) == 1
        assert _embedding_count("task_note", task_note.id) == 1
        assert _embedding_count("global_note", global_note.id) == 1

    def test_returns_count_per_entity_type(self, emb_on):
        """reembed_all returns a dict with a count per entity type."""
        from mcp_memory.repository.search import reembed_all

        proj = create_project("proj-counts")
        create_task(proj.id, "Task one")
        create_task(proj.id, "Task two")
        create_note(proj.id, "Note one", "body")
        create_global_note("Global one", "body")

        # Wipe to simulate missing embeddings
        with get_conn() as conn:
            conn.execute("DELETE FROM embeddings")

        with get_conn() as conn:
            counts = reembed_all(conn)

        assert counts["task"] == 2
        assert counts["note"] == 1
        assert counts["global_note"] == 1
        assert counts.get("decision", 0) == 0

    def test_skips_existing_embeddings_when_force_false(self, emb_on):
        """reembed_all(force=False) does not overwrite existing embeddings."""
        from mcp_memory.repository.search import reembed_all

        proj = create_project("proj-skip")
        task = create_task(proj.id, "Task with embedding")

        # task was created with emb_on, so it already has an embedding
        original_vec = _get_embedding_vector("task", task.id)
        assert original_vec is not None

        calls_before = emb_on["n"]
        with get_conn() as conn:
            counts = reembed_all(conn, force=False)

        # generate_embedding should not have been called again for this task
        assert emb_on["n"] == calls_before
        assert counts["task"] == 0
        assert _get_embedding_vector("task", task.id) == original_vec

    def test_force_true_regenerates_existing_embeddings(self, emb_on):
        """reembed_all(force=True) regenerates even entities that already have embeddings."""
        from mcp_memory.repository.search import reembed_all

        proj = create_project("proj-force")
        task = create_task(proj.id, "Task to regenerate")

        original_vec = _get_embedding_vector("task", task.id)
        assert original_vec is not None

        with get_conn() as conn:
            counts = reembed_all(conn, force=True)

        new_vec = _get_embedding_vector("task", task.id)
        assert counts["task"] == 1
        assert new_vec != original_vec  # new vector assigned by fake_generate

    def test_returns_zero_counts_when_no_entities(self, emb_on):
        """reembed_all returns zero counts when there is nothing to embed."""
        from mcp_memory.repository.search import reembed_all

        with get_conn() as conn:
            counts = reembed_all(conn)

        assert all(v == 0 for v in counts.values())

    def test_no_op_when_embeddings_unavailable(self, emb_off):
        """reembed_all returns zero counts and generates nothing when embeddings are off."""
        from mcp_memory.repository.search import reembed_all

        proj = create_project("proj-no-emb")
        create_task(proj.id, "A task")

        with get_conn() as conn:
            counts = reembed_all(conn)

        assert all(v == 0 for v in counts.values())


# ── MCP tool ──────────────────────────────────────────────────────────────────

class TestReembedMcpTool:
    def test_returns_unavailable_message_when_embeddings_off(self, emb_off):
        """reembed MCP tool returns a message when embeddings are disabled."""
        import mcp_memory.server.search as srv
        result = srv.reembed()
        assert "unavailable" in result.lower()

    def test_returns_summary_of_counts(self, emb_on):
        """reembed MCP tool returns a human-readable summary of counts."""
        import mcp_memory.server.search as srv

        proj = create_project("proj-tool")
        create_task(proj.id, "T1")
        create_note(proj.id, "N1", "body")

        with get_conn() as conn:
            conn.execute("DELETE FROM embeddings")

        result = srv.reembed()
        assert "task" in result
        assert "note" in result

    def test_force_param_passed_through(self, emb_on):
        """reembed MCP tool with force=True regenerates existing embeddings."""
        import mcp_memory.server.search as srv

        proj = create_project("proj-force-tool")
        create_task(proj.id, "Task already embedded")

        original_vec = _get_embedding_vector("task",
            create_task(proj.id, "Task two").id)

        result = srv.reembed(force=True)
        assert "task" in result


# ── REST endpoint ─────────────────────────────────────────────────────────────

class TestReembedEndpoint:
    def test_returns_400_when_embeddings_disabled(self, emb_off):
        """POST /api/reembed returns 400 when embeddings are not enabled."""
        from fastapi.testclient import TestClient
        from mcp_memory.ui_server import app
        client = TestClient(app, raise_server_exceptions=True)

        r = client.post("/api/reembed", json={})
        assert r.status_code == 400

    def test_returns_counts_on_success(self, emb_on):
        """POST /api/reembed returns counts per entity type."""
        from fastapi.testclient import TestClient
        from mcp_memory.ui_server import app
        client = TestClient(app, raise_server_exceptions=True)

        proj = create_project("proj-api")
        create_task(proj.id, "Task api")

        with get_conn() as conn:
            conn.execute("DELETE FROM embeddings")

        r = client.post("/api/reembed", json={})
        assert r.status_code == 200
        data = r.json()
        assert "task" in data
        assert data["task"] == 1

    def test_force_false_skips_existing(self, emb_on):
        """POST /api/reembed with force=false skips already-embedded entities."""
        from fastapi.testclient import TestClient
        from mcp_memory.ui_server import app
        client = TestClient(app, raise_server_exceptions=True)

        proj = create_project("proj-api-skip")
        create_task(proj.id, "Already embedded")

        r = client.post("/api/reembed", json={"force": False})
        assert r.status_code == 200
        assert r.json()["task"] == 0
