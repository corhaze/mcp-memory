from typing import List, Optional
from .mcp import mcp
import mcp_memory.db as _db
from mcp_memory import embeddings as _emb

_EMBEDDINGS_UNAVAILABLE = (
    "Semantic search is unavailable — embedding model not loaded. "
    "Use the `search` tool for keyword search instead."
)

# ── Unified Search ────────────────────────────────────────────────────────────

@mcp.tool()
def search(
    query: str,
    entity_types: Optional[List[str]] = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Full-text keyword search across entity types using FTS5.

    Searches tasks, decisions, notes, and document chunks by default.
    Use semantic_search_* tools for fuzzy/natural-language recall.

    Args:
        query:        Keyword search query.
        entity_types: List of types to search — tasks, decisions, notes, chunks.
                      Defaults to all four.
        project_id:   Optional project filter (UUID or name).
    """
    pid: Optional[str] = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None

    types = entity_types or ["tasks", "decisions", "notes", "task_notes", "global_notes", "chunks"]
    sections = []

    if "tasks" in types:
        results = _db.search_tasks(query, pid)
        if results:
            lines = [f"  [{t.status}] {t.title} ({t.id})" for t in results]
            sections.append("Tasks:\n" + "\n".join(lines))

    if "decisions" in types:
        results = _db.search_decisions(query, pid)
        if results:
            lines = [f"  [{d.status}] {d.title} ({d.id})" for d in results]
            sections.append("Decisions:\n" + "\n".join(lines))

    if "notes" in types:
        results = _db.search_notes(query, pid)
        if results:
            lines = [f"  [{n.note_type}] {n.title} ({n.id})" for n in results]
            sections.append("Notes:\n" + "\n".join(lines))

    if "task_notes" in types:
        results = _db.search_task_notes(query, pid)
        if results:
            lines = [f"  [{n.note_type}] {n.title} (task: {n.task_id[:8]}, id: {n.id})"
                     for n in results]
            sections.append("Task notes:\n" + "\n".join(lines))

    if "global_notes" in types:
        results = _db.search_global_notes(query)
        if results:
            lines = [f"  [{n.note_type}] {n.title} ({n.id})" for n in results]
            sections.append("Global notes:\n" + "\n".join(lines))

    if "chunks" in types:
        results = _db.search_chunks(query, pid)
        if results:
            lines = [f"  ...{c.chunk_text[:80]}... (doc: {c.document_id})"
                     for c in results]
            sections.append("Document chunks:\n" + "\n".join(lines))

    return "\n\n".join(sections) if sections else "No results found."


@mcp.tool()
def semantic_search_tasks(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search for tasks using semantic similarity (vector search).

    Best for natural-language queries where exact keywords may not match.

    Args:
        query:      Natural language query.
        project_id: Optional project filter.
        limit:      Max results (default 5).
    """
    if not _emb.is_available():
        return _EMBEDDINGS_UNAVAILABLE
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    tasks = _db.semantic_search_tasks(query, pid, limit)
    if not tasks:
        return "No results found."
    lines = [f"[{t.status}] {'[!] ' if t.urgent else ''}{t.title} ({t.id})" for t in tasks]
    return f"{len(tasks)} result(s):\n" + "\n".join(lines)


@mcp.tool()
def semantic_search_decisions(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search for decisions using semantic similarity (vector search).

    Args:
        query:      Natural language query.
        project_id: Optional project filter.
        limit:      Max results (default 5).
    """
    if not _emb.is_available():
        return _EMBEDDINGS_UNAVAILABLE
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    decisions = _db.semantic_search_decisions(query, pid, limit)
    if not decisions:
        return "No results found."
    lines = [f"[{d.status}] {d.title} ({d.id})" for d in decisions]
    return f"{len(decisions)} result(s):\n" + "\n".join(lines)


@mcp.tool()
def semantic_search_notes(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search for notes using semantic similarity (vector search).

    Args:
        query:      Natural language query.
        project_id: Optional project filter.
        limit:      Max results (default 5).
    """
    if not _emb.is_available():
        return _EMBEDDINGS_UNAVAILABLE
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    notes = _db.semantic_search_notes(query, pid, limit)
    if not notes:
        return "No results found."
    lines = [f"[{n.note_type}] {n.title} ({n.id})" for n in notes]
    return f"{len(notes)} result(s):\n" + "\n".join(lines)


@mcp.tool()
def semantic_search_chunks(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search document chunks using semantic similarity.

    Args:
        query:      Natural language query.
        project_id: Optional project filter.
        limit:      Max results (default 5).
    """
    if not _emb.is_available():
        return _EMBEDDINGS_UNAVAILABLE
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    chunks = _db.semantic_search_chunks(query, pid, limit)
    if not chunks:
        return "No results found."
    lines = [f"[doc:{c.document_id}] chunk {c.chunk_index}: {c.chunk_text[:100]}..."
             for c in chunks]
    return f"{len(chunks)} result(s):\n" + "\n".join(lines)
