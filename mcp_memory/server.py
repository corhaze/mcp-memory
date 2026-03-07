"""
server.py — FastMCP server for mcp-memory.

Hybrid relational + semantic retrieval model:
  1. get_working_context  — relational snapshot (summary + tasks + decisions)
  2. search               — FTS5 keyword search across entity types
  3. semantic_search_*    — vector search for fuzzy recall
  4. entity_links         — expand from one item to connected items

Run:
    python -m mcp_memory.server
    mcp-memory          (after pip install -e .)
"""
from __future__ import annotations

from typing import List, Optional
from mcp.server.fastmcp import FastMCP

import mcp_memory.db as _db
import mcp_memory.export as _export

mcp = FastMCP(
    name="mcp-memory",
    instructions=(
        "Use this server to persist and recall project context across sessions. "

        "SESSION START (MANDATORY): Always call `get_working_context` at the start of every "
        "session. It returns the current summary, open tasks, and linked decisions in one call. "
        "Never begin work without orienting yourself first. "

        "PROJECT SETUP (MANDATORY): When creating a new project, you MUST immediately: "
        "(1) call `create_project`, "
        "(2) create tasks for all known work with `create_task`, "
        "(3) call `add_project_summary` with a prose summary covering the goal, tech stack, "
        "key decisions, and current state. A project without a summary is incomplete. "

        "KEEPING RECORDS CURRENT (MANDATORY): You MUST update records as you work — do not "
        "batch updates to the end of a session. Specifically: "
        "- Move tasks to `in_progress` when you start them, `done` when complete. "
        "- Call `log_task_event` after each meaningful step on a task. "
        "- Call `create_decision` immediately when any architecture or design choice is made. "
        "- Call `create_note` when you discover something non-obvious (bugs, gotchas, findings). "
        "- Call `add_project_summary` at the END of every session to capture current state "
        "so the next agent can orient itself instantly. "
        "Failing to update records defeats the purpose of this server. "

        "RETRIEVAL ORDER: (1) get_working_context for relational state, "
        "(2) search/search_* for keyword lookup, "
        "(3) semantic_search_* for fuzzy recall when keywords fail, "
        "(4) get_links for graph traversal. "

        "TASKS: Status flow: open → in_progress → blocked/done/cancelled. "
        "Use parent_task_id for subtasks. Use blocked_by_task_id to express dependencies. "

        "DECISIONS: Use create_decision for durable architecture choices with rationale. "
        "Use supersede_decision when a decision is replaced — never silently overwrite. "

        "NOTES: Use create_note for operational memory. Types: investigation, implementation, "
        "bug, context, handover. Prefer notes over comments in code for cross-session findings. "

        "LINKS: Use create_link to connect related records (task→decision, note→task, etc). "
        "Link types: relates_to, implements, blocks, derived_from, explains, supersedes. "

        "CODE QUALITY (MANDATORY): Always prioritise clean, modular, idiomatic code. "
        "Write small, well-defined functions — one clear purpose per function. "
        "Follow language conventions: Python (PEP 8, type hints, dataclasses/Pydantic), "
        "JavaScript (const/let, async/await, descriptive names, no var). "
        "No premature abstraction — wait for a pattern to repeat before extracting. "
        "Readable over clever. If in doubt, keep it simple."
    ),
)


# ── Projects ──────────────────────────────────────────────────────────────────

@mcp.tool()
def create_project(
    name: str,
    description: Optional[str] = None,
    status: str = "active",
    summary: Optional[str] = None,
) -> str:
    """
    Create or update a project workspace.

    Always provide a summary when creating a new project. It should cover the
    goal, tech stack, key decisions, and current state so the next agent can
    orient itself instantly via get_working_context.

    Args:
        name:        Unique project name.
        description: Brief description of the project.
        status:      active, archived (default: active).
        summary:     Prose summary of the project's current state (strongly recommended).
    """
    proj = _db.create_project(name, description, status)
    if summary:
        _db.add_summary(proj.id, summary, summary_kind="current")
        return f"Project '{proj.name}' ready with summary (id: {proj.id})"
    return f"Project '{proj.name}' ready (id: {proj.id}) — consider adding a summary via add_project_summary"


