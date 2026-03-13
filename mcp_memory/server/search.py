from typing import List, Optional
from .mcp import mcp
import mcp_memory.db as _db
from mcp_memory import embeddings as _emb
from mcp_memory.repository.connection import get_conn
from mcp_memory.repository.search import reembed_all as _reembed_all

_EMBEDDINGS_UNAVAILABLE = (
    "Semantic search is unavailable — embedding model not loaded. "
    "Use the `search` tool for keyword search instead."
)

def _note_label(n) -> str:
    return f"[{n.note_type}] " if n.note_type else ""

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
            lines = [f"  {_note_label(n)}{n.title} ({n.id})" for n in results]
            sections.append("Notes:\n" + "\n".join(lines))

    if "task_notes" in types:
        results = _db.search_task_notes(query, pid)
        if results:
            lines = [f"  {_note_label(n)}{n.title} (task: {n.task_id[:8]}, id: {n.id})"
                     for n in results]
            sections.append("Task notes:\n" + "\n".join(lines))

    if "global_notes" in types:
        results = _db.search_global_notes(query)
        if results:
            lines = [f"  {_note_label(n)}{n.title} ({n.id})" for n in results]
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
    lines = [f"{_note_label(n)}{n.title} ({n.id})" for n in notes]
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


@mcp.tool()
def semantic_search_all(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Search tasks, decisions, notes, task notes, and global notes in a single
    call using semantic similarity. Returns the top results across all entity
    types ranked by relevance score.

    Prefer this over calling semantic_search_tasks/decisions/notes separately.
    Falls back gracefully when embeddings are unavailable.

    Args:
        query:      Natural language query.
        project_id: Optional project filter (UUID or name).
        limit:      Max total results across all types (default 10).
    """
    if not _emb.is_available():
        return _EMBEDDINGS_UNAVAILABLE
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    results = _db.semantic_search_all(query, pid, limit)
    if not results:
        return "No results found."

    lines = []
    for r in results:
        entity_type = r["entity_type"]
        score = r["score"]
        entity = r["entity"]

        if entity_type == "task":
            lines.append(f"[task] {entity.title} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            next_part = f" | Next: {entity.next_action}" if entity.next_action else ""
            lines.append(f"  Status: {entity.status}{next_part}")
        elif entity_type == "decision":
            lines.append(f"[decision] {entity.title} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            lines.append(f"  Status: {entity.status}")
        elif entity_type == "note":
            lines.append(f"[note] {entity.title} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            if entity.note_type:
                lines.append(f"  Type: {entity.note_type}")
        elif entity_type == "task_note":
            lines.append(f"[task_note] {entity.title} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            type_part = f"Type: {entity.note_type} | " if entity.note_type else ""
            lines.append(f"  {type_part}Task: {entity.task_id[:8]}")
        elif entity_type == "global_note":
            lines.append(f"[global_note] {entity.title} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            if entity.note_type:
                lines.append(f"  Type: {entity.note_type}")
        else:
            lines.append(f"[{entity_type}] {entity_type} (score: {score:.2f}, id: {str(entity.id)[:8]})")
            lines.append(f"  (unknown entity type)")

    return f"{len(results)} result(s):\n" + "\n".join(lines)


@mcp.tool()
def reembed(force: bool = False) -> str:
    """
    Regenerate embeddings for entities that are missing them.

    Useful after importing a database created without embeddings enabled,
    or after changing the embedding model.

    Args:
        force: If True, regenerate embeddings for all entities, not just
               those that are missing them. Defaults to False.
    """
    if not _emb.is_available():
        return (
            "Embeddings are unavailable — set MCP_MEMORY_ENABLE_EMBEDDINGS=1 "
            "and restart the server to use this tool."
        )
    with get_conn() as conn:
        counts = _reembed_all(conn, force=force)
    total = sum(counts.values())
    lines = [f"  {entity_type}: {n}" for entity_type, n in counts.items() if n > 0]
    summary = "\n".join(lines) if lines else "  (nothing to embed)"
    return f"Re-embedded {total} entity/entities:\n{summary}"
