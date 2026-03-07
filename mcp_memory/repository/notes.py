from typing import List, Optional, Tuple
from uuid import uuid4
from .connection import get_conn, _now
from .models import Note, GlobalNote, _row_to_note, _row_to_global_note
from .search import _store_embedding, _semantic_search_raw

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
                "SELECT * FROM notes WHERE project_id=? AND note_type=? ORDER BY created_at DESC",
                (project_id, note_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes WHERE project_id=? ORDER BY created_at DESC",
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

# ── Global Notes ───────────────────────────────────────────────────────────────

def create_global_note(title: str, note_text: str, note_type: str = "context") -> GlobalNote:
    now = _now()
    nid = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO global_notes (id, title, note_text, note_type, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nid, title, note_text, note_type, now, now),
        )
        _store_embedding(conn, None, "global_note", nid, f"{title}\n{note_text}")
    return GlobalNote(id=nid, title=title, note_text=note_text, note_type=note_type,
                      created_at=now, updated_at=now)

def get_global_note(note_id: str) -> Optional[GlobalNote]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM global_notes WHERE id=?", (note_id,)).fetchone()
    return _row_to_global_note(row) if row else None

def list_global_notes(note_type: Optional[str] = None) -> List[GlobalNote]:
    with get_conn() as conn:
        if note_type:
            rows = conn.execute(
                "SELECT * FROM global_notes WHERE note_type=? ORDER BY created_at DESC",
                (note_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM global_notes ORDER BY created_at DESC"
            ).fetchall()
    return [_row_to_global_note(r) for r in rows]

def update_global_note(note_id: str, title: Optional[str] = None,
                       note_text: Optional[str] = None,
                       note_type: Optional[str] = None) -> Optional[GlobalNote]:
    note = get_global_note(note_id)
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
        conn.execute(f"UPDATE global_notes SET {set_clause} WHERE id=?", vals)
        new_title = title or note.title
        new_text = note_text or note.note_text
        _store_embedding(conn, None, "global_note", note_id, f"{new_title}\n{new_text}")
    return get_global_note(note_id)

def delete_global_note(note_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM global_notes WHERE id=?", (note_id,))
    return cur.rowcount > 0

def search_global_notes(query: str) -> List[GlobalNote]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT gn.* FROM global_notes gn "
            "JOIN global_notes_fts fts ON fts.id = gn.id "
            "WHERE global_notes_fts MATCH ? ORDER BY rank",
            (query,),
        ).fetchall()
    return [_row_to_global_note(r) for r in rows]

def semantic_search_global_notes(query: str, limit: int = 5) -> List[GlobalNote]:
    results = _semantic_search_raw(query, "global_note", None, limit)
    notes = []
    for _score, eid in results:
        n = get_global_note(eid)
        if n:
            notes.append(n)
    return notes

def semantic_search_notes(query: str, project_id: Optional[str] = None,
                           limit: int = 5) -> List[Note]:
    results = _semantic_search_raw(query, "note", project_id, limit)
    notes = []
    for _score, eid in results:
        n = get_note(eid)
        if n:
            notes.append(n)
    return notes
