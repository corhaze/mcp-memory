import contextlib
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .migrations import run_migrations

# Track which DB paths have been fully initialised (schema + migrations).
# Keyed by resolved path string so each unique DB (e.g. per-test tmp paths)
# gets its own one-time init without repeating it on every connection.
_initialized_paths: set[str] = set()
_init_lock = threading.Lock()


def db_path() -> Path:
    env_path = os.environ.get("MCP_MEMORY_DB_PATH")
    p = Path(env_path) if env_path else Path.home() / ".mcp-memory" / "memory.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _repair_malformed_triggers(path_str: str) -> None:
    """Remove status triggers that used || in RAISE(), which some SQLite versions reject.

    A malformed trigger in sqlite_master causes every subsequent SQL statement
    (including PRAGMA) to raise OperationalError. This repair opens the DB with
    writable_schema=ON to bypass schema validation, deletes the offending triggers,
    and closes before normal initialisation proceeds. Safe to call on a clean DB.
    """
    conn = sqlite3.connect(path_str)
    try:
        conn.execute("PRAGMA writable_schema=ON")
        conn.execute(
            "DELETE FROM sqlite_master "
            "WHERE type = 'trigger' "
            "AND name IN ('tasks_status_insert_check', 'tasks_status_update_check')"
        )
        conn.commit()
    finally:
        conn.close()


