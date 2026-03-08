/* router.js — URL parsing and navigation logic */

import { state } from './state.js';

export const VALID_TABS = ['summary', 'tasks', 'decisions', 'notes', 'timeline', 'search'];

export function parsePath() {
    const parts = location.pathname.replace(/^\//, '').split('/').filter(Boolean);
    if (!parts.length) return null;
    const projectName = decodeURIComponent(parts[0]);
    const tab = VALID_TABS.includes(parts[1]) ? parts[1] : 'summary';
    return { projectName, tab };
}

export function setPath(projectName, tab, replace = false) {
    const url = `/${encodeURIComponent(projectName)}/${tab}`;
    if (replace) {
        history.replaceState({ projectName, tab }, '', url);
    } else {
        history.pushState({ projectName, tab }, '', url);
    }
}

export function getTabFromPath() {
    const route = parsePath();
    return route ? route.tab : 'summary';
}
