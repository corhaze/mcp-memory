from typing import List, Optional
from uuid import uuid4
from .connection import get_conn, _now
from .models import Document, DocumentChunk, _row_to_document, _row_to_chunk
from .search import _store_embedding, _semantic_search_raw

def create_document(project_id: str, title: str, source_type: str = "generated",
                    source_ref: Optional[str] = None,
                    content_hash: Optional[str] = None) -> Document:
    now = _now()
    did = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, project_id, source_type, source_ref, title, "
            "content_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (did, project_id, source_type, source_ref, title, content_hash, now),
        )
    return Document(id=did, project_id=project_id, source_type=source_type,
                    source_ref=source_ref, title=title,
                    content_hash=content_hash, created_at=now)

def get_document(document_id: str) -> Optional[Document]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    return _row_to_document(row) if row else None

def list_documents(project_id: str) -> List[Document]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return [_row_to_document(r) for r in rows]

def add_chunks(document_id: str, project_id: str,
               chunks: List[str]) -> List[DocumentChunk]:
    now = _now()
    result = []
    with get_conn() as conn:
        for idx, text in enumerate(chunks):
            cid = str(uuid4())
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, project_id, chunk_index, "
                "chunk_text, token_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cid, document_id, project_id, idx, text, len(text.split()), now),
            )
            _store_embedding(conn, project_id, "document_chunk", cid, text)
            result.append(DocumentChunk(id=cid, document_id=document_id, project_id=project_id,
                                        chunk_index=idx, chunk_text=text,
                                        token_count=len(text.split()), created_at=now))
    return result

def get_chunks(document_id: str) -> List[DocumentChunk]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM document_chunks WHERE document_id=? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
    return [_row_to_chunk(r) for r in rows]

def semantic_search_chunks(query: str, project_id: Optional[str] = None,
                            limit: int = 5) -> List[DocumentChunk]:
    results = _semantic_search_raw(query, "document_chunk", project_id, limit)
    chunks = []
    for _score, eid in results:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM document_chunks WHERE id=?", (eid,)
            ).fetchone()
        if row:
            chunks.append(_row_to_chunk(row))
    return chunks
