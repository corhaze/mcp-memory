from typing import List, Dict
from uuid import uuid4
from .connection import get_conn
from .models import Tag, _row_to_tag

def create_tag(project_id: str, name: str) -> Tag:
    tid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tags (id, project_id, name) VALUES (?, ?, ?) "
            "ON CONFLICT(project_id, name) DO NOTHING",
            (tid, project_id, name),
        )
        row = conn.execute("SELECT * FROM tags WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    return _row_to_tag(row)

def list_tags(project_id: str) -> List[Tag]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tags WHERE project_id=? ORDER BY name", (project_id,)).fetchall()
    return [_row_to_tag(row) for row in rows]

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

def list_entity_tags(entity_type: str, entity_id: str) -> List[Tag]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT t.* FROM tags t "
            "JOIN entity_tags et ON t.id = et.tag_id "
            "WHERE et.entity_type=? AND et.entity_id=? ORDER BY t.name",
            (entity_type, entity_id),
        ).fetchall()
    return [_row_to_tag(r) for r in rows]
