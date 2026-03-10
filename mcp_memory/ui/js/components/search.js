/* components/search.js — Semantic search coordination and rendering */

import { els } from '../dom.js';
import { state } from '../state.js';
import { renderTaskItem } from './tasks.js';
import { renderDecisionItem } from './decisions.js';
import { renderNoteItem } from './notes.js';
import { esc } from '../utils.js';

function getProjectName(projectId) {
    const proj = state.projects.find(p => p.id === projectId);
    return proj ? proj.name : 'Unknown Project';
}

function groupResultsByProject(results) {
    const grouped = {};
    results.forEach(item => {
        const projectId = item.project_id;
        if (!grouped[projectId]) {
            grouped[projectId] = {
                projectId,
                projectName: getProjectName(projectId),
                items: []
            };
        }
        grouped[projectId].items.push(item);
    });
    return Object.values(grouped).sort((a, b) =>
        a.projectName.localeCompare(b.projectName)
    );
}

function projectHeader(name) {
    return `<li class="project-section-header">${esc(name)}</li>`;
}

export function renderSearch(handlers = {}) {
    const rs = state.searchResults;
    if (!rs) return;

    const hasTasks = rs.tasks && rs.tasks.length > 0;
    const hasDecisions = rs.decisions && rs.decisions.length > 0;
    const hasNotes = rs.notes && rs.notes.length > 0;

    els.searchTasksList.parentElement.classList.toggle('hidden', !hasTasks);
    els.searchDecisionsList.parentElement.classList.toggle('hidden', !hasDecisions);
    els.searchNotesList.parentElement.classList.toggle('hidden', !hasNotes);

    if (!hasTasks && !hasDecisions && !hasNotes) {
        els.searchEmptyState.classList.remove('hidden');
    } else {
        els.searchEmptyState.classList.add('hidden');
    }

    if (hasTasks) {
        if (state.searchMode === 'all') {
            const groups = groupResultsByProject(rs.tasks);
            els.searchTasksList.innerHTML = groups.map(group =>
                group.items.map((task, i) =>
                    (i === 0 ? projectHeader(group.projectName) : '') + renderTaskItem(task, 0)
                ).join('')
            ).join('');
        } else {
            els.searchTasksList.innerHTML = rs.tasks.map(t => renderTaskItem(t, 0)).join('');
        }
        if (handlers.onTasksRender) handlers.onTasksRender(els.searchTasksList);
    }

    if (hasDecisions) {
        if (state.searchMode === 'all') {
            const groups = groupResultsByProject(rs.decisions);
            els.searchDecisionsList.innerHTML = groups.map(group =>
                group.items.map((d, i) =>
                    (i === 0 ? projectHeader(group.projectName) : '') + renderDecisionItem(d)
                ).join('')
            ).join('');
        } else {
            els.searchDecisionsList.innerHTML = rs.decisions.map(renderDecisionItem).join('');
        }
        if (handlers.onDecisionsRender) handlers.onDecisionsRender(els.searchDecisionsList);
    }

    if (hasNotes) {
        if (state.searchMode === 'all') {
            const groups = groupResultsByProject(rs.notes);
            els.searchNotesList.innerHTML = groups.map(group =>
                group.items.map((n, i) =>
                    (i === 0 ? projectHeader(group.projectName) : '') + renderNoteItem(n)
                ).join('')
            ).join('');
        } else {
            els.searchNotesList.innerHTML = rs.notes.map(renderNoteItem).join('');
        }
        if (handlers.onNotesRender) handlers.onNotesRender(els.searchNotesList);
    }
}
