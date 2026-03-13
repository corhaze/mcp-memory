"""
ui_server.py — FastAPI server for the mcp-memory Explorer UI.

Endpoints:
  GET /api/projects                — list all projects
  GET /api/projects/{project_id}   — project working context
  GET /api/projects/{project_id}/tasks    — all tasks (with dependency order)
  GET /api/projects/{project_id}/decisions — decisions
  GET /api/projects/{project_id}/notes    — notes
  GET /api/projects/{project_id}/timeline — task events (recent)
  GET /api/tasks                   — all tasks across projects (optional project_id filter)
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

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import mcp_memory.db as _db
import mcp_memory.embeddings as _emb

app = FastAPI(title="mcp-memory Explorer", version="0.2.0")

UI_DIR = Path(__file__).parent / "ui"

# Fields to extract per entity type for the unified semantic search response.
# next_action is handled separately for tasks (it is optional).
_SEMANTIC_SEARCH_FIELDS: dict[str, list[str]] = {
    "task":        ["id", "title", "status"],
    "decision":    ["id", "title", "status"],
    "note":        ["id", "title", "note_type"],
    "task_note":   ["id", "title", "note_type", "task_id"],
    "global_note": ["id", "title", "note_type"],
}


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
    note_type: Optional[str] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    note_text: Optional[str] = None
    note_type: Optional[str] = None

class TaskNoteCreate(BaseModel):
    title: str
    note_text: str
    note_type: Optional[str] = None

class GlobalNoteCreate(BaseModel):
    title: str
    note_text: str
    note_type: Optional[str] = None

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
    """Lightweight project context for the UI: project metadata + current summary."""
    proj = _project_or_404(project_id)
    summary = _db.get_current_summary(proj.id)
    return {
        "project": {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "description": proj.description,
        },
        "summary": summary.summary_text if summary else None,
    }


@app.get("/api/projects/{project_id}/tasks")
def get_tasks(
    project_id: str,
    status: Optional[str] = None,
    topo: bool = True,
    limit: int = 0,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Return tasks for a project, wrapped in a pagination envelope.

    Pass topo=true (default) to get tasks ordered by their dependency chain
    (blocking tasks first). Each task includes a `depth` field reflecting
    how many blockers it has in the result set.

    limit=0 (default) returns all matching tasks. Max enforced at 200.
    offset skips the first N tasks after sorting.
    """
    proj = _project_or_404(project_id)
    tree = _db.get_task_tree(proj.id)
    if status:
        tree = [t for t in tree if t.status == status]
    if topo:
        sorted_tasks = _topo_sort_tasks(tree)
    else:
        sorted_tasks = [t.to_dict() for t in tree]

    total = len(sorted_tasks)
    clamped_limit = min(limit, 200) if limit > 0 else 0
    items = sorted_tasks[offset : offset + clamped_limit] if clamped_limit > 0 else sorted_tasks[offset:]
    has_more = clamped_limit > 0 and (offset + clamped_limit) < total

    return {"items": items, "total": total, "limit": clamped_limit, "offset": offset, "has_more": has_more}


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
    from mcp_memory.repository.connection import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT e.task_id, t.title AS task_title, "
            "       e.event_type, e.event_note, e.created_at "
            "FROM task_events e "
            "JOIN tasks t ON t.id = e.task_id "
            "WHERE t.project_id = ? "
            "ORDER BY e.created_at DESC LIMIT ?",
            (proj.id, limit),
        ).fetchall()
    return [
        {
            "task_id": r["task_id"],
            "task_title": r["task_title"],
            "event_type": r["event_type"],
            "event_note": r["event_note"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
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


@app.get("/api/projects/{project_id}/search/semantic")
def unified_semantic_search(
    project_id: str,
    q: str = Query(..., min_length=1, description="Semantic search query"),
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Unified semantic search across all entity types for a project.

    Returns a flat ranked list of results with entity_type, score, id, and
    key readable fields. When embeddings are unavailable, returns an empty
    results list with embeddings_available: false.
    """
    proj = _project_or_404(project_id)
    embeddings_available = _emb.is_available()

    if not q.strip() or not embeddings_available:
        return {
            "query": q,
            "embeddings_available": embeddings_available,
            "results": [],
        }

    raw_results = _db.semantic_search_all(q, proj.id, limit=limit)
    results: List[Dict[str, Any]] = []

    for r in raw_results:
        entity_type = r["entity_type"]
        entity = r["entity"]
        fields = _SEMANTIC_SEARCH_FIELDS.get(entity_type)
        if fields is None:
            continue
        shaped = {"entity_type": entity_type, "score": r["score"], "project_name": proj.name}
        shaped.update({f: getattr(entity, f) for f in fields})
        if entity_type == "task" and entity.next_action:
            shaped["next_action"] = entity.next_action
        results.append(shaped)

    return {
        "query": q,
        "embeddings_available": embeddings_available,
        "results": results,
    }


@app.get("/api/search/semantic")
def global_semantic_search(
    q: str = Query(..., min_length=1, description="Semantic search query"),
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Unified semantic search across ALL projects and global notes.

    Same response shape as the project-scoped endpoint but resolves
    project_name per result (null for global_note entities).
    """
    embeddings_available = _emb.is_available()

    if not q.strip() or not embeddings_available:
        return {
            "query": q,
            "embeddings_available": embeddings_available,
            "results": [],
        }

    raw_results = _db.semantic_search_all(q, project_id=None, limit=limit)

    # Build a project_id → name lookup for results that have a project_id.
    project_ids = {getattr(r["entity"], "project_id", None) for r in raw_results}
    project_ids.discard(None)
    project_map: dict[str, str] = {}
    if project_ids:
        for pid in project_ids:
            proj = _db.get_project(pid)
            if proj:
                project_map[pid] = proj.name

    results: List[Dict[str, Any]] = []
    for r in raw_results:
        entity_type = r["entity_type"]
        entity = r["entity"]
        fields = _SEMANTIC_SEARCH_FIELDS.get(entity_type)
        if fields is None:
            continue
        pid = getattr(entity, "project_id", None)
        shaped = {
            "entity_type": entity_type,
            "score": r["score"],
            "project_name": project_map.get(pid) if pid else None,
        }
        shaped.update({f: getattr(entity, f) for f in fields})
        if entity_type == "task" and entity.next_action:
            shaped["next_action"] = entity.next_action
        results.append(shaped)

    return {
        "query": q,
        "embeddings_available": embeddings_available,
        "results": results,
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

@app.get("/api/projects/{project_id}/tasks/{task_id}")
def get_task_detail(project_id: str, task_id: str) -> Dict[str, Any]:
    """Return full detail for a single task: fields, subtasks, notes, and events."""
    _project_or_404(project_id)
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    notes = _db.list_task_notes(task_id)
    events = _db.get_task_events(task_id)
    data = task.to_dict()
    data["notes"] = [n.to_dict() for n in notes]
    data["events"] = [
        {
            "event_type": ev.event_type,
            "event_note": ev.event_note,
            "created_at": ev.created_at,
        }
        for ev in events
    ]
    return data


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

@app.get("/api/projects/{project_id}/notes/{note_id}")
def get_note_detail(project_id: str, note_id: str) -> Dict[str, Any]:
    """Return full detail for a single note including linked entities."""
    _project_or_404(project_id)
    note = _db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    data = note.to_dict()
    links = _db.get_links_for("note", note_id)
    data["links"] = [lnk.to_dict() for lnk in links]
    return data


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


# ── Cross-project tasks ────────────────────────────────────────────────────────

@app.get("/api/tasks")
def get_all_tasks(
    project_id: List[str] = Query(default=[]),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Return tasks across all projects as a paginated envelope.

    Each task dict includes project_name in addition to all standard task fields.
    Subtasks are not included at the top level — they are embedded in their parent's
    subtasks field via get_task_tree.

    Query parameters:
      project_id (repeatable): filter to specific projects; omit for all projects
      status: filter by task status
      limit: max tasks to return (default 50); 0 means return all. Max 200.
      offset: skip the first N matching tasks (default 0)
    """
    projects = _db.list_projects()
    if project_id:
        project_id_set = set(project_id)
        projects = [p for p in projects if p.id in project_id_set]

    result: List[Dict[str, Any]] = []
    for proj in projects:
        tree = _db.get_task_tree(proj.id)
        for task in tree:
            if status and task.status != status:
                continue
            task_dict = task.to_dict()
            task_dict["project_name"] = proj.name
            result.append(task_dict)

    total = len(result)
    clamped_limit = min(limit, 200) if limit > 0 else 0
    items = result[offset : offset + clamped_limit] if clamped_limit > 0 else result[offset:]
    has_more = clamped_limit > 0 and (offset + clamped_limit) < total

    return {"items": items, "total": total, "limit": clamped_limit, "offset": offset, "has_more": has_more}


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


@app.get("/api/global-notes/{note_id}")
def get_global_note_detail(note_id: str) -> Dict[str, Any]:
    """Return full detail for a single global note including linked entities."""
    note = _db.get_global_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Global note not found")
    data = note.to_dict()
    links = _db.get_links_for("global_note", note_id)
    data["links"] = [lnk.to_dict() for lnk in links]
    return data


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


# ── Reembed ───────────────────────────────────────────────────────────────────

class ReembedRequest(BaseModel):
    force: bool = False


@app.post("/api/reembed")
def reembed(req: ReembedRequest = ReembedRequest()) -> Dict[str, int]:
    if not _emb.is_available():
        raise HTTPException(status_code=400, detail="Embeddings are not enabled")
    from mcp_memory.repository.connection import get_conn
    from mcp_memory.repository.search import reembed_all
    with get_conn() as conn:
        return reembed_all(conn, force=req.force)


# ── Static UI + SPA catch-all ─────────────────────────────────────────────────
# Catch-all: serve static files if they exist, otherwise serve index.html so
# that client-side routes like /mcp-memory or /blog/decisions work on refresh.

@app.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    candidate = UI_DIR / full_path
    if candidate.exists() and candidate.is_file():
        # Vite hashed assets (assets/index-abc123.js) are immutable — cache aggressively.
        # Everything else (index.html) should not be cached.
        if "/assets/" in full_path:
            headers = {"Cache-Control": "public, max-age=31536000, immutable"}
        else:
            headers = {"Cache-Control": "no-store"}
        return FileResponse(str(candidate), headers=headers)
    return FileResponse(str(UI_DIR / "index.html"), headers={"Cache-Control": "no-store"})
