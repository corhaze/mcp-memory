/* tests/js/utils.test.js — Unit tests for mcp_memory/ui/js/utils.js */

import {
    esc,
    statusEmoji,
    formatTime,
    renderNoteTypeOptions,
    renderStatusOptions,
    entityNavTarget,
    STATUS_OPTIONS,
    NOTE_TYPES,
} from '../../mcp_memory/ui/js/utils.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe('STATUS_OPTIONS', () => {
    it('contains exactly the five valid statuses in order', () => {
        expect(STATUS_OPTIONS).toEqual(['open', 'in_progress', 'blocked', 'done', 'cancelled']);
    });
});

describe('NOTE_TYPES', () => {
    it('contains exactly the five valid note types in order', () => {
        expect(NOTE_TYPES).toEqual(['context', 'investigation', 'implementation', 'bug', 'handover']);
    });
});

// ---------------------------------------------------------------------------
// esc()
// ---------------------------------------------------------------------------

describe('esc()', () => {
    it('returns empty string for null', () => {
        expect(esc(null)).toBe('');
    });

    it('returns empty string for undefined', () => {
        expect(esc(undefined)).toBe('');
    });

    it('returns empty string for empty string', () => {
        expect(esc('')).toBe('');
    });

    it('escapes ampersands', () => {
        expect(esc('a & b')).toBe('a &amp; b');
    });

    it('escapes less-than', () => {
        expect(esc('<script>')).toBe('&lt;script&gt;');
    });

    it('escapes greater-than', () => {
        expect(esc('1 > 0')).toBe('1 &gt; 0');
    });

    it('escapes double quotes', () => {
        expect(esc('"hello"')).toBe('&quot;hello&quot;');
    });

    it('escapes all special characters in one string', () => {
        expect(esc('<a href="x&y">test</a>')).toBe('&lt;a href=&quot;x&amp;y&quot;&gt;test&lt;/a&gt;');
    });

    it('passes through a clean string unchanged', () => {
        expect(esc('hello world')).toBe('hello world');
    });

    it('coerces numbers to string', () => {
        expect(esc(42)).toBe('42');
    });

    it('does not double-escape already-escaped strings (by design)', () => {
        // esc() is not idempotent — calling it twice escapes the & in &amp;
        expect(esc('&amp;')).toBe('&amp;amp;');
    });
});

// ---------------------------------------------------------------------------
// statusEmoji()
// ---------------------------------------------------------------------------

describe('statusEmoji()', () => {
    it('returns ○ for open', () => expect(statusEmoji('open')).toBe('○'));
    it('returns ◑ for in_progress', () => expect(statusEmoji('in_progress')).toBe('◑'));
    it('returns ⊗ for blocked', () => expect(statusEmoji('blocked')).toBe('⊗'));
    it('returns ✓ for done', () => expect(statusEmoji('done')).toBe('✓'));
    it('returns ✕ for cancelled', () => expect(statusEmoji('cancelled')).toBe('✕'));

    it('returns ○ for unknown status', () => {
        expect(statusEmoji('whatever')).toBe('○');
    });

    it('returns ○ for undefined', () => {
        expect(statusEmoji(undefined)).toBe('○');
    });
});

// ---------------------------------------------------------------------------
// formatTime()
// ---------------------------------------------------------------------------

describe('formatTime()', () => {
    const BASE = '2024-06-15T12:00:00.000Z';

    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date(BASE));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns empty string for null', () => {
        expect(formatTime(null)).toBe('');
    });

    it('returns empty string for undefined', () => {
        expect(formatTime(undefined)).toBe('');
    });

    it('returns "just now" for a timestamp 30 seconds ago', () => {
        expect(formatTime('2024-06-15T11:59:30.000Z')).toBe('just now');
    });

    it('returns "just now" for a timestamp exactly 0 minutes ago', () => {
        expect(formatTime(BASE)).toBe('just now');
    });

    it('returns "Xm ago" for 5 minutes ago', () => {
        expect(formatTime('2024-06-15T11:55:00.000Z')).toBe('5m ago');
    });

    it('returns "Xm ago" for 59 minutes ago', () => {
        expect(formatTime('2024-06-15T11:01:00.000Z')).toBe('59m ago');
    });

    it('returns "Xh ago" for 2 hours ago', () => {
        expect(formatTime('2024-06-15T10:00:00.000Z')).toBe('2h ago');
    });

    it('returns "Xh ago" for 23 hours ago', () => {
        expect(formatTime('2024-06-14T13:00:00.000Z')).toBe('23h ago');
    });

    it('returns "Xd ago" for 3 days ago', () => {
        expect(formatTime('2024-06-12T12:00:00.000Z')).toBe('3d ago');
    });

    it('returns "Xd ago" for 6 days ago', () => {
        expect(formatTime('2024-06-09T12:00:00.000Z')).toBe('6d ago');
    });

    it('returns a formatted date for 7+ days ago', () => {
        const result = formatTime('2024-06-01T12:00:00.000Z');
        // toLocaleDateString output varies by locale; check it's not a relative string
        expect(result).not.toMatch(/ago|just now/);
        expect(result.length).toBeGreaterThan(0);
    });

    it('returns "Invalid Date" for an unparseable string (catch is unreachable in modern V8)', () => {
        // new Date('not-a-date') returns Invalid Date rather than throwing,
        // so NaN arithmetic causes all diffMins comparisons to be false and
        // toLocaleDateString() is called on Invalid Date, returning 'Invalid Date'.
        expect(formatTime('not-a-date')).toBe('Invalid Date');
    });
});

