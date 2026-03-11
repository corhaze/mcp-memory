/* tests/js/components/search.test.js — Unit tests for renderResultItem */

vi.mock('../../../mcp_memory/ui/js/dom.js', () => ({ els: {}, default: () => null }));
vi.mock('../../../mcp_memory/ui/js/state.js', () => ({ state: { searchResults: null } }));

import { renderResultItem } from '../../../mcp_memory/ui/js/components/search.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeResult(overrides = {}) {
    return {
        entity_type: 'task',
        id: 'task-abc',
        score: 0.85,
        title: 'My task',
        status: 'open',
        note_type: null,
        next_action: null,
        project_name: 'my-project',
        task_id: null,
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// renderResultItem()
// ---------------------------------------------------------------------------

describe('renderResultItem()', () => {
    it('renders the title escaped', () => {
        const html = renderResultItem(makeResult({ title: '<script>xss</script>' }));
        expect(html).toContain('&lt;script&gt;xss&lt;/script&gt;');
        expect(html).not.toContain('<script>');
    });

    it('renders the entity_type badge', () => {
        const html = renderResultItem(makeResult({ entity_type: 'decision' }));
        expect(html).toContain('badge-decision');
        expect(html).toContain('decision');
    });

    it('renders the score as a percentage', () => {
        const html = renderResultItem(makeResult({ score: 0.75 }));
        expect(html).toContain('75%');
    });

    it('renders status badge when status is present', () => {
        const html = renderResultItem(makeResult({ status: 'done' }));
        expect(html).toContain('badge-done');
        expect(html).toContain('>done<');
    });

    it('omits status badge when status is absent', () => {
        const html = renderResultItem(makeResult({ status: null }));
        expect(html).not.toContain('status-badge');
    });

    it('renders note_type pill when present', () => {
        const html = renderResultItem(makeResult({ entity_type: 'note', note_type: 'bug', status: null }));
        expect(html).toContain('note-type-pill');
        expect(html).toContain('bug');
    });

    it('renders next_action hint when present', () => {
        const html = renderResultItem(makeResult({ next_action: 'Fix the tests' }));
        expect(html).toContain('Fix the tests');
        expect(html).toContain('search-result-next-action');
    });

    it('includes data-entity-id attribute', () => {
        const html = renderResultItem(makeResult({ id: 'task-abc' }));
        expect(html).toContain('data-entity-id="task-abc"');
    });

    it('includes data-entity-type attribute', () => {
        const html = renderResultItem(makeResult({ entity_type: 'decision' }));
        expect(html).toContain('data-entity-type="decision"');
    });

    it('includes data-project-name attribute', () => {
        const html = renderResultItem(makeResult({ project_name: 'my-project' }));
        expect(html).toContain('data-project-name="my-project"');
    });

    it('includes data-task-id for task_note results', () => {
        const html = renderResultItem(makeResult({ entity_type: 'task_note', task_id: 'parent-task-1' }));
        expect(html).toContain('data-task-id="parent-task-1"');
    });

    it('has search-result-item--clickable class when entity has a nav target', () => {
        const html = renderResultItem(makeResult({ entity_type: 'task' }));
        expect(html).toContain('search-result-item--clickable');
    });

    it('does not have clickable class for chunk entity type', () => {
        const html = renderResultItem(makeResult({ entity_type: 'chunk' }));
        expect(html).not.toContain('search-result-item--clickable');
    });
});
