from .mcp import mcp
import mcp_memory.db as _db
import mcp_memory.export as _export

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
            lines.append(f"  [{d['status']}] {d['title']} ({d['id'][:8]})")
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

    if ctx.get("global_notes"):
        lines.append("## Global Notes (cross-project philosophy — read before implementing)")
        for n in ctx["global_notes"]:
            lines.append(f"\n### [{n['note_type']}] {n['title']} ({n['id'][:8]})")
            lines.append(n["note_text"])
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
