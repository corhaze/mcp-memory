#!/usr/bin/env python3
"""
End-to-end test for the cross-project global search feature.

This test file validates all aspects of the global search feature:
1. Backend API tests (current project mode and all projects mode)
2. Backend API tests for proper grouping of results
3. Verification that search works with mixed entity types
4. Edge cases and error handling
"""

import pytest
from fastapi.testclient import TestClient
from mcp_memory.ui_server import app


client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_e2e.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


class TestCrossProjectGlobalSearch:
    """Test cross-project global search functionality."""

    def test_setup_two_projects_with_different_content(self, tmp_db):
        """
        Test Setup: Create two projects with different content.
        This mirrors the manual testing step.
        """
        # Create Project A
        r = client.post("/api/projects", json={"name": "Project-A"})
        assert r.status_code == 200
        proj_a = r.json()

        # Create Project B
        r = client.post("/api/projects", json={"name": "Project-B"})
        assert r.status_code == 200
        proj_b = r.json()

        # Create task in Project A
        r = client.post(f"/api/projects/{proj_a['id']}/tasks",
                       json={"title": "Alpha Task Design", "description": "Design the alpha module"})
        assert r.status_code == 200
        task_a = r.json()
        assert task_a['project_id'] == proj_a['id']

        # Create decision in Project A
        r = client.post(f"/api/projects/{proj_a['id']}/decisions",
                       json={"title": "Use FastAPI", "decision_text": "FastAPI for REST API"})
        assert r.status_code == 200
        decision_a = r.json()
        assert decision_a['project_id'] == proj_a['id']

        # Create note in Project A
        r = client.post(f"/api/projects/{proj_a['id']}/notes",
                       json={"title": "Alpha Notes", "note_text": "Important findings about alpha",
                            "note_type": "context"})
        assert r.status_code == 200
        note_a = r.json()
        assert note_a['project_id'] == proj_a['id']

        # Create task in Project B
        r = client.post(f"/api/projects/{proj_b['id']}/tasks",
                       json={"title": "Beta Task Optimization", "description": "Optimize beta module"})
        assert r.status_code == 200
        task_b = r.json()
        assert task_b['project_id'] == proj_b['id']

        # Create decision in Project B
        r = client.post(f"/api/projects/{proj_b['id']}/decisions",
                       json={"title": "Use SQLite", "decision_text": "SQLite for local storage"})
        assert r.status_code == 200
        decision_b = r.json()
        assert decision_b['project_id'] == proj_b['id']

        # Create note in Project B
        r = client.post(f"/api/projects/{proj_b['id']}/notes",
                       json={"title": "Beta Notes", "note_text": "Key findings about beta",
                            "note_type": "investigation"})
        assert r.status_code == 200
        note_b = r.json()
        assert note_b['project_id'] == proj_b['id']

    def test_scoped_search_project_a_only(self, tmp_db):
        """
        Test Current Project Mode: Search is scoped to active project.
        Searching in Project A should only return Project A results.
        """
        # Create two projects
        proj_a = client.post("/api/projects", json={"name": "Project-A"}).json()
        proj_b = client.post("/api/projects", json={"name": "Project-B"}).json()

        # Create "design" task in Project A
        client.post(f"/api/projects/{proj_a['id']}/tasks",
                   json={"title": "Design System", "description": "Create design system"})

        # Create "design" task in Project B
        client.post(f"/api/projects/{proj_b['id']}/tasks",
                   json={"title": "Design Pattern", "description": "Apply design patterns"})

        # Search with project_id filter (current project mode)
        r = client.get(f"/api/search?q=design&project_id={proj_a['id']}&limit=10")
        assert r.status_code == 200
        data = r.json()

        # Should only get results from Project A
        assert len(data['tasks']) >= 1
        for task in data['tasks']:
            assert task['project_id'] == proj_a['id']

        # Verify no Project B results
        proj_b_results = [t for t in data['tasks'] if t['project_id'] == proj_b['id']]
        assert len(proj_b_results) == 0

    def test_global_search_across_all_projects(self, tmp_db):
        """
        Test All Projects Mode: Search without project_id returns results from all projects.
        Results should be properly grouped by project.
        """
        # Create two projects
        proj_a = client.post("/api/projects", json={"name": "Project-A"}).json()
        proj_b = client.post("/api/projects", json={"name": "Project-B"}).json()

        # Create "database" content in both projects
        task_a = client.post(f"/api/projects/{proj_a['id']}/tasks",
                            json={"title": "Database Design"}).json()
        task_b = client.post(f"/api/projects/{proj_b['id']}/tasks",
                            json={"title": "Database Optimization"}).json()

        # Global search (no project_id filter)
        r = client.get("/api/search?q=database&limit=10")
        assert r.status_code == 200
        data = r.json()

        # Should get results from both projects
        task_ids = {t['id'] for t in data['tasks']}
        assert task_a['id'] in task_ids
        assert task_b['id'] in task_ids

        # Verify project_id is included in results
        assert all('project_id' in t for t in data['tasks'])

    def test_results_grouped_by_project_in_global_mode(self, tmp_db):
        """
        Test Result Grouping: Results returned from global search include project_id
        which enables proper grouping on the frontend.
        """
        # Create three projects
        proj_a = client.post("/api/projects", json={"name": "Alpha"}).json()
        proj_b = client.post("/api/projects", json={"name": "Beta"}).json()
        proj_c = client.post("/api/projects", json={"name": "Gamma"}).json()

        # Create "task" tasks in each project
        task_a = client.post(f"/api/projects/{proj_a['id']}/tasks",
                            json={"title": "Important Task"}).json()
        task_b = client.post(f"/api/projects/{proj_b['id']}/tasks",
                            json={"title": "Critical Task"}).json()
        task_c = client.post(f"/api/projects/{proj_c['id']}/tasks",
                            json={"title": "Urgent Task"}).json()

        # Global search for "task"
        r = client.get("/api/search?q=task&limit=10")
        assert r.status_code == 200
        data = r.json()

        # Verify all results have project_id
        for task in data['tasks']:
            assert 'project_id' in task
            assert task['project_id'] in [proj_a['id'], proj_b['id'], proj_c['id']]

        # Group results by project_id on the client side (simulating frontend)
        grouped = {}
        for task in data['tasks']:
            proj_id = task['project_id']
            if proj_id not in grouped:
                grouped[proj_id] = []
            grouped[proj_id].append(task)

        # Verify we have results from multiple projects
        assert len(grouped) == 3

    def test_search_all_entity_types_in_global_mode(self, tmp_db):
        """
        Test Mixed Entity Types: Global search returns properly grouped
        tasks, decisions, and notes from all projects.
        """
        # Create two projects
        proj_a = client.post("/api/projects", json={"name": "Proj-A"}).json()
        proj_b = client.post("/api/projects", json={"name": "Proj-B"}).json()

        # Create multiple entity types in Project A
        task_a = client.post(f"/api/projects/{proj_a['id']}/tasks",
                            json={"title": "Implement Framework"}).json()
        decision_a = client.post(f"/api/projects/{proj_a['id']}/decisions",
                                json={"title": "Framework Choice",
                                     "decision_text": "Use React for framework"}).json()
        note_a = client.post(f"/api/projects/{proj_a['id']}/notes",
                            json={"title": "Framework Notes",
                                 "note_text": "Framework is critical", "note_type": "context"}).json()

        # Create same entity types in Project B
        task_b = client.post(f"/api/projects/{proj_b['id']}/tasks",
                            json={"title": "Deploy Framework"}).json()
        decision_b = client.post(f"/api/projects/{proj_b['id']}/decisions",
                                json={"title": "Deployment Strategy",
                                     "decision_text": "Use containerization for framework"}).json()
        note_b = client.post(f"/api/projects/{proj_b['id']}/notes",
                            json={"title": "Deployment Notes",
                                 "note_text": "Framework deployment challenges",
                                 "note_type": "investigation"}).json()

        # Global search for "framework"
        r = client.get("/api/search?q=framework&limit=10")
        assert r.status_code == 200
        data = r.json()

        # Verify tasks exist and have project_id
        assert len(data['tasks']) >= 2
        for task in data['tasks']:
            assert task['project_id'] in [proj_a['id'], proj_b['id']]

        # Verify decisions exist and have project_id
        assert len(data['decisions']) >= 2
        for decision in data['decisions']:
            assert decision['project_id'] in [proj_a['id'], proj_b['id']]

        # Verify notes exist and have project_id
        assert len(data['notes']) >= 2
        for note in data['notes']:
            assert note['project_id'] in [proj_a['id'], proj_b['id']]

    def test_search_distinguishes_between_modes(self, tmp_db):
        """
        Test Mode Distinction: The /api/search endpoint properly handles
        both current project mode (with project_id) and all projects mode (without).
        """
        # Create two projects
        proj_a = client.post("/api/projects", json={"name": "ProjectOne"}).json()
        proj_b = client.post("/api/projects", json={"name": "ProjectTwo"}).json()

        # Create "search" content in both
        client.post(f"/api/projects/{proj_a['id']}/tasks",
                   json={"title": "Search Algorithm"})
        client.post(f"/api/projects/{proj_b['id']}/tasks",
                   json={"title": "Search Interface"})
        client.post(f"/api/projects/{proj_a['id']}/decisions",
                   json={"title": "Search Strategy", "decision_text": "Use semantic search"})
        client.post(f"/api/projects/{proj_b['id']}/notes",
                   json={"title": "Search Notes", "note_text": "Full-text search works",
                        "note_type": "context"})

        # Test scoped mode (project A only)
        r_scoped = client.get(f"/api/search?q=search&project_id={proj_a['id']}&limit=10")
        assert r_scoped.status_code == 200
        scoped_data = r_scoped.json()

        # Test global mode (all projects)
        r_global = client.get("/api/search?q=search&limit=10")
        assert r_global.status_code == 200
        global_data = r_global.json()

        # Global search should have at least as many results as scoped
        assert len(global_data['tasks']) >= len(scoped_data['tasks'])

        # All scoped results should be from Project A
        for task in scoped_data['tasks']:
            assert task['project_id'] == proj_a['id']

    def test_empty_search_returns_proper_response(self, tmp_db):
        """Test edge case: Empty search query returns empty results."""
        r = client.get("/api/search?q=&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert data['tasks'] == []
        assert data['decisions'] == []
        assert data['notes'] == []

    def test_no_results_found(self, tmp_db):
        """Test edge case: Search for non-existent term returns empty results."""
        # Create a project with content
        proj = client.post("/api/projects", json={"name": "TestProj"}).json()
        client.post(f"/api/projects/{proj['id']}/tasks",
                   json={"title": "Real Task"})

        # Search for non-existent term
        r = client.get("/api/search?q=nonexistentxyzabc&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert data['tasks'] == []
        assert data['decisions'] == []
        assert data['notes'] == []

    def test_project_id_consistency(self, tmp_db):
        """
        Test Data Consistency: All search results include correct project_id.
        This ensures proper grouping on the frontend.
        """
        # Create three projects
        proj_a = client.post("/api/projects", json={"name": "First"}).json()
        proj_b = client.post("/api/projects", json={"name": "Second"}).json()
        proj_c = client.post("/api/projects", json={"name": "Third"}).json()

        # Create entities
        client.post(f"/api/projects/{proj_a['id']}/tasks", json={"title": "Data Test"})
        client.post(f"/api/projects/{proj_b['id']}/decisions",
                   json={"title": "Data Architecture", "decision_text": "Data strategy"})
        client.post(f"/api/projects/{proj_c['id']}/notes",
                   json={"title": "Data Notes", "note_text": "Data consistency", "note_type": "context"})

        # Global search
        r = client.get("/api/search?q=data&limit=10")
        assert r.status_code == 200
        data = r.json()

        # Verify project IDs are correct and consistent
        project_ids = {proj_a['id'], proj_b['id'], proj_c['id']}

        for task in data['tasks']:
            assert task['project_id'] in project_ids
        for decision in data['decisions']:
            assert decision['project_id'] in project_ids
        for note in data['notes']:
            assert note['project_id'] in project_ids


class TestSearchUIToggleScenarios:
    """Test scenarios that simulate UI toggle interactions."""

    def test_toggle_between_modes(self, tmp_db):
        """
        Simulate user toggling between Current and All Projects modes.
        Verify that search requests are made with/without project_id.
        """
        # Setup: Create projects
        proj_a = client.post("/api/projects", json={"name": "Mode-A"}).json()
        proj_b = client.post("/api/projects", json={"name": "Mode-B"}).json()

        task_a = client.post(f"/api/projects/{proj_a['id']}/tasks",
                            json={"title": "Toggle Test"}).json()
        task_b = client.post(f"/api/projects/{proj_b['id']}/tasks",
                            json={"title": "Toggle Test"}).json()

        # Step 1: User is in Project A in "Current" mode
        r1 = client.get(f"/api/search?q=toggle&project_id={proj_a['id']}&limit=10")
        assert len(r1.json()['tasks']) == 1

        # Step 2: User switches to "All Projects" mode
        r2 = client.get("/api/search?q=toggle&limit=10")
        assert len(r2.json()['tasks']) >= 2

        # Step 3: User switches back to "Current" mode in Project B
        r3 = client.get(f"/api/search?q=toggle&project_id={proj_b['id']}&limit=10")
        assert len(r3.json()['tasks']) == 1
        assert r3.json()['tasks'][0]['project_id'] == proj_b['id']

    def test_switching_projects_in_current_mode(self, tmp_db):
        """
        Simulate user switching between projects while in Current mode.
        Search should automatically update based on active project.
        """
        # Create projects with distinct content
        proj_x = client.post("/api/projects", json={"name": "Project-X"}).json()
        proj_y = client.post("/api/projects", json={"name": "Project-Y"}).json()

        client.post(f"/api/projects/{proj_x['id']}/tasks",
                   json={"title": "X-Ray System"})
        client.post(f"/api/projects/{proj_y['id']}/tasks",
                   json={"title": "Yoga Poses"})

        # User searches while in Project X
        r_x = client.get(f"/api/search?q=x&project_id={proj_x['id']}&limit=10")
        x_results = r_x.json()['tasks']

        # User searches while in Project Y
        r_y = client.get(f"/api/search?q=y&project_id={proj_y['id']}&limit=10")
        y_results = r_y.json()['tasks']

        # Results should be from respective projects only
        if len(x_results) > 0:
            assert all(t['project_id'] == proj_x['id'] for t in x_results)
        if len(y_results) > 0:
            assert all(t['project_id'] == proj_y['id'] for t in y_results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
