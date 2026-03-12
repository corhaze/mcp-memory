"""
tests/test_server_tools.py — unit tests for MCP server tool functions.

Server tools are plain Python functions returning formatted strings.
They are tested by calling them directly and asserting on their output.
"""

import pytest
import mcp_memory.server.projects as srv_projects
import mcp_memory.server.tasks as srv_tasks
import mcp_memory.server.decisions as srv_decisions
import mcp_memory.server.notes as srv_notes


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_server.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def proj_id():
    result = srv_projects.create_project("test-proj", description="A test project")
    # Extract ID from "Project 'test-proj' ready (id: <uuid>)..."
    return result.split("id: ")[1].split(")")[0]


@pytest.fixture
def task_id(proj_id):
    result = srv_tasks.create_task(proj_id, "Test task", description="Do something")
    return result.split("id: ")[1].split(",")[0]


# ── Projects ──────────────────────────────────────────────────────────────────

class TestProjectTools:
    def test_create_project(self):
        result = srv_projects.create_project("my-proj")
        assert "my-proj" in result
        assert "id:" in result

    def test_create_project_with_summary(self):
        result = srv_projects.create_project("summ-proj", summary="This is the summary")
        assert "with summary" in result

    def test_create_project_without_summary_hints(self):
        result = srv_projects.create_project("no-summ-proj")
        assert "consider adding a summary" in result

    def test_get_project_found(self, proj_id):
        result = srv_projects.get_project("test-proj")
        assert "test-proj" in result
        assert proj_id in result

    def test_get_project_not_found(self):
        result = srv_projects.get_project("nonexistent")
        assert "not found" in result

    def test_list_projects(self):
        srv_projects.create_project("proj-a")
        srv_projects.create_project("proj-b")
        result = srv_projects.list_projects()
        assert "proj-a" in result
        assert "proj-b" in result

    def test_list_projects_empty(self):
        result = srv_projects.list_projects()
        assert "No projects found" in result

    def test_update_project(self, proj_id):
        result = srv_projects.update_project("test-proj", status="archived")
        assert "Updated" in result

    def test_update_project_not_found(self):
        result = srv_projects.update_project("ghost-proj", status="archived")
        assert "not found" in result

    def test_add_project_summary(self, proj_id):
        result = srv_projects.add_project_summary(proj_id, "Summary text")
        assert "Summary added" in result

    def test_add_project_summary_not_found(self):
        result = srv_projects.add_project_summary("bad-id", "text")
        assert "not found" in result

    def test_get_project_summary(self, proj_id):
        srv_projects.add_project_summary(proj_id, "My summary text")
        result = srv_projects.get_project_summary(proj_id)
        assert "My summary text" in result

    def test_get_project_summary_none(self, proj_id):
        result = srv_projects.get_project_summary(proj_id)
        assert "No summary found" in result

    def test_list_project_summaries(self, proj_id):
        srv_projects.add_project_summary(proj_id, "First summary")
        result = srv_projects.list_project_summaries(proj_id)
        assert "1 summary" in result

    def test_list_project_summaries_not_found(self):
        result = srv_projects.list_project_summaries("bad-id")
        assert "not found" in result


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TestTaskTools:
    def test_create_task(self, proj_id):
        result = srv_tasks.create_task(proj_id, "My task")
        assert "My task" in result
        assert "id:" in result

    def test_create_task_project_not_found(self):
        result = srv_tasks.create_task("bad-proj", "Task")
        assert "not found" in result

    def test_get_task(self, proj_id, task_id):
        result = srv_tasks.get_task(task_id)
        assert "Test task" in result
        assert task_id in result

    def test_get_task_not_found(self):
        result = srv_tasks.get_task("bad-id")
        assert "not found" in result

    def test_get_task_with_subtasks(self, proj_id, task_id):
        srv_tasks.create_task(proj_id, "Subtask", parent_task_id=task_id)
        result = srv_tasks.get_task(task_id)
        assert "Subtask" in result
        assert "Subtasks" in result

    def test_get_task_with_next_action(self, proj_id):
        result = srv_tasks.create_task(proj_id, "Task with action")
        tid = result.split("id: ")[1].split(",")[0]
        srv_tasks.update_task(tid, next_action="Do the thing")
        detail = srv_tasks.get_task(tid)
        assert "Do the thing" in detail

    def test_list_tasks(self, proj_id, task_id):
        result = srv_tasks.list_tasks(proj_id)
        assert "Test task" in result
        assert "1 task" in result

    def test_list_tasks_project_not_found(self):
        result = srv_tasks.list_tasks("bad-proj")
        assert "not found" in result

    def test_list_tasks_empty(self, proj_id):
        result = srv_tasks.list_tasks(proj_id)
        assert "No tasks found" in result

    def test_list_tasks_status_filter(self, proj_id, task_id):
        srv_tasks.update_task(task_id, status="done")
        result = srv_tasks.list_tasks(proj_id, status="open")
        assert "No tasks found" in result

    def test_list_tasks_all_parent(self, proj_id, task_id):
        srv_tasks.create_task(proj_id, "Subtask", parent_task_id=task_id)
        result = srv_tasks.list_tasks(proj_id, parent_task_id="all")
        assert "2 task" in result

    def test_list_tasks_urgent_flag(self, proj_id):
        result = srv_tasks.create_task(proj_id, "Urgent task", urgent=True)
        tid = result.split("id: ")[1].split(",")[0]
        listing = srv_tasks.list_tasks(proj_id)
        assert "[!]" in listing

    def test_update_task(self, task_id):
        result = srv_tasks.update_task(task_id, status="in_progress")
        assert "in_progress" in result

    def test_update_task_not_found(self):
        result = srv_tasks.update_task("bad-id", title="New")
        assert "not found" in result

    def test_delete_task(self, task_id):
        result = srv_tasks.delete_task(task_id)
        assert "deleted" in result

    def test_delete_task_not_found(self):
        result = srv_tasks.delete_task("bad-id")
        assert "not found" in result

    def test_log_task_event(self, task_id):
        result = srv_tasks.log_task_event(task_id, "started", "Beginning work")
        assert "started" in result

    def test_get_task_events(self, task_id):
        srv_tasks.log_task_event(task_id, "updated", "Made a change")
        result = srv_tasks.get_task_events(task_id)
        assert "event" in result

    def test_get_task_shows_blocked_by(self, proj_id, task_id):
        r2 = srv_tasks.create_task(proj_id, "Blocked task", blocked_by_task_id=task_id)
        tid2 = r2.split("id: ")[1].split(",")[0]
        result = srv_tasks.get_task(tid2)
        assert "Blocked by" in result

    def test_get_task_shows_parent(self, proj_id, task_id):
        r2 = srv_tasks.create_task(proj_id, "Child task", parent_task_id=task_id)
        tid2 = r2.split("id: ")[1].split(",")[0]
        result = srv_tasks.get_task(tid2)
        assert "Parent" in result

    def test_get_task_shows_notes(self, proj_id, task_id):
        srv_notes.create_task_note(task_id, "A note", "Body", "bug")
        result = srv_tasks.get_task(task_id)
        assert "Notes" in result
        assert "A note" in result

    def test_get_task_events_no_task(self):
        result = srv_tasks.get_task_events("nonexistent-id")
        assert "No events found" in result


