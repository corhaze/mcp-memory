"""
export.py — render project context to a human-readable Markdown file.
"""

from pathlib import Path
from datetime import datetime, timezone
from .db import (
    get_project, get_current_summary, list_tasks, get_task_tree,
    list_decisions, list_notes, get_links_for
)


def _export_dir(project_name: str) -> Path:
    p = Path.home() / ".mcp-memory" / project_name
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_to_markdown(project_name: str, project_id: str) -> Path:
    """Write CONTEXT.md for a project and return the path."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    proj = get_project(project_id)

    lines = [
        f"# Context: {project_name}",
        f"",
        f"_Generated: {now}_",
        f"",
    ]

    if proj:
        lines += [
            f"**Status:** {proj.status}",
            f"**Description:** {proj.description or '—'}",
            "",
        ]

    # Current summary
    summary = get_current_summary(project_id)
    if summary:
        lines += ["## Summary", "", summary.summary_text, ""]

    # Tasks (tree structure)
    task_tree = get_task_tree(project_id)
    open_tasks = [t for t in task_tree if t.status in ("open", "in_progress", "blocked")]
    done_tasks = [t for t in task_tree if t.status == "done"]

    if open_tasks:
        lines += ["## Active Tasks", ""]
        for t in open_tasks:
            if t.urgent:
                bullet = f"- **[URGENT]** [{t.status}] {t.title}"
            else:
                bullet = f"- **[{t.status}]** {t.title}"
            if t.next_action:
                bullet += f" → _{t.next_action}_"
            lines.append(bullet)
            for st in t.subtasks:
                lines.append(f"  - [{st.status}] {st.title}")
        lines.append("")

    if done_tasks:
        lines += ["## Completed Tasks", ""]
        for t in done_tasks:
            done_at = t.completed_at[:10] if t.completed_at else "?"
            lines.append(f"- ~~{t.title}~~ (done {done_at})")
        lines.append("")

    # Decisions
    decisions = list_decisions(project_id, status="active")
    if decisions:
        lines += ["## Active Decisions", ""]
        for d in decisions:
            lines.append(f"### {d.title}")
            lines.append(d.decision_text)
            if d.rationale:
                lines.append(f"_Rationale: {d.rationale}_")
            lines.append("")

    # Recent notes by type
    notes = list_notes(project_id)
    if notes:
        lines += ["## Notes", ""]
        by_type: dict = {}
        for n in notes:
            by_type.setdefault(n.note_type, []).append(n)
        for ntype, typed_notes in sorted(by_type.items()):
            lines.append(f"### {ntype.capitalize()}")
            for n in typed_notes[:5]:
                lines.append(f"- **{n.title}**: {n.note_text[:120]}...")
            lines.append("")

    out = _export_dir(project_name) / "CONTEXT.md"
    out.write_text("\n".join(lines))
    return out


def build_summary_text(project_name: str, project_id: str) -> str:
    """Return a compact plain-text summary suitable for an LLM tool response."""
    summary = get_current_summary(project_id)
    open_tasks = list_tasks(project_id, status="open", parent_task_id="_root_")
    in_progress = list_tasks(project_id, status="in_progress", parent_task_id="_root_")
    decisions = list_decisions(project_id, status="active")
    notes = list_notes(project_id)

    active_tasks = open_tasks + in_progress

    lines = [
        f"Project: {project_name}",
        f"{len(active_tasks)} open task(s) | {len(decisions)} active decision(s) | {len(notes)} note(s)",
        "",
    ]

    if summary:
        lines += ["Summary:", summary.summary_text, ""]

    if active_tasks:
        lines.append("Open tasks:")
        for t in active_tasks[:5]:
            na = f" → {t.next_action}" if t.next_action else ""
            lines.append(f"  [{t.status}] {t.title}{na}")
        lines.append("")

    if decisions:
        lines.append("Active decisions:")
        for d in decisions[:5]:
            lines.append(f"  {d.title}")
        lines.append("")

    return "\n".join(lines)
