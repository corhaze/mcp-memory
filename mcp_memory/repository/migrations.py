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

def _m3_add_complex_column(conn: sqlite3.Connection) -> None:
    """Add complex column to tasks."""
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "complex" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN complex BOOLEAN NOT NULL DEFAULT 0")


def _m4_migrate_completed_to_done(conn: sqlite3.Connection) -> None:
    """Standardize task completion status: migrate 'completed' to 'done'.

    Per decision 3e0fcdb2 ("Mandatory status sync for completed tasks"), the standard
    status for completed tasks should be 'done', not 'completed'. This migration
    ensures consistency.
    """
    conn.execute("UPDATE tasks SET status='done' WHERE status='completed'")


def _m5_enforce_task_status_constraint(conn: sqlite3.Connection) -> None:
    """Add database-level constraint to enforce valid task statuses.

    Valid statuses (per decision 3e0fcdb2): {open, in_progress, blocked, done, cancelled}

    Uses triggers to prevent invalid status values at the database layer,
    complementing API-level validation.
    """
    # Create trigger to validate INSERT
    # Note: RAISE() requires a string literal — column refs (|| NEW.status) are
    # not valid in all SQLite versions, so we use a static message here.
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tasks_status_insert_check
        BEFORE INSERT ON tasks
        WHEN NEW.status NOT IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')
        BEGIN
            SELECT RAISE(ABORT,
                'Invalid task status. Valid statuses: open, in_progress, blocked, done, cancelled');
        END;
    """)
    # Create trigger to validate UPDATE
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tasks_status_update_check
        BEFORE UPDATE ON tasks
        WHEN NEW.status NOT IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')
        BEGIN
            SELECT RAISE(ABORT,
                'Invalid task status. Valid statuses: open, in_progress, blocked, done, cancelled');
        END;
    """)
    # Clean any remaining invalid statuses (defensive)
    conn.execute("""
        UPDATE tasks SET status='done'
        WHERE status NOT IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')
    """)


def _m6_fix_status_trigger_raise_syntax(conn: sqlite3.Connection) -> None:
    """Drop and recreate status validation triggers using a static RAISE() message.

    Some SQLite versions reject || column concatenation inside RAISE() at CREATE
    time, leaving the DB with a malformed schema. Drop both triggers and recreate
    them with a plain string literal.
    """
    conn.execute("DROP TRIGGER IF EXISTS tasks_status_insert_check")
    conn.execute("DROP TRIGGER IF EXISTS tasks_status_update_check")
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tasks_status_insert_check
        BEFORE INSERT ON tasks
        WHEN NEW.status NOT IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')
        BEGIN
            SELECT RAISE(ABORT,
                'Invalid task status. Valid statuses: open, in_progress, blocked, done, cancelled');
        END;
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tasks_status_update_check
        BEFORE UPDATE ON tasks
        WHEN NEW.status NOT IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')
        BEGIN
            SELECT RAISE(ABORT,
                'Invalid task status. Valid statuses: open, in_progress, blocked, done, cancelled');
        END;
    """)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone()
    return row is not None


def _m7_add_embedding_orphan_triggers(conn: sqlite3.Connection) -> None:
    """Add AFTER DELETE triggers to remove orphaned embeddings.

    The embeddings table uses a polymorphic (entity_type, entity_id) key that
    cannot carry a real FK. These triggers keep embeddings in sync when the
    backing entity is deleted.

    Skips any table that does not exist in this DB (e.g. old partial schemas).
    """
    for entity_table, entity_type in [
        ("tasks",           "task"),
        ("decisions",       "decision"),
        ("notes",           "note"),
        ("task_notes",      "task_note"),
        ("global_notes",    "global_note"),
        ("document_chunks", "chunk"),
    ]:
        if not _table_exists(conn, entity_table):
            continue
        trigger = f"tad_{entity_table}_embeddings"
        conn.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {trigger}
            AFTER DELETE ON {entity_table} BEGIN
                DELETE FROM embeddings WHERE entity_type='{entity_type}' AND entity_id=old.id;
            END;
        """)