@contextlib.contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Open (or create) the database, running schema init and migrations once per path."""
    path = db_path()
    path_str = str(path)

    if path_str not in _initialized_paths:
        with _init_lock:
            if path_str not in _initialized_paths:  # double-checked locking
                _repair_malformed_triggers(path_str)
                init_conn = sqlite3.connect(path_str)
                init_conn.row_factory = sqlite3.Row
                init_conn.execute("PRAGMA journal_mode=WAL;")
                init_conn.execute("PRAGMA foreign_keys = ON;")
                try:
                    _init_schema(init_conn)
                    run_migrations(init_conn)
                    _initialized_paths.add(path_str)
                finally:
                    init_conn.close()

    conn = sqlite3.connect(path_str)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        with conn:
            yield conn
    finally:
        conn.close()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        -- ── Schema version (migration tracking) ───────────────────────────
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        -- ── Core project workspace ─────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            status      TEXT NOT NULL DEFAULT 'active',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

        -- ── Rolling project summaries ──────────────────────────────────────
        CREATE TABLE IF NOT EXISTS project_summaries (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            summary_kind TEXT NOT NULL DEFAULT 'current',
            created_at   TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_summaries_project ON project_summaries(project_id);
        CREATE INDEX IF NOT EXISTS idx_summaries_kind ON project_summaries(project_id, summary_kind);

        -- ── Tasks ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS tasks (
            id                 TEXT PRIMARY KEY,
            project_id         TEXT NOT NULL,
            title              TEXT NOT NULL,
            description        TEXT,
            status             TEXT NOT NULL DEFAULT 'open',
            urgent             BOOLEAN DEFAULT 0,
            complex            BOOLEAN DEFAULT 0,
            parent_task_id     TEXT,
            assigned_agent     TEXT,
            blocked_by_task_id TEXT,
            next_action        TEXT,
            due_at             TEXT,
            created_at         TEXT NOT NULL,
            updated_at         TEXT NOT NULL,
            completed_at       TEXT,
            FOREIGN KEY(project_id)         REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(parent_task_id)     REFERENCES tasks(id),
            FOREIGN KEY(blocked_by_task_id) REFERENCES tasks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_project       ON tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status        ON tasks(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_tasks_parent        ON tasks(parent_task_id);

        -- ── Task events (append-only history) ─────────────────────────────
        CREATE TABLE IF NOT EXISTS task_events (
            id         TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, created_at);

        -- ── Decisions ──────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS decisions (
            id                     TEXT PRIMARY KEY,
            project_id             TEXT NOT NULL,
            title                  TEXT NOT NULL,
            decision_text          TEXT NOT NULL,
            rationale              TEXT,
            status                 TEXT NOT NULL DEFAULT 'active',
            supersedes_decision_id TEXT,
            created_at             TEXT NOT NULL,
            updated_at             TEXT NOT NULL,
            FOREIGN KEY(project_id)             REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(supersedes_decision_id) REFERENCES decisions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
        CREATE INDEX IF NOT EXISTS idx_decisions_status  ON decisions(project_id, status);

        -- ── Notes ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS notes (
            id         TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title      TEXT NOT NULL,
            note_text  TEXT NOT NULL,
            note_type  TEXT NOT NULL DEFAULT 'context',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id);
        CREATE INDEX IF NOT EXISTS idx_notes_type    ON notes(project_id, note_type);

        -- ── Documents ──────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS documents (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            source_type  TEXT NOT NULL DEFAULT 'generated',
            source_ref   TEXT,
            title        TEXT NOT NULL,
            content_hash TEXT,
            created_at   TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);

        -- ── Document chunks (chunked text for semantic retrieval) ──────────
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            project_id  TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text  TEXT NOT NULL,
            token_count INTEGER,
            created_at  TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id)  REFERENCES projects(id)  ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id, chunk_index);
        CREATE INDEX IF NOT EXISTS idx_chunks_project  ON document_chunks(project_id);

        -- ── Embeddings (unified, polymorphic) ─────────────────────────────
        CREATE TABLE IF NOT EXISTS embeddings (
            id               TEXT PRIMARY KEY,
            project_id       TEXT,
            entity_type      TEXT NOT NULL,
            entity_id        TEXT NOT NULL,
            embedding_model  TEXT NOT NULL,
            embedding_vector BLOB NOT NULL,
            created_at       TEXT NOT NULL,
            UNIQUE(entity_type, entity_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_embeddings_entity    ON embeddings(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_embeddings_project   ON embeddings(project_id);

        -- ── Entity links (generic graph edges) ────────────────────────────
        CREATE TABLE IF NOT EXISTS entity_links (
            id               TEXT PRIMARY KEY,
            project_id       TEXT NOT NULL,
            from_entity_type TEXT NOT NULL,
            from_entity_id   TEXT NOT NULL,
            link_type        TEXT NOT NULL,
            to_entity_type   TEXT NOT NULL,
            to_entity_id     TEXT NOT NULL,
            created_at       TEXT NOT NULL,
            UNIQUE(from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_links_from ON entity_links(from_entity_type, from_entity_id);
        CREATE INDEX IF NOT EXISTS idx_links_to   ON entity_links(to_entity_type, to_entity_id);

        -- ── Tags ───────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS tags (
            id         TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name       TEXT NOT NULL,
            UNIQUE(project_id, name),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tags_project ON tags(project_id);

        -- ── Entity tags (many-to-many) ─────────────────────────────────────
        CREATE TABLE IF NOT EXISTS entity_tags (
            entity_type TEXT NOT NULL,
            entity_id   TEXT NOT NULL,
            tag_id      TEXT NOT NULL,
            PRIMARY KEY(entity_type, entity_id, tag_id),
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_entity_tags_tag ON entity_tags(tag_id);

        -- ── FTS5: tasks ────────────────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, title, description
        );
        CREATE TRIGGER IF NOT EXISTS tai_tasks AFTER INSERT ON tasks BEGIN
            INSERT INTO tasks_fts(id, project_id, title, description)
            VALUES (new.id, new.project_id, new.title, COALESCE(new.description, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS tad_tasks AFTER DELETE ON tasks BEGIN
            DELETE FROM tasks_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_tasks AFTER UPDATE ON tasks BEGIN
            UPDATE tasks_fts SET title = new.title,
                description = COALESCE(new.description, '')
            WHERE id = old.id;
        END;

        -- ── FTS5: decisions ────────────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, title, decision_text, rationale
        );
        CREATE TRIGGER IF NOT EXISTS tai_decisions AFTER INSERT ON decisions BEGIN
            INSERT INTO decisions_fts(id, project_id, title, decision_text, rationale)
            VALUES (new.id, new.project_id, new.title, new.decision_text, COALESCE(new.rationale, ''));
        END;
        CREATE TRIGGER IF NOT EXISTS tad_decisions AFTER DELETE ON decisions BEGIN
            DELETE FROM decisions_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_decisions AFTER UPDATE ON decisions BEGIN
            UPDATE decisions_fts SET title = new.title,
                decision_text = new.decision_text,
                rationale     = COALESCE(new.rationale, '')
            WHERE id = old.id;
        END;

        -- ── FTS5: notes ────────────────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, title, note_text
        );
        CREATE TRIGGER IF NOT EXISTS tai_notes AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(id, project_id, title, note_text)
            VALUES (new.id, new.project_id, new.title, new.note_text);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_notes AFTER DELETE ON notes BEGIN
            DELETE FROM notes_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_notes AFTER UPDATE ON notes BEGIN
            UPDATE notes_fts SET title = new.title, note_text = new.note_text
            WHERE id = old.id;
        END;

        -- ── FTS5: document_chunks ──────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, document_id UNINDEXED, chunk_text
        );
        CREATE TRIGGER IF NOT EXISTS tai_chunks AFTER INSERT ON document_chunks BEGIN
            INSERT INTO chunks_fts(id, project_id, document_id, chunk_text)
            VALUES (new.id, new.project_id, new.document_id, new.chunk_text);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_chunks AFTER DELETE ON document_chunks BEGIN
            DELETE FROM chunks_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_chunks AFTER UPDATE ON document_chunks BEGIN
            UPDATE chunks_fts SET chunk_text = new.chunk_text WHERE id = old.id;
        END;

        -- ── Global notes (cross-project, no project_id) ───────────────────
        CREATE TABLE IF NOT EXISTS global_notes (
            id         TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            note_text  TEXT NOT NULL,
            note_type  TEXT NOT NULL DEFAULT 'context',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_global_notes_type ON global_notes(note_type);

        CREATE VIRTUAL TABLE IF NOT EXISTS global_notes_fts USING fts5(
            id UNINDEXED, title, note_text
        );
        CREATE TRIGGER IF NOT EXISTS tai_global_notes AFTER INSERT ON global_notes BEGIN
            INSERT INTO global_notes_fts(id, title, note_text)
            VALUES (new.id, new.title, new.note_text);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_global_notes AFTER DELETE ON global_notes BEGIN
            DELETE FROM global_notes_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_global_notes AFTER UPDATE ON global_notes BEGIN
            UPDATE global_notes_fts SET title = new.title, note_text = new.note_text
            WHERE id = old.id;
        END;

        -- ── Task notes ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS task_notes (
            id         TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_id    TEXT NOT NULL,
            title      TEXT NOT NULL,
            note_text  TEXT NOT NULL,
            note_type  TEXT NOT NULL DEFAULT 'context',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(task_id)    REFERENCES tasks(id)    ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_task_notes_task    ON task_notes(task_id);
        CREATE INDEX IF NOT EXISTS idx_task_notes_project ON task_notes(project_id);
        CREATE INDEX IF NOT EXISTS idx_task_notes_type    ON task_notes(task_id, note_type);

        -- ── FTS5: task_notes ───────────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS task_notes_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, task_id UNINDEXED, title, note_text
        );
        CREATE TRIGGER IF NOT EXISTS tai_task_notes AFTER INSERT ON task_notes BEGIN
            INSERT INTO task_notes_fts(id, project_id, task_id, title, note_text)
            VALUES (new.id, new.project_id, new.task_id, new.title, new.note_text);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_task_notes AFTER DELETE ON task_notes BEGIN
            DELETE FROM task_notes_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_task_notes AFTER UPDATE ON task_notes BEGIN
            UPDATE task_notes_fts SET title = new.title, note_text = new.note_text
            WHERE id = old.id;
        END;

        -- ── FTS5: project_summaries ────────────────────────────────────────
        CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts USING fts5(
            id UNINDEXED, project_id UNINDEXED, summary_text
        );
        CREATE TRIGGER IF NOT EXISTS tai_summaries AFTER INSERT ON project_summaries BEGIN
            INSERT INTO summaries_fts(id, project_id, summary_text)
            VALUES (new.id, new.project_id, new.summary_text);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_summaries AFTER DELETE ON project_summaries BEGIN
            DELETE FROM summaries_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_summaries AFTER UPDATE ON project_summaries BEGIN
            UPDATE summaries_fts SET summary_text = new.summary_text WHERE id = old.id;
        END;
    """)
    conn.commit()
