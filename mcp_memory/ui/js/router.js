/* router.js — URL parsing and navigation logic */

import { state } from './state.js';

export const VALID_TABS = ['summary', 'tasks', 'board', 'decisions', 'notes', 'timeline', 'search'];
export const VALID_GLOBAL_TABS = ['notes'];

export function parsePath() {
    const parts = location.pathname.replace(/^\//, '').split('/').filter(Boolean);
    if (!parts.length) return null;

    if (parts[0] === 'global') {
        const tab = VALID_GLOBAL_TABS.includes(parts[1]) ? parts[1] : 'notes';
        return { namespace: 'global', tab };
    }

    const projectName = decodeURIComponent(parts[0]);

    // /{project}/tasks/{taskId} — task detail route
    if (parts[1] === 'tasks' && parts[2]) {
        return { namespace: 'task', projectName, taskId: parts[2] };
    }

    const tab = VALID_TABS.includes(parts[1]) ? parts[1] : 'summary';
    return { namespace: 'project', projectName, tab };
}

export function setPath(projectName, tab, replace = false) {
    const url = `/${encodeURIComponent(projectName)}/${tab}`;
    if (replace) {
        history.replaceState({ namespace: 'project', projectName, tab }, '', url);
    } else {
        history.pushState({ namespace: 'project', projectName, tab }, '', url);
    }
}

export function setTaskPath(projectName, taskId, replace = false) {
    const url = `/${encodeURIComponent(projectName)}/tasks/${taskId}`;
    if (replace) {
        history.replaceState({ namespace: 'task', projectName, taskId }, '', url);
    } else {
        history.pushState({ namespace: 'task', projectName, taskId }, '', url);
    }
}

export function setGlobalPath(tab, replace = false) {
    const url = `/global/${tab}`;
    if (replace) {
        history.replaceState({ namespace: 'global', tab }, '', url);
    } else {
        history.pushState({ namespace: 'global', tab }, '', url);
    }
}

export function getTabFromPath() {
    const route = parsePath();
    return route ? route.tab : 'summary';
}
