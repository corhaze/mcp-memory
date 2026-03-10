import heapq
import pickle
import sqlite3
from typing import List, Optional, Tuple
from uuid import uuid4
from .. import embeddings as _emb
from .connection import get_conn, _now
from .models import (
    Task, Decision, Note, DocumentChunk, TaskNote, GlobalNote,
    _row_to_task, _row_to_decision, _row_to_note, _row_to_chunk, _row_to_task_note, _row_to_global_note
)

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

def _store_embedding(conn: sqlite3.Connection, project_id: Optional[str], entity_type: str,
                     entity_id: str, text: str) -> None:
    """Generate and upsert an embedding for any entity.

    Skips silently when the embedding model is unavailable.
    """
    if not _emb.is_available():
        return
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

def _semantic_search_raw(query: str, entity_type: str, project_id: Optional[str],
                          limit: int) -> List[Tuple[float, str]]:
    """Return [(score, entity_id)] for a given entity_type.

    Returns an empty list when the embedding model is unavailable.
    Uses a fixed-size heap to keep memory proportional to `limit` rather than
    to the total number of stored embeddings.
    """
    if not _emb.is_available():
        return []
    query_vec = _emb.generate_embedding(query)
    top_k: list[tuple[float, str]] = []

    with get_conn() as conn:
        if project_id:
            cursor = conn.execute(
                "SELECT entity_id, embedding_vector FROM embeddings "
                "WHERE entity_type=? AND project_id=?",
                (entity_type, project_id),
            )
        else:
            cursor = conn.execute(
                "SELECT entity_id, embedding_vector FROM embeddings WHERE entity_type=?",
                (entity_type,),
            )
        for row in cursor:
            vec = pickle.loads(row["embedding_vector"])
            score = _emb.cosine_similarity(query_vec, vec)
            if len(top_k) < limit:
                heapq.heappush(top_k, (score, row["entity_id"]))
            elif score > top_k[0][0]:
                heapq.heapreplace(top_k, (score, row["entity_id"]))

    return sorted(top_k, key=lambda x: x[0], reverse=True)

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

# Note: Search wrappers for specific domains are moved to their respective domain modules
# to keep them grouped with related CRUD, but they call _semantic_search_raw here.

# ── Unified Semantic Search ────────────────────────────────────────────────────

def semantic_search_all(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Fan out semantic search across all entity types and return merged results.

    Each result dict has:
        entity_type: one of "task", "decision", "note", "task_note", "global_note"
        score:       float cosine similarity
        entity:      the model object (Task, Decision, Note, TaskNote, GlobalNote)

    global_note has no project_id filter and is always included regardless of
    the project_id argument.  Returns [] if embeddings are unavailable.
    """
    if not _emb.is_available():
        return []

    # Fan out: over-fetch per type so we have enough candidates after merging.
    raw: dict[str, List[Tuple[float, str]]] = {
        "task":        _semantic_search_raw(query, "task",        project_id, limit),
        "decision":    _semantic_search_raw(query, "decision",    project_id, limit),
        "note":        _semantic_search_raw(query, "note",        project_id, limit),
        "task_note":   _semantic_search_raw(query, "task_note",   project_id, limit),
        "global_note": _semantic_search_raw(query, "global_note", None,       limit),
    }

    merged: list[dict] = []

    # tasks
    task_ids = [eid for _, eid in raw["task"]]
    if task_ids:
        placeholders = ", ".join("?" * len(task_ids))
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM tasks WHERE id IN ({placeholders})", task_ids
            ).fetchall()
        task_map = {row["id"]: _row_to_task(row) for row in rows}
        for score, eid in raw["task"]:
            entity = task_map.get(eid)
            if entity is not None:
                merged.append({"entity_type": "task", "score": score, "entity": entity})

    # decisions
    decision_ids = [eid for _, eid in raw["decision"]]
    if decision_ids:
        placeholders = ", ".join("?" * len(decision_ids))
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM decisions WHERE id IN ({placeholders})", decision_ids
            ).fetchall()
        decision_map = {row["id"]: _row_to_decision(row) for row in rows}
        for score, eid in raw["decision"]:
            entity = decision_map.get(eid)
            if entity is not None:
                merged.append({"entity_type": "decision", "score": score, "entity": entity})

    # notes
    note_ids = [eid for _, eid in raw["note"]]
    if note_ids:
        placeholders = ", ".join("?" * len(note_ids))
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM notes WHERE id IN ({placeholders})", note_ids
            ).fetchall()
        note_map = {row["id"]: _row_to_note(row) for row in rows}
        for score, eid in raw["note"]:
            entity = note_map.get(eid)
            if entity is not None:
                merged.append({"entity_type": "note", "score": score, "entity": entity})

    # task_notes
    task_note_ids = [eid for _, eid in raw["task_note"]]
    if task_note_ids:
        placeholders = ", ".join("?" * len(task_note_ids))
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM task_notes WHERE id IN ({placeholders})", task_note_ids
            ).fetchall()
        task_note_map = {row["id"]: _row_to_task_note(row) for row in rows}
        for score, eid in raw["task_note"]:
            entity = task_note_map.get(eid)
            if entity is not None:
                merged.append({"entity_type": "task_note", "score": score, "entity": entity})

    # global_notes
    global_note_ids = [eid for _, eid in raw["global_note"]]
    if global_note_ids:
        placeholders = ", ".join("?" * len(global_note_ids))
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM global_notes WHERE id IN ({placeholders})", global_note_ids
            ).fetchall()
        global_note_map = {row["id"]: _row_to_global_note(row) for row in rows}
        for score, eid in raw["global_note"]:
            entity = global_note_map.get(eid)
            if entity is not None:
                merged.append({"entity_type": "global_note", "score": score, "entity": entity})

    merged.sort(key=lambda r: r["score"], reverse=True)
    return merged[:limit]
