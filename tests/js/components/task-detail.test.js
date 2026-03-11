/* tests/js/components/task-detail.test.js — Unit tests for renderTaskDetail */

vi.mock('../../../mcp_memory/ui/js/dom.js', () => ({ els: {}, default: () => null }));
vi.mock('../../../mcp_memory/ui/js/state.js', () => ({ state: {} }));

// marked is a CDN global in the browser; stub it before importing the component.
vi.stubGlobal('marked', { parse: s => `<p>${s}</p>` });

import { renderTaskDetail, renderSubtaskExpansion } from '../../../mcp_memory/ui/js/components/task-detail.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTask(overrides = {}) {
    return {
        id: 'task-001',
        title: 'My Task',
        status: 'in_progress',
        description: 'Some description',
        urgent: false,
        complex: false,
        next_action: null,
        assigned_agent: null,
        parent_task_id: null,
        blocked_by_task_id: null,
        due_at: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        completed_at: null,
        subtasks: [],
        notes: [],
        events: [],
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// renderTaskDetail()
// ---------------------------------------------------------------------------

describe('renderTaskDetail()', () => {
    it('renders the task title escaped', () => {
        const html = renderTaskDetail(makeTask({ title: '<b>Evil</b>' }));
        expect(html).toContain('&lt;b&gt;Evil&lt;/b&gt;');
        expect(html).not.toContain('<b>Evil</b>');
    });

    it('renders the status badge', () => {
        const html = renderTaskDetail(makeTask({ status: 'in_progress' }));
        expect(html).toContain('badge-in_progress');
        expect(html).toContain('in_progress');
    });

    it('renders description via marked.parse', () => {
        const html = renderTaskDetail(makeTask({ description: 'Hello world' }));
        expect(html).toContain('<p>Hello world</p>');
    });

    it('renders next_action when present', () => {
        const html = renderTaskDetail(makeTask({ next_action: 'Fix the bug' }));
        expect(html).toContain('Fix the bug');
    });

    it('omits next_action section when absent', () => {
        const html = renderTaskDetail(makeTask({ next_action: null }));
        expect(html).not.toContain('next-action');
    });

    it('renders subtasks list when subtasks are present', () => {
        const html = renderTaskDetail(makeTask({
            subtasks: [{ id: 'sub-1', title: 'Subtask One', status: 'open' }],
        }));
        expect(html).toContain('Subtask One');
        expect(html).toContain('badge-open');
    });

    it('renders notes list when notes are present', () => {
        const html = renderTaskDetail(makeTask({
            notes: [{ id: 'note-1', title: 'Note Title', note_text: 'Note body', note_type: 'bug' }],
        }));
        expect(html).toContain('Note Title');
        expect(html).toContain('bug');
    });

    it('renders events list when events are present', () => {
        const html = renderTaskDetail(makeTask({
            events: [{ event_type: 'status_change', event_note: 'moved to done', created_at: '2024-01-10T10:00:00Z' }],
        }));
        expect(html).toContain('status_change');
        expect(html).toContain('moved to done');
    });

    it('renders a back-to-tasks link', () => {
        const html = renderTaskDetail(makeTask());
        expect(html).toContain('task-detail-back');
    });

    it('renders the task id', () => {
        const html = renderTaskDetail(makeTask({ id: 'task-001' }));
        expect(html).toContain('task-001');
    });

    it('renders urgent badge when urgent is true', () => {
        const html = renderTaskDetail(makeTask({ urgent: true }));
        expect(html).toContain('urgent');
    });

    it('omits urgent badge when urgent is false', () => {
        const html = renderTaskDetail(makeTask({ urgent: false }));
        // Only check the specific urgent badge class, not any mention of the word
        expect(html).not.toContain('badge-urgent');
    });

    it('subtask items include data-task-id for click-through navigation', () => {
        const html = renderTaskDetail(makeTask({
            subtasks: [{ id: 'sub-abc', title: 'Sub A', status: 'open' }],
        }));
        expect(html).toContain('data-task-id="sub-abc"');
        expect(html).toContain('task-detail-subtask-link');
    });

    it('renders a parent task link when parent_task_id is present', () => {
        const html = renderTaskDetail(makeTask({ parent_task_id: 'parent-xyz' }));
        expect(html).toContain('data-task-id="parent-xyz"');
        expect(html).toContain('task-detail-parent-link');
    });

    it('omits parent task link when parent_task_id is null', () => {
        const html = renderTaskDetail(makeTask({ parent_task_id: null }));
        expect(html).not.toContain('task-detail-parent-link');
    });

    it('each subtask has an expand toggle button', () => {
        const html = renderTaskDetail(makeTask({
            subtasks: [{ id: 'sub-abc', title: 'Sub A', status: 'open' }],
        }));
        expect(html).toContain('subtask-expand-toggle');
        expect(html).toContain('data-subtask-id="sub-abc"');
    });

    it('each subtask has a hidden expansion container', () => {
        const html = renderTaskDetail(makeTask({
            subtasks: [{ id: 'sub-abc', title: 'Sub A', status: 'open' }],
        }));
        expect(html).toContain('id="subtask-expansion-sub-abc"');
    });
});

// ---------------------------------------------------------------------------
// renderSubtaskExpansion()
// ---------------------------------------------------------------------------

describe('renderSubtaskExpansion()', () => {
    function makeDetail(overrides = {}) {
        return {
            id: 'sub-001',
            title: 'Sub Task',
            status: 'open',
            description: null,
            next_action: null,
            notes: [],
            events: [],
            subtasks: [],
            ...overrides,
        };
    }

    it('renders description when present', () => {
        const html = renderSubtaskExpansion(makeDetail({ description: 'Do the thing' }));
        expect(html).toContain('<p>Do the thing</p>');
    });

    it('omits description when absent', () => {
        const html = renderSubtaskExpansion(makeDetail({ description: null }));
        expect(html).not.toContain('task-detail-description');
    });

    it('renders notes when present', () => {
        const html = renderSubtaskExpansion(makeDetail({
            notes: [{ id: 'n1', title: 'Note A', note_text: 'Body', note_type: 'bug' }],
        }));
        expect(html).toContain('Note A');
        expect(html).toContain('bug');
    });

    it('renders events when present', () => {
        const html = renderSubtaskExpansion(makeDetail({
            events: [{ event_type: 'created', event_note: null, created_at: '2024-01-01T00:00:00Z' }],
        }));
        expect(html).toContain('created');
    });

    it('renders a placeholder when nothing to show', () => {
        const html = renderSubtaskExpansion(makeDetail());
        expect(html).toContain('subtask-expansion-empty');
    });
});
