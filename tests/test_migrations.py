"""
tests/test_migrations.py — tests for the versioned migration system.
"""

import sqlite3
import pytest
from mcp_memory.repository.migrations import run_migrations, _get_version, _MIGRATIONS
from mcp_memory.repository.connection import _init_schema


@pytest.fixture
def fresh_conn(tmp_path):
    """Open a fresh in-memory-equivalent DB with schema but no migrations applied."""
    db_file = tmp_path / "migrations_test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def legacy_v0_conn(tmp_path):
    """
    Simulate a legacy DB at version 0:
    - tasks table without 'urgent' column
    - embeddings table with project_id NOT NULL
    """
    db_file = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            description TEXT, status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
            title TEXT NOT NULL, description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            parent_task_id TEXT, assigned_agent TEXT,
            blocked_by_task_id TEXT, next_action TEXT, due_at TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
            embedding_model TEXT NOT NULL, embedding_vector BLOB NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(entity_type, entity_id)
        );
    """)
    yield conn
    conn.close()


# ── Version tracking ───────────────────────────────────────────────────────────

class TestVersionTracking:
    def test_fresh_db_is_version_zero(self, fresh_conn):
        assert _get_version(fresh_conn) == 0

    def test_run_migrations_advances_version(self, fresh_conn):
        run_migrations(fresh_conn)
        assert _get_version(fresh_conn) == len(_MIGRATIONS)

    def test_run_migrations_is_idempotent(self, fresh_conn):
        run_migrations(fresh_conn)
        run_migrations(fresh_conn)
        assert _get_version(fresh_conn) == len(_MIGRATIONS)


# ── Migration 1: urgent column ────────────────────────────────────────────────

class TestMigration1Urgent:
    def test_adds_urgent_column_when_missing(self, legacy_v0_conn):
        cols_before = [r["name"] for r in legacy_v0_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "urgent" not in cols_before

        run_migrations(legacy_v0_conn)

        cols_after = [r["name"] for r in legacy_v0_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "urgent" in cols_after

    def test_urgent_column_skipped_when_present(self, fresh_conn):
        # fresh_conn already has urgent in schema; migration should not raise
        run_migrations(fresh_conn)
        cols = [r["name"] for r in fresh_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "urgent" in cols


# ── Migration 2: embeddings.project_id nullable ───────────────────────────────

class TestMigration2EmbeddingsNullable:
    def test_makes_project_id_nullable(self, legacy_v0_conn):
        col_info = {r["name"]: r for r in legacy_v0_conn.execute("PRAGMA table_info(embeddings)").fetchall()}
        assert col_info["project_id"]["notnull"] == 1

        run_migrations(legacy_v0_conn)

        col_info_after = {r["name"]: r for r in legacy_v0_conn.execute("PRAGMA table_info(embeddings)").fetchall()}
        assert col_info_after["project_id"]["notnull"] == 0

    def test_nullable_skipped_when_already_nullable(self, fresh_conn):
        # fresh schema already has nullable project_id; migration should be a no-op
        run_migrations(fresh_conn)
        col_info = {r["name"]: r for r in fresh_conn.execute("PRAGMA table_info(embeddings)").fetchall()}
        assert col_info["project_id"]["notnull"] == 0

    def test_existing_embeddings_preserved_after_migration(self, legacy_v0_conn):
        legacy_v0_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        legacy_v0_conn.execute(
            "INSERT INTO embeddings(id,project_id,entity_type,entity_id,embedding_model,embedding_vector,created_at) "
            "VALUES ('e1','p1','task','t1','model',X'00','now')"
        )
        legacy_v0_conn.commit()

        run_migrations(legacy_v0_conn)

        rows = legacy_v0_conn.execute("SELECT * FROM embeddings").fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == "e1"
