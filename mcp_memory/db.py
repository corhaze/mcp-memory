"""
db.py — SQLite storage layer for mcp-memory.

Hybrid relational + semantic model:
  - Relational-first for tasks, decisions, projects, events
  - Semantic second for notes, summaries, decisions, document chunks
  - Entity links for graph edges between any records

All data lives in ~/.mcp-memory/memory.db.
"""

from __future__ import annotations

import json
import pickle
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from . import embeddings as _emb

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


# ── Paths ──────────────────────────────────────────────────────────────────────

def db_path() -> Path:
    p = Path.home() / ".mcp-memory" / "memory.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    """Open (or create) the database and ensure the schema exists."""
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    _init_schema(conn)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema ─────────────────────────────────────────────────────────────────────

def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
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
            priority           TEXT NOT NULL DEFAULT 'medium',
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
            project_id       TEXT NOT NULL,
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


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class Project:
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str


@dataclass
class ProjectSummary:
    id: str
    project_id: str
    summary_text: str
    summary_kind: str
    created_at: str


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    parent_task_id: Optional[str]
    assigned_agent: Optional[str]
    blocked_by_task_id: Optional[str]
    next_action: Optional[str]
    due_at: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    subtasks: List["Task"] = field(default_factory=list)


@dataclass
class TaskEvent:
    id: str
    task_id: str
    event_type: str
    event_note: Optional[str]
    created_at: str


@dataclass
class Decision:
    id: str
    project_id: str
    title: str
    decision_text: str
    rationale: Optional[str]
    status: str
    supersedes_decision_id: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class Note:
    id: str
    project_id: str
    title: str
    note_text: str
    note_type: str
    created_at: str
    updated_at: str


@dataclass
class Document:
    id: str
    project_id: str
    source_type: str
    source_ref: Optional[str]
    title: str
    content_hash: Optional[str]
    created_at: str


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    project_id: str
    chunk_index: int
    chunk_text: str
    token_count: Optional[int]
    created_at: str


@dataclass
class Embedding:
    id: str
    project_id: str
    entity_type: str
    entity_id: str
    embedding_model: str
    created_at: str


@dataclass
class EntityLink:
    id: str
    project_id: str
    from_entity_type: str
    from_entity_id: str
    link_type: str
    to_entity_type: str
    to_entity_id: str
    created_at: str


@dataclass
class Tag:
    id: str
    project_id: str
    name: str


# ── Row helpers ────────────────────────────────────────────────────────────────

def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"], name=row["name"], description=row["description"],
        status=row["status"], created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _row_to_summary(row: sqlite3.Row) -> ProjectSummary:
    return ProjectSummary(
        id=row["id"], project_id=row["project_id"], summary_text=row["summary_text"],
        summary_kind=row["summary_kind"], created_at=row["created_at"],
    )


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        description=row["description"], status=row["status"], priority=row["priority"],
        parent_task_id=row["parent_task_id"], assigned_agent=row["assigned_agent"],
        blocked_by_task_id=row["blocked_by_task_id"], next_action=row["next_action"],
        due_at=row["due_at"], created_at=row["created_at"], updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


def _row_to_task_event(row: sqlite3.Row) -> TaskEvent:
    return TaskEvent(
        id=row["id"], task_id=row["task_id"], event_type=row["event_type"],
        event_note=row["event_note"], created_at=row["created_at"],
    )


def _row_to_decision(row: sqlite3.Row) -> Decision:
    return Decision(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        decision_text=row["decision_text"], rationale=row["rationale"],
        status=row["status"], supersedes_decision_id=row["supersedes_decision_id"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _row_to_note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        note_text=row["note_text"], note_type=row["note_type"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"], project_id=row["project_id"], source_type=row["source_type"],
        source_ref=row["source_ref"], title=row["title"], content_hash=row["content_hash"],
        created_at=row["created_at"],
    )


def _row_to_chunk(row: sqlite3.Row) -> DocumentChunk:
    return DocumentChunk(
        id=row["id"], document_id=row["document_id"], project_id=row["project_id"],
        chunk_index=row["chunk_index"], chunk_text=row["chunk_text"],
        token_count=row["token_count"], created_at=row["created_at"],
    )


def _row_to_link(row: sqlite3.Row) -> EntityLink:
    return EntityLink(
        id=row["id"], project_id=row["project_id"],
        from_entity_type=row["from_entity_type"], from_entity_id=row["from_entity_id"],
        link_type=row["link_type"],
        to_entity_type=row["to_entity_type"], to_entity_id=row["to_entity_id"],
        created_at=row["created_at"],
    )


def _row_to_tag(row: sqlite3.Row) -> Tag:
    return Tag(id=row["id"], project_id=row["project_id"], name=row["name"])


# ── Embedding helpers ──────────────────────────────────────────────────────────

def _store_embedding(conn: sqlite3.Connection, project_id: str, entity_type: str,
                     entity_id: str, text: str) -> None:
    """Generate and upsert an embedding for any entity."""
    vector = _emb.generate_embedding(text)
    emb_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO embeddings (id, project_id, entity_type, entity_id,
                                embedding_model, embedding_vector, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(entity_type, entity_id) DO UPDATE SET
            embedding_vector = excluded.embedding_vector,
            embedding_model  = excluded.embedding_model
        """,
        (emb_id, project_id, entity_type, entity_id,
         EMBEDDING_MODEL, pickle.dumps(vector), _now()),
    )


