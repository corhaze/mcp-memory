from typing import List, Optional
from uuid import uuid4
from .connection import get_conn, _now
from .models import EntityLink, _row_to_link

def create_link(
    project_id: str,
    from_entity_type: str, from_entity_id: str,
    link_type: str,
    to_entity_type: str, to_entity_id: str,
) -> EntityLink:
    now = _now()
    lid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO entity_links
               (id, project_id, from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id) DO UPDATE SET created_at=excluded.created_at""",
            (lid, project_id, from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id, now),
        )
        row = conn.execute("SELECT * FROM entity_links WHERE project_id=? AND from_entity_type=? AND from_entity_id=? AND link_type=? AND to_entity_type=? AND to_entity_id=?",
                           (project_id, from_entity_type, from_entity_id, link_type, to_entity_type, to_entity_id)).fetchone()
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

def list_links(entity_type: str, entity_id: str,
               direction: str = "both") -> List[EntityLink]:
    """Alias for get_links_for to match newer naming patterns if needed."""
    return get_links_for(entity_type, entity_id, direction)

def delete_link(link_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM entity_links WHERE id=?", (link_id,))
    return cur.rowcount > 0
