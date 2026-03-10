/* tests/js/components/decisions.test.js — Unit tests for renderDecisionItem */

vi.mock('../../../mcp_memory/ui/js/dom.js', () => ({ els: {}, default: () => null }));
vi.mock('../../../mcp_memory/ui/js/state.js', () => ({
    state: { decisionFilter: '' },
}));

// marked is a CDN global in the browser; stub it before importing the component.
vi.stubGlobal('marked', { parse: s => `<p>${s}</p>` });

import { renderDecisionItem } from '../../../mcp_memory/ui/js/components/decisions.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeDecision(overrides = {}) {
    return {
        id: 'dec-001',
        title: 'Use SQLite',
        status: 'active',
        decision_text: 'We chose SQLite for simplicity.',
        rationale: null,
        supersedes_decision_id: null,
        created_at: '2024-01-10T10:00:00Z',
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// renderDecisionItem()
// ---------------------------------------------------------------------------

describe('renderDecisionItem()', () => {
    it('renders the decision title escaped', () => {
        const html = renderDecisionItem(makeDecision({ title: '<b>Bold</b>' }));
        expect(html).toContain('&lt;b&gt;Bold&lt;/b&gt;');
        expect(html).not.toContain('<b>Bold</b>');
    });

    it('renders the status badge with correct class', () => {
        const html = renderDecisionItem(makeDecision({ status: 'active' }));
        expect(html).toContain('badge-active');
        expect(html).toContain('>active<');
    });

    it('does NOT add "superseded" class for a non-superseded decision', () => {
        const html = renderDecisionItem(makeDecision({ status: 'active' }));
        // The <li> class attribute should not contain 'superseded'
        const liMatch = html.match(/<li class="([^"]+)"/);
        expect(liMatch[1]).not.toContain('superseded');
    });

    it('adds "superseded" class when status is superseded', () => {
        const html = renderDecisionItem(makeDecision({ status: 'superseded' }));
        const liMatch = html.match(/<li class="([^"]+)"/);
        expect(liMatch[1]).toContain('superseded');
    });

    it('renders edit and delete buttons with the decision id', () => {
        const html = renderDecisionItem(makeDecision({ id: 'dec-001' }));
        expect(html).toContain('data-id="dec-001"');
        expect(html).toContain('class="icon-btn edit-decision"');
        expect(html).toContain('class="icon-btn danger delete-decision"');
    });

    it('renders decision_text through marked.parse', () => {
        const html = renderDecisionItem(makeDecision({ decision_text: 'Hello world' }));
        expect(html).toContain('<p>Hello world</p>');
    });

    it('omits the rationale div when rationale is null', () => {
        const html = renderDecisionItem(makeDecision({ rationale: null }));
        expect(html).not.toContain('decision-rationale');
    });

    it('renders the rationale div when rationale is present', () => {
        const html = renderDecisionItem(makeDecision({ rationale: 'For simplicity.' }));
        expect(html).toContain('class="decision-rationale"');
        expect(html).toContain('For simplicity.');
    });

    it('escapes HTML in rationale', () => {
        const html = renderDecisionItem(makeDecision({ rationale: '<script>evil</script>' }));
        expect(html).toContain('&lt;script&gt;evil&lt;/script&gt;');
    });

    it('omits the supersedes link when supersedes_decision_id is null', () => {
        const html = renderDecisionItem(makeDecision({ supersedes_decision_id: null }));
        expect(html).not.toContain('Supersedes');
    });

    it('renders the supersedes link with truncated id when present', () => {
        const html = renderDecisionItem(makeDecision({ supersedes_decision_id: 'abcdef12-1234-5678-abcd-000000000000' }));
        expect(html).toContain('Supersedes abcdef12');
    });
});