@mcp.tool()
def get_project(name_or_id: str) -> str:
    """
    Get details for a project by name or ID.

    Args:
        name_or_id: Project name or UUID.
    """
    proj = _db.get_project(name_or_id)
    if not proj:
        return f"Project '{name_or_id}' not found."
    lines = [
        f"Project: {proj.name}",
        f"ID: {proj.id}",
        f"Status: {proj.status}",
        f"Description: {proj.description or '—'}",
        f"Created: {proj.created_at[:10]}",
    ]
    return "\n".join(lines)


@mcp.tool()
def list_projects(status: Optional[str] = None) -> str:
    """
    List all known projects.

    Call this when it is unclear which project the user is working on.
    Show the results to the user and confirm before proceeding.

    Args:
        status: Optional filter — active or archived.
    """
    projects = _db.list_projects(status)
    if not projects:
        return "No projects found."
    lines = [f"  - {p.name} [{p.status}]  (id: {p.id})" for p in projects]
    return f"{len(projects)} project(s):\n" + "\n".join(lines)


@mcp.tool()
def update_project(
    name_or_id: str,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """
    Update a project's description or status.

    Args:
        name_or_id:  Project name or UUID.
        description: New description.
        status:      active or archived.
    """
    proj = _db.update_project(name_or_id, description, status)
    if not proj:
        return f"Project '{name_or_id}' not found."
    return f"Updated project '{proj.name}'."


# ── Project Summaries ─────────────────────────────────────────────────────────

@mcp.tool()
def add_project_summary(
    project_id: str,
    summary_text: str,
    summary_kind: str = "current",
) -> str:
    """
    Add a rolling summary for a project.

    Use this to capture the current state of a project for cheap rehydration
    at the start of the next session.

    Args:
        project_id:   Project UUID or name.
        summary_text: The summary content.
        summary_kind: current (default), milestone, or handover.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    s = _db.add_summary(proj.id, summary_text, summary_kind)
    return f"Summary added (id: {s.id}, kind: {s.summary_kind})"


@mcp.tool()
def get_project_summary(project_id: str) -> str:
    """
    Get the current summary for a project.

    Args:
        project_id: Project UUID or name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    s = _db.get_current_summary(proj.id)
    if not s:
        return f"No summary found for project '{proj.name}'."
    return f"[{proj.name} — {s.created_at[:10]}]\n\n{s.summary_text}"


@mcp.tool()
def list_project_summaries(project_id: str, summary_kind: Optional[str] = None) -> str:
    """
    List summaries for a project.

    Args:
        project_id:   Project UUID or name.
        summary_kind: Optional filter — current, milestone, handover.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    summaries = _db.list_summaries(proj.id, summary_kind)
    if not summaries:
        return "No summaries found."
    lines = [f"  [{s.summary_kind}] {s.created_at[:10]} — {s.summary_text[:80]}..." for s in summaries]
    return f"{len(summaries)} summary(ies):\n" + "\n".join(lines)


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
        lines.append(f"[{t.status}][{t.priority}] {t.title} ({t.id}){child_hint}")
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
        priority:           low, medium, high.
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


# ── Decisions ─────────────────────────────────────────────────────────────────

@mcp.tool()
def create_decision(
    project_id: str,
    title: str,
    decision_text: str,
    rationale: Optional[str] = None,
    status: str = "active",
) -> str:
    """
    Record a durable architecture or workflow decision.

    Decisions are one of the highest-value memory types. Use them for:
    - Technology choices
    - API contracts
    - Data model choices
    - Process decisions

    Args:
        project_id:    Project UUID or name.
        title:         Short decision title.
        decision_text: The decision itself.
        rationale:     Why this decision was made.
        status:        active (default), draft, superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    dec = _db.create_decision(proj.id, title, decision_text, rationale, status)
    return f"Decision created: '{dec.title}' (id: {dec.id})"


@mcp.tool()
def get_decision(decision_id: str) -> str:
    """
    Retrieve a specific decision.

    Args:
        decision_id: UUID of the decision.
    """
    dec = _db.get_decision(decision_id)
    if not dec:
        return f"Decision '{decision_id}' not found."
    lines = [
        f"Decision: {dec.title}",
        f"Status: {dec.status}",
        f"",
        dec.decision_text,
    ]
    if dec.rationale:
        lines += ["", f"Rationale: {dec.rationale}"]
    if dec.supersedes_decision_id:
        lines.append(f"Supersedes: {dec.supersedes_decision_id}")
    return "\n".join(lines)


@mcp.tool()
def list_decisions(
    project_id: str,
    status: Optional[str] = None,
) -> str:
    """
    List decisions for a project.

    Args:
        project_id: Project UUID or name.
        status:     Filter by status — active, draft, superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    decisions = _db.list_decisions(proj.id, status)
    if not decisions:
        return "No decisions found."
    lines = [f"[{d.status}] {d.title} ({d.id})" for d in decisions]
    return f"{len(decisions)} decision(s):\n" + "\n".join(lines)


@mcp.tool()
def update_decision(
    decision_id: str,
    title: Optional[str] = None,
    decision_text: Optional[str] = None,
    rationale: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """
    Update a decision's fields.

    Args:
        decision_id:   UUID of the decision.
        title:         New title.
        decision_text: New decision text.
        rationale:     New rationale.
        status:        active, draft, or superseded.
    """
    dec = _db.update_decision(decision_id, title, decision_text, rationale, status)
    if not dec:
        return f"Decision '{decision_id}' not found."
    return f"Updated decision '{dec.title}' — status: {dec.status}"


@mcp.tool()
def supersede_decision(
    old_decision_id: str,
    project_id: str,
    title: str,
    decision_text: str,
    rationale: Optional[str] = None,
) -> str:
    """
    Create a new decision that supersedes an existing one.
    The old decision is automatically marked 'superseded'.

    Args:
        old_decision_id: UUID of the decision being replaced.
        project_id:      Project UUID or name.
        title:           Title of the new decision.
        decision_text:   The new decision text.
        rationale:       Why the old decision was superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    new_dec = _db.supersede_decision(old_decision_id, proj.id, title, decision_text, rationale)
    return (f"Decision superseded. New decision: '{new_dec.title}' (id: {new_dec.id}). "
            f"Old decision {old_decision_id[:8]} marked superseded.")


# ── Notes ─────────────────────────────────────────────────────────────────────

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


# ── Entity Links ──────────────────────────────────────────────────────────────

@mcp.tool()
def create_link(
    project_id: str,
    from_entity_type: str,
    from_entity_id: str,
    link_type: str,
    to_entity_type: str,
    to_entity_id: str,
) -> str:
    """
    Create a typed link between any two entities.

    Link types: relates_to, implements, blocks, derived_from, explains, supersedes.
    Entity types: task, decision, note, document, summary.

    Example: link a task to the decision it implements:
      create_link(proj, 'task', task_id, 'implements', 'decision', dec_id)

    Args:
        project_id:       Project UUID or name.
        from_entity_type: Source entity type.
        from_entity_id:   Source entity UUID.
        link_type:        Relationship type.
        to_entity_type:   Target entity type.
        to_entity_id:     Target entity UUID.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    lnk = _db.create_link(proj.id, from_entity_type, from_entity_id,
                           link_type, to_entity_type, to_entity_id)
    return (f"Link created: {from_entity_type}/{from_entity_id[:8]} "
            f"--[{link_type}]--> {to_entity_type}/{to_entity_id[:8]} (id: {lnk.id})")


@mcp.tool()
def get_links(
    entity_type: str,
    entity_id: str,
    direction: str = "both",
) -> str:
    """
    Get all links for an entity.

    Args:
        entity_type: task, decision, note, document, summary.
        entity_id:   UUID of the entity.
        direction:   from, to, or both (default).
    """
    links = _db.get_links_for(entity_type, entity_id, direction)
    if not links:
        return "No links found."
    lines = []
    for lnk in links:
        lines.append(
            f"{lnk.from_entity_type}/{lnk.from_entity_id} "
            f"--[{lnk.link_type}]--> "
            f"{lnk.to_entity_type}/{lnk.to_entity_id}"
        )
    return f"{len(links)} link(s):\n" + "\n".join(lines)


# ── Tags ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_tag(project_id: str, name: str) -> str:
    """
    Create a tag for a project.

    Args:
        project_id: Project UUID or name.
        name:       Tag name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tag = _db.create_tag(proj.id, name)
    return f"Tag '{tag.name}' ready (id: {tag.id})"


@mcp.tool()
def tag_entity(
    project_id: str,
    tag_name: str,
    entity_type: str,
    entity_id: str,
) -> str:
    """
    Apply a tag to any entity.

    Args:
        project_id:  Project UUID or name.
        tag_name:    Tag name (will be created if it doesn't exist).
        entity_type: task, decision, note, document.
        entity_id:   UUID of the entity.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tag = _db.create_tag(proj.id, tag_name)
    _db.tag_entity(tag.id, entity_type, entity_id)
    return f"Tagged {entity_type}/{entity_id[:8]} with '{tag_name}'"


@mcp.tool()
def list_tags(project_id: str) -> str:
    """
    List all tags for a project.

    Args:
        project_id: Project UUID or name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tags = _db.list_tags(proj.id)
    if not tags:
        return "No tags found."
    return f"{len(tags)} tag(s): " + ", ".join(t.name for t in tags)


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

    types = entity_types or ["tasks", "decisions", "notes", "chunks"]
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


# ── Working Context ───────────────────────────────────────────────────────────

@mcp.tool()
def get_working_context(project_id: str) -> str:
    """
    Get a compact working context packet for a project.

    CALL THIS AT THE START OF EVERY SESSION. It returns:
      1. Current project summary
      2. Open and in-progress tasks
      3. Decisions linked to active tasks
      4. Active project-wide decisions
      5. Recent notes

    This is the prescribed retrieval flow — relational-first, cheap, and complete.

    Args:
        project_id: Project UUID or name.
    """
    ctx = _db.get_working_context(project_id)
    if "error" in ctx:
        return ctx["error"]

    proj = ctx["project"]
    lines = [
        f"# Working Context: {proj['name']}",
        f"Status: {proj['status']}",
        f"Description: {proj.get('description') or '—'}",
        "",
    ]

    if ctx["summary"]:
        lines += ["## Current Summary", ctx["summary"], ""]

    if ctx["active_tasks"]:
        lines.append("## Active Tasks")
        for t in ctx["active_tasks"]:
            na = f" → {t['next_action']}" if t.get("next_action") else ""
            urgent_flag = "[!] " if t.get("urgent") else ""
            lines.append(f"  [{t['status']}] {urgent_flag}{t['title']} ({t['id'][:8]}){na}")
        lines.append("")

    if ctx["linked_decisions"]:
        lines.append("## Linked Decisions (from active tasks)")
        for d in ctx["linked_decisions"]:
            lines.append(f"  {d['title']}: {d['decision_text'][:100]}")
        lines.append("")

    if ctx["active_decisions"]:
        lines.append("## Active Decisions")
        for d in ctx["active_decisions"]:
            lines.append(f"  [{d['status']}] {d['title']} ({d['id'][:8]})")
        lines.append("")

    if ctx["recent_notes"]:
        lines.append("## Recent Notes")
        for n in ctx["recent_notes"]:
            lines.append(f"  [{n['note_type']}] {n['title']} ({n['id'][:8]})")
        lines.append("")

    return "\n".join(lines)


# ── Summarize / Export ────────────────────────────────────────────────────────

@mcp.tool()
def summarize(project_id: str) -> str:
    """
    Export the full project context to Markdown and return a summary.

    Writes ~/.mcp-memory/{project}/CONTEXT.md and returns a condensed view.
    Call this at the start of a session for deep context, or use
    get_working_context for a faster relational snapshot.

    Args:
        project_id: Project UUID or name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    path = _export.export_to_markdown(proj.name, proj.id)
    text = _export.build_summary_text(proj.name, proj.id)
    return f"Exported to {path}\n\n{text}"


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("memory://{project_id}/context")
def resource_context(project_id: str) -> str:
    """Working context for a project."""
    return _db.get_working_context.__doc__ or get_working_context(project_id)


@mcp.resource("memory://{project_id}/tasks")
def resource_tasks(project_id: str) -> str:
    """Open tasks for a project."""
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tasks = _db.list_tasks(proj.id, status=None, parent_task_id="_root_")
    lines = [f"[{t.status}] {t.title} ({t.id})" for t in tasks]
    return "\n".join(lines) if lines else "No tasks."


@mcp.resource("memory://{project_id}/decisions")
def resource_decisions(project_id: str) -> str:
    """Active decisions for a project."""
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    decisions = _db.list_decisions(proj.id, status="active")
    lines = [f"{d.title}: {d.decision_text[:100]}" for d in decisions]
    return "\n".join(lines) if lines else "No active decisions."


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="mcp-memory server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
