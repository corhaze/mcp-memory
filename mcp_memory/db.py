"""
db.py — SQLite storage layer for mcp-memory.

All data lives in ~/.mcp-memory/memory.db.
No server required; sqlite3 is part of the Python standard library.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4
import pickle
from . import embeddings as _emb


# ── Paths ─────────────────────────────────────────────────────────────────────

def db_path() -> Path:
    p = Path.home() / ".mcp-memory" / "memory.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    """Open (or create) the database and ensure the schema exists."""
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contexts (
            id       TEXT PRIMARY KEY,
            project  TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            key      TEXT NOT NULL,
            value    TEXT NOT NULL,
            tags     TEXT NOT NULL DEFAULT '[]',
            created  TEXT NOT NULL,
            updated  TEXT NOT NULL,
            UNIQUE(project, category, key)
        );

        CREATE TABLE IF NOT EXISTS events (
            id         TEXT PRIMARY KEY,
            project    TEXT NOT NULL,
            event_type TEXT NOT NULL,
            summary    TEXT NOT NULL,
            detail     TEXT,
            timestamp  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_contexts_project
            ON contexts(project);
        CREATE INDEX IF NOT EXISTS idx_events_project_ts
            ON events(project, timestamp DESC);

        CREATE TABLE IF NOT EXISTS insights (
            id          TEXT PRIMARY KEY,
            scope       TEXT NOT NULL DEFAULT 'global',  -- 'global' or a project name
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            example     TEXT,                            -- optional code snippet / illustration
            tags        TEXT NOT NULL DEFAULT '[]',      -- JSON array
            created     TEXT NOT NULL,
            updated     TEXT NOT NULL,
            UNIQUE(scope, title)
        );

        CREATE INDEX IF NOT EXISTS idx_insights_scope
            ON insights(scope);

        -- FTS5 Virtual Table for Insights
        CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts USING fts5(
            id UNINDEXED,
            title,
            body,
            tags
        );

        -- Triggers to keep insights_fts in sync
        CREATE TRIGGER IF NOT EXISTS tai_insights AFTER INSERT ON insights BEGIN
            INSERT INTO insights_fts(id, title, body, tags)
            VALUES (new.id, new.title, new.body, new.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_insights AFTER DELETE ON insights BEGIN
            DELETE FROM insights_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_insights AFTER UPDATE ON insights BEGIN
            UPDATE insights_fts SET 
                title = new.title,
                body = new.body,
                tags = new.tags
            WHERE id = old.id;
        END;

        -- FTS5 Virtual Table for Contexts
        CREATE VIRTUAL TABLE IF NOT EXISTS contexts_fts USING fts5(
            id UNINDEXED,
            project,
            category,
            key,
            value,
            tags
        );

        -- Triggers to keep contexts_fts in sync
        CREATE TRIGGER IF NOT EXISTS tai_contexts AFTER INSERT ON contexts BEGIN
            INSERT INTO contexts_fts(id, project, category, key, value, tags)
            VALUES (new.id, new.project, new.category, new.key, new.value, new.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_contexts AFTER DELETE ON contexts BEGIN
            DELETE FROM contexts_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_contexts AFTER UPDATE ON contexts BEGIN
            UPDATE contexts_fts SET 
                project = new.project,
                category = new.category,
                key = new.key,
                value = new.value,
                tags = new.tags
            WHERE id = old.id;
        END;

        CREATE TABLE IF NOT EXISTS todos (
            id          TEXT PRIMARY KEY,
            project     TEXT NOT NULL,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            priority    TEXT NOT NULL DEFAULT 'medium',
            created     TEXT NOT NULL,
            updated     TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_todos_project_status
            ON todos(project, status);

        -- FTS5 Virtual Table for Todos
        CREATE VIRTUAL TABLE IF NOT EXISTS todos_fts USING fts5(
            id UNINDEXED,
            project,
            title,
            description
        );

        -- Triggers to keep todos_fts in sync
        CREATE TRIGGER IF NOT EXISTS tai_todos AFTER INSERT ON todos BEGIN
            INSERT INTO todos_fts(id, project, title, description)
            VALUES (new.id, new.project, new.title, new.description);
        END;
        CREATE TRIGGER IF NOT EXISTS tad_todos AFTER DELETE ON todos BEGIN
            DELETE FROM todos_fts WHERE id = old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS tau_todos AFTER UPDATE ON todos BEGIN
            UPDATE todos_fts SET 
                project = new.project,
                title = new.title,
                description = new.description
            WHERE id = old.id;
        END;

        -- Backfill FTS tables if they are empty
        INSERT INTO insights_fts(id, title, body, tags)
            SELECT id, title, body, tags FROM insights
            WHERE NOT EXISTS (SELECT 1 FROM insights_fts WHERE id = insights.id);

        INSERT INTO contexts_fts(id, project, category, key, value, tags)
            SELECT id, project, category, key, value, tags FROM contexts
            WHERE NOT EXISTS (SELECT 1 FROM contexts_fts WHERE id = contexts.id);

        INSERT INTO todos_fts(id, project, title, description)
            SELECT id, project, title, description FROM todos
            WHERE NOT EXISTS (SELECT 1 FROM todos_fts WHERE id = todos.id);

        -- Embedding Storage
        CREATE TABLE IF NOT EXISTS contexts_embeddings (
            id        TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            FOREIGN KEY(id) REFERENCES contexts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS insights_embeddings (
            id        TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            FOREIGN KEY(id) REFERENCES insights(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS todos_embeddings (
            id        TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            FOREIGN KEY(id) REFERENCES todos(id) ON DELETE CASCADE
        );
    """)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.commit()


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ContextEntry:
    id: str
    project: str
    category: str
    key: str
    value: str
    tags: List[str]
    created: str
    updated: str