# ── Decisions ─────────────────────────────────────────────────────────────────

class TestDecisionTools:
    def test_create_decision(self, proj_id):
        result = srv_decisions.create_decision(proj_id, "Use SQLite", "SQLite is sufficient")
        assert "Use SQLite" in result
        assert "id:" in result

    def test_create_decision_project_not_found(self):
        result = srv_decisions.create_decision("bad-proj", "Title", "Text")
        assert "not found" in result

    def test_get_decision(self, proj_id):
        r = srv_decisions.create_decision(proj_id, "Use WAL", "WAL mode for performance")
        did = r.split("id: ")[1].split(")")[0]
        result = srv_decisions.get_decision(did)
        assert "Use WAL" in result

    def test_get_decision_not_found(self):
        result = srv_decisions.get_decision("bad-id")
        assert "not found" in result

    def test_list_decisions(self, proj_id):
        srv_decisions.create_decision(proj_id, "Dec A", "Text A")
        srv_decisions.create_decision(proj_id, "Dec B", "Text B")
        result = srv_decisions.list_decisions(proj_id)
        assert "Dec A" in result
        assert "Dec B" in result

    def test_list_decisions_empty(self, proj_id):
        result = srv_decisions.list_decisions(proj_id)
        assert "No decisions found" in result

    def test_list_decisions_project_not_found(self):
        result = srv_decisions.list_decisions("bad-proj")
        assert "not found" in result

    def test_get_decision_with_rationale_and_supersedes(self, proj_id):
        r = srv_decisions.create_decision(proj_id, "Old dec", "Old text", rationale="Because")
        did = r.split("id: ")[1].split(")")[0]
        r2 = srv_decisions.supersede_decision(did, proj_id, "New dec", "New text", rationale="Improved")
        new_did = r2.split("id: ")[1].split(")")[0]
        result = srv_decisions.get_decision(new_did)
        assert "New dec" in result

    def test_update_decision(self, proj_id):
        r = srv_decisions.create_decision(proj_id, "Dec", "Text")
        did = r.split("id: ")[1].split(")")[0]
        result = srv_decisions.update_decision(did, status="draft")
        assert "draft" in result

    def test_update_decision_not_found(self):
        result = srv_decisions.update_decision("bad-id", title="New")
        assert "not found" in result

    def test_supersede_decision_project_not_found(self, proj_id):
        r = srv_decisions.create_decision(proj_id, "Dec", "Text")
        did = r.split("id: ")[1].split(")")[0]
        result = srv_decisions.supersede_decision(did, "bad-proj", "New", "Text")
        assert "not found" in result


