"""
export.py — render project context to a human-readable Markdown file.
"""

from pathlib import Path
from datetime import datetime, timezone
from .db import list_contexts, get_timeline, list_todos


def _export_dir(project: str) -> Path:
    p = Path.home() / ".mcp-memory" / project
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_to_markdown(project: str) -> Path:
    """Write CONTEXT.md for *project* and return the path."""
    contexts = list_contexts(project)
    events = get_timeline(project, limit=20)
    todos = list_todos(project)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Context: {project}",
        f"",
        f"_Generated: {now}_",
        f"",
    ]

    # Group by category
    categories: list[str] = sorted({e.category for e in contexts})
    for cat in categories:
        lines.append(f"## {cat.capitalize()}")
        lines.append("")
        for e in contexts:
            if e.category != cat:
                continue
            tag_str = f"  _{', '.join(e.tags)}_" if e.tags else ""
            lines.append(f"- **{e.key}**: {e.value}{tag_str}")
        lines.append("")

    if todos:
        lines += [
            "## Tasks",
            "",
            "| Status | Priority | Title |",
            "|---|---|---|",
        ]
        for t in todos:
            lines.append(f"| {t.status} | {t.priority} | {t.title} |")
        lines.append("")

    if events:
        lines += [
            "## Timeline",
            "",
            "| Date | Type | Summary |",
            "|---|---|---|",
        ]
        for ev in events:
            date = ev.timestamp[:10]
            time = ev.timestamp[11:16]
            lines.append(f"| {date} {time} | {ev.event_type} | {ev.summary} |")
        lines.append("")

    out = _export_dir(project) / "CONTEXT.md"
    out.write_text("\n".join(lines))
    return out


def build_summary_text(project: str) -> str:
    """Return a compact plain-text summary suitable for an LLM tool response."""
    contexts = list_contexts(project)
    events = get_timeline(project, limit=5)
    todos = list_todos(project, status="pending") + list_todos(project, status="in_progress")

    lines = [
        f"Project: {project}",
        f"{len(contexts)} context entries",
        f"{len(todos)} open tasks",
        "",
    ]

    categories = sorted({e.category for e in contexts})
    for cat in categories:
        lines.append(f"[{cat}]")
        for e in contexts:
            if e.category == cat:
                lines.append(f"  {e.key}: {e.value}")

    if events:
        lines.append("")
        lines.append("Recent events:")
        for ev in events:
            lines.append(
                f"  [{ev.timestamp[:10]} {ev.timestamp[11:16]}] {ev.event_type} — {ev.summary}"
            )

    return "\n".join(lines)