// ---------------------------------------------------------------------------
// renderNoteTypeOptions()
// ---------------------------------------------------------------------------

describe('renderNoteTypeOptions()', () => {
    it('renders an <option> for each of the 5 note types', () => {
        const html = renderNoteTypeOptions('context');
        const matches = html.match(/<option/g);
        expect(matches).toHaveLength(5);
    });

    it('marks the current type as selected', () => {
        const html = renderNoteTypeOptions('bug');
        expect(html).toContain('<option value="bug" selected>bug</option>');
    });

    it('does not mark other types as selected', () => {
        const html = renderNoteTypeOptions('bug');
        for (const type of NOTE_TYPES.filter(t => t !== 'bug')) {
            expect(html).toContain(`<option value="${type}" >${type}</option>`);
        }
    });

    it('selects nothing when current is null', () => {
        const html = renderNoteTypeOptions(null);
        expect(html).not.toContain('selected');
    });

    it('selects nothing when current is undefined', () => {
        const html = renderNoteTypeOptions(undefined);
        expect(html).not.toContain('selected');
    });

    it('selects nothing when current does not match any type', () => {
        const html = renderNoteTypeOptions('unknown');
        expect(html).not.toContain('selected');
    });
});

// ---------------------------------------------------------------------------
// renderStatusOptions()
// ---------------------------------------------------------------------------

describe('renderStatusOptions()', () => {
    it('renders an <option> for each of the 5 statuses', () => {
        const html = renderStatusOptions('open');
        const matches = html.match(/<option/g);
        expect(matches).toHaveLength(5);
    });

    it('marks the current status as selected', () => {
        const html = renderStatusOptions('done');
        expect(html).toContain('<option value="done" selected>done</option>');
    });

    it('does not mark other statuses as selected', () => {
        const html = renderStatusOptions('done');
        for (const status of STATUS_OPTIONS.filter(s => s !== 'done')) {
            expect(html).toContain(`<option value="${status}" >${status}</option>`);
        }
    });

    it('selects nothing when current is null', () => {
        const html = renderStatusOptions(null);
        expect(html).not.toContain('selected');
    });
});

// ---------------------------------------------------------------------------
// entityNavTarget()
// ---------------------------------------------------------------------------

describe('entityNavTarget()', () => {
    it('returns tasks tab and task anchor for task entity', () => {
        const result = { entity_type: 'task', id: 'abc123', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toEqual({
            projectName: 'my-proj',
            tab: 'tasks',
            anchor: 'task-abc123',
        });
    });

    it('returns decisions tab and decision anchor for decision entity', () => {
        const result = { entity_type: 'decision', id: 'def456', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toEqual({
            projectName: 'my-proj',
            tab: 'decisions',
            anchor: 'decision-def456',
        });
    });

    it('returns notes tab and note anchor for note entity', () => {
        const result = { entity_type: 'note', id: 'ghi789', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toEqual({
            projectName: 'my-proj',
            tab: 'notes',
            anchor: 'note-ghi789',
        });
    });

    it('returns tasks tab and task anchor for task_note (navigate to parent task)', () => {
        const result = { entity_type: 'task_note', id: 'tn1', task_id: 'parent1', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toEqual({
            projectName: 'my-proj',
            tab: 'tasks',
            anchor: 'task-parent1',
        });
    });

    it('returns null projectName for global_note', () => {
        const result = { entity_type: 'global_note', id: 'gn1', project_name: 'irrelevant' };
        const target = entityNavTarget(result);
        expect(target.projectName).toBeNull();
        expect(target.tab).toBe('notes');
        expect(target.anchor).toBe('global-note-gn1');
    });

    it('returns null for chunk (no specific anchor target)', () => {
        const result = { entity_type: 'chunk', id: 'ch1', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toBeNull();
    });

    it('returns null for unknown entity type', () => {
        const result = { entity_type: 'unknown', id: 'x', project_name: 'my-proj' };
        expect(entityNavTarget(result)).toBeNull();
    });
});
