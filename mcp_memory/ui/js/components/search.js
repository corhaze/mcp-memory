/* components/search.js — Semantic search coordination and rendering */

import { els } from '../dom.js';
import { state } from '../state.js';
import { renderTaskItem } from './tasks.js';
import { esc } from '../utils.js';

// Get project name by ID from state
function getProjectName(projectId) {
    const proj = state.projects.find(p => p.id === projectId);
    return proj ? proj.name : 'Unknown Project';
}

// Group results by project_id and return structured format
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

    // Convert to array and sort by project name
    return Object.values(grouped).sort((a, b) =>
        a.projectName.localeCompare(b.projectName)
    );
}

// Render task item with optional project header
function renderTaskWithHeader(task, depth, projectHeader = null) {
    const header = projectHeader ? `<li class="project-section-header">${esc(projectHeader)}</li>` : '';
    return header + renderTaskItem(task, depth);
}

// Render decision item with optional project header
function renderDecisionWithHeader(decision, projectHeader = null) {
    const header = projectHeader ? `<li class="project-section-header">${esc(projectHeader)}</li>` : '';
    const decisionHtml = `
        <li class="decision-item ${decision.status === 'superseded' ? 'superseded' : ''}">
          <div class="decision-header">
            <span class="decision-title">${esc(decision.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-decision" data-id="${decision.id}">✎</button>
              <button class="icon-btn danger delete-decision" data-id="${decision.id}">✗</button>
            </div>
            <span class="status-badge badge-${decision.status}">${decision.status}</span>
          </div>
          <div class="decision-text">${esc(decision.decision_text)}</div>
          ${decision.rationale ? `<div class="decision-rationale">${esc(decision.rationale)}</div>` : ''}
        </li>
      `;
    return header + decisionHtml;
}

// Render note item with optional project header
function renderNoteWithHeader(note, projectHeader = null) {
    const header = projectHeader ? `<li class="project-section-header">${esc(projectHeader)}</li>` : '';
    const noteHtml = `
        <li class="note-item">
          <div class="note-header">
            <span class="note-title">${esc(note.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-note" data-id="${note.id}">✎</button>
              <button class="icon-btn danger delete-note" data-id="${note.id}">✗</button>
            </div>
            <span class="note-type-pill note-type-${note.note_type}">${note.note_type}</span>
          </div>
          <div class="note-text">${esc(note.note_text)}</div>
        </li>
      `;
    return header + noteHtml;
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

    // Render tasks (flat or grouped)
    if (hasTasks) {
        if (state.searchMode === 'all') {
            const groupedTasks = groupResultsByProject(rs.tasks);
            els.searchTasksList.innerHTML = groupedTasks.map((group, idx) => {
                return group.items.map((task, itemIdx) =>
                    renderTaskWithHeader(task, 0, itemIdx === 0 ? group.projectName : null)
                ).join('');
            }).join('');
        } else {
            els.searchTasksList.innerHTML = rs.tasks.map(t => renderTaskItem(t, 0)).join('');
        }
        if (handlers.onTasksRender) handlers.onTasksRender(els.searchTasksList);
    }

    // Render decisions (flat or grouped)
    if (hasDecisions) {
        if (state.searchMode === 'all') {
            const groupedDecisions = groupResultsByProject(rs.decisions);
            els.searchDecisionsList.innerHTML = groupedDecisions.map((group, idx) => {
                return group.items.map((decision, itemIdx) =>
                    renderDecisionWithHeader(decision, itemIdx === 0 ? group.projectName : null)
                ).join('');
            }).join('');
        } else {
            els.searchDecisionsList.innerHTML = rs.decisions.map(d =>
                renderDecisionWithHeader(d, null)
            ).join('');
        }
        if (handlers.onDecisionsRender) handlers.onDecisionsRender(els.searchDecisionsList);
    }

    // Render notes (flat or grouped)
    if (hasNotes) {
        if (state.searchMode === 'all') {
            const groupedNotes = groupResultsByProject(rs.notes);
            els.searchNotesList.innerHTML = groupedNotes.map((group, idx) => {
                return group.items.map((note, itemIdx) =>
                    renderNoteWithHeader(note, itemIdx === 0 ? group.projectName : null)
                ).join('');
            }).join('');
        } else {
            els.searchNotesList.innerHTML = rs.notes.map(n =>
                renderNoteWithHeader(n, null)
            ).join('');
        }
        if (handlers.onNotesRender) handlers.onNotesRender(els.searchNotesList);
    }
}