@dataclass
class InsightEntry:
    id: str
    scope: str
    title: str
    body: str
    example: Optional[str]
    tags: List[str]
    created: str
    updated: str
    snippet: Optional[str] = None  # Match preview from FTS5


@dataclass
class EventEntry:
    id: str
    project: str
    event_type: str
    summary: str
    detail: Optional[str]
    timestamp: str


@dataclass
class TodoEntry:
    id: str
    project: str
    title: str
    description: str
    status: str
    priority: str
    created: str
    updated: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_context(row: sqlite3.Row) -> ContextEntry:
    return ContextEntry(
        id=row["id"],
        project=row["project"],
        category=row["category"],
        key=row["key"],
        value=row["value"],
        tags=json.loads(row["tags"]),
        created=row["created"],
        updated=row["updated"],
    )


# ── Context CRUD ──────────────────────────────────────────────────────────────

def upsert_context(
    project: str,
    key: str,
    value: str,
    category: str = "general",
    tags: Optional[List[str]] = None,
) -> ContextEntry:
    tags = tags or []
    now = _now()
    entry_id = str(uuid4())

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO contexts (id, project, category, key, value, tags, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project, category, key) DO UPDATE SET
                value   = excluded.value,
                tags    = excluded.tags,
                updated = excluded.updated
            """,
            (entry_id, project, category, key, value, json.dumps(tags), now, now),
        )
        row = conn.execute(
            "SELECT * FROM contexts WHERE project=? AND category=? AND key=?",
            (project, category, key),
        ).fetchone()
        
        # Update embedding
        emb_vector = _emb.generate_embedding(value)
        conn.execute(
            "INSERT INTO contexts_embeddings (id, embedding) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET embedding=excluded.embedding",
            (row["id"], pickle.dumps(emb_vector)),
        )
        
    return _row_to_context(row)


def get_context(
    project: str, key: str, category: str = "general"
) -> Optional[ContextEntry]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contexts WHERE project=? AND category=? AND key=?",
            (project, category, key),
        ).fetchone()
    return _row_to_context(row) if row else None


def list_contexts(
    project: str,
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[ContextEntry]:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM contexts WHERE project=? AND category=? ORDER BY category, key",
                (project, category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contexts WHERE project=? ORDER BY category, key",
                (project,),
            ).fetchall()

    entries = [_row_to_context(r) for r in rows]
    if tag:
        entries = [e for e in entries if tag in e.tags]
    return entries


def delete_context(
    project: str, key: str, category: str = "general"
) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM contexts WHERE project=? AND category=? AND key=?",
            (project, category, key),
        )
    return cur.rowcount > 0



def list_all_projects() -> List[str]:
    """Return a sorted list of all distinct project names in the DB."""
    with get_conn() as conn:
        # Combine from contexts, events, and todos
        query = """
            SELECT project FROM contexts
            UNION
            SELECT project FROM events
            UNION
            SELECT project FROM todos
            ORDER BY project
        """
        rows = conn.execute(query).fetchall()
    return [r["project"] for r in rows]


def delete_project(project: str) -> None:
    """Delete all data associated with a project."""
    with get_conn() as conn:
        conn.execute("DELETE FROM contexts WHERE project = ?", (project,))
        conn.execute("DELETE FROM events WHERE project = ?", (project,))
        conn.execute("DELETE FROM todos WHERE project = ?", (project,))
        # Insights use 'scope'
        conn.execute("DELETE FROM insights WHERE scope = ?", (project,))
        conn.commit()



# ── Insights ──────────────────────────────────────────────────────────────────

def _row_to_insight(row: sqlite3.Row) -> InsightEntry:
    return InsightEntry(
        id=row["id"],
        scope=row["scope"],
        title=row["title"],
        body=row["body"],
        example=row["example"],
        tags=json.loads(row["tags"]),
        created=row["created"],
        updated=row["updated"],
        snippet=row["snippet"] if "snippet" in row.keys() else None,
    )


def add_insight(
    title: str,
    body: str,
    scope: str = "global",
    example: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> InsightEntry:
    """Add or update an insight. Upserts by (scope, title)."""
    tags = tags or []
    now = _now()
    entry_id = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO insights (id, scope, title, body, example, tags, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, title) DO UPDATE SET
                body    = excluded.body,
                example = excluded.example,
                tags    = excluded.tags,
                updated = excluded.updated
            """,
            (entry_id, scope, title, body, example, json.dumps(tags), now, now),
        )
        row = conn.execute(
            "SELECT * FROM insights WHERE scope=? AND title=?",
            (scope, title),
        ).fetchone()

        # Update embedding (title + body)
        emb_vector = _emb.generate_embedding(f"{title}\n{body}")
        conn.execute(
            "INSERT INTO insights_embeddings (id, embedding) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET embedding=excluded.embedding",
            (row["id"], pickle.dumps(emb_vector)),
        )

    return _row_to_insight(row)


