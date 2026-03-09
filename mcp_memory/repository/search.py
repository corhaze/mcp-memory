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
    """Generate and upsert an embedding for any entity."""
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

    Uses a fixed-size heap to keep memory proportional to `limit` rather than
    to the total number of stored embeddings.
    """
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