# ── Projects ───────────────────────────────────────────────────────────────────

def create_project(name: str, description: Optional[str] = None,
                   status: str = "active") -> Project:
    now = _now()
    pid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET description=excluded.description, "
            "status=excluded.status, updated_at=excluded.updated_at",
            (pid, name, description, status, now, now),
        )
        row = conn.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
    return _row_to_project(row)


def get_project(name_or_id: str) -> Optional[Project]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id=? OR name=?", (name_or_id, name_or_id)
        ).fetchone()
    return _row_to_project(row) if row else None


def list_projects(status: Optional[str] = None) -> List[Project]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM projects WHERE status=? ORDER BY name", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    return [_row_to_project(r) for r in rows]


def update_project(name_or_id: str, description: Optional[str] = None,
                   status: Optional[str] = None) -> Optional[Project]:
    proj = get_project(name_or_id)
    if not proj:
        return None
    now = _now()
    updates: List[Tuple] = []
    if description is not None:
        updates.append(("description", description))
    if status is not None:
        updates.append(("status", status))
    if not updates:
        return proj
    set_clause = ", ".join(f"{k}=?" for k, _ in updates) + ", updated_at=?"
    vals = [v for _, v in updates] + [now, proj.id]
    with get_conn() as conn:
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id=?", vals)
        row = conn.execute("SELECT * FROM projects WHERE id=?", (proj.id,)).fetchone()
    return _row_to_project(row)


def delete_project(name_or_id: str) -> bool:
    proj = get_project(name_or_id)
    if not proj:
        return False
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id=?", (proj.id,))
    return cur.rowcount > 0


def list_all_project_names() -> List[str]:
    """Return sorted list of all project names (for backwards compat)."""
    return [p.name for p in list_projects()]


# ── Project Summaries ──────────────────────────────────────────────────────────

def add_summary(project_id: str, summary_text: str,
                summary_kind: str = "current") -> ProjectSummary:
    now = _now()
    sid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO project_summaries (id, project_id, summary_text, summary_kind, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, project_id, summary_text, summary_kind, now),
        )
        _store_embedding(conn, project_id, "summary", sid, summary_text)
    return ProjectSummary(id=sid, project_id=project_id, summary_text=summary_text,
                          summary_kind=summary_kind, created_at=now)


def get_current_summary(project_id: str) -> Optional[ProjectSummary]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM project_summaries WHERE project_id=? AND summary_kind='current' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
    return _row_to_summary(row) if row else None


