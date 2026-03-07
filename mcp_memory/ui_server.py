"""
ui_server.py — FastAPI server for the mcp-memory Explorer UI.

Endpoints:
  GET /api/projects                — list all projects
  GET /api/projects/{project_id}   — project working context
  GET /api/projects/{project_id}/tasks    — all tasks (with dependency order)
  GET /api/projects/{project_id}/decisions — decisions
  GET /api/projects/{project_id}/notes    — notes
  GET /api/projects/{project_id}/timeline — task events (recent)
  DELETE /api/projects/{project_id}       — delete project

Run:
    uvicorn mcp_memory.ui_server:app --reload --port 7878
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import mcp_memory.db as _db

app = FastAPI(title="mcp-memory Explorer", version="0.2.0")

UI_DIR = Path(__file__).parent / "ui"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _project_or_404(name_or_id: str) -> _db.Project:
    proj = _db.get_project(name_or_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{name_or_id}' not found.")
    return proj


def _topo_sort_tasks(tasks: List[_db.Task]) -> List[Dict[str, Any]]:
    """
    Topologically sort tasks by blocked_by_task_id so that blocking tasks
    always appear before the tasks they block.

    Returns dicts with an extra `depth` field (0 = root, 1 = blocked-by root, …)
    used by the UI to visually indent dependency chains.
    """
    by_id = {t.id: t for t in tasks}
    result: List[Dict[str, Any]] = []
    visited: set = set()

    def visit(task: _db.Task, depth: int) -> None:
        if task.id in visited:
            return
        visited.add(task.id)
        # Recurse into the blocker first so it appears above the blocked task
        if task.blocked_by_task_id and task.blocked_by_task_id in by_id:
            visit(by_id[task.blocked_by_task_id], max(0, depth - 1))
        result.append(_task_dict(task, depth=depth))

    # Visit tasks without a blocker (or whose blocker is outside this list) first
    roots = [t for t in tasks if not t.blocked_by_task_id or t.blocked_by_task_id not in by_id]
    blocked = [t for t in tasks if t.blocked_by_task_id and t.blocked_by_task_id in by_id]

    for t in sorted(roots, key=lambda x: x.created_at):
        visit(t, depth=0)
    for t in sorted(blocked, key=lambda x: x.created_at):
        visit(t, depth=1)

    return result


def _task_dict(task: _db.Task, depth: int = 0) -> Dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "parent_task_id": task.parent_task_id,
        "blocked_by_task_id": task.blocked_by_task_id,
        "next_action": task.next_action,
        "assigned_agent": task.assigned_agent,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "depth": depth,
        "subtasks": [_task_dict(st) for st in task.subtasks],
    }


def _decision_dict(d: _db.Decision) -> Dict[str, Any]:
    return {
        "id": d.id,
        "title": d.title,
        "decision_text": d.decision_text,
        "rationale": d.rationale,
        "status": d.status,
        "supersedes_decision_id": d.supersedes_decision_id,
        "created_at": d.created_at,
    }


def _note_dict(n: _db.Note) -> Dict[str, Any]:
    return {
        "id": n.id,
        "title": n.title,
        "note_text": n.note_text,
        "note_type": n.note_type,
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }


# ── API routes ─────────────────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects() -> List[Dict[str, Any]]:
    """List all projects."""
    projects = _db.list_projects()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in projects
    ]


@app.get("/api/projects/{project_id}")
def get_project_context(project_id: str) -> Dict[str, Any]:
    """Working context for a project (summary + active tasks + decisions + notes)."""
    proj = _project_or_404(project_id)
    ctx = _db.get_working_context(proj.id)
    return ctx


@app.get("/api/projects/{project_id}/tasks")
def get_tasks(
    project_id: str,
    status: Optional[str] = None,
    topo: bool = True,
) -> List[Dict[str, Any]]:
    """
    Return tasks for a project.

    Pass topo=true (default) to get tasks ordered by their dependency chain
    (blocking tasks first). Each task includes a `depth` field reflecting
    how many blockers it has in the result set.
    """
    proj = _project_or_404(project_id)
    # Load all top-level tasks with subtasks already attached
    tree = _db.get_task_tree(proj.id)
    if status:
        tree = [t for t in tree if t.status == status]
    if topo:
        return _topo_sort_tasks(tree)
    return [_task_dict(t) for t in tree]


@app.get("/api/projects/{project_id}/decisions")
def get_decisions(
    project_id: str,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return decisions for a project, optionally filtered by status."""
    proj = _project_or_404(project_id)
    decisions = _db.list_decisions(proj.id, status)
    return [_decision_dict(d) for d in decisions]


@app.get("/api/projects/{project_id}/notes")
def get_notes(
    project_id: str,
    note_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return notes for a project, optionally filtered by type."""
    proj = _project_or_404(project_id)
    notes = _db.list_notes(proj.id, note_type)
    return [_note_dict(n) for n in notes]


@app.get("/api/projects/{project_id}/timeline")
def get_timeline(project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recent task events for a project (acts as a worklog timeline)."""
    proj = _project_or_404(project_id)
    # Gather all top-level tasks and collect their recent events
    tasks = _db.list_tasks(proj.id, parent_task_id=None)
    events = []
    for task in tasks:
        for ev in _db.get_task_events(task.id, limit=20):
            events.append({
                "task_id": ev.task_id,
                "task_title": task.title,
                "event_type": ev.event_type,
                "event_note": ev.event_note,
                "created_at": ev.created_at,
            })
    # Sort all events newest-first
    events.sort(key=lambda e: e["created_at"], reverse=True)
    return events[:limit]


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> Dict[str, str]:
    """Delete a project and all its data."""
    proj = _project_or_404(project_id)
    _db.delete_project(proj.id)
    return {"deleted": proj.name}


# ── Static UI + SPA catch-all ─────────────────────────────────────────────────
# Catch-all: serve static files if they exist, otherwise serve index.html so
# that client-side routes like /mcp-memory or /blog/decisions work on refresh.

@app.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    candidate = UI_DIR / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(str(candidate))
    return FileResponse(str(UI_DIR / "index.html"))
