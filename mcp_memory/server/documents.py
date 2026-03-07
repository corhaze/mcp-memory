from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

# ── Documents ─────────────────────────────────────────────────────────────────

@mcp.tool()
def create_document(
    project_id: str,
    title: str,
    content: str,
    source_type: str = "generated",
    source_ref: Optional[str] = None,
    chunk_size: int = 500,
) -> str:
    """
    Import or create a document and chunk it for semantic retrieval.

    Args:
        project_id:  Project UUID or name.
        title:       Document title.
        content:     Full document text.
        source_type: file, url, generated (default), chat_import.
        source_ref:  File path or URL.
        chunk_size:  Approximate words per chunk (default 500).
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    doc = _db.create_document(proj.id, title, source_type, source_ref)
    words = content.split()
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    added = _db.add_chunks(doc.id, proj.id, chunks)
    return (f"Document '{doc.title}' created (id: {doc.id}) with {len(added)} chunk(s).")


@mcp.tool()
def list_documents(project_id: str) -> str:
    """
    List documents for a project.

    Args:
        project_id: Project UUID or name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    docs = _db.list_documents(proj.id)
    if not docs:
        return "No documents found."
    lines = [f"[{d.source_type}] {d.title} ({d.id}) — {d.created_at[:10]}" for d in docs]
    return f"{len(docs)} document(s):\n" + "\n".join(lines)
