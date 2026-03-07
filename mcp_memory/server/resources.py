from .mcp import mcp
import mcp_memory.db as _db

# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("memory://{project_id}/context")
def resource_context(project_id: str) -> str:
    """Working context for a project."""
    # This matches the pattern in server.py which was:
    # return _db.get_working_context.__doc__ or get_working_context(project_id)
    # However, get_working_context is now in .context. We can import it or just 
    # call _db.get_working_context if we want the docstring, but here it likely 
    # meant to return the content.
    from .context import get_working_context
    return get_working_context(project_id)


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
