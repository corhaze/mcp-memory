"""
tests/test_db.py — pytest unit tests for mcp-memory storage layer.

Uses a temporary SQLite database for isolation — no disk side-effects.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

# ── Fixture: redirect DB to a temp file for every test ────────────────────────

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("mcp_memory.repository.connection.db_path", lambda: db_file)
    yield db_file


from mcp_memory.db import (
    # Projects
    create_project, get_project, list_projects, update_project, delete_project,
    # Summaries
    add_summary, get_current_summary, list_summaries,
    # Tasks
    create_task, get_task, list_tasks, update_task, delete_task, get_task_tree,
    # Task Events
    log_task_event, get_task_events,
    # Decisions
    create_decision, get_decision, list_decisions, update_decision, supersede_decision,
    # Notes
    create_note, get_note, list_notes, update_note, delete_note,
    # Task Notes
    create_task_note, get_task_note, list_task_notes, update_task_note, delete_task_note,
    # Global Notes
    create_global_note, get_global_note, list_global_notes, update_global_note, delete_global_note,
    # Documents
    create_document, get_document, list_documents, add_chunks, get_chunks,
    # Links
    create_link, get_links_for, delete_link,
    # Tags
    create_tag, list_tags, tag_entity, untag_entity, get_entities_by_tag,
    # Working context
    get_working_context,
)


# ── Projects ───────────────────────────────────────────────────────────────────

class TestProjects:
    def test_create_and_get_by_name(self):
        proj = create_project("alpha", "Test project")
        assert proj.name == "alpha"
        assert proj.description == "Test project"
        assert proj.status == "active"

        found = get_project("alpha")
        assert found is not None
        assert found.id == proj.id

    def test_create_idempotent_upserts(self):
        p1 = create_project("beta", "v1")
        p2 = create_project("beta", "v2-updated")
        assert p1.id == p2.id
        assert get_project("beta").description == "v2-updated"

    def test_get_by_id(self):
        proj = create_project("gamma")
        found = get_project(proj.id)
        assert found is not None
        assert found.name == "gamma"

    def test_get_missing_returns_none(self):
        assert get_project("no-such-project") is None

    def test_list_projects(self):
        create_project("p1")
        create_project("p2")
        create_project("p3", status="archived")
        all_projects = list_projects()
        assert len(all_projects) == 3

    def test_list_projects_filter_status(self):
        create_project("active-1")
        create_project("archived-1", status="archived")
        active = list_projects(status="active")
        assert len(active) == 1
        assert active[0].name == "active-1"

    def test_update_project_description(self):
        proj = create_project("updatable", "old description")
        updated = update_project("updatable", description="new description")
        assert updated.description == "new description"

    def test_update_project_status(self):
        create_project("archivable")
        updated = update_project("archivable", status="archived")
        assert updated.status == "archived"

    def test_delete_project(self):
        proj = create_project("deletable")
        assert delete_project("deletable") is True
        assert get_project(proj.id) is None

    def test_delete_missing_returns_false(self):
        assert delete_project("nonexistent") is False


# ── Project Summaries ──────────────────────────────────────────────────────────

class TestProjectSummaries:
    def setup_method(self):
        self.proj = create_project("summary-proj")

    def test_add_and_get_current(self):
        add_summary(self.proj.id, "First summary", "current")
        s = get_current_summary(self.proj.id)
        assert s is not None
        assert s.summary_text == "First summary"
        assert s.summary_kind == "current"

    def test_latest_current_returned(self):
        add_summary(self.proj.id, "Old summary", "current")
        add_summary(self.proj.id, "New summary", "current")
        s = get_current_summary(self.proj.id)
        assert s.summary_text == "New summary"

    def test_list_summaries_all(self):
        add_summary(self.proj.id, "Current", "current")
        add_summary(self.proj.id, "Milestone", "milestone")
        summaries = list_summaries(self.proj.id)
        assert len(summaries) == 2

    def test_list_summaries_filter_kind(self):
        add_summary(self.proj.id, "Current", "current")
        add_summary(self.proj.id, "Handover", "handover")
        handovers = list_summaries(self.proj.id, summary_kind="handover")
        assert len(handovers) == 1
        assert handovers[0].summary_text == "Handover"

    def test_no_summary_returns_none(self):
        assert get_current_summary(self.proj.id) is None


# ── Tasks ──────────────────────────────────────────────────────────────────────

class TestTasks:
    def setup_method(self):
        self.proj = create_project("task-proj")

    def test_create_task_defaults(self):
        t = create_task(self.proj.id, "Write tests")
        assert t.title == "Write tests"
        assert t.status == "open"
        assert t.urgent is False
        assert t.parent_task_id is None

    def test_create_task_with_all_fields(self):
        t = create_task(
            self.proj.id, "Complex task",
            description="Do many things",
            status="in_progress",
            urgent=True,
            complex=True,
            next_action="Start with step 1",
        )
        assert t.status == "in_progress"
        assert t.urgent is True
        assert t.complex is True
        assert t.next_action == "Start with step 1"

    def test_get_task(self):
        t = create_task(self.proj.id, "Fetchable")
        fetched = get_task(t.id)
        assert fetched is not None
        assert fetched.id == t.id

    def test_get_missing_task_returns_none(self):
        assert get_task("nonexistent-id") is None

    def test_list_tasks_top_level_only(self):
        parent = create_task(self.proj.id, "Parent")
        create_task(self.proj.id, "Child", parent_task_id=parent.id)
        top_level = list_tasks(self.proj.id, parent_task_id="_root_")
        assert len(top_level) == 1
        assert top_level[0].id == parent.id

    def test_list_tasks_all(self):
        parent = create_task(self.proj.id, "Parent")
        create_task(self.proj.id, "Child", parent_task_id=parent.id)
        all_tasks = list_tasks(self.proj.id, parent_task_id=None)
        assert len(all_tasks) == 2

    def test_list_tasks_filter_status(self):
        create_task(self.proj.id, "Open task")
        create_task(self.proj.id, "Done task", status="done")
        open_tasks = list_tasks(self.proj.id, status="open", parent_task_id=None)
        assert len(open_tasks) == 1
        assert open_tasks[0].title == "Open task"

    def test_update_task_status(self):
        t = create_task(self.proj.id, "To update")
        updated = update_task(t.id, status="in_progress")
        assert updated.status == "in_progress"

    def test_update_task_to_done_sets_completed_at(self):
        t = create_task(self.proj.id, "To complete")
        updated = update_task(t.id, status="done")
        assert updated.status == "done"
        assert updated.completed_at is not None

    def test_update_task_description(self):
        t = create_task(self.proj.id, "Describable", description="Old desc")
        updated = update_task(t.id, description="New desc")
        assert updated.description == "New desc"

    def test_delete_task(self):
        t = create_task(self.proj.id, "Deletable")
        assert delete_task(t.id) is True
        assert get_task(t.id) is None

    def test_delete_missing_task_returns_false(self):
        assert delete_task("nonexistent") is False

    def test_parent_child_relationship(self):
        parent = create_task(self.proj.id, "Parent task")
        child1 = create_task(self.proj.id, "Child 1", parent_task_id=parent.id)
        child2 = create_task(self.proj.id, "Child 2", parent_task_id=parent.id)
        fetched_parent = get_task(parent.id)
        assert len(fetched_parent.subtasks) == 2
        subtask_ids = {st.id for st in fetched_parent.subtasks}
        assert child1.id in subtask_ids
        assert child2.id in subtask_ids

    def test_blocked_by_relationship(self):
        blocker = create_task(self.proj.id, "Blocker")
        blocked = create_task(self.proj.id, "Blocked", blocked_by_task_id=blocker.id)
        assert blocked.blocked_by_task_id == blocker.id

    def test_get_task_tree(self):
        parent = create_task(self.proj.id, "Parent")
        create_task(self.proj.id, "Child A", parent_task_id=parent.id)
        create_task(self.proj.id, "Child B", parent_task_id=parent.id)
        tree = get_task_tree(self.proj.id)
        assert len(tree) == 1
        assert len(tree[0].subtasks) == 2

    def test_project_isolation(self):
        proj2 = create_project("other-proj")
        create_task(self.proj.id, "Task for proj1")
        create_task(proj2.id, "Task for proj2")
        p1_tasks = list_tasks(self.proj.id, parent_task_id=None)
        p2_tasks = list_tasks(proj2.id, parent_task_id=None)
        assert len(p1_tasks) == 1
        assert len(p2_tasks) == 1


# ── Task Events ────────────────────────────────────────────────────────────────

class TestTaskEvents:
    def setup_method(self):
        self.proj = create_project("events-proj")
        self.task = create_task(self.proj.id, "Tracked task")

    def test_create_task_auto_logs_created_event(self):
        events = get_task_events(self.task.id)
        assert any(e.event_type == "created" for e in events)

    def test_manual_log_event(self):
        ev = log_task_event(self.task.id, "started", "Beginning implementation")
        assert ev.task_id == self.task.id
        assert ev.event_type == "started"
        assert ev.event_note == "Beginning implementation"

    def test_events_in_chronological_order(self):
        log_task_event(self.task.id, "started")
        log_task_event(self.task.id, "blocked", "Waiting on API")
        log_task_event(self.task.id, "unblocked")
        events = get_task_events(self.task.id)
        event_types = [e.event_type for e in events]
        assert event_types.index("started") < event_types.index("blocked")
        assert event_types.index("blocked") < event_types.index("unblocked")

    def test_update_task_logs_event(self):
        update_task(self.task.id, status="done")
        events = get_task_events(self.task.id)
        assert any(e.event_type == "completed" for e in events)

    def test_get_task_events_limit(self):
        for i in range(10):
            log_task_event(self.task.id, "note", f"Note {i}")
        events = get_task_events(self.task.id, limit=5)
        assert len(events) == 5


# ── Decisions ──────────────────────────────────────────────────────────────────

class TestDecisions:
    def setup_method(self):
        self.proj = create_project("decisions-proj")

    def test_create_and_get(self):
        d = create_decision(
            self.proj.id, "Use SQLite",
            "SQLite will be the primary data store.",
            rationale="Simple, no server needed",
        )
        assert d.title == "Use SQLite"
        assert d.status == "active"

        fetched = get_decision(d.id)
        assert fetched is not None
        assert fetched.rationale == "Simple, no server needed"

    def test_list_decisions_all(self):
        create_decision(self.proj.id, "D1", "Text 1")
        create_decision(self.proj.id, "D2", "Text 2")
        decisions = list_decisions(self.proj.id)
        assert len(decisions) == 2

    def test_list_decisions_filter_status(self):
        create_decision(self.proj.id, "Active", "Active decision")
        d_draft = create_decision(self.proj.id, "Draft", "Draft decision", status="draft")
        active_only = list_decisions(self.proj.id, status="active")
        assert len(active_only) == 1
        assert active_only[0].title == "Active"

    def test_update_decision(self):
        d = create_decision(self.proj.id, "Updatable", "Old text")
        updated = update_decision(d.id, decision_text="New text")
        assert updated.decision_text == "New text"

    def test_supersede_decision(self):
        old = create_decision(self.proj.id, "Old approach", "Use approach A")
        new = supersede_decision(old.id, self.proj.id, "New approach", "Use approach B")

        assert new.status == "active"
        assert new.supersedes_decision_id == old.id

        old_reloaded = get_decision(old.id)
        assert old_reloaded.status == "superseded"

    def test_supersede_chain(self):
        d1 = create_decision(self.proj.id, "V1", "Version 1")
        d2 = supersede_decision(d1.id, self.proj.id, "V2", "Version 2")
        d3 = supersede_decision(d2.id, self.proj.id, "V3", "Version 3")

        assert get_decision(d1.id).status == "superseded"
        assert get_decision(d2.id).status == "superseded"
        assert d3.status == "active"

        active = list_decisions(self.proj.id, status="active")
        assert len(active) == 1
        assert active[0].id == d3.id

    def test_get_missing_decision_returns_none(self):
        assert get_decision("no-such-decision") is None


# ── Notes ──────────────────────────────────────────────────────────────────────

class TestNotes:
    def setup_method(self):
        self.proj = create_project("notes-proj")

    def test_create_and_get(self):
        note = create_note(self.proj.id, "My finding", "SQLite is fast for reads.")
        assert note.note_type == "context"
        fetched = get_note(note.id)
        assert fetched.title == "My finding"

    def test_create_with_type(self):
        note = create_note(self.proj.id, "Bug found", "NPE in export.py", note_type="bug")
        assert note.note_type == "bug"

    def test_list_notes_all(self):
        create_note(self.proj.id, "N1", "text1")
        create_note(self.proj.id, "N2", "text2", note_type="bug")
        notes = list_notes(self.proj.id)
        assert len(notes) == 2

    def test_list_notes_filter_type(self):
        create_note(self.proj.id, "Context note", "ctx")
        create_note(self.proj.id, "Bug note", "bug", note_type="bug")
        bugs = list_notes(self.proj.id, note_type="bug")
        assert len(bugs) == 1
        assert bugs[0].title == "Bug note"

    def test_update_note(self):
        note = create_note(self.proj.id, "Updatable", "old text")
        updated = update_note(note.id, note_text="new text")
        assert updated.note_text == "new text"

    def test_update_note_type(self):
        note = create_note(self.proj.id, "Reclassify", "content")
        updated = update_note(note.id, note_type="handover")
        assert updated.note_type == "handover"

    def test_delete_note(self):
        note = create_note(self.proj.id, "Deletable", "bye")
        assert delete_note(note.id) is True
        assert get_note(note.id) is None

    def test_delete_missing_note_returns_false(self):
        assert delete_note("nope") is False


# ── Documents & Chunks ─────────────────────────────────────────────────────────

class TestDocumentsAndChunks:
    def setup_method(self):
        self.proj = create_project("doc-proj")

    def test_create_document(self):
        doc = create_document(self.proj.id, "README", source_type="file",
                              source_ref="/path/to/readme.md")
        assert doc.title == "README"
        assert doc.source_type == "file"
        fetched = get_document(doc.id)
        assert fetched.id == doc.id

    def test_list_documents(self):
        create_document(self.proj.id, "Doc A")
        create_document(self.proj.id, "Doc B")
        docs = list_documents(self.proj.id)
        assert len(docs) == 2

    def test_add_chunks(self):
        doc = create_document(self.proj.id, "Chunked doc")
        chunks = add_chunks(doc.id, self.proj.id, ["chunk one", "chunk two", "chunk three"])
        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1

    def test_get_chunks_in_order(self):
        doc = create_document(self.proj.id, "Ordered doc")
        add_chunks(doc.id, self.proj.id, ["first", "second", "third"])
        fetched = get_chunks(doc.id)
        assert len(fetched) == 3
        assert [c.chunk_text for c in fetched] == ["first", "second", "third"]


# ── Entity Links ───────────────────────────────────────────────────────────────

class TestEntityLinks:
    def setup_method(self):
        self.proj = create_project("links-proj")
        self.task = create_task(self.proj.id, "Linked task")
        self.dec = create_decision(self.proj.id, "Linked decision", "Use X")

    def test_create_link(self):
        lnk = create_link(self.proj.id, "task", self.task.id,
                          "implements", "decision", self.dec.id)
        assert lnk.link_type == "implements"
        assert lnk.from_entity_id == self.task.id
        assert lnk.to_entity_id == self.dec.id

    def test_get_links_from(self):
        create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        links = get_links_for("task", self.task.id, direction="from")
        assert len(links) == 1
        assert links[0].to_entity_id == self.dec.id

    def test_get_links_to(self):
        create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        links = get_links_for("decision", self.dec.id, direction="to")
        assert len(links) == 1
        assert links[0].from_entity_id == self.task.id

    def test_get_links_both_directions(self):
        note = create_note(self.proj.id, "Explains note", "related content")
        create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        create_link(self.proj.id, "note", note.id, "explains", "task", self.task.id)
        links = get_links_for("task", self.task.id, direction="both")
        assert len(links) == 2

    def test_link_deduplication(self):
        create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        links = get_links_for("task", self.task.id)
        assert len(links) == 1

    def test_delete_link(self):
        lnk = create_link(self.proj.id, "task", self.task.id, "implements", "decision", self.dec.id)
        assert delete_link(lnk.id) is True
        links = get_links_for("task", self.task.id)
        assert len(links) == 0


# ── Tags ───────────────────────────────────────────────────────────────────────

class TestTags:
    def setup_method(self):
        self.proj = create_project("tags-proj")
        self.task = create_task(self.proj.id, "Taggable task")

    def test_create_tag(self):
        tag = create_tag(self.proj.id, "frontend")
        assert tag.name == "frontend"

    def test_create_tag_idempotent(self):
        t1 = create_tag(self.proj.id, "backend")
        t2 = create_tag(self.proj.id, "backend")
        assert t1.id == t2.id

    def test_list_tags(self):
        create_tag(self.proj.id, "alpha")
        create_tag(self.proj.id, "beta")
        tags = list_tags(self.proj.id)
        assert len(tags) == 2
        assert [t.name for t in tags] == ["alpha", "beta"]

    def test_tag_entity(self):
        tag = create_tag(self.proj.id, "important")
        tag_entity(tag.id, "task", self.task.id)
        entities = get_entities_by_tag(tag.id)
        assert len(entities) == 1
        assert entities[0]["entity_id"] == self.task.id

    def test_tag_multiple_entities(self):
        tag = create_tag(self.proj.id, "shared")
        dec = create_decision(self.proj.id, "Tagged decision", "D")
        tag_entity(tag.id, "task", self.task.id)
        tag_entity(tag.id, "decision", dec.id)
        entities = get_entities_by_tag(tag.id)
        assert len(entities) == 2

    def test_untag_entity(self):
        tag = create_tag(self.proj.id, "removable")
        tag_entity(tag.id, "task", self.task.id)
        untag_entity(tag.id, "task", self.task.id)
        assert len(get_entities_by_tag(tag.id)) == 0


# ── Working Context ────────────────────────────────────────────────────────────

class TestWorkingContext:
    def setup_method(self):
        self.proj = create_project("ctx-proj", "A context project")

    def test_working_context_structure(self):
        ctx = get_working_context(self.proj.id)
        assert "project" in ctx
        assert "summary" in ctx
        assert "active_tasks" in ctx
        assert "active_decisions" in ctx
        assert "recent_notes" in ctx

    def test_working_context_by_name(self):
        ctx = get_working_context("ctx-proj")
        assert ctx["project"]["name"] == "ctx-proj"

    def test_working_context_includes_summary(self):
        add_summary(self.proj.id, "Project is in early development.", "current")
        ctx = get_working_context(self.proj.id)
        assert ctx["summary"] == "Project is in early development."

    def test_working_context_includes_open_tasks(self):
        create_task(self.proj.id, "Open task", status="open")
        create_task(self.proj.id, "In progress", status="in_progress")
        create_task(self.proj.id, "Done task", status="done")
        ctx = get_working_context(self.proj.id)
        assert len(ctx["active_tasks"]) == 2

    def test_working_context_includes_linked_decisions(self):
        task = create_task(self.proj.id, "Active task")
        dec = create_decision(self.proj.id, "Linked decision", "Use X")
        create_link(self.proj.id, "task", task.id, "implements", "decision", dec.id)
        ctx = get_working_context(self.proj.id)
        linked_ids = [d["id"] for d in ctx["linked_decisions"]]
        assert dec.id in linked_ids

    def test_working_context_nonexistent_project(self):
        ctx = get_working_context("no-such-project")
        assert "error" in ctx

    def test_working_context_empty_project(self):
        ctx = get_working_context(self.proj.id)
        assert ctx["active_tasks"] == []
        assert ctx["active_decisions"] == []
        assert ctx["recent_notes"] == []


# ── Task Notes ─────────────────────────────────────────────────────────────────

class TestTaskNotes:
    def setup_method(self):
        self.proj = create_project("task-notes-proj")
        self.task = create_task(self.proj.id, "Task with notes")

    def test_create_and_get(self):
        note = create_task_note(self.proj.id, self.task.id, "Finding", "Important observation")
        assert note.task_id == self.task.id
        assert note.note_type == "context"
        fetched = get_task_note(note.id)
        assert fetched.title == "Finding"

    def test_create_with_type(self):
        note = create_task_note(self.proj.id, self.task.id, "Bug found", "NPE here", note_type="bug")
        assert note.note_type == "bug"

    def test_list_task_notes(self):
        create_task_note(self.proj.id, self.task.id, "N1", "text1")
        create_task_note(self.proj.id, self.task.id, "N2", "text2", note_type="investigation")
        notes = list_task_notes(self.task.id)
        assert len(notes) == 2

    def test_list_task_notes_filter_type(self):
        create_task_note(self.proj.id, self.task.id, "Context", "ctx")
        create_task_note(self.proj.id, self.task.id, "Bug", "bug", note_type="bug")
        bugs = list_task_notes(self.task.id, note_type="bug")
        assert len(bugs) == 1
        assert bugs[0].title == "Bug"

    def test_task_notes_isolated_from_other_tasks(self):
        other_task = create_task(self.proj.id, "Other task")
        create_task_note(self.proj.id, self.task.id, "Mine", "text")
        create_task_note(self.proj.id, other_task.id, "Theirs", "text")
        assert len(list_task_notes(self.task.id)) == 1
        assert len(list_task_notes(other_task.id)) == 1

    def test_update_task_note(self):
        note = create_task_note(self.proj.id, self.task.id, "Old title", "old text")
        updated = update_task_note(note.id, title="New title", note_text="new text")
        assert updated.title == "New title"
        assert updated.note_text == "new text"

    def test_delete_task_note(self):
        note = create_task_note(self.proj.id, self.task.id, "Bye", "gone")
        assert delete_task_note(note.id) is True
        assert get_task_note(note.id) is None

    def test_delete_missing_task_note_returns_false(self):
        assert delete_task_note("nonexistent") is False

    def test_task_deleted_cascades_to_task_notes(self):
        note = create_task_note(self.proj.id, self.task.id, "Cascade test", "should vanish")
        nid = note.id
        delete_task(self.task.id)
        assert get_task_note(nid) is None


# ── Global Notes ───────────────────────────────────────────────────────────────

class TestGlobalNotes:
    def test_create_and_get(self):
        note = create_global_note("Style guide", "Always use type hints.")
        assert note.note_type == "context"
        fetched = get_global_note(note.id)
        assert fetched.title == "Style guide"
        assert fetched.note_text == "Always use type hints."

    def test_create_with_type(self):
        note = create_global_note("Coding standard", "PEP 8.", note_type="implementation")
        assert note.note_type == "implementation"

    def test_list_global_notes(self):
        create_global_note("Note A", "text A")
        create_global_note("Note B", "text B")
        notes = list_global_notes()
        assert len(notes) == 2

    def test_list_global_notes_filter_type(self):
        create_global_note("Philosophy", "Keep it simple.", note_type="context")
        create_global_note("Bug pattern", "Check nulls.", note_type="bug")
        bugs = list_global_notes(note_type="bug")
        assert len(bugs) == 1
        assert bugs[0].title == "Bug pattern"

    def test_global_notes_not_project_scoped(self):
        """Global notes are visible regardless of active project."""
        create_global_note("Cross-project rule", "Always write tests.")
        notes = list_global_notes()
        assert any(n.title == "Cross-project rule" for n in notes)

    def test_update_global_note(self):
        note = create_global_note("Draft rule", "Initial text.")
        updated = update_global_note(note.id, note_text="Refined text.")
        assert updated.note_text == "Refined text."

    def test_update_global_note_type(self):
        note = create_global_note("Reclassify", "content")
        updated = update_global_note(note.id, note_type="handover")
        assert updated.note_type == "handover"

    def test_delete_global_note(self):
        note = create_global_note("Temporary", "Will be removed.")
        assert delete_global_note(note.id) is True
        assert get_global_note(note.id) is None

    def test_delete_missing_global_note_returns_false(self):
        assert delete_global_note("no-such-note") is False

    def test_working_context_includes_global_notes(self):
        """Global notes appear in get_working_context regardless of project."""
        proj = create_project("ctx-global-proj")
        create_global_note("Global standard", "Write clean code.")
        ctx = get_working_context(proj.id)
        assert len(ctx["global_notes"]) >= 1
        titles = [n["title"] for n in ctx["global_notes"]]
        assert "Global standard" in titles