def list_insights(
    scope: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[InsightEntry]:
    """Return insights.
    - scope=<project>: returns that project's insights AND global ones combined
    - scope='global': returns only global insights
    - scope=None: returns everything
    """
    with get_conn() as conn:
        if scope and scope != "global":
            rows = conn.execute(
                "SELECT * FROM insights WHERE scope=? OR scope='global' ORDER BY scope, title",
                (scope,),
            ).fetchall()
        elif scope == "global":
            rows = conn.execute(
                "SELECT * FROM insights WHERE scope='global' ORDER BY title"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM insights ORDER BY scope, title"
            ).fetchall()

    insights = [_row_to_insight(r) for r in rows]
    if tag:
        insights = [i for i in insights if tag in i.tags]
    return insights


def delete_insight(scope: str, title: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM insights WHERE scope=? AND title=?",
            (scope, title),
        )
    return cur.rowcount > 0


def search_insights(query: str) -> List[InsightEntry]:
    """Search for insights using FTS5 with BM25 ranking and snippets."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT i.*, 
                   snippet(insights_fts, 2, '<b>', '</b>', '...', 20) as snippet
            FROM insights i
            JOIN insights_fts f ON i.id = f.id
            WHERE insights_fts MATCH ?
            ORDER BY rank
            """,
            (query,),
        ).fetchall()
    return [_row_to_insight(r) for r in rows]


def search_contexts(query: str) -> List[ContextEntry]:
    """Search for context entries using FTS5 with BM25 ranking."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.*
            FROM contexts c
            JOIN contexts_fts f ON c.id = f.id
            WHERE contexts_fts MATCH ?
            ORDER BY rank
            """,
            (query,),
        ).fetchall()
    return [_row_to_context(r) for r in rows]


# ── Todos ──────────────────────────────────────────────────────────────────

