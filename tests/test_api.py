"""
tests/test_api.py — FastAPI REST API tests for mcp-memory UI server.

Uses FastAPI's TestClient (backed by httpx) to exercise every endpoint.
Each test class owns an isolated temporary database via the autouse fixture.
"""

import pytest
from fastapi.testclient import TestClient
from mcp_memory.ui_server import app

client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_api.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


@pytest.fixture
def proj(tmp_db):
    r = client.post("/api/projects", json={"name": "test-proj"})
    assert r.status_code == 200
    return r.json()


@pytest.fixture
def task(proj):
    r = client.post(f"/api/projects/{proj['id']}/tasks", json={"title": "Test task"})
    assert r.status_code == 200
    return r.json()


@pytest.fixture
def decision(proj):
    r = client.post(f"/api/projects/{proj['id']}/decisions",
                    json={"title": "Use SQLite", "decision_text": "SQLite is sufficient"})
    assert r.status_code == 200
    return r.json()


@pytest.fixture
def note(proj):
    r = client.post(f"/api/projects/{proj['id']}/notes",
                    json={"title": "My note", "note_text": "Some context"})
    assert r.status_code == 200
    return r.json()


# ── Projects ──────────────────────────────────────────────────────────────────

class TestProjectEndpoints:
    def test_list_projects_empty(self):
        r = client.get("/api/projects")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_projects(self, proj):
        r = client.get("/api/projects")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-proj"

    def test_create_project(self):
        r = client.post("/api/projects", json={"name": "new-proj", "description": "Desc"})
        assert r.status_code == 200
        assert r.json()["name"] == "new-proj"

    def test_get_project_context(self, proj):
        r = client.get(f"/api/projects/{proj['id']}")
        assert r.status_code == 200

    def test_get_project_context_404(self):
        r = client.get("/api/projects/nonexistent")
        assert r.status_code == 404

    def test_update_project(self, proj):
        r = client.patch(f"/api/projects/{proj['id']}", json={"status": "archived"})
        assert r.status_code == 200
        assert r.json()["id"] == proj["id"]

    def test_update_project_404(self):
        r = client.patch("/api/projects/bad-id", json={"status": "archived"})
        assert r.status_code == 404

    def test_delete_project(self, proj):
        r = client.delete(f"/api/projects/{proj['id']}")
        assert r.status_code == 200
        assert r.json()["deleted"] == "test-proj"

    def test_delete_project_404(self):
        r = client.delete("/api/projects/nonexistent")
        assert r.status_code == 404


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TestTaskEndpoints:
    def test_get_tasks_empty(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/tasks")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    def test_get_tasks_404(self):
        r = client.get("/api/projects/bad-id/tasks")
        assert r.status_code == 404

    def test_create_task(self, proj):
        r = client.post(f"/api/projects/{proj['id']}/tasks",
                        json={"title": "New task", "description": "Do something"})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "New task"
        assert data["status"] == "open"

    def test_create_task_404(self):
        r = client.post("/api/projects/bad-id/tasks", json={"title": "Task"})
        assert r.status_code == 404

    def test_get_tasks_returns_list(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test task"
        assert "depth" in data["items"][0]

    def test_get_tasks_status_filter(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks?status=done")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_tasks_no_topo(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks?topo=false")
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_update_task(self, proj, task):
        r = client.patch(f"/api/projects/{proj['id']}/tasks/{task['id']}",
                         json={"status": "in_progress"})
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_update_task_404(self, proj):
        r = client.patch(f"/api/projects/{proj['id']}/tasks/bad-id", json={"status": "done"})
        assert r.status_code == 404

    def test_delete_task(self, proj, task):
        r = client.delete(f"/api/projects/{proj['id']}/tasks/{task['id']}")
        assert r.status_code == 200
        assert r.json()["deleted"] == task["id"]

    def test_delete_task_404(self, proj):
        r = client.delete(f"/api/projects/{proj['id']}/tasks/bad-id")
        assert r.status_code == 404

    def test_topo_sort_dependency_ordering(self, proj):
        r1 = client.post(f"/api/projects/{proj['id']}/tasks", json={"title": "Blocker"})
        blocker_id = r1.json()["id"]
        client.post(f"/api/projects/{proj['id']}/tasks",
                    json={"title": "Blocked", "blocked_by_task_id": blocker_id})

        r = client.get(f"/api/projects/{proj['id']}/tasks")
        data = r.json()["items"]
        titles = [t["title"] for t in data]
        assert titles.index("Blocker") < titles.index("Blocked")

    def test_default_returns_all(self, proj):
        """Default limit=0 returns all tasks wrapped in a pagination envelope."""
        for i in range(3):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get(f"/api/projects/{proj['id']}/tasks")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["has_more"] is False

    def test_limit_and_offset(self, proj):
        """limit=2&offset=1 returns 2 items starting from index 1, has_more=True."""
        for i in range(5):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get(f"/api/projects/{proj['id']}/tasks?limit=2&offset=1")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert data["has_more"] is True

    def test_limit_zero_returns_all(self, proj):
        """Explicit limit=0 returns all tasks."""
        for i in range(4):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get(f"/api/projects/{proj['id']}/tasks?limit=0")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 4
        assert data["total"] == 4
        assert data["has_more"] is False

    def test_has_more_accurate_last_page(self, proj):
        """has_more is False when the last page is exactly reached."""
        for i in range(4):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        # Page 1 of 2: offset=0, limit=2 → has_more=True
        r1 = client.get(f"/api/projects/{proj['id']}/tasks?limit=2&offset=0")
        assert r1.json()["has_more"] is True

        # Page 2 of 2: offset=2, limit=2 → has_more=False
        r2 = client.get(f"/api/projects/{proj['id']}/tasks?limit=2&offset=2")
        assert r2.json()["has_more"] is False
        assert len(r2.json()["items"]) == 2


# ── Decisions ─────────────────────────────────────────────────────────────────

class TestDecisionEndpoints:
    def test_get_decisions_empty(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/decisions")
        assert r.status_code == 200
        assert r.json() == []

    def test_get_decisions_404(self):
        r = client.get("/api/projects/bad-id/decisions")
        assert r.status_code == 404

    def test_create_decision(self, proj):
        r = client.post(f"/api/projects/{proj['id']}/decisions",
                        json={"title": "Use WAL", "decision_text": "WAL mode is better",
                              "rationale": "Performance"})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Use WAL"
        assert data["rationale"] == "Performance"

    def test_create_decision_404(self):
        r = client.post("/api/projects/bad-id/decisions",
                        json={"title": "T", "decision_text": "D"})
        assert r.status_code == 404

    def test_get_decisions_with_filter(self, proj, decision):
        r = client.get(f"/api/projects/{proj['id']}/decisions?status=active")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_update_decision(self, proj, decision):
        r = client.patch(f"/api/projects/{proj['id']}/decisions/{decision['id']}",
                         json={"status": "superseded"})
        assert r.status_code == 200
        assert r.json()["status"] == "superseded"

    def test_update_decision_404(self, proj):
        r = client.patch(f"/api/projects/{proj['id']}/decisions/bad-id",
                         json={"status": "draft"})
        assert r.status_code == 404

    def test_delete_decision(self, proj, decision):
        r = client.delete(f"/api/projects/{proj['id']}/decisions/{decision['id']}")
        assert r.status_code == 200
        assert r.json()["deleted"] == decision["id"]

    def test_delete_decision_404(self, proj):
        r = client.delete(f"/api/projects/{proj['id']}/decisions/bad-id")
        assert r.status_code == 404


# ── Notes ─────────────────────────────────────────────────────────────────────

class TestNoteEndpoints:
    def test_get_notes_empty(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/notes")
        assert r.status_code == 200
        assert r.json() == []

    def test_get_notes_404(self):
        r = client.get("/api/projects/bad-id/notes")
        assert r.status_code == 404

    def test_create_note(self, proj):
        r = client.post(f"/api/projects/{proj['id']}/notes",
                        json={"title": "Finding", "note_text": "Something interesting",
                              "note_type": "investigation"})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Finding"
        assert data["note_type"] == "investigation"

    def test_create_note_404(self):
        r = client.post("/api/projects/bad-id/notes",
                        json={"title": "T", "note_text": "B"})
        assert r.status_code == 404

    def test_get_notes_type_filter(self, proj, note):
        r = client.get(f"/api/projects/{proj['id']}/notes?note_type=bug")
        assert r.status_code == 200
        assert r.json() == []

    def test_update_note(self, proj, note):
        r = client.patch(f"/api/projects/{proj['id']}/notes/{note['id']}",
                         json={"title": "Updated title"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated title"

    def test_update_note_404(self, proj):
        r = client.patch(f"/api/projects/{proj['id']}/notes/bad-id",
                         json={"title": "X"})
        assert r.status_code == 404

    def test_delete_note(self, proj, note):
        r = client.delete(f"/api/projects/{proj['id']}/notes/{note['id']}")
        assert r.status_code == 200
        assert r.json()["deleted"] == note["id"]

    def test_delete_note_404(self, proj):
        r = client.delete(f"/api/projects/{proj['id']}/notes/bad-id")
        assert r.status_code == 404

    def test_get_note_detail(self, proj, note):
        r = client.get(f"/api/projects/{proj['id']}/notes/{note['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == note["id"]
        assert data["title"] == note["title"]
        assert "links" in data
        assert isinstance(data["links"], list)

    def test_get_note_detail_404(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/notes/bad-id")
        assert r.status_code == 404


# ── Task Notes ────────────────────────────────────────────────────────────────

class TestTaskNoteEndpoints:
    def test_get_task_notes_empty(self, task):
        r = client.get(f"/api/tasks/{task['id']}/notes")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_task_note(self, task):
        r = client.post(f"/api/tasks/{task['id']}/notes",
                        json={"title": "Bug found", "note_text": "It crashes", "note_type": "bug"})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Bug found"
        assert data["task_id"] == task["id"]

    def test_create_task_note_404(self):
        r = client.post("/api/tasks/bad-id/notes",
                        json={"title": "T", "note_text": "B"})
        assert r.status_code == 404

    def test_get_task_notes_returns_list(self, task):
        client.post(f"/api/tasks/{task['id']}/notes",
                    json={"title": "Note A", "note_text": "Body A"})
        r = client.get(f"/api/tasks/{task['id']}/notes")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_delete_task_note(self, task):
        r = client.post(f"/api/tasks/{task['id']}/notes",
                        json={"title": "To delete", "note_text": "Body"})
        note_id = r.json()["id"]
        r2 = client.delete(f"/api/task-notes/{note_id}")
        assert r2.status_code == 200
        assert r2.json()["deleted"] == note_id

    def test_delete_task_note_404(self):
        r = client.delete("/api/task-notes/bad-id")
        assert r.status_code == 404


# ── Global Notes ──────────────────────────────────────────────────────────────

class TestGlobalNoteEndpoints:
    def test_get_global_notes_empty(self):
        r = client.get("/api/global-notes")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_global_note(self):
        r = client.post("/api/global-notes",
                        json={"title": "Always test", "note_text": "Write tests",
                              "note_type": "implementation"})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Always test"

    def test_get_global_notes_type_filter(self):
        client.post("/api/global-notes",
                    json={"title": "Rule A", "note_text": "Body", "note_type": "context"})
        client.post("/api/global-notes",
                    json={"title": "Rule B", "note_text": "Body", "note_type": "implementation"})
        r = client.get("/api/global-notes?note_type=context")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["note_type"] == "context"

    def test_update_global_note(self):
        r = client.post("/api/global-notes",
                        json={"title": "Old title", "note_text": "Body"})
        note_id = r.json()["id"]
        r2 = client.patch(f"/api/global-notes/{note_id}",
                          json={"title": "New title"})
        assert r2.status_code == 200
        assert r2.json()["title"] == "New title"

    def test_update_global_note_404(self):
        r = client.patch("/api/global-notes/bad-id", json={"title": "X"})
        assert r.status_code == 404

    def test_delete_global_note(self):
        r = client.post("/api/global-notes",
                        json={"title": "To delete", "note_text": "Body"})
        note_id = r.json()["id"]
        r2 = client.delete(f"/api/global-notes/{note_id}")
        assert r2.status_code == 200
        assert r2.json()["deleted"] == note_id

    def test_delete_global_note_404(self):
        r = client.delete("/api/global-notes/bad-id")
        assert r.status_code == 404

    def test_get_global_note_detail(self):
        r = client.post("/api/global-notes",
                        json={"title": "Detail test", "note_text": "Body"})
        note_id = r.json()["id"]
        r2 = client.get(f"/api/global-notes/{note_id}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["id"] == note_id
        assert data["title"] == "Detail test"
        assert "links" in data

    def test_get_global_note_detail_404(self):
        r = client.get("/api/global-notes/bad-id")
        assert r.status_code == 404


# ── Timeline ──────────────────────────────────────────────────────────────────

class TestTimelineEndpoint:
    def test_timeline_empty(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/timeline")
        assert r.status_code == 200
        assert r.json() == []

    def test_timeline_returns_events(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/timeline")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["task_title"] == "Test task"
        assert "event_type" in data[0]
        assert "created_at" in data[0]

    def test_timeline_404(self):
        r = client.get("/api/projects/bad-id/timeline")
        assert r.status_code == 404


class TestGlobalSearch:
    """Test the global /api/search endpoint with and without project_id filter."""

    def test_search_empty_query(self):
        """Empty query returns empty results."""
        r = client.get("/api/search?q=")
        assert r.status_code == 200
        data = r.json()
        assert data["tasks"] == []
        assert data["decisions"] == []
        assert data["notes"] == []

    def test_global_search_across_projects(self, tmp_db):
        """Search without project_id returns results from all projects."""
        # Create two projects with tasks
        proj1 = client.post("/api/projects", json={"name": "alpha"}).json()
        proj2 = client.post("/api/projects", json={"name": "beta"}).json()

        task1 = client.post(f"/api/projects/{proj1['id']}/tasks", json={"title": "database design"}).json()
        task2 = client.post(f"/api/projects/{proj2['id']}/tasks", json={"title": "database optimization"}).json()

        # Global search finds both tasks
        r = client.get("/api/search?q=database&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tasks"]) == 2
        task_ids = {t["id"] for t in data["tasks"]}
        assert task1["id"] in task_ids
        assert task2["id"] in task_ids

    def test_scoped_search_with_project_id(self, tmp_db):
        """Search with project_id parameter returns results from that project only."""
        # Create two projects with tasks
        proj1 = client.post("/api/projects", json={"name": "gamma"}).json()
        proj2 = client.post("/api/projects", json={"name": "delta"}).json()

        task1 = client.post(f"/api/projects/{proj1['id']}/tasks", json={"title": "api design"}).json()
        task2 = client.post(f"/api/projects/{proj2['id']}/tasks", json={"title": "api documentation"}).json()

        # Scoped search returns only results from proj1
        r = client.get(f"/api/search?q=api&project_id={proj1['id']}&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task1["id"]

    def test_search_includes_decisions_and_notes(self, tmp_db):
        """Global search includes decisions and notes from all projects."""
        proj = client.post("/api/projects", json={"name": "epsilon"}).json()
        client.post(f"/api/projects/{proj['id']}/tasks", json={"title": "testing framework"})
        client.post(f"/api/projects/{proj['id']}/decisions",
                   json={"title": "Test runner", "decision_text": "use pytest for testing"})
        client.post(f"/api/projects/{proj['id']}/notes",
                   json={"title": "Testing notes", "note_text": "testing is important", "note_type": "context"})

        r = client.get("/api/search?q=testing&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tasks"]) >= 1
        assert len(data["decisions"]) >= 1
        assert len(data["notes"]) >= 1

    def test_search_respects_limit(self, tmp_db):
        """Search respects the limit parameter."""
        proj = client.post("/api/projects", json={"name": "zeta"}).json()
        for i in range(5):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"task {i}"})

        # Default limit is 10, should get all 5
        r = client.get("/api/search?q=task&limit=10")
        assert len(r.json()["tasks"]) == 5

        # With limit=2, should get only 2
        r = client.get("/api/search?q=task&limit=2")
        assert len(r.json()["tasks"]) == 2


# ── Task Detail ───────────────────────────────────────────────────────────────

class TestTaskDetailEndpoint:
    def test_returns_task_fields(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks/{task['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == task["id"]
        assert data["title"] == task["title"]
        assert data["status"] == task["status"]

    def test_returns_404_for_unknown_task(self, proj):
        r = client.get(f"/api/projects/{proj['id']}/tasks/nonexistent")
        assert r.status_code == 404

    def test_returns_404_for_unknown_project(self, task):
        r = client.get(f"/api/projects/nonexistent/tasks/{task['id']}")
        assert r.status_code == 404

    def test_includes_subtasks(self, proj, task):
        client.post(f"/api/projects/{proj['id']}/tasks",
                    json={"title": "Subtask A", "parent_task_id": task["id"]})
        r = client.get(f"/api/projects/{proj['id']}/tasks/{task['id']}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["subtasks"]) == 1
        assert data["subtasks"][0]["title"] == "Subtask A"

    def test_includes_task_notes(self, proj, task):
        client.post(f"/api/tasks/{task['id']}/notes",
                    json={"title": "Note 1", "note_text": "Body", "note_type": "bug"})
        r = client.get(f"/api/projects/{proj['id']}/tasks/{task['id']}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["notes"]) == 1
        assert data["notes"][0]["title"] == "Note 1"

    def test_includes_events(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks/{task['id']}")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert len(data["events"]) >= 1


# ── Cross-project Task Listing ────────────────────────────────────────────────

class TestGetAllTasks:
    """Tests for GET /api/tasks (cross-project task listing)."""

    def test_returns_tasks_from_all_projects(self, tmp_db):
        proj1 = client.post("/api/projects", json={"name": "proj-alpha"}).json()
        proj2 = client.post("/api/projects", json={"name": "proj-beta"}).json()

        task1 = client.post(f"/api/projects/{proj1['id']}/tasks",
                            json={"title": "Alpha task"}).json()
        task2 = client.post(f"/api/projects/{proj2['id']}/tasks",
                            json={"title": "Beta task"}).json()

        r = client.get("/api/tasks")
        assert r.status_code == 200
        data = r.json()
        ids = {t["id"] for t in data["items"]}
        assert task1["id"] in ids
        assert task2["id"] in ids

    def test_includes_project_name(self, tmp_db):
        proj1 = client.post("/api/projects", json={"name": "proj-alpha"}).json()
        proj2 = client.post("/api/projects", json={"name": "proj-beta"}).json()

        client.post(f"/api/projects/{proj1['id']}/tasks", json={"title": "Alpha task"})
        client.post(f"/api/projects/{proj2['id']}/tasks", json={"title": "Beta task"})

        r = client.get("/api/tasks")
        assert r.status_code == 200
        data = r.json()
        names = {t["project_name"] for t in data["items"]}
        assert "proj-alpha" in names
        assert "proj-beta" in names

    def test_project_id_filter_returns_single_project(self, tmp_db):
        proj1 = client.post("/api/projects", json={"name": "proj-gamma"}).json()
        proj2 = client.post("/api/projects", json={"name": "proj-delta"}).json()

        task1 = client.post(f"/api/projects/{proj1['id']}/tasks",
                            json={"title": "Gamma task"}).json()
        task2 = client.post(f"/api/projects/{proj2['id']}/tasks",
                            json={"title": "Delta task"}).json()

        r = client.get(f"/api/tasks?project_id={proj1['id']}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == task1["id"]
        assert data["items"][0]["project_name"] == "proj-gamma"

    def test_returns_empty_when_no_projects(self, tmp_db):
        r = client.get("/api/tasks")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_status_filter(self, tmp_db):
        proj = client.post("/api/projects", json={"name": "proj-status"}).json()
        t1 = client.post(f"/api/projects/{proj['id']}/tasks",
                         json={"title": "Open task"}).json()
        t2 = client.post(f"/api/projects/{proj['id']}/tasks",
                         json={"title": "Done task", "status": "done"}).json()

        r = client.get("/api/tasks?status=done")
        assert r.status_code == 200
        data = r.json()
        ids = {t["id"] for t in data["items"]}
        assert t2["id"] in ids
        assert t1["id"] not in ids

    def test_limit_parameter(self, tmp_db):
        proj = client.post("/api/projects", json={"name": "proj-limit"}).json()
        for i in range(5):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get("/api/tasks?limit=3")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["has_more"] is True

    def test_all_tasks_paginated(self, tmp_db):
        """Paginated cross-project task listing: limit and offset work correctly."""
        proj = client.post("/api/projects", json={"name": "proj-paginate"}).json()
        for i in range(4):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get("/api/tasks?limit=2&offset=0")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 4
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert data["has_more"] is True

        r2 = client.get("/api/tasks?limit=2&offset=2")
        data2 = r2.json()
        assert len(data2["items"]) == 2
        assert data2["has_more"] is False

    def test_limit_zero_returns_all(self, tmp_db):
        """limit=0 means return all tasks without an upper bound."""
        proj = client.post("/api/projects", json={"name": "proj-nolimit"}).json()
        for i in range(5):
            client.post(f"/api/projects/{proj['id']}/tasks", json={"title": f"Task {i}"})

        r = client.get("/api/tasks?limit=0")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 5
        assert data["has_more"] is False


# ── Unified Semantic Search ────────────────────────────────────────────────────

class TestUnifiedSemanticSearch:
    """Tests for GET /api/projects/{project_id}/search/semantic."""

    def test_returns_200_when_embeddings_unavailable(self, proj):
        """When embeddings are off, returns 200 with empty results and embeddings_available=false."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=auth+bug")
        assert r.status_code == 200
        data = r.json()
        assert data["query"] == "auth bug"
        assert data["embeddings_available"] is False
        assert data["results"] == []

    def test_returns_404_for_unknown_project(self):
        """Unknown project_id returns 404."""
        r = client.get("/api/projects/does-not-exist/search/semantic?q=anything")
        assert r.status_code == 404

    def test_empty_query_rejected(self, proj):
        """Empty string query is rejected at the validation layer (min_length=1)."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=")
        assert r.status_code == 422

    def test_whitespace_only_query_returns_empty_results(self, proj):
        """Whitespace-only query is treated as empty."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=   ")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_response_shape(self, proj):
        """Response always has query, embeddings_available, and results keys."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=test")
        assert r.status_code == 200
        data = r.json()
        assert "query" in data
        assert "embeddings_available" in data
        assert "results" in data

    def test_default_limit_is_15(self, proj):
        """Smoke test: default limit param parses without error.

        Embeddings are off in tests so we verify the no-embeddings response
        contract rather than actual ranking behaviour.
        """
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=auth")
        assert r.status_code == 200
        data = r.json()
        assert data["embeddings_available"] is False
        assert data["results"] == []
        assert data["query"] == "auth"

    def test_results_include_project_name(self, proj, monkeypatch):
        """Each search result includes project_name for client-side navigation."""
        from unittest.mock import MagicMock
        import mcp_memory.embeddings as _emb
        import mcp_memory.db as _db
        from mcp_memory.repository.models import Task
        from datetime import datetime, timezone

        monkeypatch.setattr(_emb, "_model_available", True)

        fake_task = Task(
            id="task-abc", project_id=proj["id"], title="Auth task",
            description=None, status="open", urgent=False, complex=False,
            parent_task_id=None, assigned_agent=None, blocked_by_task_id=None,
            next_action=None, due_at=None,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            completed_at=None, subtasks=[],
        )
        monkeypatch.setattr(
            _db, "semantic_search_all",
            lambda q, pid, limit: [{"entity_type": "task", "score": 0.9, "entity": fake_task}],
        )

        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=auth")
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["project_name"] == proj["name"]

    def test_custom_limit_param_accepted(self, proj):
        """Smoke test: explicit limit param is parsed without error.

        Embeddings are off in tests so we verify the no-embeddings response
        contract rather than actual ranking behaviour.
        """
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=auth&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert data["embeddings_available"] is False
        assert data["results"] == []
        assert data["query"] == "auth"


# ── Global Semantic Search ────────────────────────────────────────────────────

class TestGlobalSemanticSearch:
    """Tests for GET /api/search/semantic (no project_id required)."""

    def test_returns_200_when_embeddings_unavailable(self):
        r = client.get("/api/search/semantic?q=anything")
        assert r.status_code == 200
        data = r.json()
        assert data["embeddings_available"] is False
        assert data["results"] == []

    def test_empty_query_rejected(self):
        r = client.get("/api/search/semantic?q=")
        assert r.status_code == 422

    def test_response_shape(self):
        r = client.get("/api/search/semantic?q=test")
        assert r.status_code == 200
        data = r.json()
        assert "query" in data
        assert "embeddings_available" in data
        assert "results" in data

    def test_results_include_project_name_per_entity(self, proj, monkeypatch):
        """Global results resolve project_name from entity's project_id."""
        from unittest.mock import MagicMock
        import mcp_memory.embeddings as _emb
        import mcp_memory.db as _db
        from mcp_memory.repository.models import Task, GlobalNote
        from datetime import datetime, timezone

        monkeypatch.setattr(_emb, "_model_available", True)

        now = datetime.now(timezone.utc).isoformat()
        fake_task = Task(
            id="task-abc", project_id=proj["id"], title="Auth task",
            description=None, status="open", urgent=False, complex=False,
            parent_task_id=None, assigned_agent=None, blocked_by_task_id=None,
            next_action=None, due_at=None,
            created_at=now, updated_at=now, completed_at=None, subtasks=[],
        )
        fake_global = GlobalNote(
            id="gn-abc", title="Code standards", note_text="Be clean",
            note_type="context", created_at=now, updated_at=now,
        )
        monkeypatch.setattr(
            _db, "semantic_search_all",
            lambda q, project_id, limit: [
                {"entity_type": "task", "score": 0.9, "entity": fake_task},
                {"entity_type": "global_note", "score": 0.8, "entity": fake_global},
            ],
        )

        r = client.get("/api/search/semantic?q=auth")
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 2
        assert results[0]["project_name"] == proj["name"]
        assert results[1]["project_name"] is None
