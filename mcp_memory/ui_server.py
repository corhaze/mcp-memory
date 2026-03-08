"""
ui_server.py — FastAPI server for the mcp-memory Explorer UI.

Endpoints:
  GET /api/projects                — list all projects
  GET /api/projects/{project_id}   — project working context
  GET /api/projects/{project_id}/tasks    — all tasks (with dependency order)
  GET /api/projects/{project_id}/decisions — decisions
  GET /api/projects/{project_id}/notes    — notes
  GET /api/projects/{project_id}/timeline — task events (recent)
  GET /api/search                  — keyword search across all entities
  DELETE /api/projects/{project_id}       — delete project

Run:
    uv run uvicorn mcp_memory.ui_server:app --reload --reload-dir mcp_memory --port 7878

    IMPORTANT: always pass --reload-dir mcp_memory when using --reload.
    Without it, uvicorn watches ~/.mcp-memory/memory.db and its WAL/SHM files.
    Every DB write triggers a module reload → new ONNX InferenceSession →
    new thread pool. Threads accumulate rapidly (observed: 742 threads, 78% kernel CPU).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
        result.append(task.to_dict(depth=depth))

    # Visit tasks without a blocker (or whose blocker is outside this list) first
    roots = [t for t in tasks if not t.blocked_by_task_id or t.blocked_by_task_id not in by_id]
    blocked = [t for t in tasks if t.blocked_by_task_id and t.blocked_by_task_id in by_id]

    for t in sorted(roots, key=lambda x: x.created_at, reverse=True):
        visit(t, depth=0)
    for t in sorted(blocked, key=lambda x: x.created_at, reverse=True):
        visit(t, depth=1)

    return result



# ── Request Models ────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"

class ProjectUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "open"
    urgent: bool = False
    complex: bool = False
    parent_task_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    blocked_by_task_id: Optional[str] = None
    next_action: Optional[str] = None
    due_at: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    urgent: Optional[bool] = None
    complex: Optional[bool] = None
    assigned_agent: Optional[str] = None
    blocked_by_task_id: Optional[str] = None
    next_action: Optional[str] = None
    due_at: Optional[str] = None

class DecisionCreate(BaseModel):
    title: str
    decision_text: str
    rationale: Optional[str] = None
    status: str = "active"
    supersedes_decision_id: Optional[str] = None

class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    decision_text: Optional[str] = None
    rationale: Optional[str] = None
    status: Optional[str] = None

class NoteCreate(BaseModel):
    title: str
    note_text: str
    note_type: str = "context"

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    note_text: Optional[str] = None
    note_type: Optional[str] = None

class TaskNoteCreate(BaseModel):
    title: str
    note_text: str
    note_type: str = "context"

class GlobalNoteCreate(BaseModel):
    title: str
    note_text: str
    note_type: str = "context"

class GlobalNoteUpdate(BaseModel):
    title: Optional[str] = None
    note_text: Optional[str] = None
    note_type: Optional[str] = None

class SummaryCreate(BaseModel):
    summary_text: str
    summary_kind: str = "current"

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
    return [t.to_dict() for t in tree]


@app.get("/api/projects/{project_id}/decisions")
def get_decisions(
    project_id: str,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return decisions for a project, optionally filtered by status."""
    proj = _project_or_404(project_id)
    decisions = _db.list_decisions(proj.id, status)
    return [d.to_dict() for d in decisions]


