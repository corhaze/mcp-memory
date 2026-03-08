"""
mcp_memory/repository/migrations.py — versioned schema migrations.

Each migration is a (description, callable) pair. The callable receives an open
sqlite3.Connection and performs all necessary DDL. Migrations are numbered
implicitly by their position in the list (1-based).

To add a new migration: append a new entry to _MIGRATIONS. Never edit or
reorder existing entries — that would corrupt the version history on live DBs.
"""

import sqlite3
from typing import Callable, List, Tuple


# ── Migration definitions ──────────────────────────────────────────────────────

def _m1_add_urgent_column(conn: sqlite3.Connection) -> None:
    """Add urgent column to tasks (was missing from initial schema)."""
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "urgent" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN urgent INTEGER NOT NULL DEFAULT 0")


def _m2_make_embeddings_project_id_nullable(conn: sqlite3.Connection) -> None:
    """Recreate embeddings table with nullable project_id (needed for global notes)."""
    col_info = {r["name"]: r for r in conn.execute("PRAGMA table_info(embeddings)").fetchall()}
    if not col_info.get("project_id") or not col_info["project_id"]["notnull"]:
        return  # Already nullable or column absent — nothing to do
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("""
        CREATE TABLE embeddings_new (
            id               TEXT PRIMARY KEY,
            project_id       TEXT,
            entity_type      TEXT NOT NULL,
            entity_id        TEXT NOT NULL,
            embedding_model  TEXT NOT NULL,
            embedding_vector BLOB NOT NULL,
            created_at       TEXT NOT NULL,
            UNIQUE(entity_type, entity_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    conn.execute("INSERT INTO embeddings_new SELECT * FROM embeddings")
    conn.execute("DROP TABLE embeddings")
    conn.execute("ALTER TABLE embeddings_new RENAME TO embeddings")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_project ON embeddings(project_id)")
    conn.execute("PRAGMA foreign_keys = ON")


# Ordered list of (description, migration_fn). Index + 1 == migration version.
_MIGRATIONS: List[Tuple[str, Callable[[sqlite3.Connection], None]]] = [
    ("Add urgent column to tasks",                  _m1_add_urgent_column),
    ("Make embeddings.project_id nullable",         _m2_make_embeddings_project_id_nullable),
]


# ── Version tracking ───────────────────────────────────────────────────────────

def _get_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return row["version"] if row else 0


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))


# ── Public entry point ─────────────────────────────────────────────────────────

def run_migrations(conn: sqlite3.Connection) -> None:
    """Run any pending migrations against an open connection."""
    current = _get_version(conn)
    for i, (description, migrate_fn) in enumerate(_MIGRATIONS):
        version = i + 1
        if version <= current:
            continue
        migrate_fn(conn)
        _set_version(conn, version)
