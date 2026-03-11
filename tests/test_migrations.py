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


# ── Migration 3: complex column ────────────────────────────────────────────────

class TestMigration3Complex:
    def test_complex_column_present_on_fresh_schema(self, fresh_conn):
        run_migrations(fresh_conn)
        cols = [r["name"] for r in fresh_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "complex" in cols

    def test_complex_column_added_to_legacy_schema(self, legacy_v0_conn):
        cols_before = [r["name"] for r in legacy_v0_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "complex" not in cols_before

        run_migrations(legacy_v0_conn)

        cols_after = [r["name"] for r in legacy_v0_conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "complex" in cols_after


# ── Migration 4: completed → done status ───────────────────────────────────────

class TestMigration4CompletedToDone:
    def test_completed_status_migrated_to_done(self, legacy_v0_conn):
        legacy_v0_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        legacy_v0_conn.execute(
            "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
            "VALUES ('t1','p1','task','completed','now','now')"
        )
        legacy_v0_conn.commit()

        run_migrations(legacy_v0_conn)

        row = legacy_v0_conn.execute("SELECT status FROM tasks WHERE id='t1'").fetchone()
        assert row["status"] == "done"

    def test_valid_statuses_unchanged(self, legacy_v0_conn):
        legacy_v0_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        for task_id, status in [("t1", "open"), ("t2", "done"), ("t3", "in_progress")]:
            legacy_v0_conn.execute(
                "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
                "VALUES (?,?,?,?,'now','now')",
                (task_id, "p1", f"task-{task_id}", status),
            )
        legacy_v0_conn.commit()

        run_migrations(legacy_v0_conn)

        rows = {r["id"]: r["status"] for r in legacy_v0_conn.execute("SELECT id, status FROM tasks").fetchall()}
        assert rows["t1"] == "open"
        assert rows["t2"] == "done"
        assert rows["t3"] == "in_progress"


# ── Migration 5: status constraint triggers ────────────────────────────────────

class TestMigration5StatusConstraint:
    def test_triggers_created(self, fresh_conn):
        run_migrations(fresh_conn)
        triggers = [
            r["name"]
            for r in fresh_conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        ]
        assert "tasks_status_insert_check" in triggers
        assert "tasks_status_update_check" in triggers

    def test_invalid_status_insert_rejected(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.commit()
        with pytest.raises(Exception, match="Invalid task status"):
            fresh_conn.execute(
                "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
                "VALUES ('t1','p1','task','invalid_status','now','now')"
            )

    def test_invalid_status_update_rejected(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
            "VALUES ('t1','p1','task','open','now','now')"
        )
        fresh_conn.commit()
        with pytest.raises(Exception, match="Invalid task status"):
            fresh_conn.execute("UPDATE tasks SET status='bad_status' WHERE id='t1'")

    def test_valid_statuses_accepted(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.commit()
        for i, status in enumerate(["open", "in_progress", "blocked", "done", "cancelled"]):
            fresh_conn.execute(
                "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
                "VALUES (?,?,?,?,'now','now')",
                (f"t{i}", "p1", f"task-{i}", status),
            )
        fresh_conn.commit()
        count = fresh_conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        assert count == 5


# ── Fresh-init schema completeness ─────────────────────────────────────────────

EXPECTED_TABLES = {
    "schema_version",
    "projects",
    "project_summaries",
    "tasks",
    "task_events",
    "decisions",
    "notes",
    "documents",
    "document_chunks",
    "embeddings",
    "entity_links",
    "tags",
    "entity_tags",
    "global_notes",
    "task_notes",
}

EXPECTED_FTS_TABLES = {
    "tasks_fts",
    "decisions_fts",
    "notes_fts",
    "chunks_fts",
    "global_notes_fts",
    "task_notes_fts",
    "summaries_fts",
}


class TestFreshInitSchema:
    def test_all_tables_created(self, fresh_conn):
        run_migrations(fresh_conn)
        tables = {
            r[0]
            for r in fresh_conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow') AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        assert EXPECTED_TABLES <= tables, f"Missing tables: {EXPECTED_TABLES - tables}"

    def test_all_fts_tables_created(self, fresh_conn):
        run_migrations(fresh_conn)
        fts_tables = {
            r[0]
            for r in fresh_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts'"
            ).fetchall()
        }
        assert EXPECTED_FTS_TABLES <= fts_tables, f"Missing FTS tables: {EXPECTED_FTS_TABLES - fts_tables}"

    def test_schema_version_at_max_after_fresh_init(self, fresh_conn):
        run_migrations(fresh_conn)
        assert _get_version(fresh_conn) == len(_MIGRATIONS)

    def test_get_conn_creates_db_on_first_use(self, tmp_path, monkeypatch):
        """End-to-end: get_conn() on a non-existent path creates a working DB."""
        db_file = tmp_path / "fresh" / "memory.db"
        monkeypatch.setenv("MCP_MEMORY_DB_PATH", str(db_file))
        assert not db_file.exists()

        from mcp_memory.repository.connection import get_conn
        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        assert count == 0
        assert db_file.exists()

# ── Migration 7: embedding orphan-cleanup triggers ────────────────────────────

class TestMigration7EmbeddingOrphanTriggers:
    def test_triggers_created_on_fresh_db(self, fresh_conn):
        run_migrations(fresh_conn)
        triggers = {
            r["name"]
            for r in fresh_conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        }
        for name in [
            "tad_tasks_embeddings", "tad_decisions_embeddings", "tad_notes_embeddings",
            "tad_task_notes_embeddings", "tad_global_notes_embeddings", "tad_chunks_embeddings",
        ]:
            assert name in triggers, f"Missing trigger: {name}"

    def test_deleting_task_removes_its_embedding(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
            "VALUES ('t1','p1','task','open','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO embeddings(id,project_id,entity_type,entity_id,embedding_model,embedding_vector,created_at) "
            "VALUES ('e1','p1','task','t1','model',X'00','now')"
        )
        fresh_conn.commit()

        fresh_conn.execute("DELETE FROM tasks WHERE id='t1'")
        fresh_conn.commit()

        count = fresh_conn.execute("SELECT COUNT(*) FROM embeddings WHERE entity_id='t1'").fetchone()[0]
        assert count == 0

    def test_deleting_note_removes_its_embedding(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO notes(id,project_id,title,note_text,note_type,created_at,updated_at) "
            "VALUES ('n1','p1','note','text','context','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO embeddings(id,project_id,entity_type,entity_id,embedding_model,embedding_vector,created_at) "
            "VALUES ('e1','p1','note','n1','model',X'00','now')"
        )
        fresh_conn.commit()

        fresh_conn.execute("DELETE FROM notes WHERE id='n1'")
        fresh_conn.commit()

        count = fresh_conn.execute("SELECT COUNT(*) FROM embeddings WHERE entity_id='n1'").fetchone()[0]
        assert count == 0


# ── Migration 8: entity_links / entity_tags orphan-cleanup triggers ───────────

class TestMigration8LinksTagsOrphanTriggers:
    def test_triggers_created_on_fresh_db(self, fresh_conn):
        run_migrations(fresh_conn)
        triggers = {
            r["name"]
            for r in fresh_conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        }
        for name in [
            "tad_tasks_links", "tad_decisions_links", "tad_notes_links",
            "tad_task_notes_links", "tad_global_notes_links",
            "tad_tasks_tags", "tad_decisions_tags", "tad_notes_tags",
            "tad_task_notes_tags", "tad_global_notes_tags",
        ]:
            assert name in triggers, f"Missing trigger: {name}"

    def test_deleting_task_removes_its_links(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
            "VALUES ('t1','p1','task','open','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO notes(id,project_id,title,note_text,note_type,created_at,updated_at) "
            "VALUES ('n1','p1','note','text','context','now','now')"
        )
        # link from task to note and note back to task
        fresh_conn.execute(
            "INSERT INTO entity_links(id,project_id,from_entity_type,from_entity_id,link_type,to_entity_type,to_entity_id,created_at) "
            "VALUES ('l1','p1','task','t1','relates_to','note','n1','now')"
        )
        fresh_conn.execute(
            "INSERT INTO entity_links(id,project_id,from_entity_type,from_entity_id,link_type,to_entity_type,to_entity_id,created_at) "
            "VALUES ('l2','p1','note','n1','explains','task','t1','now')"
        )
        fresh_conn.commit()

        fresh_conn.execute("DELETE FROM tasks WHERE id='t1'")
        fresh_conn.commit()

        remaining = fresh_conn.execute("SELECT id FROM entity_links").fetchall()
        assert len(remaining) == 0

    def test_deleting_entity_removes_its_tags(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO tasks(id,project_id,title,status,created_at,updated_at) "
            "VALUES ('t1','p1','task','open','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO tags(id,project_id,name) VALUES ('tag1','p1','backend')"
        )
        fresh_conn.execute(
            "INSERT INTO entity_tags(entity_type,entity_id,tag_id) VALUES ('task','t1','tag1')"
        )
        fresh_conn.commit()

        fresh_conn.execute("DELETE FROM tasks WHERE id='t1'")
        fresh_conn.commit()

        count = fresh_conn.execute("SELECT COUNT(*) FROM entity_tags WHERE entity_id='t1'").fetchone()[0]
        assert count == 0


# ── Migration 9: supersedes_decision_id ON DELETE SET NULL ────────────────────

class TestMigration9SupersedesDecisionFk:
    def test_data_preserved_after_table_recreation(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO decisions(id,project_id,title,decision_text,status,created_at,updated_at) "
            "VALUES ('d1','p1','Dec 1','text','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO decisions(id,project_id,title,decision_text,status,supersedes_decision_id,created_at,updated_at) "
            "VALUES ('d2','p1','Dec 2','text','active','d1','now','now')"
        )
        fresh_conn.commit()

        rows = fresh_conn.execute("SELECT id FROM decisions ORDER BY id").fetchall()
        assert [r["id"] for r in rows] == ["d1", "d2"]

    def test_deleting_superseded_decision_nullifies_fk(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.commit()  # flush pending transaction so PRAGMA takes effect
        fresh_conn.execute("PRAGMA foreign_keys = ON")
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO decisions(id,project_id,title,decision_text,status,created_at,updated_at) "
            "VALUES ('d1','p1','Old Dec','text','superseded','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO decisions(id,project_id,title,decision_text,status,supersedes_decision_id,created_at,updated_at) "
            "VALUES ('d2','p1','New Dec','text','active','d1','now','now')"
        )
        fresh_conn.commit()

        fresh_conn.execute("DELETE FROM decisions WHERE id='d1'")
        fresh_conn.commit()

        row = fresh_conn.execute("SELECT supersedes_decision_id FROM decisions WHERE id='d2'").fetchone()
        assert row["supersedes_decision_id"] is None

    def test_fts_triggers_still_work_after_table_recreation(self, fresh_conn):
        run_migrations(fresh_conn)
        fresh_conn.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at) VALUES ('p1','proj','active','now','now')"
        )
        fresh_conn.execute(
            "INSERT INTO decisions(id,project_id,title,decision_text,status,created_at,updated_at) "
            "VALUES ('d1','p1','Searchable','important choice','active','now','now')"
        )
        fresh_conn.commit()

        rows = fresh_conn.execute(
            "SELECT id FROM decisions_fts WHERE decisions_fts MATCH 'Searchable'"
        ).fetchall()
        assert len(rows) == 1

        fresh_conn.execute("DELETE FROM decisions WHERE id='d1'")
        fresh_conn.commit()

        rows = fresh_conn.execute(
            "SELECT id FROM decisions_fts WHERE decisions_fts MATCH 'Searchable'"
        ).fetchall()
        assert len(rows) == 0


# ── Fresh-init schema completeness ─────────────────────────────────────────────

    def test_schema_init_runs_only_once_per_path(self, tmp_path, monkeypatch):
        """Schema init and migrations must not repeat on every get_conn() call."""
        import unittest.mock as mock
        db_file = tmp_path / "once" / "memory.db"
        monkeypatch.setenv("MCP_MEMORY_DB_PATH", str(db_file))

        from mcp_memory.repository import connection as conn_module
        # Clear the cache so this path starts fresh regardless of test order
        conn_module._initialized_paths.discard(str(db_file))

        with mock.patch.object(conn_module, "_init_schema", wraps=conn_module._init_schema) as mock_init:
            # First call: should run init
            with conn_module.get_conn() as conn:
                conn.execute("SELECT 1")
            # Second call: must NOT run init again
            with conn_module.get_conn() as conn:
                conn.execute("SELECT 1")
            # Third call: same
            with conn_module.get_conn() as conn:
                conn.execute("SELECT 1")

        assert mock_init.call_count == 1, (
            f"_init_schema called {mock_init.call_count} times; expected exactly 1"
        )
