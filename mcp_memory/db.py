"""
Storage layer facade for mcp-memory.
This module re-exports functionality from the modularised repository package
 to maintain backwards compatibility.
"""

from .repository.connection import (
    db_path,
    get_conn,
    _now,
)
from .repository.models import (
    Project,
    ProjectSummary,
    Task,
    TaskEvent,
    Decision,
    Note,
    GlobalNote,
    TaskNote,
    Document,
    DocumentChunk,
    Embedding,
    EntityLink,
    Tag,
    _row_to_project,
    _row_to_summary,
    _row_to_task,
    _row_to_task_event,
    _row_to_decision,
    _row_to_note,
    _row_to_global_note,
    _row_to_task_note,
    _row_to_document,
    _row_to_chunk,
    _row_to_link,
    _row_to_tag,
)
from .repository.projects import (
    create_project,
    get_project,
    list_projects,
    update_project,
    delete_project,
    add_summary,
    get_current_summary,
    list_summaries,
)
from .repository.tasks import (
    create_task,
    get_task,
    list_tasks,
    update_task,
    delete_task,
    get_task_tree,
    log_task_event,
    get_task_events,
    create_task_note,
    get_task_note,
    list_task_notes,
    update_task_note,
    delete_task_note,
    search_task_notes,
    semantic_search_task_notes,
    semantic_search_tasks,
)
from .repository.decisions import (
    create_decision,
    get_decision,
    list_decisions,
    update_decision,
    supersede_decision,
    delete_decision,
    semantic_search_decisions,
)
from .repository.notes import (
    create_note,
    get_note,
    list_notes,
    update_note,
    delete_note,
    create_global_note,
    get_global_note,
    list_global_notes,
    update_global_note,
    delete_global_note,
    search_global_notes,
    semantic_search_global_notes,
    semantic_search_notes,
)
from .repository.documents import (
    create_document,
    get_document,
    list_documents,
    add_chunks,
    get_chunks,
    semantic_search_chunks,
)
from .repository.links import (
    create_link,
    get_links_for,
    delete_link,
)
from .repository.tags import (
    create_tag,
    list_tags,
    tag_entity,
    untag_entity,
    get_entities_by_tag,
    list_entity_tags,
)
from .repository.search import (
    _store_embedding,
    _semantic_search_raw,
    search_tasks,
    search_decisions,
    search_notes,
    search_chunks,
    semantic_search_all,
)
from .repository.context import (
    get_working_context,
)

# Export everything for standard db usage
__all__ = [
    "db_path", "get_conn", "Project", "ProjectSummary", "Task", "TaskEvent",
    "Decision", "Note", "GlobalNote", "TaskNote", "Document", "DocumentChunk",
    "Embedding", "EntityLink", "Tag", "create_project", "get_project",
    "list_projects", "update_project", "delete_project",
    "add_summary", "get_current_summary", "list_summaries", "create_task",
    "get_task", "list_tasks", "update_task", "delete_task", "get_task_tree",
    "log_task_event", "get_task_events", "create_task_note", "get_task_note",
    "list_task_notes", "update_task_note", "delete_task_note", "search_task_notes",
    "semantic_search_task_notes", "semantic_search_tasks", "create_decision",
    "get_decision", "list_decisions", "update_decision", "supersede_decision",
    "delete_decision", "semantic_search_decisions", "create_note", "get_note",
    "list_notes", "update_note", "delete_note", "create_global_note",
    "get_global_note", "list_global_notes", "update_global_note",
    "delete_global_note", "search_global_notes", "semantic_search_global_notes",
    "semantic_search_notes", "create_document", "get_document", "list_documents",
    "add_chunks", "get_chunks", "semantic_search_chunks", "create_link",
    "get_links_for", "delete_link", "create_tag", "list_tags",
    "tag_entity", "untag_entity", "get_entities_by_tag", "list_entity_tags",
    "search_tasks", "search_decisions", "search_notes", "search_chunks",
    "semantic_search_all", "get_working_context"
]
