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
                    json={"title": "My note", "note_text": "Some context", "note_type": "context"})
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
        assert r.json() == []

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
        assert len(data) == 1
        assert data[0]["title"] == "Test task"
        assert "depth" in data[0]

    def test_get_tasks_status_filter(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks?status=done")
        assert r.status_code == 200
        assert r.json() == []

    def test_get_tasks_no_topo(self, proj, task):
        r = client.get(f"/api/projects/{proj['id']}/tasks?topo=false")
        assert r.status_code == 200
        assert len(r.json()) == 1

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
        data = r.json()
        titles = [t["title"] for t in data]
        assert titles.index("Blocker") < titles.index("Blocked")


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

    def test_empty_query_returns_empty_results(self, proj):
        """Blank/whitespace query returns empty results without hitting the model."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=")
        assert r.status_code == 200
        data = r.json()
        assert data["results"] == []

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
        """Endpoint accepts limit param; default is 15 (tested via no error with no param)."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=anything")
        assert r.status_code == 200

    def test_custom_limit_param_accepted(self, proj):
        """Explicit limit param is accepted without error."""
        r = client.get(f"/api/projects/{proj['id']}/search/semantic?q=anything&limit=5")
        assert r.status_code == 200
