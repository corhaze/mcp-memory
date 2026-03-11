from typing import List, Optional, Tuple
from uuid import uuid4
from .connection import get_conn, _now
from .models import Project, ProjectSummary, _row_to_project, _row_to_summary
from .search import _store_embedding

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
                "SELECT * FROM projects WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
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
