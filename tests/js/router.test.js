/* tests/js/router.test.js — Unit tests for mcp_memory/ui/js/router.js */

// router.js reads location.pathname and calls history.pushState/replaceState
// at call time (not at import time), so we can stub them per-test.

vi.stubGlobal('location', { pathname: '/' });
vi.stubGlobal('history', { pushState: vi.fn(), replaceState: vi.fn() });

import {
    parsePath,
    setPath,
    setGlobalPath,
    getTabFromPath,
    VALID_TABS,
    VALID_GLOBAL_TABS,
} from '../../mcp_memory/ui/js/router.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe('VALID_TABS', () => {
    it('contains the expected tab names', () => {
        expect(VALID_TABS).toEqual(['summary', 'tasks', 'board', 'decisions', 'notes', 'timeline', 'search']);
    });
});

describe('VALID_GLOBAL_TABS', () => {
    it('contains the expected global tab names', () => {
        expect(VALID_GLOBAL_TABS).toEqual(['notes']);
    });
});

// ---------------------------------------------------------------------------
// parsePath()
// ---------------------------------------------------------------------------

describe('parsePath()', () => {
    afterEach(() => {
        // Reset to root between tests
        location.pathname = '/';
    });

    it('returns null for root path', () => {
        location.pathname = '/';
        expect(parsePath()).toBeNull();
    });

    it('returns null for empty path', () => {
        location.pathname = '';
        expect(parsePath()).toBeNull();
    });

    it('returns global/notes for /global with no tab', () => {
        location.pathname = '/global';
        expect(parsePath()).toEqual({ namespace: 'global', tab: 'notes' });
    });

    it('returns global/notes for /global/notes', () => {
        location.pathname = '/global/notes';
        expect(parsePath()).toEqual({ namespace: 'global', tab: 'notes' });
    });

    it('falls back to "notes" for /global/invalid-tab', () => {
        location.pathname = '/global/invalid-tab';
        expect(parsePath()).toEqual({ namespace: 'global', tab: 'notes' });
    });

    it('returns project/summary for a bare project name', () => {
        location.pathname = '/my-project';
        expect(parsePath()).toEqual({ namespace: 'project', projectName: 'my-project', tab: 'summary' });
    });

    it('returns project/tasks for /my-project/tasks', () => {
        location.pathname = '/my-project/tasks';
        expect(parsePath()).toEqual({ namespace: 'project', projectName: 'my-project', tab: 'tasks' });
    });

    it('returns project/decisions for /my-project/decisions', () => {
        location.pathname = '/my-project/decisions';
        expect(parsePath()).toEqual({ namespace: 'project', projectName: 'my-project', tab: 'decisions' });
    });

    it('URL-decodes percent-encoded project names', () => {
        location.pathname = '/my%20project/tasks';
        expect(parsePath()).toEqual({ namespace: 'project', projectName: 'my project', tab: 'tasks' });
    });

    it('falls back to "summary" for an invalid tab', () => {
        location.pathname = '/my-project/invalid-tab';
        expect(parsePath()).toEqual({ namespace: 'project', projectName: 'my-project', tab: 'summary' });
    });

    it('accepts all valid tab names', () => {
        for (const tab of VALID_TABS) {
            location.pathname = `/my-project/${tab}`;
            expect(parsePath().tab).toBe(tab);
        }
    });

    it('returns task namespace for /{project}/tasks/{taskId}', () => {
        location.pathname = '/my-project/tasks/abc-123';
        expect(parsePath()).toEqual({ namespace: 'task', projectName: 'my-project', taskId: 'abc-123' });
    });

    it('URL-decodes project name in task detail route', () => {
        location.pathname = '/my%20project/tasks/abc-123';
        expect(parsePath()).toEqual({ namespace: 'task', projectName: 'my project', taskId: 'abc-123' });
    });
});

// ---------------------------------------------------------------------------
// setTaskPath()
// ---------------------------------------------------------------------------

describe('setTaskPath()', () => {
    let pushState;
    let replaceState;

    beforeEach(() => {
        pushState = vi.fn();
        replaceState = vi.fn();
        vi.stubGlobal('history', { pushState, replaceState });
    });

    it('calls history.pushState with /{project}/tasks/{taskId}', async () => {
        const { setTaskPath } = await import('../../mcp_memory/ui/js/router.js');
        setTaskPath('my-project', 'abc-123');
        expect(pushState).toHaveBeenCalledOnce();
        const [state, , url] = pushState.mock.calls[0];
        expect(url).toBe('/my-project/tasks/abc-123');
        expect(state).toMatchObject({ namespace: 'task', projectName: 'my-project', taskId: 'abc-123' });
    });
});

// ---------------------------------------------------------------------------
// setPath()
// ---------------------------------------------------------------------------

describe('setPath()', () => {
    let pushState;
    let replaceState;

    beforeEach(() => {
        pushState = vi.fn();
        replaceState = vi.fn();
        vi.stubGlobal('history', { pushState, replaceState });
    });

    it('calls history.pushState with the encoded URL', () => {
        setPath('my-project', 'tasks');
        expect(pushState).toHaveBeenCalledOnce();
        const [state, , url] = pushState.mock.calls[0];
        expect(url).toBe('/my-project/tasks');
        expect(state).toMatchObject({ namespace: 'project', projectName: 'my-project', tab: 'tasks' });
    });

    it('percent-encodes spaces in project names', () => {
        setPath('my project', 'summary');
        const [, , url] = pushState.mock.calls[0];
        expect(url).toBe('/my%20project/summary');
    });

    it('calls history.replaceState when replace=true', () => {
        setPath('my-project', 'notes', true);
        expect(replaceState).toHaveBeenCalledOnce();
        expect(pushState).not.toHaveBeenCalled();
    });

    it('calls history.pushState when replace=false (default)', () => {
        setPath('my-project', 'board');
        expect(pushState).toHaveBeenCalledOnce();
        expect(replaceState).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// setGlobalPath()
// ---------------------------------------------------------------------------

describe('setGlobalPath()', () => {
    let pushState;
    let replaceState;

    beforeEach(() => {
        pushState = vi.fn();
        replaceState = vi.fn();
        vi.stubGlobal('history', { pushState, replaceState });
    });

    it('calls history.pushState with /global/<tab>', () => {
        setGlobalPath('notes');
        expect(pushState).toHaveBeenCalledOnce();
        const [state, , url] = pushState.mock.calls[0];
        expect(url).toBe('/global/notes');
        expect(state).toMatchObject({ namespace: 'global', tab: 'notes' });
    });

    it('calls history.replaceState when replace=true', () => {
        setGlobalPath('notes', true);
        expect(replaceState).toHaveBeenCalledOnce();
        expect(pushState).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// getTabFromPath()
// ---------------------------------------------------------------------------

describe('getTabFromPath()', () => {
    afterEach(() => {
        location.pathname = '/';
    });

    it('returns "summary" when path is root (parsePath returns null)', () => {
        location.pathname = '/';
        expect(getTabFromPath()).toBe('summary');
    });

    it('returns the tab from the current path', () => {
        location.pathname = '/my-project/decisions';
        expect(getTabFromPath()).toBe('decisions');
    });
});
