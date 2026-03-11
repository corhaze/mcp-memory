"""Contextual enrichment for task status transitions.

When a task moves to `in_progress`, returns related decisions, notes,
and task_notes found via semantic search, plus any linked entities.

When a task moves to `done`, checks for documentation gaps — missing
task_notes and missing linked decisions.
"""

from typing import Any

from .connection import get_conn
from .models import Task, _row_to_decision, _row_to_note, _row_to_task_note
from .search import _semantic_search_raw

SCORE_THRESHOLD = 0.65
MAX_RESULTS = 5


def enrich_in_progress(task: Task) -> dict[str, list[dict[str, Any]]]:
    """Context enrichment for in_progress transitions.

    Searches decisions, notes, and task_notes semantically using the task's
    title + description. Returns related entities above the score threshold,
    plus any entities linked to this task.
    """
    query_text = f"{task.title}\n{task.description or ''}"

    related_decisions = _search_entity_type(
        query_text, "decision", task.project_id,
    )
    related_notes = _search_entity_type(
        query_text, "note", task.project_id,
    )
    related_task_notes = _search_entity_type(
        query_text, "task_note", task.project_id,
    )
    linked_entities = _fetch_linked_entities(task.id)

    return {
        "related_decisions": related_decisions,
        "related_notes": related_notes,
        "related_task_notes": related_task_notes,
        "linked_entities": linked_entities,
    }


def enrich_done(task: Task) -> dict[str, bool]:
    """Gap detection for done transitions.

    Checks whether the task has task_notes and whether it is linked
    to at least one decision.
    """
    with get_conn() as conn:
        has_notes = conn.execute(
            "SELECT 1 FROM task_notes WHERE task_id = ? LIMIT 1",
            (task.id,),
        ).fetchone() is not None

        has_decision_link = conn.execute(
            "SELECT 1 FROM entity_links "
            "WHERE (from_entity_type = 'task' AND from_entity_id = ? "
            "       AND to_entity_type = 'decision') "
            "   OR (to_entity_type = 'task' AND to_entity_id = ? "
            "       AND from_entity_type = 'decision') "
            "LIMIT 1",
            (task.id, task.id),
        ).fetchone() is not None

    return {
        "missing_task_notes": not has_notes,
        "missing_linked_decisions": not has_decision_link,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

_ENTITY_TABLE = {
    "decision": ("decisions", _row_to_decision),
    "note": ("notes", _row_to_note),
    "task_note": ("task_notes", _row_to_task_note),
}

_ENTITY_SUMMARY_FIELDS = {
    "decision": lambda e: {"id": e.id, "title": e.title, "status": e.status},
    "note": lambda e: {"id": e.id, "title": e.title, "note_type": e.note_type},
    "task_note": lambda e: {
        "id": e.id, "title": e.title, "task_id": e.task_id,
    },
}


def _search_entity_type(
    query: str, entity_type: str, project_id: str,
) -> list[dict[str, Any]]:
    """Semantic search for a single entity type, filtered by score threshold."""
    raw = _semantic_search_raw(query, entity_type, project_id, MAX_RESULTS)
    filtered = [(score, eid) for score, eid in raw if score >= SCORE_THRESHOLD]
    if not filtered:
        return []

    table, row_converter = _ENTITY_TABLE[entity_type]
    summarise = _ENTITY_SUMMARY_FIELDS[entity_type]
    ids = [eid for _, eid in filtered]
    placeholders = ", ".join("?" * len(ids))

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders})", ids,
        ).fetchall()
    entity_map = {row["id"]: row_converter(row) for row in rows}

    results = []
    for score, eid in filtered:
        entity = entity_map.get(eid)
        if entity is not None:
            summary = summarise(entity)
            summary["score"] = round(score, 4)
            results.append(summary)
    return results


def _fetch_linked_entities(task_id: str) -> list[dict[str, Any]]:
    """Fetch entities linked to a task, with their titles."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM entity_links "
            "WHERE (from_entity_type = 'task' AND from_entity_id = ?) "
            "   OR (to_entity_type = 'task' AND to_entity_id = ?) "
            "ORDER BY created_at",
            (task_id, task_id),
        ).fetchall()

    results = []
    for row in rows:
        # Determine the "other" side of the link (not the task)
        if row["from_entity_type"] == "task" and row["from_entity_id"] == task_id:
            other_type = row["to_entity_type"]
            other_id = row["to_entity_id"]
        else:
            other_type = row["from_entity_type"]
            other_id = row["from_entity_id"]

        title = _lookup_entity_title(other_type, other_id)
        results.append({
            "entity_type": other_type,
            "entity_id": other_id,
            "link_type": row["link_type"],
            "title": title,
        })
    return results


# Map entity types to (table, title_column)
_TITLE_LOOKUP = {
    "task": "tasks",
    "decision": "decisions",
    "note": "notes",
    "task_note": "task_notes",
    "global_note": "global_notes",
}


def _lookup_entity_title(entity_type: str, entity_id: str) -> str | None:
    """Look up an entity's title by type and ID."""
    table = _TITLE_LOOKUP.get(entity_type)
    if not table:
        return None
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT title FROM {table} WHERE id = ?", (entity_id,),
        ).fetchone()
    return row["title"] if row else None
