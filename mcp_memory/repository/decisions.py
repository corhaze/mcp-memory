from typing import List, Optional, Tuple
from uuid import uuid4
from .connection import get_conn, _now
from .models import Decision, _row_to_decision
from .search import _store_embedding, _semantic_search_raw

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

def delete_decision(decision_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM decisions WHERE id=?", (decision_id,))
    return cur.rowcount > 0

def semantic_search_decisions(query: str, project_id: Optional[str] = None,
                               limit: int = 5) -> List[Decision]:
    results = _semantic_search_raw(query, "decision", project_id, limit)
    decisions = []
    for _score, eid in results:
        d = get_decision(eid)
        if d:
            decisions.append(d)
    return decisions
