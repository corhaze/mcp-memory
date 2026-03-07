from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

# ── Project Notes ─────────────────────────────────────────────────────────────

@mcp.tool()
def create_note(
    project_id: str,
    title: str,
    note_text: str,
    note_type: str = "context",
) -> str:
    """
    Create a freeform operational note.

    Note types:
      - investigation: Research findings, debugging notes
      - implementation: How something was built
      - bug: A bug found or fixed
      - context: General project context
      - handover: Session handover notes

    Args:
        project_id: Project UUID or name.
        title:      Short note title.
        note_text:  The note content.
        note_type:  investigation, implementation, bug, context (default), handover.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    note = _db.create_note(proj.id, title, note_text, note_type)
    return f"Note created: '{note.title}' (id: {note.id}, type: {note.note_type})"


@mcp.tool()
def get_note(note_id: str) -> str:
    """
    Retrieve a specific note.

    Args:
        note_id: UUID of the note.
    """
    note = _db.get_note(note_id)
    if not note:
        return f"Note '{note_id}' not found."
    return f"[{note.note_type}] {note.title}\n\n{note.note_text}"


@mcp.tool()
def list_notes(
    project_id: str,
    note_type: Optional[str] = None,
) -> str:
    """
    List notes for a project.

    Args:
        project_id: Project UUID or name.
        note_type:  Filter by type — investigation, implementation, bug, context, handover.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    notes = _db.list_notes(proj.id, note_type)
    if not notes:
        return "No notes found."
    lines = [f"[{n.note_type}] {n.title} ({n.id})" for n in notes]
    return f"{len(notes)} note(s):\n" + "\n".join(lines)


@mcp.tool()
def update_note(
    note_id: str,
    title: Optional[str] = None,
    note_text: Optional[str] = None,
    note_type: Optional[str] = None,
) -> str:
    """
    Update a note's content or type.

    Args:
        note_id:   UUID of the note.
        title:     New title.
        note_text: New content.
        note_type: New type.
    """
    note = _db.update_note(note_id, title, note_text, note_type)
    if not note:
        return f"Note '{note_id}' not found."
    return f"Updated note '{note.title}'."


@mcp.tool()
def delete_note(note_id: str) -> str:
    """
    Delete a note.

    Args:
        note_id: UUID of the note.
    """
    ok = _db.delete_note(note_id)
    return "Note deleted." if ok else f"Note '{note_id}' not found."


# ── Global Notes ──────────────────────────────────────────────────────────────

@mcp.tool()
def create_global_note(
    title: str,
    note_text: str,
    note_type: str = "context",
) -> str:
    """
    Create a global note — not tied to any project.

    Global notes capture cross-project coding philosophy, universal style rules,
    and development standards that apply to all work. Keep them sparse and
    high-value. They are included in every get_working_context response.

    Note types: investigation, implementation, bug, context (default), handover.

    Args:
        title:     Short note title.
        note_text: The note content.
        note_type: investigation, implementation, bug, context, handover.
    """
    note = _db.create_global_note(title, note_text, note_type)
    return f"Global note created: '{note.title}' (id: {note.id}, type: {note.note_type})"


@mcp.tool()
def get_global_note(note_id: str) -> str:
    """
    Retrieve a specific global note.

    Args:
        note_id: UUID of the global note.
    """
    note = _db.get_global_note(note_id)
    if not note:
        return f"Global note '{note_id}' not found."
    return f"[{note.note_type}] {note.title}\n\n{note.note_text}"


@mcp.tool()
def list_global_notes(note_type: Optional[str] = None) -> str:
    """
    List all global notes (cross-project development philosophy and style rules).

    Call this at the start of every session alongside get_working_context.

    Args:
        note_type: Optional filter — investigation, implementation, bug, context, handover.
    """
    notes = _db.list_global_notes(note_type)
    if not notes:
        return "No global notes found."
    lines = [f"[{n.note_type}] {n.title} ({n.id})" for n in notes]
    return f"{len(notes)} global note(s):\n" + "\n".join(lines)