def _m8_add_links_and_tags_orphan_triggers(conn: sqlite3.Connection) -> None:
    """Add AFTER DELETE triggers to remove orphaned entity_links and entity_tags.

    entity_links and entity_tags use polymorphic (entity_type, entity_id) keys
    that cannot carry real FKs. These triggers enforce referential integrity when
    entities are deleted.

    Skips any table that does not exist in this DB (e.g. old partial schemas).
    """
    for entity_table, entity_type in [
        ("tasks",        "task"),
        ("decisions",    "decision"),
        ("notes",        "note"),
        ("task_notes",   "task_note"),
        ("global_notes", "global_note"),
    ]:
        if not _table_exists(conn, entity_table):
            continue
        if _table_exists(conn, "entity_links"):
            links_trigger = f"tad_{entity_table}_links"
            conn.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {links_trigger}
                AFTER DELETE ON {entity_table} BEGIN
                    DELETE FROM entity_links
                    WHERE (from_entity_type='{entity_type}' AND from_entity_id=old.id)
                       OR (to_entity_type='{entity_type}'   AND to_entity_id=old.id);
                END;
            """)
        if _table_exists(conn, "entity_tags"):
            tags_trigger = f"tad_{entity_table}_tags"
            conn.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {tags_trigger}
                AFTER DELETE ON {entity_table} BEGIN
                    DELETE FROM entity_tags
                    WHERE entity_type='{entity_type}' AND entity_id=old.id;
                END;
            """)


def _m9_fix_supersedes_decision_id_fk(conn: sqlite3.Connection) -> None:
    """Recreate decisions table with ON DELETE SET NULL on supersedes_decision_id.

    SQLite does not support ALTER COLUMN, so we rebuild the table. The rename
    approach is used (decisions → decisions_old → new decisions) so that the
    self-referential FK correctly names the final table 'decisions', not a temp name.

    All FTS and orphan-cleanup triggers are recreated after the rebuild.
    """
    if not _table_exists(conn, "decisions"):
        return

    # PRAGMA foreign_keys is a no-op inside a transaction. Flush any pending
    # DML transaction (e.g. from _set_version of a prior migration) first.
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    # Rename old table; SQLite auto-updates trigger references on the renamed table.
    conn.execute("ALTER TABLE decisions RENAME TO decisions_old")

    conn.execute("""
        CREATE TABLE decisions (
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
            FOREIGN KEY(supersedes_decision_id) REFERENCES decisions(id) ON DELETE SET NULL
        )
    """)
    conn.execute("INSERT INTO decisions SELECT * FROM decisions_old")
    # Dropping decisions_old also drops all triggers that were migrated onto it.
    conn.execute("DROP TABLE decisions_old")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_status  ON decisions(project_id, status)")

    # Recreate FTS triggers.
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tai_decisions AFTER INSERT ON decisions BEGIN
            INSERT INTO decisions_fts(id, project_id, title, decision_text, rationale)
            VALUES (new.id, new.project_id, new.title, new.decision_text, COALESCE(new.rationale, ''));
        END;
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tad_decisions AFTER DELETE ON decisions BEGIN
            DELETE FROM decisions_fts WHERE id = old.id;
        END;
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tau_decisions AFTER UPDATE ON decisions BEGIN
            UPDATE decisions_fts SET title = new.title,
                decision_text = new.decision_text,
                rationale     = COALESCE(new.rationale, '')
            WHERE id = old.id;
        END;
    """)
    # Recreate orphan-cleanup triggers (added by m7/m8 then dropped with decisions_old).
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS tad_decisions_embeddings AFTER DELETE ON decisions BEGIN
            DELETE FROM embeddings WHERE entity_type='decision' AND entity_id=old.id;
        END;
    """)
    if _table_exists(conn, "entity_links"):
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS tad_decisions_links AFTER DELETE ON decisions BEGIN
                DELETE FROM entity_links
                WHERE (from_entity_type='decision' AND from_entity_id=old.id)
                   OR (to_entity_type='decision'   AND to_entity_id=old.id);
            END;
        """)
    if _table_exists(conn, "entity_tags"):
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS tad_decisions_tags AFTER DELETE ON decisions BEGIN
                DELETE FROM entity_tags WHERE entity_type='decision' AND entity_id=old.id;
            END;
        """)

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


# Ordered list of (description, migration_fn). Index + 1 == migration version.
_MIGRATIONS: List[Tuple[str, Callable[[sqlite3.Connection], None]]] = [
    ("Add urgent column to tasks",                  _m1_add_urgent_column),
    ("Make embeddings.project_id nullable",         _m2_make_embeddings_project_id_nullable),
    ("Add complex column to tasks",                 _m3_add_complex_column),
    ("Migrate 'completed' status to 'done'",        _m4_migrate_completed_to_done),
    ("Enforce task status constraint",              _m5_enforce_task_status_constraint),
    ("Fix status trigger RAISE() syntax",           _m6_fix_status_trigger_raise_syntax),
    ("Add orphan-cleanup triggers for embeddings",  _m7_add_embedding_orphan_triggers),
    ("Add orphan-cleanup triggers for links/tags",  _m8_add_links_and_tags_orphan_triggers),
    ("Fix supersedes_decision_id ON DELETE SET NULL", _m9_fix_supersedes_decision_id_fk),
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
