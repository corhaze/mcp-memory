"""
cli.py — Command-line interface for mcp-memory.

Usage:
    mcp-memory-cli project create --name my-app --description "..."
    mcp-memory-cli project list
    mcp-memory-cli task create --project my-app --title "Fix bug" --priority high
    mcp-memory-cli task list --project my-app --status open
    mcp-memory-cli decision add --project my-app --title "Use SQLite" --text "..."
    mcp-memory-cli note add --project my-app --title "Finding" --text "..."
    mcp-memory-cli search "keyword query" --project my-app
    mcp-memory-cli search "keyword" --semantic
"""

import click
import json
from . import db as _db



@click.group()
def main():
    """mcp-memory CLI — manage projects, tasks, decisions, and notes."""
    pass


# ── Project commands ───────────────────────────────────────────────────────────

@main.group()
def project():
    """Manage projects."""
    pass


@project.command("create")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--description", "-d", help="Project description")
@click.option("--status", default="active", help="Status (active|archived)")
@click.option("--summary", "-s", help="Initial project summary (goal, stack, current state)")
def project_create(name, description, status, summary):
    """Create or update a project."""
    proj = _db.create_project(name, description, status)
    if summary:
        _db.add_summary(proj.id, summary, summary_kind="current")
        click.echo(f"OK: Project '{proj.name}' created with summary (id: {proj.id})")
    else:
        click.echo(f"OK: Project '{proj.name}' (id: {proj.id})")


@project.command("summary")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--text", "-t", required=True, help="Summary text")
@click.option("--kind", "-k", default="current", help="Summary kind: current, milestone, handover")
def project_summary(project, text, kind):
    """Add or update the project summary."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    s = _db.add_summary(proj.id, text, summary_kind=kind)
    click.echo(f"OK: Summary added to '{proj.name}' (kind: {s.summary_kind}, id: {s.id[:8]})")


@project.command("list")
@click.option("--status", help="Filter by status")
def project_list(status):
    """List all projects."""
    projects = _db.list_projects(status)
    if not projects:
        click.echo("No projects found.")
        return
    for p in projects:
        click.echo(f"  [{p.status}] {p.name}  ({p.id})")


@project.command("context")
@click.option("--project", "-p", required=True, help="Project name or ID")
def project_context(project):
    """Show working context for a project."""
    ctx = _db.get_working_context(project)
    if "error" in ctx:
        click.echo(ctx["error"])
        return
    click.echo(f"Project: {ctx['project']['name']} [{ctx['project']['status']}]")
    if ctx["summary"]:
        click.echo(f"\nSummary:\n{ctx['summary']}")
    if ctx["active_tasks"]:
        click.echo(f"\nActive tasks ({len(ctx['active_tasks'])}):")
        for t in ctx["active_tasks"]:
            click.echo(f"  [{t['status']}][{t['priority']}] {t['title']}")
    if ctx["active_decisions"]:
        click.echo(f"\nActive decisions ({len(ctx['active_decisions'])}):")
        for d in ctx["active_decisions"]:
            click.echo(f"  {d['title']}")


# ── Task commands ──────────────────────────────────────────────────────────────

@main.group()
def task():
    """Manage tasks."""
    pass


@task.command("create")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--description", "-d", default="", help="Detailed description")
@click.option("--priority", default="medium", help="low|medium|high")
@click.option("--parent", help="Parent task UUID")
@click.option("--next-action", help="Immediate next step")
def task_create(project, title, description, priority, parent, next_action):
    """Create a new task."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    t = _db.create_task(proj.id, title, description, priority=priority,
                        parent_task_id=parent, next_action=next_action)
    click.echo(f"OK: Task '{t.title}' (id: {t.id}, status: {t.status})")


