"""
server.py — FastMCP server exposing memory tools and resources.

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
        "IMPORTANT: Before calling any tool that requires a 'project' argument, you MUST "
        "establish which project is being discussed. Do this by: "
        "(1) inferring clearly from the user's message (e.g. they say 'in my auth service'), or "
        "(2) calling list_projects to show known projects and asking the user to confirm or name one. "
        "Never guess or assume a project name — always confirm if it is ambiguous. "
        "ORIENTATION (MANDATORY): Once the project is known, ALWAYS call `get_context` for "
        "category='orientation' and key='GET_STARTED' to understand core patterns. "
        "PROACTIVE LOGGING: As you finish milestones, fix bugs, or make architectural decisions, "
        "ALWAYS call `log_event` to record the change. Do not wait for user prompts. "
        "GIT WORKFLOW: Once a feature is complete and verified with tests, ALWAYS perform a git commit "
        "with a descriptive message and push to the remote repository. "
        "SEARCH BEFORE ACTING: When starting a new task, always call `search_insights` and "
        "`semantic_search_insights` with relevant keywords/natural language to discover past "
        "lessons, patterns, or 'gotchas'. "
        "TODO TRACKING: Use `add_todo`, `update_todo`, and `list_todos` to track future work. "
        "Each todo can store a detailed implementation plan in its `description` field. "
        "Use add_insight to save reusable lessons, skills, or patterns."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def set_context(
    project: str,
    key: str,
    value: str,
    category: str = "general",
    tags: Optional[List[str]] = None,
) -> str:
    """Store or update a context entry for a project.

    Use this to persist facts, decisions, config values, or any information that
    should survive across sessions (e.g. tech stack, architecture choices, team
    members, deadlines).

    Args:
        project:  Project identifier, e.g. "my-blog" or "auth-service".
        key:      Unique label for this piece of information, e.g. "language".
        value:    The value to store, e.g. "Python".
        category: Namespace/group (default "general"). Use e.g. "stack",
                  "decisions", "team", "config" to keep things organised.
        tags:     Optional list of tags for later filtering.
    """
    entry = _db.upsert_context(project, key, value, category, tags)
    return (
        f"Stored [{entry.project}/{entry.category}] "
        f"{entry.key} = {entry.value}  (updated: {entry.updated})"
    )


@mcp.tool()
def get_context(
    project: str,
    key: str,
    category: str = "general",
) -> str:
    """Retrieve a specific context entry by project, category, and key.

    Args:
        project:  Project identifier.
        key:      The key to look up.
        category: Category (default "general").
    """
    entry = _db.get_context(project, key, category)
    if not entry:
        return f"No entry found for project='{project}' category='{category}' key='{key}'"
    tag_str = ", ".join(entry.tags) if entry.tags else "none"
    return (
        f"{entry.key} = {entry.value}\n"
        f"category: {entry.category}\n"
        f"tags: {tag_str}\n"
        f"updated: {entry.updated}"
    )


@mcp.tool()
def list_contexts(
    project: str,
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> str:
    """List all context entries for a project, optionally filtered.

    Args:
        project:  Project identifier.
        category: Only return entries in this category.
        tag:      Only return entries that have this tag.
    """
    entries = _db.list_contexts(project, category, tag)
    if not entries:
        return "No context entries found."

    lines = [f"{len(entries)} entries for project '{project}':\n"]
    current_cat = None
    for e in entries:
        if e.category != current_cat:
            current_cat = e.category
            lines.append(f"[{current_cat}]")
        tag_str = f"  tags: {', '.join(e.tags)}" if e.tags else ""
        lines.append(f"  {e.key}: {e.value}{tag_str}")
    return "\n".join(lines)


@mcp.tool()
def delete_context(
    project: str,
    key: str,
    category: str = "general",
) -> str:
    """Delete a context entry.

    Args:
        project:  Project identifier.
        key:      The key to delete.
        category: Category (default "general").
    """
    deleted = _db.delete_context(project, key, category)
    if deleted:
        return f"Deleted [{project}/{category}] {key}"
    return f"Nothing found to delete: [{project}/{category}] {key}"


@mcp.tool()
def log_event(
    project: str,
    event_type: str,
    summary: str,
    detail: Optional[str] = None,
) -> str:
    """Append an event to the project timeline.

    Use for decisions, milestones, bugs found, or any notable occurrence.

    Args:
        project:    Project identifier.
        event_type: Short label, e.g. "decision", "milestone", "issue", "note".
        summary:    One-line description.
        detail:     Optional longer explanation.
    """
    event = _db.log_event(project, event_type, summary, detail)
    return f"Logged [{event.event_type}] {event.summary}  (at {event.timestamp})"


@mcp.tool()
def get_timeline(
    project: str,
    limit: int = 20,
) -> str:
    """Retrieve recent events from the project timeline.

    Args:
        project: Project identifier.
        limit:   Maximum number of events to return (default 20).
    """
    events = _db.get_timeline(project, limit)
    if not events:
        return "No events found."
    lines = [
        f"[{ev.timestamp[:10]} {ev.timestamp[11:16]}] {ev.event_type} — {ev.summary}"
        + (f"\n  {ev.detail}" if ev.detail else "")
        for ev in events
    ]
    return "\n".join(lines)


@mcp.tool()
def list_projects() -> str:
    """List all project names that have stored context.

    Call this when it is unclear which project the user is working on.
    Show the results to the user and ask them to confirm or name a project
    before proceeding with any other memory tool.
    """
    projects = _db.list_all_projects()
    if not projects:
        return "No projects found. Use set_context to store context for a new project."
    lines = [f"{len(projects)} known project(s):"] + [f"  - {p}" for p in projects]
    return "\n".join(lines)


@mcp.tool()
def summarize(project: str) -> str:
    """Export the full project context to Markdown and return a text summary.

    Writes ~/.mcp-memory/{project}/CONTEXT.md and returns a condensed view.
    Call this at the start of a session to quickly restore context.

    Args:
        project: Project identifier.
    """
    path = _export.export_to_markdown(project)
    summary_text = _export.build_summary_text(project)
    return f"Exported to: {path}\n\n{summary_text}"


@mcp.tool()
def add_insight(
    title: str,
    body: str,
    scope: str = "global",
    example: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """Add a reusable insight, lesson, or skill to the memory bank.

    Insights can be 'global' (apply everywhere) or scoped to a specific project.
    Use this to persist coding patterns, 'gotchas', or shared knowledge
    discovered during development.

    Args:
        title:   Short, descriptive name for the insight.
        body:    The lesson or pattern itself.
        scope:   'global' (default) or a specific project name.
        example: Optional code snippet or example illustrating the point.
        tags:    Optional list of tags for searching.
    """
    insight = _db.add_insight(title, body, scope, example, tags)
    return f"Saved insight '{insight.title}' in scope '{insight.scope}'"


@mcp.tool()
def list_insights(
    scope: Optional[str] = None,
    tag: Optional[str] = None,
) -> str:
    """Browse stored insights.

    If a project scope is provided, it returns both project-specific
    and global insights combined.

    Args:
        scope: Filter by scope ('global' or a project name).
        tag:   Only return insights with this tag.
    """
    insights = _db.list_insights(scope, tag)
    if not insights:
        return "No insights found."
    lines = [f"Found {len(insights)} insight(s):"]
    for i in insights:
        lines.append(f"[{i.scope}] {i.title}")
    return "\n".join(lines)


@mcp.tool()
def search_insights(query: str) -> str:
    """Search for insights by keyword in the title, body, or tags.
    
    Uses FTS5 for ranked results and match previews (snippets).

    Args:
        query: Search term.
    """
    insights = _db.search_insights(query)
    if not insights:
        return f"No insights matching '{query}' found."
    lines = [f"Search results for '{query}':"]
    for i in insights:
        preview = i.snippet if i.snippet else f"{i.body[:100]}..."
        lines.append(f"[{i.scope}] {i.title}\n  {preview}")
    return "\n".join(lines)


@mcp.tool()
def semantic_search_insights(query: str, scope: Optional[str] = None) -> str:
    """Search for insights using semantic similarity (vector search).
    
    Excellent for finding related concepts even if exact keywords don't match.

    Args:
        query: Search query (natural language).
        scope: Optional project name or 'global'.
    """
    insights = _db.semantic_search_insights(query, scope)
    if not insights:
        return f"No insights found semantically related to '{query}'."
    lines = [f"Semantic search results for '{query}':"]
    for i in insights:
        lines.append(f"[{i.scope}] {i.title}\n  {i.body[:150]}...")
    return "\n".join(lines)


@mcp.tool()
def search_contexts(query: str) -> str:
    """Search for context entries (facts, config, etc.) by keyword.

    Args:
        query: Search term.
    """
    entries = _db.search_contexts(query)
    if not entries:
        return f"No context entries matching '{query}' found."
    lines = [f"Search results for '{query}':"]
    for e in entries:
        lines.append(f"[{e.project}/{e.category}] {e.key}: {e.value}")
    return "\n".join(lines)


@mcp.tool()
def semantic_search_contexts(query: str, project: Optional[str] = None) -> str:
    """Search for context entries using semantic similarity (vector search).

    Args:
        query:   Search query.
        project: Optional project filter.
    """
    entries = _db.semantic_search_contexts(query, project)
    if not entries:
        return f"No context entries found semantically related to '{query}'."
    lines = [f"Semantic search results for '{query}':"]
    for e in entries:
        lines.append(f"[{e.project}/{e.category}] {e.key}: {e.value}")
    return "\n".join(lines)


@mcp.tool()
def add_todo(
    project: str,
    title: str,
    description: str,
    priority: str = "medium",
) -> str:
    """Add a new todo/task for a project.

    Use the description field for rich detail like implementation plans.

    Args:
        project:     Project identifier.
        title:       Short summary of the task.
        description: Detailed instructions or implementation plan.
        priority:    low, medium, or high (default: medium).
    """
    todo = _db.upsert_todo(project, title, description, priority=priority)
    return f"Created todo '{todo.title}' (ID: {todo.id}) in project '{project}'"


@mcp.tool()
def update_todo(
    todo_id: str,
    status: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """Update an existing todo's status, description, or other fields.

    Args:
        todo_id:     The unique ID of the todo.
        status:      pending, in_progress, completed, or cancelled.
        title:       Update the title.
        description: Update the detailed plan.
        priority:    Update the priority.
    """
    todo = _db.get_todo(todo_id)
    if not todo:
        return f"Todo with ID {todo_id} not found."

    todo = _db.upsert_todo(
        project=todo.project,
        title=title or todo.title,
        description=description or todo.description,
        status=status or todo.status,
        priority=priority or todo.priority,
        todo_id=todo_id,
    )
    return f"Updated todo '{todo.title}' (ID: {todo.id}). Status: {todo.status}"


@mcp.tool()
def list_todos(
    project: str,
    status: Optional[str] = None,
) -> str:
    """List todos for a project, optionally filtered by status.

    Args:
        project: Project identifier.
        status:  Filter by status (pending, in_progress, etc.).
    """
    todos = _db.list_todos(project, status)
    if not todos:
        return f"No todos found for project '{project}'" + (f" with status '{status}'" if status else "")

    lines = [f"Found {len(todos)} todo(s) for project '{project}':"]
    for t in todos:
        lines.append(f"[{t.status}] ({t.id}) {t.title} - Priority: {t.priority}")
    return "\n".join(lines)


@mcp.tool()
def get_todo(todo_id: str) -> str:
    """Retrieve the full details of a specific todo, including its description.

    Args:
        todo_id: The unique ID of the todo.
    """
    todo = _db.get_todo(todo_id)
    if not todo:
        return f"Todo with ID {todo_id} not found."
    
    return (
        f"Title: {todo.title}\n"
        f"ID: {todo.id}\n"
        f"Project: {todo.project}\n"
        f"Status: {todo.status}\n"
        f"Priority: {todo.priority}\n"
        f"Updated: {todo.updated}\n"
        f"---\n"
        f"Description:\n{todo.description}"
    )


@mcp.tool()
def search_todos(query: str) -> str:
    """Search for todos by keyword in the title or description.

    Args:
        query: Search term.
    """
    todos = _db.search_todos(query)
    if not todos:
        return f"No todos matching '{query}' found."
    
    lines = [f"Search results for todos matching '{query}':"]
    for t in todos:
        lines.append(f"[{t.project}/{t.status}] {t.title} (ID: {t.id})")
    return "\n".join(lines)


@mcp.tool()
def semantic_search_todos(query: str, project: Optional[str] = None) -> str:
    """Search for todos using semantic similarity (vector search).

    Args:
        query:   Search query.
        project: Optional project filter.
    """
    todos = _db.semantic_search_todos(query, project)
    if not todos:
        return f"No todos found semantically related to '{query}'."
    lines = [f"Semantic search results for '{query}':"]
    for t in todos:
        lines.append(f"[{t.project}/{t.status}] {t.title} ({t.id})")
    return "\n".join(lines)


@mcp.tool()
def delete_todo(todo_id: str) -> str:
    """Delete a todo entry.

    Args:
        todo_id: The unique ID of the todo to delete.
    """
    deleted = _db.delete_todo(todo_id)
    if deleted:
        return f"Deleted todo with ID {todo_id}"
    return f"Todo with ID {todo_id} not found."


# ── Resources ─────────────────────────────────────────────────────────────────


@mcp.resource("memory://project/{project}/summary")
def resource_summary(project: str) -> str:
    """Plain-text summary of all context for a project."""
    return _export.build_summary_text(project)


@mcp.resource("memory://project/{project}/timeline")
def resource_timeline(project: str) -> str:
    """Recent events for a project, one per line."""
    events = _db.get_timeline(project, 50)
    if not events:
        return "No events."
    return "\n".join(
        f"[{ev.timestamp[:10]} {ev.timestamp[11:16]}] {ev.event_type} — {ev.summary}"
        for ev in events
    )


@mcp.resource("memory://project/{project}/entities", mime_type="application/json")
def resource_entities(project: str) -> str:
    """JSON dump of all context entries for a project."""
    import json
    from dataclasses import asdict
    entries = _db.list_contexts(project)
    return json.dumps([asdict(e) for e in entries], indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    import os
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        # Note: SSE transport requires uvicorn to be installed
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