@app.get("/api/projects/{project_id}/notes")
def get_notes(
    project_id: str,
    note_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return notes for a project, optionally filtered by type."""
    proj = _project_or_404(project_id)
    notes = _db.list_notes(proj.id, note_type)
    return [n.to_dict() for n in notes]


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
@app.get("/api/search")
def search(q: str, project_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Search across all entity types using keyword search.

    Query parameters:
      q (required): search query string
      project_id (optional): scope to project; if absent, search all projects
      limit (optional): max results per entity type (default 10)
    """
    if not q.strip():
        return {"tasks": [], "decisions": [], "notes": [], "chunks": []}

    # Call search functions from repository
    tasks = _db.search_tasks(q, project_id=project_id)[:limit]
    decisions = _db.search_decisions(q, project_id=project_id)[:limit]
    notes = _db.search_notes(q, project_id=project_id)[:limit]
    chunks = _db.search_chunks(q, project_id=project_id)[:limit]

    return {
        "tasks": [t.to_dict() for t in tasks],
        "decisions": [d.to_dict() for d in decisions],
        "notes": [n.to_dict() for n in notes],
        "chunks": [{"id": c.id, "document_id": c.document_id, "project_id": c.project_id,
                    "chunk_index": c.chunk_index, "chunk_text": c.chunk_text,
                    "created_at": c.created_at} for c in chunks]
    }


@app.get("/api/projects/{project_id}/semantic_search")
def semantic_search(
    project_id: str,
    q: str,
    limit: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """Perform semantic search across tasks, decisions, and notes."""
    proj = _project_or_404(project_id)
    if not q:
        return {"tasks": [], "decisions": [], "notes": []}

    tasks = _db.semantic_search_tasks(q, proj.id, limit=limit)
    decisions = _db.semantic_search_decisions(q, proj.id, limit=limit)
    notes = _db.semantic_search_notes(q, proj.id, limit=limit)

    return {
        "tasks": [t.to_dict() for t in tasks],
        "decisions": [d.to_dict() for d in decisions],
        "notes": [n.to_dict() for n in notes]
    }


@app.post("/api/projects")
def create_project(req: ProjectCreate) -> Dict[str, Any]:
    proj = _db.create_project(req.name, req.description, req.status)
    return {"id": proj.id, "name": proj.name}

@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdate) -> Dict[str, Any]:
    proj = _db.update_project(project_id, req.description, req.status)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": proj.id, "name": proj.name}

@app.post("/api/projects/{project_id}/summary")
def set_project_summary(project_id: str, req: SummaryCreate) -> Dict[str, Any]:
    """Set the project summary."""
    proj = _project_or_404(project_id)
    s = _db.add_summary(proj.id, req.summary_text, req.summary_kind)
    return {"id": s.id, "summary_text": s.summary_text, "summary_kind": s.summary_kind}

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> Dict[str, str]:
    """Delete a project and all its data."""
    proj = _project_or_404(project_id)
    _db.delete_project(proj.id)
    return {"deleted": proj.name}

# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/tasks")
def create_task(project_id: str, req: TaskCreate) -> Dict[str, Any]:
    proj = _project_or_404(project_id)
    task = _db.create_task(
        proj.id, req.title, req.description, req.status, req.urgent, req.complex,
        req.parent_task_id, req.assigned_agent, req.blocked_by_task_id,
        req.next_action, req.due_at
    )
    return task.to_dict()

@app.patch("/api/projects/{project_id}/tasks/{task_id}")
def update_task(project_id: str, task_id: str, req: TaskUpdate) -> Dict[str, Any]:
    task = _db.update_task(
        task_id, req.title, req.description, req.status, req.urgent, req.complex,
        req.assigned_agent, req.blocked_by_task_id, req.next_action, req.due_at
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@app.delete("/api/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: str, task_id: str) -> Dict[str, str]:
    if not _db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": task_id}

# ── Decisions ──────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/decisions")
def create_decision(project_id: str, req: DecisionCreate) -> Dict[str, Any]:
    proj = _project_or_404(project_id)
    dec = _db.create_decision(
        proj.id, req.title, req.decision_text, req.rationale, req.status,
        req.supersedes_decision_id
    )
    return dec.to_dict()

@app.patch("/api/projects/{project_id}/decisions/{decision_id}")
def update_decision(project_id: str, decision_id: str, req: DecisionUpdate) -> Dict[str, Any]:
    dec = _db.update_decision(
        decision_id, req.title, req.decision_text, req.rationale, req.status
    )
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")
    return dec.to_dict()

@app.delete("/api/projects/{project_id}/decisions/{decision_id}")
def delete_decision(project_id: str, decision_id: str) -> Dict[str, str]:
    if not _db.delete_decision(decision_id):
        raise HTTPException(status_code=404, detail="Decision not found")
    return {"deleted": decision_id}

# ── Notes ──────────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/notes")
def create_note(project_id: str, req: NoteCreate) -> Dict[str, Any]:
    proj = _project_or_404(project_id)
    note = _db.create_note(proj.id, req.title, req.note_text, req.note_type)
    return note.to_dict()

@app.patch("/api/projects/{project_id}/notes/{note_id}")
def update_note(project_id: str, note_id: str, req: NoteUpdate) -> Dict[str, Any]:
    note = _db.update_note(note_id, req.title, req.note_text, req.note_type)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()

@app.delete("/api/projects/{project_id}/notes/{note_id}")
def delete_note(project_id: str, note_id: str) -> Dict[str, str]:
    if not _db.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": note_id}


# ── Task Notes ────────────────────────────────────────────────────────────────

@app.get("/api/tasks/{task_id}/notes")
def get_task_notes(task_id: str) -> List[Dict[str, Any]]:
    """Return all notes attached to a task."""
    notes = _db.list_task_notes(task_id)
    return [n.to_dict() for n in notes]


@app.post("/api/tasks/{task_id}/notes")
def create_task_note(task_id: str, req: TaskNoteCreate) -> Dict[str, Any]:
    """Add a note to a task."""
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    note = _db.create_task_note(task.project_id, task_id, req.title, req.note_text, req.note_type)
    return note.to_dict()


@app.delete("/api/task-notes/{note_id}")
def delete_task_note(note_id: str) -> Dict[str, str]:
    """Delete a task note."""
    if not _db.delete_task_note(note_id):
        raise HTTPException(status_code=404, detail="Task note not found")
    return {"deleted": note_id}


# ── Global Notes ──────────────────────────────────────────────────────────────

@app.get("/api/global-notes")
def get_global_notes(note_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all global notes, optionally filtered by type."""
    return [n.to_dict() for n in _db.list_global_notes(note_type)]


@app.post("/api/global-notes")
def create_global_note(req: GlobalNoteCreate) -> Dict[str, Any]:
    note = _db.create_global_note(req.title, req.note_text, req.note_type)
    return note.to_dict()


@app.patch("/api/global-notes/{note_id}")
def update_global_note(note_id: str, req: GlobalNoteUpdate) -> Dict[str, Any]:
    note = _db.update_global_note(note_id, req.title, req.note_text, req.note_type)
    if not note:
        raise HTTPException(status_code=404, detail="Global note not found")
    return note.to_dict()


@app.delete("/api/global-notes/{note_id}")
def delete_global_note(note_id: str) -> Dict[str, str]:
    if not _db.delete_global_note(note_id):
        raise HTTPException(status_code=404, detail="Global note not found")
    return {"deleted": note_id}


# ── Static UI + SPA catch-all ─────────────────────────────────────────────────
# Catch-all: serve static files if they exist, otherwise serve index.html so
# that client-side routes like /mcp-memory or /blog/decisions work on refresh.

_NO_CACHE_SUFFIXES = {".js", ".css"}

@app.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    candidate = UI_DIR / full_path
    if candidate.exists() and candidate.is_file():
        headers = {"Cache-Control": "no-store"} if candidate.suffix in _NO_CACHE_SUFFIXES else {}
        return FileResponse(str(candidate), headers=headers)
    return FileResponse(str(UI_DIR / "index.html"), headers={"Cache-Control": "no-store"})
