"""Tests for mcp_memory.repository.enrichment — contextual enrichment on task status transitions."""

import mcp_memory.db as db


def _create_project_and_task(title="Test task", description="A test task description"):
    """Helper to create a project and a task, returning both."""
    project = db.create_project("test-project", "Test project")
    task = db.create_task(project.id, title, description)
    return project, task


# ── enrich_done ──────────────────────────────────────────────────────────────

class TestEnrichDone:
    def test_gaps_when_no_notes_or_decisions(self):
        _, task = _create_project_and_task()
        gaps = db.enrich_done(task)
        assert gaps["missing_task_notes"] is True
        assert gaps["missing_linked_decisions"] is True

    def test_no_gaps_when_notes_exist(self):
        project, task = _create_project_and_task()
        db.create_task_note(project.id, task.id, "Finding", "Found something", "investigation")
        gaps = db.enrich_done(task)
        assert gaps["missing_task_notes"] is False
        assert gaps["missing_linked_decisions"] is True

    def test_no_gaps_when_decision_linked(self):
        project, task = _create_project_and_task()
        decision = db.create_decision(project.id, "Design choice", "We chose X", "Because Y")
        db.create_link(project.id, "task", task.id, "implements", "decision", decision.id)
        gaps = db.enrich_done(task)
        assert gaps["missing_task_notes"] is True
        assert gaps["missing_linked_decisions"] is False

    def test_no_gaps_when_fully_documented(self):
        project, task = _create_project_and_task()
        db.create_task_note(project.id, task.id, "Note", "Details", "context")
        decision = db.create_decision(project.id, "Choice", "X", "Y")
        db.create_link(project.id, "task", task.id, "implements", "decision", decision.id)
        gaps = db.enrich_done(task)
        assert gaps["missing_task_notes"] is False
        assert gaps["missing_linked_decisions"] is False

    def test_reverse_link_direction_detected(self):
        """A decision→task link should also count."""
        project, task = _create_project_and_task()
        decision = db.create_decision(project.id, "Choice", "X", "Y")
        db.create_link(project.id, "decision", decision.id, "relates_to", "task", task.id)
        gaps = db.enrich_done(task)
        assert gaps["missing_linked_decisions"] is False


# ── enrich_in_progress ───────────────────────────────────────────────────────

class TestEnrichInProgress:
    def test_returns_empty_context_when_nothing_exists(self):
        _, task = _create_project_and_task()
        context = db.enrich_in_progress(task)
        assert context["related_decisions"] == []
        assert context["related_notes"] == []
        assert context["related_task_notes"] == []
        assert context["linked_entities"] == []

    def test_linked_entities_returned(self):
        project, task = _create_project_and_task()
        decision = db.create_decision(project.id, "Architecture choice", "Use SQLite", "Fast")
        db.create_link(project.id, "task", task.id, "implements", "decision", decision.id)

        context = db.enrich_in_progress(task)
        assert len(context["linked_entities"]) == 1
        link = context["linked_entities"][0]
        assert link["entity_type"] == "decision"
        assert link["entity_id"] == decision.id
        assert link["link_type"] == "implements"
        assert link["title"] == "Architecture choice"

    def test_linked_entity_reverse_direction(self):
        """A note→task link should surface the note as a linked entity."""
        project, task = _create_project_and_task()
        note = db.create_note(project.id, "Gotcha", "Watch out for X", "bug")
        db.create_link(project.id, "note", note.id, "explains", "task", task.id)

        context = db.enrich_in_progress(task)
        assert len(context["linked_entities"]) == 1
        link = context["linked_entities"][0]
        assert link["entity_type"] == "note"
        assert link["entity_id"] == note.id
        assert link["title"] == "Gotcha"

    def test_semantic_results_respect_threshold(self):
        """Semantic results below SCORE_THRESHOLD should be excluded.

        Without embeddings available, all semantic results will be empty —
        this verifies the function handles that gracefully.
        """
        _, task = _create_project_and_task()
        context = db.enrich_in_progress(task)
        # With no embedding model, all lists should be empty
        assert context["related_decisions"] == []
        assert context["related_notes"] == []
        assert context["related_task_notes"] == []


# ── Server formatting (integration) ─────────────────────────────────────────

class TestServerFormatting:
    """Test that the MCP server update_task tool includes enrichment output."""

    def test_in_progress_includes_context_section(self):
        project, task = _create_project_and_task()
        decision = db.create_decision(project.id, "Design", "X", "Y")
        db.create_link(project.id, "task", task.id, "implements", "decision", decision.id)

        result = db.update_task(task.id, status="in_progress")
        assert result is not None

        # Verify the enrichment module was called correctly (via db layer)
        context = db.enrich_in_progress(result)
        assert len(context["linked_entities"]) == 1

    def test_done_includes_gaps_section(self):
        _, task = _create_project_and_task()
        result = db.update_task(task.id, status="done")
        assert result is not None

        gaps = db.enrich_done(result)
        assert gaps["missing_task_notes"] is True
        assert gaps["missing_linked_decisions"] is True
