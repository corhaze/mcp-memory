/* tests/js/components/tasks.test.js — Unit tests for renderTaskNotesHtml and findTask */

vi.mock('../../../mcp_memory/ui/js/dom.js', () => ({ els: {}, default: () => null }));
vi.mock('../../../mcp_memory/ui/js/api.js', () => ({ api: {} }));

// vi.mock is hoisted — use vi.hoisted() so mockState is defined before the factory runs.
const mockState = vi.hoisted(() => ({
    editingTaskId: null,
    expandedTasks: new Set(),
    showAddSubtaskForm: new Set(),
    showAddTaskNoteForm: new Set(),
    taskNotes: {},
    taskFilter: 'open',
}));
vi.mock('../../../mcp_memory/ui/js/state.js', () => ({ state: mockState }));

vi.stubGlobal('marked', { parse: s => `<p>${s}</p>` });

import {
    renderTaskNotesHtml,
    findTask,
    renderTaskItem,
} from '../../../mcp_memory/ui/js/components/tasks.js';

// ---------------------------------------------------------------------------
// renderTaskNotesHtml()
// ---------------------------------------------------------------------------

describe('renderTaskNotesHtml()', () => {
    it('returns empty-state message when notes array is empty', () => {
        const html = renderTaskNotesHtml('task-001', []);
        expect(html).toContain('No notes yet.');
        expect(html).toContain('task-notes-list');
    });

    it('renders one note item per note', () => {
        const notes = [
            { id: 'n1', title: 'First', note_type: 'context', note_text: 'text' },
            { id: 'n2', title: 'Second', note_type: 'bug', note_text: 'more text' },
        ];
        const html = renderTaskNotesHtml('task-001', notes);
        expect(html.match(/task-note-item/g)).toHaveLength(2);
    });

    it('escapes HTML in note titles', () => {
        const notes = [{ id: 'n1', title: '<script>evil</script>', note_type: 'bug', note_text: '' }];
        const html = renderTaskNotesHtml('task-001', notes);
        expect(html).toContain('&lt;script&gt;evil&lt;/script&gt;');
        expect(html).not.toContain('<script>evil</script>');
    });

    it('renders note type pill with correct class', () => {
        const notes = [{ id: 'n1', title: 'Note', note_type: 'investigation', note_text: '' }];
        const html = renderTaskNotesHtml('task-001', notes);
        expect(html).toContain('note-type-investigation');
        expect(html).toContain('>investigation<');
    });

    it('renders delete button with note id and task id as data attributes', () => {
        const notes = [{ id: 'note-abc', title: 'Note', note_type: 'context', note_text: '' }];
        const html = renderTaskNotesHtml('task-xyz', notes);
        expect(html).toContain('data-note-id="note-abc"');
        expect(html).toContain('data-task-id="task-xyz"');
    });

    it('renders note_text through marked.parse', () => {
        const notes = [{ id: 'n1', title: 'Note', note_type: 'context', note_text: 'Hello world' }];
        const html = renderTaskNotesHtml('task-001', notes);
        expect(html).toContain('<p>Hello world</p>');
    });

    it('wraps all notes in a task-notes-list ul', () => {
        const notes = [{ id: 'n1', title: 'Note', note_type: 'context', note_text: '' }];
        const html = renderTaskNotesHtml('task-001', notes);
        expect(html).toMatch(/^<ul class="task-notes-list">/);
        expect(html).toMatch(/<\/ul>$/);
    });
});

// ---------------------------------------------------------------------------
// findTask()
// ---------------------------------------------------------------------------

describe('findTask()', () => {
    const tree = [
        { id: 'a', subtasks: [
            { id: 'b', subtasks: [
                { id: 'c', subtasks: [] },
            ]},
        ]},
        { id: 'd', subtasks: [] },
    ];

    it('finds a top-level task by id', () => {
        expect(findTask('a', tree)).toMatchObject({ id: 'a' });
    });

    it('finds a second top-level task by id', () => {
        expect(findTask('d', tree)).toMatchObject({ id: 'd' });
    });

    it('finds a direct subtask', () => {
        expect(findTask('b', tree)).toMatchObject({ id: 'b' });
    });

    it('finds a deeply nested subtask', () => {
        expect(findTask('c', tree)).toMatchObject({ id: 'c' });
    });

    it('returns null when id does not exist', () => {
        expect(findTask('zzz', tree)).toBeNull();
    });

    it('returns null for an empty task list', () => {
        expect(findTask('a', [])).toBeNull();
    });

    it('handles tasks without a subtasks array', () => {
        const flat = [{ id: 'x' }, { id: 'y' }];
        expect(findTask('y', flat)).toMatchObject({ id: 'y' });
    });
});

// ---------------------------------------------------------------------------
// renderTaskItem() — anchor ID
// ---------------------------------------------------------------------------

function makeTask(overrides = {}) {
    return {
        id: 'task-001',
        title: 'Test task',
        status: 'open',
        urgent: false,
        complex: false,
        description: null,
        next_action: null,
        parent_task_id: null,
        blocked_by_task_id: null,
        assigned_agent: null,
        created_at: '2024-01-10T10:00:00Z',
        subtasks: [],
        ...overrides,
    };
}

describe('renderTaskItem()', () => {
    it('renders the <li> with id="task-{id}" for scroll targeting', () => {
        const html = renderTaskItem(makeTask({ id: 'task-001' }));
        expect(html).toContain('id="task-task-001"');
    });
});
