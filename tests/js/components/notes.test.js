/* tests/js/components/notes.test.js — Unit tests for renderNoteItem */

vi.mock('../../../mcp_memory/ui/js/dom.js', () => ({ els: {}, default: () => null }));

// vi.mock is hoisted — use vi.hoisted() so mockState is defined before the factory runs.
const mockState = vi.hoisted(() => ({ editingNoteId: null, noteFilter: '' }));
vi.mock('../../../mcp_memory/ui/js/state.js', () => ({ state: mockState }));

vi.stubGlobal('marked', { parse: s => `<p>${s}</p>` });

import { renderNoteItem } from '../../../mcp_memory/ui/js/components/notes.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeNote(overrides = {}) {
    return {
        id: 'note-001',
        title: 'Test note',
        note_type: 'context',
        note_text: 'Some content.',
        created_at: '2024-01-10T10:00:00Z',
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// renderNoteItem()
// ---------------------------------------------------------------------------

describe('renderNoteItem()', () => {
    beforeEach(() => {
        mockState.editingNoteId = null;
    });

    it('renders the note title escaped', () => {
        const html = renderNoteItem(makeNote({ title: '<b>Bold</b>' }));
        expect(html).toContain('&lt;b&gt;Bold&lt;/b&gt;');
        expect(html).not.toContain('<b>Bold</b>');
    });

    it('renders the note type pill with the correct class', () => {
        const html = renderNoteItem(makeNote({ note_type: 'bug' }));
        expect(html).toContain('note-type-bug');
        expect(html).toContain('>bug<');
    });

    it('renders note_text through marked.parse', () => {
        const html = renderNoteItem(makeNote({ note_text: 'Hello world' }));
        expect(html).toContain('<p>Hello world</p>');
    });

    it('renders edit and delete buttons with the note id', () => {
        const html = renderNoteItem(makeNote({ id: 'note-001' }));
        expect(html).toContain('data-id="note-001"');
        expect(html).toContain('class="icon-btn edit-note"');
        expect(html).toContain('class="icon-btn danger delete-note"');
    });

    it('shows note-view-content and hides edit form when not editing', () => {
        mockState.editingNoteId = null;
        const html = renderNoteItem(makeNote({ id: 'note-001' }));
        expect(html).toContain('note-edit-form hidden');
        expect(html).toContain('note-view-content"');
        expect(html).not.toContain('note-view-content hidden');
    });

    it('shows edit form and hides note-view-content when editing', () => {
        mockState.editingNoteId = 'note-001';
        const html = renderNoteItem(makeNote({ id: 'note-001' }));
        expect(html).not.toContain('note-edit-form hidden');
        expect(html).toContain('note-view-content hidden');
    });

    it('shows edit form based on state.editingNoteId matching the note id', () => {
        mockState.editingNoteId = 'note-999'; // different note
        const html = renderNoteItem(makeNote({ id: 'note-001' }));
        expect(html).toContain('note-edit-form hidden');
    });

    it('renders the edit form with the correct note id', () => {
        const html = renderNoteItem(makeNote({ id: 'note-abc' }));
        expect(html).toContain('data-note-id="note-abc"');
    });
});
