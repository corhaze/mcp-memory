from typing import List, Optional, Any, Tuple, Dict
from uuid import uuid4
from .connection import get_conn, _now
from .models import (
    Task, TaskEvent, TaskNote,
    _row_to_task, _row_to_task_event, _row_to_task_note
)
from .search import _store_embedding, _semantic_search_raw

# Valid task statuses per decision 3e0fcdb2: "Mandatory status sync for completed tasks"
VALID_TASK_STATUSES = {"open", "in_progress", "blocked", "done", "cancelled"}

def create_task(
    project_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "open",
    urgent: bool = False,
    complex: bool = False,
    parent_task_id: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> Task:
    if status not in VALID_TASK_STATUSES:
        raise ValueError(
            f"Invalid task status '{status}'. Valid statuses are: {', '.join(sorted(VALID_TASK_STATUSES))}. "
            f"See decision 3e0fcdb2 'Mandatory status sync for completed tasks'."
        )
    now = _now()
    tid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, description, status, urgent, complex,
                parent_task_id, assigned_agent, blocked_by_task_id,
                next_action, due_at, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (tid, project_id, title, description, status, 1 if urgent else 0, 1 if complex else 0,
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
    urgent: Optional[bool] = None,
    complex: Optional[bool] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> Optional[Task]:
    if status is not None and status not in VALID_TASK_STATUSES:
        raise ValueError(
            f"Invalid task status '{status}'. Valid statuses are: {', '.join(sorted(VALID_TASK_STATUSES))}. "
            f"See decision 3e0fcdb2 'Mandatory status sync for completed tasks'."
        )
    task = get_task(task_id)
    if not task:
        return None
    now = _now()
    # Build SQL update query dynamically
    fields = []
    vals = []
    
    if title is not None:
        fields.append("title = ?")
        vals.append(title)
    if description is not None:
        fields.append("description = ?")
        vals.append(description)
    if status is not None:
        fields.append("status = ?")
        vals.append(status)
    if urgent is not None:
        fields.append("urgent = ?")
        vals.append(1 if urgent else 0)
    if complex is not None:
        fields.append("complex = ?")
        vals.append(1 if complex else 0)
    if assigned_agent is not None:
        fields.append("assigned_agent = ?")
        vals.append(assigned_agent)
    if blocked_by_task_id is not None:
        fields.append("blocked_by_task_id = ?")
        vals.append(blocked_by_task_id)
    if next_action is not None:
        fields.append("next_action = ?")
        vals.append(next_action)
    if due_at is not None:
        fields.append("due_at = ?")
        vals.append(due_at)

    # Always update updated_at
    fields.append("updated_at = ?")
    vals.append(now)

    # Handle completed_at logic
    if status == "done":
        fields.append("completed_at = ?")
        vals.append(now)
    elif status in ("open", "in_progress", "blocked"):
        fields.append("completed_at = NULL")

    # Final ID parameter
    vals.append(task_id)
    
    set_clause = ", ".join(fields)
    query = f"UPDATE tasks SET {set_clause} WHERE id = ?"

    with get_conn() as conn:
        conn.execute(query, vals)
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
    """Return top-level tasks with subtasks eagerly loaded at all depths."""
    all_tasks = list_tasks(project_id, parent_task_id=None)
    by_id = {t.id: t for t in all_tasks}
    for task in all_tasks:
        if task.parent_task_id and task.parent_task_id in by_id:
            by_id[task.parent_task_id].subtasks.append(task)
    return [t for t in all_tasks if not t.parent_task_id]

# ── Task Events ────────────────────────────────────────────────────────────────

def _log_task_event_inner(conn: Any, task_id: str,
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
        _log_task_event_inner(conn, task_id, event_type, event_note)
    return TaskEvent(id=eid, task_id=task_id, event_type=event_type,
                     event_note=event_note, created_at=now)

def get_task_events(task_id: str, limit: int = 50) -> List[TaskEvent]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM task_events WHERE task_id=? ORDER BY created_at ASC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    return [_row_to_task_event(r) for r in rows]

# ── Task Notes ─────────────────────────────────────────────────────────────────

def create_task_note(project_id: str, task_id: str, title: str,
                     note_text: str, note_type: str = "context") -> TaskNote:
    now = _now()
    nid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO task_notes (id, project_id, task_id, title, note_text, note_type, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nid, project_id, task_id, title, note_text, note_type, now, now),
        )
        _store_embedding(conn, project_id, "task_note", nid, f"{title}\n{note_text}")
    return TaskNote(id=nid, project_id=project_id, task_id=task_id, title=title,
                    note_text=note_text, note_type=note_type, created_at=now, updated_at=now)

def get_task_note(note_id: str) -> Optional[TaskNote]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM task_notes WHERE id=?", (note_id,)).fetchone()
    return _row_to_task_note(row) if row else None

def list_task_notes(task_id: str, note_type: Optional[str] = None) -> List[TaskNote]:
    with get_conn() as conn:
        if note_type:
            rows = conn.execute(
                "SELECT * FROM task_notes WHERE task_id=? AND note_type=? ORDER BY created_at DESC",
                (task_id, note_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM task_notes WHERE task_id=? ORDER BY created_at DESC",
                (task_id,),
            ).fetchall()
    return [_row_to_task_note(r) for r in rows]

def update_task_note(note_id: str, title: Optional[str] = None,
                     note_text: Optional[str] = None,
                     note_type: Optional[str] = None) -> Optional[TaskNote]:
    note = get_task_note(note_id)
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
        conn.execute(f"UPDATE task_notes SET {set_clause} WHERE id=?", vals)
        new_title = title or note.title
        new_text = note_text or note.note_text
        _store_embedding(conn, note.project_id, "task_note", note_id, f"{new_title}\n{new_text}")
    return get_task_note(note_id)

def delete_task_note(note_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM task_notes WHERE id=?", (note_id,))
    return cur.rowcount > 0

def search_task_notes(query: str, project_id: Optional[str] = None,
                      task_id: Optional[str] = None) -> List[TaskNote]:
    with get_conn() as conn:
        if project_id and task_id:
            rows = conn.execute(
                "SELECT tn.* FROM task_notes tn "
                "JOIN task_notes_fts fts ON fts.id = tn.id "
                "WHERE task_notes_fts MATCH ? AND tn.project_id=? AND tn.task_id=? "
                "ORDER BY rank",
                (query, project_id, task_id),
            ).fetchall()
        elif project_id:
            rows = conn.execute(
                "SELECT tn.* FROM task_notes tn "
                "JOIN task_notes_fts fts ON fts.id = tn.id "
                "WHERE task_notes_fts MATCH ? AND tn.project_id=? ORDER BY rank",
                (query, project_id),
            ).fetchall()
        elif task_id:
            rows = conn.execute(
                "SELECT tn.* FROM task_notes tn "
                "JOIN task_notes_fts fts ON fts.id = tn.id "
                "WHERE task_notes_fts MATCH ? AND tn.task_id=? ORDER BY rank",
                (query, task_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT tn.* FROM task_notes tn "
                "JOIN task_notes_fts fts ON fts.id = tn.id "
                "WHERE task_notes_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
    return [_row_to_task_note(r) for r in rows]

def semantic_search_task_notes(query: str, project_id: Optional[str] = None,
                                task_id: Optional[str] = None,
                                limit: int = 5) -> List[TaskNote]:
    results = _semantic_search_raw(query, "task_note", project_id, limit * 3)
    notes = []
    for _score, eid in results:
        n = get_task_note(eid)
        if n and (task_id is None or n.task_id == task_id):
            notes.append(n)
            if len(notes) >= limit:
                break
    return notes

def semantic_search_tasks(query: str, project_id: Optional[str] = None,
                           limit: int = 5) -> List[Task]:
    results = _semantic_search_raw(query, "task", project_id, limit)
    tasks = []
    for _score, eid in results:
        t = get_task(eid)
        if t:
            tasks.append(t)
    return tasks
