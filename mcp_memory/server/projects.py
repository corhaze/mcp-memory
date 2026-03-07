from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

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

    Always provide a summary when creating a new project. It should be a stable
    high-level overview — goal, tech stack, and key architectural decisions.
    Write it as an introduction, not a status update. Current state is tracked
    through tasks, not the summary.

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
    Set the summary for a project.

    The summary is a stable, high-level introduction to the project — what it
    is, what it aims to achieve, the tech stack, and key architectural decisions.
    It should not be updated every session. Current project state is expressed
    through tasks, not the summary.

    Only update the summary when the project's fundamental nature or architecture
    changes, not when tasks are completed or work progresses.

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
