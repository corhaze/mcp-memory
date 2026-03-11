"""Tests for FOUNDATION note_type — context load filtering."""

import mcp_memory.db as db


def _setup_project():
    return db.create_project("test-project", "Test project")


class TestFoundationContextFiltering:
    """get_working_context should only return foundation-typed global notes."""

    def test_foundation_notes_included_in_context(self):
        proj = _setup_project()
        db.create_global_note("Code quality", "Standards text", note_type="foundation")
        ctx = db.get_working_context(proj.id)
        assert len(ctx["global_notes"]) == 1
        assert ctx["global_notes"][0]["note_type"] == "foundation"

    def test_non_foundation_notes_excluded_from_context(self):
        proj = _setup_project()
        db.create_global_note("Investigation note", "Details", note_type="investigation")
        db.create_global_note("Bug note", "Details", note_type="bug")
        db.create_global_note("Context note", "Details", note_type="context")
        ctx = db.get_working_context(proj.id)
        assert len(ctx["global_notes"]) == 0

    def test_mixed_types_only_foundation_returned(self):
        proj = _setup_project()
        db.create_global_note("Foundation 1", "Text", note_type="foundation")
        db.create_global_note("Impl note", "Text", note_type="implementation")
        db.create_global_note("Foundation 2", "Text", note_type="foundation")
        db.create_global_note("Bug note", "Text", note_type="bug")
        ctx = db.get_working_context(proj.id)
        assert len(ctx["global_notes"]) == 2
        titles = {n["title"] for n in ctx["global_notes"]}
        assert titles == {"Foundation 1", "Foundation 2"}

    def test_non_foundation_still_searchable(self):
        _setup_project()
        db.create_global_note("Important impl", "Details about impl", note_type="implementation")
        # list_global_notes without filter returns all
        all_notes = db.list_global_notes()
        assert len(all_notes) == 1
        assert all_notes[0].note_type == "implementation"

    def test_non_foundation_still_in_unfiltered_list(self):
        _setup_project()
        db.create_global_note("Foundation", "Text", note_type="foundation")
        db.create_global_note("Context", "Text", note_type="context")
        all_notes = db.list_global_notes()
        assert len(all_notes) == 2
        foundation_only = db.list_global_notes(note_type="foundation")
        assert len(foundation_only) == 1

    def test_context_includes_full_note_text(self):
        proj = _setup_project()
        db.create_global_note("Standards", "Full text here", note_type="foundation")
        ctx = db.get_working_context(proj.id)
        assert ctx["global_notes"][0]["note_text"] == "Full text here"