# ── Notes ─────────────────────────────────────────────────────────────────────

class TestNoteTools:
    def test_create_note(self, proj_id):
        result = srv_notes.create_note(proj_id, "My note", "Note body", "bug")
        assert "My note" in result

    def test_create_note_project_not_found(self):
        result = srv_notes.create_note("bad-proj", "Title", "Body")
        assert "not found" in result

    def test_get_note(self, proj_id):
        r = srv_notes.create_note(proj_id, "Finding", "Important context", "investigation")
        nid = r.split("id: ")[1].rstrip(")")
        result = srv_notes.get_note(nid)
        assert "Finding" in result
        assert "Important context" in result

    def test_get_note_not_found(self):
        result = srv_notes.get_note("bad-id")
        assert "not found" in result

    def test_list_notes(self, proj_id):
        srv_notes.create_note(proj_id, "Note A", "Body A", "context")
        srv_notes.create_note(proj_id, "Note B", "Body B", "bug")
        result = srv_notes.list_notes(proj_id)
        assert "Note A" in result
        assert "Note B" in result

    def test_list_notes_project_not_found(self):
        result = srv_notes.list_notes("bad-proj")
        assert "not found" in result

    def test_create_task_note(self, proj_id, task_id):
        result = srv_notes.create_task_note(task_id, "Task finding", "Found a bug", "bug")
        assert "Task finding" in result

    def test_create_task_note_task_not_found(self):
        result = srv_notes.create_task_note("bad-id", "Title", "Body")
        assert "not found" in result

    def test_list_task_notes(self, proj_id, task_id):
        srv_notes.create_task_note(task_id, "Note 1", "Body", "context")
        result = srv_notes.list_task_notes(task_id)
        assert "Note 1" in result

    def test_create_global_note(self):
        result = srv_notes.create_global_note("Always test", "Write tests for everything", "implementation")
        assert "Always test" in result
        assert "id:" in result

    def test_list_global_notes(self):
        srv_notes.create_global_note("Rule A", "Body A", "context")
        srv_notes.create_global_note("Rule B", "Body B", "implementation")
        result = srv_notes.list_global_notes()
        assert "Rule A" in result
        assert "Rule B" in result
