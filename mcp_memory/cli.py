"""
cli.py — Command-line interface for manual mcp-memory updates.

Usage:
    mcp-memory-cli push --project my-app --key lang --value Python
    mcp-memory-cli log --project my-app --summary "Started project"
    mcp-memory-cli list --project my-app
"""

import click
import json
from . import db as _db

@click.group()
def main():
    """Manual management for MCP Memory."""
    pass

@main.command()
@click.option("--project", "-p", required=True, help="Project name")
@click.option("--key", "-k", required=True, help="Context key")
@click.option("--value", "-v", required=True, help="Context value")
@click.option("--category", "-c", default="general", help="Category (default: general)")
@click.option("--tag", "-t", multiple=True, help="Tags (can be repeated)")
def push(project, key, value, category, tag):
    """Store or update a context entry."""
    entry = _db.upsert_context(project, key, value, category, list(tag))
    click.echo(f"OK: [{entry.project}/{entry.category}] {entry.key} = {entry.value}")

@main.command()
@click.option("--project", "-p", required=True, help="Project name")
@click.option("--type", "-t", "event_type", default="note", help="Event type (default: note)")
@click.option("--summary", "-s", required=True, help="Short summary")
@click.option("--detail", "-d", help="Optional detail")
def log(project, event_type, summary, detail):
    """Add an event to the timeline."""
    event = _db.log_event(project, event_type, summary, detail)
    click.echo(f"OK: Logged [{event.event_type}] {event.summary}")

@main.command(name="list")
@click.option("--project", "-p", required=True, help="Project name")
@click.option("--category", "-c", help="Filter by category")
def list_cmd(project, category):
    """List all context for a project."""
    entries = _db.list_contexts(project, category)
    if not entries:
        click.echo("No entries found.")
        return
    
    current_cat = None
    for e in entries:
        if e.category != current_cat:
            current_cat = e.category
            click.echo(f"\n[{current_cat}]")
        click.echo(f"  {e.key}: {e.value}")

@main.command()
def projects():
    """List all known projects."""
    names = _db.list_all_projects()
    if not names:
        click.echo("No projects found.")
    else:
        click.echo("Projects:")
        for n in names:
            click.echo(f"  - {n}")

@main.command()
@click.argument("query")
@click.option("--project", "-p", help="Filter by project")
@click.option("--semantic", "-s", is_flag=True, help="Use semantic search instead of keyword")
@click.option("--limit", "-l", default=5, help="Limit results")
def search(query, project, semantic, limit):
    """Search across context, insights, and todos."""
    if semantic:
        click.echo(f"Searching semantically for '{query}'...")
        contexts = _db.semantic_search_contexts(query, project, limit=limit)
        insights = _db.semantic_search_insights(query, project, limit=limit) # project maps to scope here
        todos = _db.semantic_search_todos(query, project, limit=limit)
    else:
        click.echo(f"Searching keywords for '{query}'...")
        contexts = _db.search_contexts(query)
        insights = _db.search_insights(query)
        todos = _db.search_todos(query)
    
    if contexts:
        click.echo("\n--- Context ---")
        for e in contexts:
            click.echo(f"[{e.project}/{e.category}] {e.key}: {e.value}")
            
    if insights:
        click.echo("\n--- Insights ---")
        for i in insights:
            click.echo(f"[{i.scope}] {i.title}")
            
    if todos:
        click.echo("\n--- Todos ---")
        for t in todos:
            click.echo(f"[{t.project}/{t.status}] {t.title} ({t.id[:8]})")

    if not (contexts or insights or todos):
        click.echo("No results found.")

if __name__ == "__main__":
    main()
