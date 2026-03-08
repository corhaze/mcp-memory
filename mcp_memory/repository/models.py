from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Project:
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class ProjectSummary:
    id: str
    project_id: str
    summary_text: str
    summary_kind: str
    created_at: str

@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: Optional[str]
    status: str
    urgent: bool
    complex: bool
    parent_task_id: Optional[str]
    assigned_agent: Optional[str]
    blocked_by_task_id: Optional[str]
    next_action: Optional[str]
    due_at: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    subtasks: List["Task"] = field(default_factory=list)

    def to_dict(self, depth: int = 0) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "urgent": self.urgent,
            "complex": self.complex,
            "parent_task_id": self.parent_task_id,
            "blocked_by_task_id": self.blocked_by_task_id,
            "next_action": self.next_action,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "depth": depth,
            "subtasks": [st.to_dict() for st in self.subtasks],
        }

@dataclass
class TaskEvent:
    id: str
    task_id: str
    event_type: str
    event_note: Optional[str]
    created_at: str

@dataclass
class Decision:
    id: str
    project_id: str
    title: str
    decision_text: str
    rationale: Optional[str]
    status: str
    supersedes_decision_id: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "decision_text": self.decision_text,
            "rationale": self.rationale,
            "status": self.status,
            "supersedes_decision_id": self.supersedes_decision_id,
            "created_at": self.created_at,
        }

@dataclass
class Note:
    id: str
    project_id: str
    title: str
    note_text: str
    note_type: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "note_text": self.note_text,
            "note_type": self.note_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class GlobalNote:
    id: str
    title: str
    note_text: str
    note_type: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "note_text": self.note_text,
            "note_type": self.note_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class TaskNote:
    id: str
    project_id: str
    task_id: str
    title: str
    note_text: str
    note_type: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "note_text": self.note_text,
            "note_type": self.note_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class Document:
    id: str
    project_id: str
    source_type: str
    source_ref: Optional[str]
    title: str
    content_hash: Optional[str]
    created_at: str

@dataclass
class DocumentChunk:
    id: str
    document_id: str
    project_id: str
    chunk_index: int
    chunk_text: str
    token_count: Optional[int]
    created_at: str

@dataclass
class Embedding:
    id: str
    project_id: str
    entity_type: str
    entity_id: str
    embedding_model: str
    created_at: str

@dataclass
class EntityLink:
    id: str
    project_id: str
    from_entity_type: str
    from_entity_id: str
    link_type: str
    to_entity_type: str
    to_entity_id: str
    created_at: str

@dataclass
class Tag:
    id: str
    project_id: str
    name: str

# ── Row helpers ────────────────────────────────────────────────────────────────

def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"], name=row["name"], description=row["description"],
        status=row["status"], created_at=row["created_at"], updated_at=row["updated_at"],
    )

def _row_to_summary(row: sqlite3.Row) -> ProjectSummary:
    return ProjectSummary(
        id=row["id"], project_id=row["project_id"], summary_text=row["summary_text"],
        summary_kind=row["summary_kind"], created_at=row["created_at"],
    )

def _row_to_task(row: sqlite3.Row) -> Task:
    urgent_val = bool(row["urgent"]) if "urgent" in row.keys() else False
    complex_val = bool(row["complex"]) if "complex" in row.keys() else False
    return Task(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        description=row["description"], status=row["status"], urgent=urgent_val,
        complex=complex_val,
        parent_task_id=row["parent_task_id"], assigned_agent=row["assigned_agent"],
        blocked_by_task_id=row["blocked_by_task_id"], next_action=row["next_action"],
        due_at=row["due_at"], created_at=row["created_at"], updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )

def _row_to_task_event(row: sqlite3.Row) -> TaskEvent:
    return TaskEvent(
        id=row["id"], task_id=row["task_id"], event_type=row["event_type"],
        event_note=row["event_note"], created_at=row["created_at"],
    )

def _row_to_decision(row: sqlite3.Row) -> Decision:
    return Decision(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        decision_text=row["decision_text"], rationale=row["rationale"],
        status=row["status"], supersedes_decision_id=row["supersedes_decision_id"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )

def _row_to_note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"], project_id=row["project_id"], title=row["title"],
        note_text=row["note_text"], note_type=row["note_type"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )

def _row_to_global_note(row: sqlite3.Row) -> GlobalNote:
    return GlobalNote(
        id=row["id"], title=row["title"], note_text=row["note_text"],
        note_type=row["note_type"], created_at=row["created_at"], updated_at=row["updated_at"],
    )

def _row_to_task_note(row: sqlite3.Row) -> TaskNote:
    return TaskNote(
        id=row["id"], project_id=row["project_id"], task_id=row["task_id"],
        title=row["title"], note_text=row["note_text"], note_type=row["note_type"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )

def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"], project_id=row["project_id"], source_type=row["source_type"],
        source_ref=row["source_ref"], title=row["title"], content_hash=row["content_hash"],
        created_at=row["created_at"],
    )

def _row_to_chunk(row: sqlite3.Row) -> DocumentChunk:
    return DocumentChunk(
        id=row["id"], document_id=row["document_id"], project_id=row["project_id"],
        chunk_index=row["chunk_index"], chunk_text=row["chunk_text"],
        token_count=row["token_count"], created_at=row["created_at"],
    )

def _row_to_link(row: sqlite3.Row) -> EntityLink:
    return EntityLink(
        id=row["id"], project_id=row["project_id"],
        from_entity_type=row["from_entity_type"], from_entity_id=row["from_entity_id"],
        link_type=row["link_type"],
        to_entity_type=row["to_entity_type"], to_entity_id=row["to_entity_id"],
        created_at=row["created_at"],
    )

def _row_to_tag(row: sqlite3.Row) -> Tag:
    return Tag(id=row["id"], project_id=row["project_id"], name=row["name"])