def list_summaries(project_id: str,
                   summary_kind: Optional[str] = None) -> List[ProjectSummary]:
    with get_conn() as conn:
        if summary_kind:
            rows = conn.execute(
                "SELECT * FROM project_summaries WHERE project_id=? AND summary_kind=? "
                "ORDER BY created_at DESC",
                (project_id, summary_kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM project_summaries WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
    return [_row_to_summary(r) for r in rows]


# ── Tasks ──────────────────────────────────────────────────────────────────────

def create_task(
    project_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "open",
    priority: str = "medium",
    parent_task_id: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> Task:
    now = _now()
    tid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, description, status, priority,
                parent_task_id, assigned_agent, blocked_by_task_id,
                next_action, due_at, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (tid, project_id, title, description, status, priority,
             parent_task_id, assigned_agent, blocked_by_task_id, next_action, due_at, now, now),
        )
        _log_task_event_inner(conn, tid, "created", f"Task created: {title}")
        embed_text = f"{title}\n{description or ''}"
        _store_embedding(conn, project_id, "task", tid, embed_text)
    return get_task(tid)


def get_task(task_id: str) -> Optional[Task]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            return None
        task = _row_to_task(row)
        # Eager-load direct children
        child_rows = conn.execute(
            "SELECT * FROM tasks WHERE parent_task_id=? ORDER BY created_at",
            (task_id,),
        ).fetchall()
        task.subtasks = [_row_to_task(r) for r in child_rows]
    return task


def list_tasks(
    project_id: str,
    status: Optional[str] = None,
    parent_task_id: Optional[str] = "_root_",  # "_root_" = top-level only, None = all
) -> List[Task]:
    with get_conn() as conn:
        params: List[Any] = [project_id]
        where = ["project_id=?"]
        if status:
            where.append("status=?")
            params.append(status)
        if parent_task_id == "_root_":
            where.append("parent_task_id IS NULL")
        elif parent_task_id is not None:
            where.append("parent_task_id=?")
            params.append(parent_task_id)
        sql = f"SELECT * FROM tasks WHERE {' AND '.join(where)} ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_task(r) for r in rows]


def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> Optional[Task]:
    task = get_task(task_id)
    if not task:
        return None
    now = _now()
    updates: List[Tuple] = []
    if title is not None:          updates.append(("title", title))
    if description is not None:    updates.append(("description", description))
    if status is not None:         updates.append(("status", status))
    if priority is not None:       updates.append(("priority", priority))
    if assigned_agent is not None: updates.append(("assigned_agent", assigned_agent))
    if blocked_by_task_id is not None: updates.append(("blocked_by_task_id", blocked_by_task_id))
    if next_action is not None:    updates.append(("next_action", next_action))
    if due_at is not None:         updates.append(("due_at", due_at))

    completed_at_update = ""
    if status == "done":
        completed_at_update = ", completed_at=?"
    elif status in ("open", "in_progress", "blocked"):
        completed_at_update = ", completed_at=NULL"

    set_clause = (", ".join(f"{k}=?" for k, _ in updates)
                  + (", " if updates else "") + "updated_at=?" + completed_at_update)
    vals: List[Any] = [v for _, v in updates] + [now]
    if status == "done":
        vals.append(now)
    vals.append(task_id)

    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", vals)
        event_note = f"Status → {status}" if status else "Updated"
        _log_task_event_inner(conn, task_id, "updated", event_note)
        if status == "done":
            _log_task_event_inner(conn, task_id, "completed", "Task marked done")
        if status == "blocked":
            _log_task_event_inner(conn, task_id, "blocked", next_action or "")
        new_title = title or task.title
        new_desc = description or task.description or ""
        _store_embedding(conn, task.project_id, "task", task_id, f"{new_title}\n{new_desc}")
    return get_task(task_id)


def delete_task(task_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    return cur.rowcount > 0


def get_task_tree(project_id: str) -> List[Task]:
    """Return top-level tasks with subtasks eagerly loaded."""
    top_tasks = list_tasks(project_id, parent_task_id="_root_")
    for task in top_tasks:
        task.subtasks = list_tasks(project_id, parent_task_id=task.id)
    return top_tasks


# ── Task Events ────────────────────────────────────────────────────────────────

def _log_task_event_inner(conn: sqlite3.Connection, task_id: str,
                          event_type: str, event_note: Optional[str] = None) -> None:
    conn.execute(
        "INSERT INTO task_events (id, task_id, event_type, event_note, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), task_id, event_type, event_note, _now()),
    )


def log_task_event(task_id: str, event_type: str,
                   event_note: Optional[str] = None) -> TaskEvent:
    now = _now()
    eid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO task_events (id, task_id, event_type, event_note, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (eid, task_id, event_type, event_note, now),
        )
    return TaskEvent(id=eid, task_id=task_id, event_type=event_type,
                     event_note=event_note, created_at=now)


def get_task_events(task_id: str, limit: int = 50) -> List[TaskEvent]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM task_events WHERE task_id=? ORDER BY created_at ASC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    return [_row_to_task_event(r) for r in rows]


# ── Decisions ──────────────────────────────────────────────────────────────────

def create_decision(
    project_id: str, title: str, decision_text: str,
    rationale: Optional[str] = None, status: str = "active",
    supersedes_decision_id: Optional[str] = None,
) -> Decision:
    now = _now()
    did = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO decisions
               (id, project_id, title, decision_text, rationale, status,
                supersedes_decision_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (did, project_id, title, decision_text, rationale, status,
             supersedes_decision_id, now, now),
        )
        if supersedes_decision_id:
            conn.execute(
                "UPDATE decisions SET status='superseded', updated_at=? WHERE id=?",
                (now, supersedes_decision_id),
            )
        embed_text = f"{title}\n{decision_text}\n{rationale or ''}"
        _store_embedding(conn, project_id, "decision", did, embed_text)
    return get_decision(did)


def get_decision(decision_id: str) -> Optional[Decision]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    return _row_to_decision(row) if row else None


def list_decisions(project_id: str, status: Optional[str] = None) -> List[Decision]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE project_id=? AND status=? ORDER BY created_at DESC",
                (project_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
    return [_row_to_decision(r) for r in rows]


def update_decision(decision_id: str, title: Optional[str] = None,
                    decision_text: Optional[str] = None, rationale: Optional[str] = None,
                    status: Optional[str] = None) -> Optional[Decision]:
    dec = get_decision(decision_id)
    if not dec:
        return None
    now = _now()
    updates: List[Tuple] = []
    if title is not None:         updates.append(("title", title))
    if decision_text is not None: updates.append(("decision_text", decision_text))
    if rationale is not None:     updates.append(("rationale", rationale))
    if status is not None:        updates.append(("status", status))
    if not updates:
        return dec
    set_clause = ", ".join(f"{k}=?" for k, _ in updates) + ", updated_at=?"
    vals = [v for _, v in updates] + [now, decision_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE decisions SET {set_clause} WHERE id=?", vals)
        new_title = title or dec.title
        new_text = decision_text or dec.decision_text
        new_rat = rationale or dec.rationale or ""
        _store_embedding(conn, dec.project_id, "decision", decision_id,
                         f"{new_title}\n{new_text}\n{new_rat}")
    return get_decision(decision_id)


def supersede_decision(old_decision_id: str, project_id: str, title: str,
                       decision_text: str, rationale: Optional[str] = None) -> Decision:
    return create_decision(project_id, title, decision_text, rationale,
                           status="active", supersedes_decision_id=old_decision_id)


# ── Notes ──────────────────────────────────────────────────────────────────────

def create_note(project_id: str, title: str, note_text: str,
                note_type: str = "context") -> Note:
    now = _now()
    nid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notes (id, project_id, title, note_text, note_type, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nid, project_id, title, note_text, note_type, now, now),
        )
        _store_embedding(conn, project_id, "note", nid, f"{title}\n{note_text}")
    return Note(id=nid, project_id=project_id, title=title, note_text=note_text,
                note_type=note_type, created_at=now, updated_at=now)


def get_note(note_id: str) -> Optional[Note]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    return _row_to_note(row) if row else None


def list_notes(project_id: str, note_type: Optional[str] = None) -> List[Note]:
    with get_conn() as conn:
        if note_type:
            rows = conn.execute(
                "SELECT * FROM notes WHERE project_id=? AND note_type=? ORDER BY updated_at DESC",
                (project_id, note_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes WHERE project_id=? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
    return [_row_to_note(r) for r in rows]


def update_note(note_id: str, title: Optional[str] = None,
                note_text: Optional[str] = None, note_type: Optional[str] = None) -> Optional[Note]:
    note = get_note(note_id)
    if not note:
        return None
    now = _now()
    updates: List[Tuple] = []
    if title is not None:     updates.append(("title", title))
    if note_text is not None: updates.append(("note_text", note_text))
    if note_type is not None: updates.append(("note_type", note_type))
    if not updates:
        return note
    set_clause = ", ".join(f"{k}=?" for k, _ in updates) + ", updated_at=?"
    vals = [v for _, v in updates] + [now, note_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE notes SET {set_clause} WHERE id=?", vals)
        new_title = title or note.title
        new_text = note_text or note.note_text
        _store_embedding(conn, note.project_id, "note", note_id, f"{new_title}\n{new_text}")
    return get_note(note_id)


def delete_note(note_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    return cur.rowcount > 0


# ── Documents ──────────────────────────────────────────────────────────────────

def create_document(project_id: str, title: str, source_type: str = "generated",
                    source_ref: Optional[str] = None,
                    content_hash: Optional[str] = None) -> Document:
    now = _now()
    did = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, project_id, source_type, source_ref, title, "
            "content_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (did, project_id, source_type, source_ref, title, content_hash, now),
        )
    return Document(id=did, project_id=project_id, source_type=source_type,
                    source_ref=source_ref, title=title,
                    content_hash=content_hash, created_at=now)


def get_document(document_id: str) -> Optional[Document]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    return _row_to_document(row) if row else None


def list_documents(project_id: str) -> List[Document]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return [_row_to_document(r) for r in rows]


def add_chunks(document_id: str, project_id: str,
               chunks: List[str]) -> List[DocumentChunk]:
    now = _now()
    result = []
    with get_conn() as conn:
        for idx, text in enumerate(chunks):
            cid = str(uuid4())
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, project_id, chunk_index, "
                "chunk_text, token_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cid, document_id, project_id, idx, text, len(text.split()), now),
            )
            _store_embedding(conn, project_id, "document_chunk", cid, text)
            result.append(DocumentChunk(id=cid, document_id=document_id, project_id=project_id,
                                        chunk_index=idx, chunk_text=text,
                                        token_count=len(text.split()), created_at=now))
    return result


def get_chunks(document_id: str) -> List[DocumentChunk]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM document_chunks WHERE document_id=? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
    return [_row_to_chunk(r) for r in rows]


# ── Entity Links ───────────────────────────────────────────────────────────────

def create_link(project_id: str, from_entity_type: str, from_entity_id: str,
                link_type: str, to_entity_type: str, to_entity_id: str) -> EntityLink:
    now = _now()
    lid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO entity_links
               (id, project_id, from_entity_type, from_entity_id, link_type,
                to_entity_type, to_entity_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT DO NOTHING""",
            (lid, project_id, from_entity_type, from_entity_id,
             link_type, to_entity_type, to_entity_id, now),
        )
        row = conn.execute(
            "SELECT * FROM entity_links WHERE from_entity_type=? AND from_entity_id=? "
            "AND link_type=? AND to_entity_type=? AND to_entity_id=?",
            (from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id),
        ).fetchone()
    return _row_to_link(row)


def get_links_for(entity_type: str, entity_id: str,
                  direction: str = "both") -> List[EntityLink]:
    with get_conn() as conn:
        if direction == "from":
            rows = conn.execute(
                "SELECT * FROM entity_links WHERE from_entity_type=? AND from_entity_id=? "
                "ORDER BY created_at",
                (entity_type, entity_id),
            ).fetchall()
        elif direction == "to":
            rows = conn.execute(
                "SELECT * FROM entity_links WHERE to_entity_type=? AND to_entity_id=? "
                "ORDER BY created_at",
                (entity_type, entity_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM entity_links WHERE "
                "(from_entity_type=? AND from_entity_id=?) OR "
                "(to_entity_type=? AND to_entity_id=?) ORDER BY created_at",
                (entity_type, entity_id, entity_type, entity_id),
            ).fetchall()
    return [_row_to_link(r) for r in rows]


def delete_link(link_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM entity_links WHERE id=?", (link_id,))
    return cur.rowcount > 0


# ── Tags ───────────────────────────────────────────────────────────────────────

def create_tag(project_id: str, name: str) -> Tag:
    tid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tags (id, project_id, name) VALUES (?, ?, ?) "
            "ON CONFLICT(project_id, name) DO NOTHING",
            (tid, project_id, name),
        )
        row = conn.execute(
            "SELECT * FROM tags WHERE project_id=? AND name=?", (project_id, name)
        ).fetchone()
    return _row_to_tag(row)


def list_tags(project_id: str) -> List[Tag]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tags WHERE project_id=? ORDER BY name", (project_id,)
        ).fetchall()
    return [_row_to_tag(r) for r in rows]


def tag_entity(tag_id: str, entity_type: str, entity_id: str) -> bool:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO entity_tags (entity_type, entity_id, tag_id) VALUES (?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            (entity_type, entity_id, tag_id),
        )
    return True


def untag_entity(tag_id: str, entity_type: str, entity_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM entity_tags WHERE tag_id=? AND entity_type=? AND entity_id=?",
            (tag_id, entity_type, entity_id),
        )
    return cur.rowcount > 0


def get_entities_by_tag(tag_id: str) -> List[Dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT entity_type, entity_id FROM entity_tags WHERE tag_id=?", (tag_id,)
        ).fetchall()
    return [{"entity_type": r["entity_type"], "entity_id": r["entity_id"]} for r in rows]


# ── FTS5 Keyword Search ────────────────────────────────────────────────────────

def search_tasks(query: str, project_id: Optional[str] = None) -> List[Task]:
    with get_conn() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT t.* FROM tasks t JOIN tasks_fts f ON t.id=f.id "
                "WHERE tasks_fts MATCH ? AND t.project_id=? ORDER BY rank",
                (query, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT t.* FROM tasks t JOIN tasks_fts f ON t.id=f.id "
                "WHERE tasks_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
    return [_row_to_task(r) for r in rows]


def search_decisions(query: str, project_id: Optional[str] = None) -> List[Decision]:
    with get_conn() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT d.* FROM decisions d JOIN decisions_fts f ON d.id=f.id "
                "WHERE decisions_fts MATCH ? AND d.project_id=? ORDER BY rank",
                (query, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT d.* FROM decisions d JOIN decisions_fts f ON d.id=f.id "
                "WHERE decisions_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
    return [_row_to_decision(r) for r in rows]


def search_notes(query: str, project_id: Optional[str] = None) -> List[Note]:
    with get_conn() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT n.* FROM notes n JOIN notes_fts f ON n.id=f.id "
                "WHERE notes_fts MATCH ? AND n.project_id=? ORDER BY rank",
                (query, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT n.* FROM notes n JOIN notes_fts f ON n.id=f.id "
                "WHERE notes_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
    return [_row_to_note(r) for r in rows]


def search_chunks(query: str, project_id: Optional[str] = None) -> List[DocumentChunk]:
    with get_conn() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT c.* FROM document_chunks c JOIN chunks_fts f ON c.id=f.id "
                "WHERE chunks_fts MATCH ? AND c.project_id=? ORDER BY rank",
                (query, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT c.* FROM document_chunks c JOIN chunks_fts f ON c.id=f.id "
                "WHERE chunks_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
    return [_row_to_chunk(r) for r in rows]


# ── Semantic Search ────────────────────────────────────────────────────────────

def _semantic_search_raw(query: str, entity_type: str, project_id: Optional[str],
                          limit: int) -> List[Tuple[float, str]]:
    """Return [(score, entity_id)] for a given entity_type."""
    query_vec = _emb.generate_embedding(query)
    with get_conn() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT entity_id, embedding_vector FROM embeddings "
                "WHERE entity_type=? AND project_id=?",
                (entity_type, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT entity_id, embedding_vector FROM embeddings WHERE entity_type=?",
                (entity_type,),
            ).fetchall()
    scored = []
    for r in rows:
        vec = pickle.loads(r["embedding_vector"])
        score = _emb.cosine_similarity(query_vec, vec)
        scored.append((score, r["entity_id"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def semantic_search_tasks(query: str, project_id: Optional[str] = None,
                           limit: int = 5) -> List[Task]:
    results = _semantic_search_raw(query, "task", project_id, limit)
    tasks = []
    for _score, eid in results:
        t = get_task(eid)
        if t:
            tasks.append(t)
    return tasks


def semantic_search_decisions(query: str, project_id: Optional[str] = None,
                               limit: int = 5) -> List[Decision]:
    results = _semantic_search_raw(query, "decision", project_id, limit)
    decisions = []
    for _score, eid in results:
        d = get_decision(eid)
        if d:
            decisions.append(d)
    return decisions


def semantic_search_notes(query: str, project_id: Optional[str] = None,
                           limit: int = 5) -> List[Note]:
    results = _semantic_search_raw(query, "note", project_id, limit)
    notes = []
    for _score, eid in results:
        n = get_note(eid)
        if n:
            notes.append(n)
    return notes


def semantic_search_chunks(query: str, project_id: Optional[str] = None,
                            limit: int = 5) -> List[DocumentChunk]:
    results = _semantic_search_raw(query, "document_chunk", project_id, limit)
    chunks = []
    for _score, eid in results:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM document_chunks WHERE id=?", (eid,)
            ).fetchone()
        if row:
            chunks.append(_row_to_chunk(row))
    return chunks


# ── Working Context (prescribed retrieval flow) ────────────────────────────────

def get_working_context(project_id: str) -> Dict[str, Any]:
    """
    Assemble a compact working context packet for an agent session.

    Flow:
      1. Current project summary
      2. Open / in-progress tasks
      3. Decisions linked to each open task
      4. Active decisions (global to project)
      5. Recent notes

    Returns a structured dict — callers can format as needed.
    """
    proj = get_project(project_id)
    if not proj:
        # Try by name
        proj_by_name = None
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE name=?", (project_id,)
            ).fetchone()
            if row:
                proj_by_name = _row_to_project(row)
                project_id = proj_by_name.id
        if not proj_by_name:
            return {"error": f"Project '{project_id}' not found."}
        proj = proj_by_name

    # 1. Current summary
    summary = get_current_summary(project_id)

    # 2. Open tasks
    open_tasks = list_tasks(project_id, status="open", parent_task_id=None)
    in_progress = list_tasks(project_id, status="in_progress", parent_task_id=None)
    active_tasks = open_tasks + in_progress

    # 3. Decisions linked to active tasks
    linked_decision_ids: set = set()
    for task in active_tasks:
        links = get_links_for("task", task.id, direction="from")
        for lnk in links:
            if lnk.to_entity_type == "decision":
                linked_decision_ids.add(lnk.to_entity_id)

    linked_decisions = []
    for did in linked_decision_ids:
        d = get_decision(did)
        if d:
            linked_decisions.append(d)

    # 4. Active decisions (project-wide)
    active_decisions = list_decisions(project_id, status="active")

    # 5. Recent notes
    recent_notes = list_notes(project_id)[:5]

    return {
        "project": {"id": proj.id, "name": proj.name, "status": proj.status,
                    "description": proj.description},
        "summary": summary.summary_text if summary else None,
        "active_tasks": [
            {"id": t.id, "title": t.title, "status": t.status,
             "priority": t.priority, "next_action": t.next_action}
            for t in active_tasks
        ],
        "linked_decisions": [
            {"id": d.id, "title": d.title, "decision_text": d.decision_text}
            for d in linked_decisions
        ],
        "active_decisions": [
            {"id": d.id, "title": d.title, "status": d.status}
            for d in active_decisions
        ],
        "recent_notes": [
            {"id": n.id, "title": n.title, "note_type": n.note_type}
            for n in recent_notes
        ],
    }