@mcp.tool()
def update_global_note(
    note_id: str,
    title: Optional[str] = None,
    note_text: Optional[str] = None,
    note_type: Optional[str] = None,
) -> str:
    """
    Update a global note's content or type.

    Args:
        note_id:   UUID of the global note.
        title:     New title.
        note_text: New content.
        note_type: New type.
    """
    note = _db.update_global_note(note_id, title, note_text, note_type)
    if not note:
        return f"Global note '{note_id}' not found."
    return f"Updated global note '{note.title}'."


@mcp.tool()
def delete_global_note(note_id: str) -> str:
    """
    Delete a global note.

    Args:
        note_id: UUID of the global note.
    """
    ok = _db.delete_global_note(note_id)
    return "Global note deleted." if ok else f"Global note '{note_id}' not found."


@mcp.tool()
def semantic_search_global_notes(query: str, limit: int = 5) -> str:
    """
    Search global notes using semantic similarity (vector search).

    Args:
        query: Natural language query.
        limit: Max results (default 5).
    """
    notes = _db.semantic_search_global_notes(query, limit)
    if not notes:
        return "No results found."
    lines = [f"[{n.note_type}] {n.title} ({n.id})" for n in notes]
    return f"{len(notes)} result(s):\n" + "\n".join(lines)


# ── Task Notes ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_task_note(
    task_id: str,
    title: str,
    note_text: str,
    note_type: str = "context",
) -> str:
    """
    Create a note scoped to a specific task.

    Task notes are distinct from project-level notes — they capture
    task-specific findings, attempts, and context rather than project-wide
    observations.

    Note types: investigation, implementation, bug, context (default), handover.

    Args:
        task_id:   UUID of the task.
        title:     Short note title.
        note_text: The note content.
        note_type: investigation, implementation, bug, context, handover.
    """
    task = _db.get_task(task_id)
    if not task:
        return f"Task '{task_id}' not found."
    note = _db.create_task_note(task.project_id, task_id, title, note_text, note_type)
    return f"Task note created: '{note.title}' (id: {note.id}, type: {note.note_type})"


@mcp.tool()
def get_task_note(note_id: str) -> str:
    """
    Retrieve a specific task note.

    Args:
        note_id: UUID of the task note.
    """
    note = _db.get_task_note(note_id)
    if not note:
        return f"Task note '{note_id}' not found."
    return f"[{note.note_type}] {note.title}\n\n{note.note_text}"


@mcp.tool()
def list_task_notes(task_id: str, note_type: Optional[str] = None) -> str:
    """
    List all notes attached to a task.

    Args:
        task_id:   UUID of the task.
        note_type: Optional filter — investigation, implementation, bug, context, handover.
    """
    notes = _db.list_task_notes(task_id, note_type)
    if not notes:
        return "No task notes found."
    lines = [f"[{n.note_type}] {n.title} ({n.id})" for n in notes]
    return f"{len(notes)} note(s):\n" + "\n".join(lines)


@mcp.tool()
def update_task_note(
    note_id: str,
    title: Optional[str] = None,
    note_text: Optional[str] = None,
    note_type: Optional[str] = None,
) -> str:
    """
    Update a task note's content or type.

    Args:
        note_id:   UUID of the task note.
        title:     New title.
        note_text: New content.
        note_type: New type.
    """
    note = _db.update_task_note(note_id, title, note_text, note_type)
    if not note:
        return f"Task note '{note_id}' not found."
    return f"Updated task note '{note.title}'."


@mcp.tool()
def delete_task_note(note_id: str) -> str:
    """
    Delete a task note.

    Args:
        note_id: UUID of the task note.
    """
    ok = _db.delete_task_note(note_id)
    return "Task note deleted." if ok else f"Task note '{note_id}' not found."


@mcp.tool()
def semantic_search_task_notes(
    query: str,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search task notes using semantic similarity (vector search).

    Args:
        query:      Natural language query.
        project_id: Optional project filter.
        task_id:    Optional task filter — restrict results to one task.
        limit:      Max results (default 5).
    """
    pid = None
    if project_id:
        proj = _db.get_project(project_id)
        pid = proj.id if proj else None
    notes = _db.semantic_search_task_notes(query, pid, task_id, limit)
    if not notes:
        return "No results found."
    lines = [f"[{n.note_type}] {n.title} (task: {n.task_id[:8]}, id: {n.id})" for n in notes]
    return f"{len(notes)} result(s):\n" + "\n".join(lines)
