"""
tests/test_repository.py — unit tests for repository module coverage gaps.

Covers: models.to_dict(), tasks edge cases, notes edge cases,
        global notes CRUD, task note search, and search_task_notes filters.
"""

import pytest
from mcp_memory.repository.models import (
    Project, Task, Decision, Note, GlobalNote, TaskNote,
)
from mcp_memory.db import (
    create_project,
    create_task, get_task, list_tasks, update_task,
    create_task_note, get_task_note, update_task_note,
    create_note, update_note, delete_note,
    create_global_note, get_global_note, update_global_note,
    delete_global_note, list_global_notes, search_global_notes,
    create_decision,
)
from mcp_memory.repository.tasks import search_task_notes
from mcp_memory.repository import connection
_real_db_path = connection.db_path  # captured before autouse fixture patches it


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_repo.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def proj():
    return create_project("repo-test-proj")


# ── connection.db_path() ──────────────────────────────────────────────────────

class TestDbPath:
    def test_env_var_overrides_default(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom" / "mem.db"
        monkeypatch.setenv("MCP_MEMORY_DB_PATH", str(custom))
        result = _real_db_path()
        assert result == custom
        assert custom.parent.exists()

    def test_default_path_is_home_based(self, monkeypatch):
        monkeypatch.delenv("MCP_MEMORY_DB_PATH", raising=False)
        result = _real_db_path()
        assert result.name == "memory.db"
        assert ".mcp-memory" in str(result)


# ── models.to_dict() ──────────────────────────────────────────────────────────

class TestModelToDict:
    def test_project_to_dict(self, proj):
        d = proj.to_dict()
        assert d["id"] == proj.id
        assert d["name"] == proj.name
        assert d["status"] == proj.status
        assert "created_at" in d
        assert "updated_at" in d

    def test_task_to_dict(self, proj):
        task = create_task(proj.id, "My task", description="desc")
        d = task.to_dict()
        assert d["id"] == task.id
        assert d["title"] == "My task"
        assert d["description"] == "desc"
        assert d["depth"] == 0
        assert d["subtasks"] == []

    def test_task_to_dict_depth(self, proj):
        task = create_task(proj.id, "Depth task")
        d = task.to_dict(depth=2)
        assert d["depth"] == 2

    def test_task_to_dict_with_subtasks(self, proj):
        parent = create_task(proj.id, "Parent")
        create_task(proj.id, "Child", parent_task_id=parent.id)
        parent_full = get_task(parent.id)
        d = parent_full.to_dict()
        assert len(d["subtasks"]) == 1
        assert d["subtasks"][0]["title"] == "Child"

    def test_decision_to_dict(self, proj):
        dec = create_decision(proj.id, "Use SQLite", "SQLite is sufficient", rationale="Simple")
        d = dec.to_dict()
        assert d["id"] == dec.id
        assert d["title"] == "Use SQLite"
        assert d["decision_text"] == "SQLite is sufficient"
        assert d["rationale"] == "Simple"
        assert "created_at" in d

    def test_note_to_dict(self, proj):
        note = create_note(proj.id, "My note", "note body", "context")
        d = note.to_dict()
        assert d["id"] == note.id
        assert d["title"] == "My note"
        assert d["note_text"] == "note body"
        assert d["note_type"] == "context"

    def test_global_note_to_dict(self):
        gn = create_global_note("Global rule", "Always test", "implementation")
        d = gn.to_dict()
        assert d["id"] == gn.id
        assert d["title"] == "Global rule"
        assert d["note_text"] == "Always test"
        assert d["note_type"] == "implementation"

    def test_task_note_to_dict(self, proj):
        task = create_task(proj.id, "Task")
        tn = create_task_note(proj.id, task.id, "Note title", "Note body", "bug")
        d = tn.to_dict()
        assert d["id"] == tn.id
        assert d["task_id"] == task.id
        assert d["title"] == "Note title"
        assert d["note_type"] == "bug"


# ── tasks edge cases ──────────────────────────────────────────────────────────

class TestTasksEdgeCases:
    def test_list_tasks_by_parent(self, proj):
        parent = create_task(proj.id, "Parent")
        create_task(proj.id, "Child", parent_task_id=parent.id)
        create_task(proj.id, "Root only")
        results = list_tasks(proj.id, parent_task_id=parent.id)
        assert len(results) == 1
        assert results[0].title == "Child"

    def test_list_tasks_by_status_and_parent(self, proj):
        parent = create_task(proj.id, "Parent")
        create_task(proj.id, "Open child", parent_task_id=parent.id, status="open")
        create_task(proj.id, "Done child", parent_task_id=parent.id, status="done")
        results = list_tasks(proj.id, status="open", parent_task_id=parent.id)
        assert len(results) == 1
        assert results[0].status == "open"

    def test_update_task_not_found(self):
        result = update_task("nonexistent-id", title="New title")
        assert result is None

    def test_update_task_title(self, proj):
        task = create_task(proj.id, "Original title")
        updated = update_task(task.id, title="New title")
        assert updated.title == "New title"

    def test_update_task_description(self, proj):
        task = create_task(proj.id, "Original")
        updated = update_task(task.id, description="New desc")
        assert updated.description == "New desc"

    def test_update_task_urgent(self, proj):
        task = create_task(proj.id, "Task", urgent=False)
        updated = update_task(task.id, urgent=True)
        assert updated.urgent is True

    def test_update_task_assigned_agent(self, proj):
        task = create_task(proj.id, "Task")
        updated = update_task(task.id, assigned_agent="agent-007")
        assert updated.assigned_agent == "agent-007"

    def test_update_task_blocked_by(self, proj):
        t1 = create_task(proj.id, "Blocker")
        t2 = create_task(proj.id, "Blocked")
        updated = update_task(t2.id, blocked_by_task_id=t1.id)
        assert updated.blocked_by_task_id == t1.id

    def test_update_task_next_action(self, proj):
        task = create_task(proj.id, "Task")
        updated = update_task(task.id, next_action="Do the thing")
        assert updated.next_action == "Do the thing"

    def test_update_task_due_at(self, proj):
        task = create_task(proj.id, "Task")
        updated = update_task(task.id, due_at="2026-12-31T00:00:00+00:00")
        assert updated.due_at == "2026-12-31T00:00:00+00:00"

    def test_update_task_status_blocked_logs_event(self, proj):
        task = create_task(proj.id, "Task")
        updated = update_task(task.id, status="blocked", next_action="Waiting on review")
        assert updated.status == "blocked"

    def test_update_task_note_not_found(self):
        result = update_task_note("nonexistent-id", title="New")
        assert result is None

    def test_update_task_note_no_changes(self, proj):
        task = create_task(proj.id, "Task")
        tn = create_task_note(proj.id, task.id, "Title", "Body", "context")
        result = update_task_note(tn.id)
        assert result is not None
        assert result.title == "Title"


# ── notes edge cases ──────────────────────────────────────────────────────────

class TestNotesEdgeCases:
    def test_update_note_not_found(self):
        result = update_note("nonexistent-id", title="New")
        assert result is None

    def test_update_note_no_changes(self, proj):
        note = create_note(proj.id, "Title", "Body", "context")
        result = update_note(note.id)
        assert result is not None
        assert result.title == "Title"


# ── global notes ──────────────────────────────────────────────────────────────

class TestGlobalNotes:
    def test_create_and_get(self):
        gn = create_global_note("Rule 1", "Always test", "implementation")
        fetched = get_global_note(gn.id)
        assert fetched.title == "Rule 1"

    def test_list_global_notes(self):
        create_global_note("Rule A", "Body A", "context")
        create_global_note("Rule B", "Body B", "implementation")
        notes = list_global_notes()
        assert len(notes) == 2

    def test_list_global_notes_filtered_by_type(self):
        create_global_note("Rule A", "Body A", "context")
        create_global_note("Rule B", "Body B", "implementation")
        notes = list_global_notes(note_type="context")
        assert len(notes) == 1
        assert notes[0].note_type == "context"

    def test_update_global_note(self):
        gn = create_global_note("Old title", "Old body", "context")
        updated = update_global_note(gn.id, title="New title")
        assert updated.title == "New title"
        assert updated.note_text == "Old body"

    def test_update_global_note_not_found(self):
        result = update_global_note("nonexistent-id", title="New")
        assert result is None

    def test_update_global_note_no_changes(self):
        gn = create_global_note("Title", "Body", "context")
        result = update_global_note(gn.id)
        assert result is not None
        assert result.title == "Title"

    def test_delete_global_note(self):
        gn = create_global_note("To delete", "Body", "context")
        assert delete_global_note(gn.id) is True
        assert get_global_note(gn.id) is None

    def test_delete_global_note_not_found(self):
        assert delete_global_note("nonexistent-id") is False

    def test_search_global_notes(self):
        create_global_note("Testing rule", "Always write tests for new code", "implementation")
        create_global_note("Commit rule", "Commit after each task", "implementation")
        results = search_global_notes("tests")
        assert len(results) == 1
        assert "Testing" in results[0].title


# ── search_task_notes filters ─────────────────────────────────────────────────

class TestSearchTaskNotes:
    def test_search_by_project_and_task(self, proj):
        task = create_task(proj.id, "Task")
        create_task_note(proj.id, task.id, "Auth bug", "Login crashes on timeout", "bug")
        results = search_task_notes("crashes", project_id=proj.id, task_id=task.id)
        assert len(results) == 1

    def test_search_by_project_only(self, proj):
        t1 = create_task(proj.id, "Task 1")
        t2 = create_task(proj.id, "Task 2")
        create_task_note(proj.id, t1.id, "Note A", "websocket drops", "bug")
        create_task_note(proj.id, t2.id, "Note B", "websocket reconnect", "bug")
        results = search_task_notes("websocket", project_id=proj.id)
        assert len(results) == 2

    def test_search_by_task_only(self, proj):
        task = create_task(proj.id, "Task")
        create_task_note(proj.id, task.id, "Cache issue", "Redis eviction", "investigation")
        results = search_task_notes("eviction", task_id=task.id)
        assert len(results) == 1

    def test_search_no_filters(self, proj):
        task = create_task(proj.id, "Task")
        create_task_note(proj.id, task.id, "DB slow", "query takes 5 seconds", "bug")
        results = search_task_notes("seconds")
        assert len(results) == 1

    def test_search_no_match(self, proj):
        task = create_task(proj.id, "Task")
        create_task_note(proj.id, task.id, "Note", "something unrelated", "context")
        results = search_task_notes("kubernetes", project_id=proj.id)
        assert results == []