@task.command("list")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--status", "-s", help="Filter by status")
def task_list(project, status):
    """List tasks for a project."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    tasks = _db.list_tasks(proj.id, status, parent_task_id="_root_")
    if not tasks:
        click.echo("No tasks found.")
        return
    for t in tasks:
        subtask_hint = f" [{len(t.subtasks)} sub]" if t.subtasks else ""
        click.echo(f"  [{t.status}][{t.priority}] {t.title}{subtask_hint}  ({t.id[:8]})")


@task.command("update")
@click.option("--id", "task_id", required=True, help="Task UUID")
@click.option("--status", "-s", help="New status")
@click.option("--priority", help="New priority")
@click.option("--next-action", help="New next action")
@click.option("--description", "-d", help="New description")
def task_update(task_id, status, priority, next_action, description):
    """Update a task."""
    t = _db.update_task(task_id, status=status, priority=priority,
                        next_action=next_action, description=description)
    if not t:
        click.echo(f"Task '{task_id}' not found.")
        return
    click.echo(f"OK: Task '{t.title}' — {t.status}")


@task.command("log")
@click.option("--id", "task_id", required=True, help="Task UUID")
@click.option("--type", "event_type", required=True, help="Event type")
@click.option("--note", default=None, help="Event note")
def task_log(task_id, event_type, note):
    """Log an event against a task."""
    ev = _db.log_task_event(task_id, event_type, note)
    click.echo(f"OK: Logged [{ev.event_type}] at {ev.created_at[:10]}")


# ── Decision commands ──────────────────────────────────────────────────────────

@main.group()
def decision():
    """Manage decisions."""
    pass


@decision.command("add")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--title", "-t", required=True, help="Decision title")
@click.option("--text", required=True, help="Decision text")
@click.option("--rationale", "-r", default=None, help="Rationale")
def decision_add(project, title, text, rationale):
    """Record a new decision."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    d = _db.create_decision(proj.id, title, text, rationale)
    click.echo(f"OK: Decision '{d.title}' (id: {d.id})")


@decision.command("list")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--status", "-s", default=None, help="Filter by status")
def decision_list(project, status):
    """List decisions for a project."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    decisions = _db.list_decisions(proj.id, status)
    if not decisions:
        click.echo("No decisions found.")
        return
    for d in decisions:
        click.echo(f"  [{d.status}] {d.title}  ({d.id[:8]})")


# ── Note commands ──────────────────────────────────────────────────────────────

@main.group()
def note():
    """Manage notes."""
    pass


@note.command("add")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--title", "-t", required=True, help="Note title")
@click.option("--text", required=True, help="Note text")
@click.option("--type", "note_type", default="context",
              help="investigation|implementation|bug|context|handover")
def note_add(project, title, text, note_type):
    """Add a note."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    n = _db.create_note(proj.id, title, text, note_type)
    click.echo(f"OK: Note '{n.title}' (id: {n.id})")


@note.command("list")
@click.option("--project", "-p", required=True, help="Project name or ID")
@click.option("--type", "note_type", default=None, help="Filter by type")
def note_list(project, note_type):
    """List notes for a project."""
    proj = _db.get_project(project)
    if not proj:
        click.echo(f"Project '{project}' not found.")
        return
    notes = _db.list_notes(proj.id, note_type)
    if not notes:
        click.echo("No notes found.")
        return
    for n in notes:
        click.echo(f"  [{n.note_type}] {n.title}  ({n.id[:8]})")


# ── Search ─────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("query")
@click.option("--project", "-p", help="Filter by project name or ID")
@click.option("--semantic", "-s", is_flag=True, help="Use semantic search")
@click.option("--limit", "-l", default=5, help="Max results per entity type")
def search(query, project, semantic, limit):
    """Search across tasks, decisions, notes, and document chunks."""
    pid = None
    if project:
        proj = _db.get_project(project)
        if not proj:
            click.echo(f"Project '{project}' not found.")
            return
        pid = proj.id

    if semantic:
        click.echo(f"Semantic search: '{query}'\n")
        for label, fn in [
            ("Tasks", _db.semantic_search_tasks),
            ("Decisions", _db.semantic_search_decisions),
            ("Notes", _db.semantic_search_notes),
        ]:
            results = fn(query, pid, limit)
            if results:
                click.echo(f"--- {label} ---")
                for r in results:
                    click.echo(f"  {getattr(r, 'title', str(r))}")
    else:
        click.echo(f"Keyword search: '{query}'\n")
        for label, fn in [
            ("Tasks", _db.search_tasks),
            ("Decisions", _db.search_decisions),
            ("Notes", _db.search_notes),
        ]:
            results = fn(query, pid)
            if results:
                click.echo(f"--- {label} ---")
                for r in results:
                    click.echo(f"  {getattr(r, 'title', str(r))}")

    click.echo("")



if __name__ == "__main__":
    main()
