from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

# ── Tasks ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_task(
    project_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "open",
    urgent: bool = False,
    parent_task_id: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> str:
    """
    Create a new task for a project.

    Tasks have status: open, in_progress, blocked, done, cancelled.
    Use parent_task_id to create subtasks.
    Use the description field for detailed implementation plans.

    Args:
        project_id:         Project UUID or name.
        title:              Short task title.
        description:        Detailed plan or context.
        status:             open (default), in_progress, blocked, done, cancelled.
        urgent:             Boolean flag indicating high urgency.
        parent_task_id:     UUID of parent task (for subtasks).
        assigned_agent:     Agent identifier.
        blocked_by_task_id: UUID of blocking task.
        next_action:        Immediate next step.
        due_at:             ISO 8601 datetime.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    task = _db.create_task(
        proj.id, title, description, status, urgent,
        parent_task_id, assigned_agent, blocked_by_task_id, next_action, due_at,
    )
    return f"Task created: '{task.title}' (id: {task.id}, status: {task.status})"


@mcp.tool()
def get_task(task_id: str) -> str:
    """
    Retrieve the full details of a task, including subtasks and events.

    Args:
        task_id: The UUID of the task.
    """
    task = _db.get_task(task_id)
    if not task:
        return f"Task '{task_id}' not found."
    lines = [
        f"Task: {task.title}",
        f"ID: {task.id}",
        f"Status: {task.status}  Urgent: {'Yes' if task.urgent else 'No'}",
        f"Description: {task.description or '—'}",
    ]
    if task.next_action:
        lines.append(f"Next action: {task.next_action}")
    if task.blocked_by_task_id:
        lines.append(f"Blocked by: {task.blocked_by_task_id}")
    if task.parent_task_id:
        lines.append(f"Parent: {task.parent_task_id}")
    if task.subtasks:
        lines.append(f"\nSubtasks ({len(task.subtasks)}):")
        for st in task.subtasks:
            lines.append(f"  [{st.status}] {st.title} ({st.id})")
    events = _db.get_task_events(task_id, limit=10)
    if events:
        lines.append(f"\nRecent events ({len(events)}):")
        for ev in events:
            lines.append(f"  [{ev.created_at[:10]}] {ev.event_type}: {ev.event_note or ''}")
    notes = _db.list_task_notes(task_id)
    if notes:
        lines.append(f"\nNotes ({len(notes)}):")
        for n in notes:
            lines.append(f"  [{n.note_type}] {n.title} ({n.id})")
    return "\n".join(lines)


@mcp.tool()
def list_tasks(
    project_id: str,
    status: Optional[str] = None,
    parent_task_id: Optional[str] = None,
) -> str:
    """
    List tasks for a project.

    Args:
        project_id:    Project UUID or name.
        status:        Filter by status (open, in_progress, blocked, done, cancelled).
        parent_task_id: Filter by parent task UUID. Omit for top-level tasks only.
                        Pass 'all' to list all tasks regardless of parent.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    effective_parent = None if parent_task_id == "all" else (parent_task_id or "_root_")
    tasks = _db.list_tasks(proj.id, status, effective_parent)
    if not tasks:
        return "No tasks found."
    lines = []
    for t in tasks:
        child_hint = f"  [{len(t.subtasks)} subtask(s)]" if t.subtasks else ""
        urgent_flag = "[!] " if t.urgent else ""
        lines.append(f"[{t.status}] {urgent_flag}{t.title} ({t.id}){child_hint}")
    return f"{len(tasks)} task(s):\n" + "\n".join(lines)


@mcp.tool()
def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    urgent: Optional[bool] = None,
    assigned_agent: Optional[str] = None,
    blocked_by_task_id: Optional[str] = None,
    next_action: Optional[str] = None,
    due_at: Optional[str] = None,
) -> str:
    """
    Update a task's fields. Only provided fields are changed.
    Automatically logs a task_event for the change.
    Setting status to 'done' records completed_at.

    Args:
        task_id:            UUID of the task.
        title:              New title.
        description:        New description.
        status:             open, in_progress, blocked, done, cancelled.
        urgent:             Boolean flag indicating high urgency.
        assigned_agent:     Agent identifier.
        blocked_by_task_id: Blocking task UUID.
        next_action:        Next immediate step.
        due_at:             ISO 8601 datetime.
    """
    task = _db.update_task(task_id, title, description, status, urgent,
                           assigned_agent, blocked_by_task_id, next_action, due_at)
    if not task:
        return f"Task '{task_id}' not found."
    return f"Updated task '{task.title}' — status: {task.status}"


@mcp.tool()
def delete_task(task_id: str) -> str:
    """
    Delete a task and all its events.

    Args:
        task_id: UUID of the task.
    """
    ok = _db.delete_task(task_id)
    return "Task deleted." if ok else f"Task '{task_id}' not found."


# ── Task Events ───────────────────────────────────────────────────────────────

@mcp.tool()
def log_task_event(
    task_id: str,
    event_type: str,
    event_note: Optional[str] = None,
) -> str:
    """
    Append an event to a task's history.

    Event types: created, started, blocked, unblocked, updated, completed, cancelled.
    Use this to record why a task changed state, not just that it did.

    Args:
        task_id:    UUID of the task.
        event_type: Short label for the event.
        event_note: Optional explanation or context.
    """
    ev = _db.log_task_event(task_id, event_type, event_note)
    return f"Logged [{ev.event_type}] on task {task_id[:8]} at {ev.created_at[:10]}"


@mcp.tool()
def get_task_events(task_id: str, limit: int = 20) -> str:
    """
    Retrieve the history of a task.

    Args:
        task_id: UUID of the task.
        limit:   Max events to return (default 20).
    """
    events = _db.get_task_events(task_id, limit)
    if not events:
        return f"No events found for task '{task_id}'."
    lines = [f"[{ev.created_at[:16]}] {ev.event_type}: {ev.event_note or ''}"
             for ev in events]
    return f"{len(events)} event(s):\n" + "\n".join(lines)