def _row_to_todo(row: sqlite3.Row) -> TodoEntry:
    return TodoEntry(
        id=row["id"],
        project=row["project"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        priority=row["priority"],
        created=row["created"],
        updated=row["updated"],
    )


def upsert_todo(
    project: str,
    title: str,
    description: str,
    status: str = "pending",
    priority: str = "medium",
    todo_id: Optional[str] = None,
) -> TodoEntry:
    now = _now()
    entry_id = todo_id or str(uuid4())

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO todos (id, project, title, description, status, priority, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title       = excluded.title,
                description = excluded.description,
                status      = excluded.status,
                priority    = excluded.priority,
                updated     = excluded.updated
            """,
            (entry_id, project, title, description, status, priority, now, now),
        )
        row = conn.execute(
            "SELECT * FROM todos WHERE id=?", (entry_id,)
        ).fetchone()

        # Update embedding (title + description)
        emb_vector = _emb.generate_embedding(f"{title}\n{description}")
        conn.execute(
            "INSERT INTO todos_embeddings (id, embedding) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET embedding=excluded.embedding",
            (row["id"], pickle.dumps(emb_vector)),
        )

    return _row_to_todo(row)


def get_todo(todo_id: str) -> Optional[TodoEntry]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM todos WHERE id=?", (todo_id,)
        ).fetchone()
    return _row_to_todo(row) if row else None


def list_todos(
    project: str,
    status: Optional[str] = None,
) -> List[TodoEntry]:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM todos WHERE project=? AND status=? ORDER BY created DESC",
                (project, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM todos WHERE project=? ORDER BY status, created DESC",
                (project,),
            ).fetchall()
    return [_row_to_todo(r) for r in rows]


def search_todos(query: str) -> List[TodoEntry]:
    """Search for todos using FTS5 with BM25 ranking."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.*
            FROM todos t
            JOIN todos_fts f ON t.id = f.id
            WHERE todos_fts MATCH ?
            ORDER BY rank
            """,
            (query,),
        ).fetchall()
    return [_row_to_todo(r) for r in rows]


def delete_todo(todo_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM todos WHERE id=?", (todo_id,)
        )
    return cur.rowcount > 0


# ── Events ────────────────────────────────────────────────────────────────────

def log_event(
    project: str,
    event_type: str,
    summary: str,
    detail: Optional[str] = None,
) -> EventEntry:
    now = _now()
    entry_id = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO events (id, project, event_type, summary, detail, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entry_id, project, event_type, summary, detail, now),
        )
    return EventEntry(
        id=entry_id,
        project=project,
        event_type=event_type,
        summary=summary,
        detail=detail,
        timestamp=now,
    )


def get_timeline(project: str, limit: int = 20) -> List[EventEntry]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events WHERE project=?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (project, limit),
        ).fetchall()
    return [
        EventEntry(
            id=r["id"],
            project=r["project"],
            event_type=r["event_type"],
            summary=r["summary"],
            detail=r["detail"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]


# ── Semantic Search ───────────────────────────────────────────────────────────

def semantic_search_contexts(query: str, project: Optional[str] = None, limit: int = 5) -> List[ContextEntry]:
    """Perform semantic search for context entries."""
    query_emb = _emb.generate_embedding(query)
    with get_conn() as conn:
        if project:
            rows = conn.execute(
                "SELECT c.*, e.embedding FROM contexts c "
                "JOIN contexts_embeddings e ON c.id = e.id "
                "WHERE c.project = ?", (project,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT c.*, e.embedding FROM contexts c "
                "JOIN contexts_embeddings e ON c.id = e.id"
            ).fetchall()

    results = []
    for r in rows:
        emb = pickle.loads(r["embedding"])
        score = _emb.cosine_similarity(query_emb, emb)
        results.append((score, _row_to_context(r)))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:limit]]


def semantic_search_insights(query: str, scope: Optional[str] = None, limit: int = 5) -> List[InsightEntry]:
    """Perform semantic search for insights."""
    query_emb = _emb.generate_embedding(query)
    with get_conn() as conn:
        if scope:
            rows = conn.execute(
                "SELECT i.*, e.embedding FROM insights i "
                "JOIN insights_embeddings e ON i.id = e.id "
                "WHERE i.scope = ? OR i.scope = 'global'", (scope,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT i.*, e.embedding FROM insights i "
                "JOIN insights_embeddings e ON i.id = e.id"
            ).fetchall()

    results = []
    for r in rows:
        emb = pickle.loads(r["embedding"])
        score = _emb.cosine_similarity(query_emb, emb)
        results.append((score, _row_to_insight(r)))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:limit]]


def semantic_search_todos(query: str, project: Optional[str] = None, limit: int = 5) -> List[TodoEntry]:
    """Perform semantic search for todos."""
    query_emb = _emb.generate_embedding(query)
    with get_conn() as conn:
        if project:
            rows = conn.execute(
                "SELECT t.*, e.embedding FROM todos t "
                "JOIN todos_embeddings e ON t.id = e.id "
                "WHERE t.project = ?", (project,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT t.*, e.embedding FROM todos t "
                "JOIN todos_embeddings e ON t.id = e.id"
            ).fetchall()

    results = []
    for r in rows:
        emb = pickle.loads(r["embedding"])
        score = _emb.cosine_similarity(query_emb, emb)
        results.append((score, _row_to_todo(r)))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:limit]]
