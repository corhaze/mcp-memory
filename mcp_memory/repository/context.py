from typing import Dict, Any, List
from .connection import get_conn
from .projects import get_project, get_current_summary
from .tasks import list_tasks
from .decisions import list_decisions, get_decision
from .notes import list_notes, list_global_notes
from .links import get_links_for

def get_working_context(project_id: str) -> Dict[str, Any]:
    """Return a summary of the project's current state for an agent's context."""
    proj = get_project(project_id)
    if not proj:
        # Try by name if ID fails (legary shim)
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM projects WHERE name=?", (project_id,)).fetchone()
            if row:
                from .models import _row_to_project
                proj = _row_to_project(row)
            else:
                return {"error": f"Project '{project_id}' not found."}
    
    summary = get_current_summary(proj.id)
    
    # 2. Active tasks: open or in_progress top-level tasks
    open_tasks = list_tasks(proj.id, status="open", parent_task_id="_root_")
    in_progress = list_tasks(proj.id, status="in_progress", parent_task_id="_root_")
    active_tasks_objs = open_tasks + in_progress
    
    # 3. Decisions linked to active tasks
    linked_decision_ids = set()
    for t in active_tasks_objs:
        links = get_links_for("task", t.id, direction="both")
        for l in links:
            if l.from_entity_type == "decision":
                linked_decision_ids.add(l.from_entity_id)
            elif l.to_entity_type == "decision":
                linked_decision_ids.add(l.to_entity_id)
    
    linked_decisions = []
    for did in linked_decision_ids:
        d = get_decision(did)
        if d:
            linked_decisions.append({"id": d.id, "title": d.title, "status": d.status})
            
    # 4. Active decisions (global to project)
    active_decisions_objs = list_decisions(proj.id, status="active")[:10]
    
    # 5. Recent notes
    recent_notes_objs = list_notes(proj.id)[:10]
    
    # 6. Global notes — only foundation notes are auto-injected into context;
    #    other types remain searchable but don't consume context window.
    global_notes_objs = list_global_notes(note_type="foundation")

    return {
        "project": {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "description": proj.description,
        },
        "summary": summary.summary_text if summary else None,
        "active_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "urgent": t.urgent,
                "next_action": t.next_action,
            }
            for t in active_tasks_objs
        ],
        "linked_decisions": linked_decisions,
        "active_decisions": [
            {"id": d.id, "title": d.title, "status": d.status}
            for d in active_decisions_objs
        ],
        "recent_notes": [
            {"id": n.id, "title": n.title, "note_type": n.note_type}
            for n in recent_notes_objs
        ],
        "global_notes": [
            {
                "id": n.id,
                "title": n.title,
                "note_type": n.note_type,
                "note_text": n.note_text,
            }
            for n in global_notes_objs
        ],
    }
